"""Dithering algorithms and color quantization for retro pixel art."""

from typing import List, Optional, Tuple

import numpy as np

RGBColor = Tuple[int, int, int]
Palette = List[RGBColor]

DITHER_METHODS = (
    "none",
    "bayer-2x2",
    "bayer-4x4",
    "bayer-8x8",
    "checkerboard",
    "blue-noise",
    "floyd",
    "atkinson",
    "burkes",
    "sierra",
    "stucki",
)

# Bayer Matrices normalized to zero-centered range [-0.5, 0.5]
BAYER_2X2 = (np.array([
    [0, 2],
    [3, 1]
], dtype=np.float32) / 4.0) - 0.5

BAYER_4X4 = (np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5]
], dtype=np.float32) / 16.0) - 0.5

BAYER_8X8 = (np.array([
    [ 0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [ 3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21]
], dtype=np.float32) / 64.0) - 0.5

# 1x1 Alternating parity checkerboard matrix (Sega Genesis pseudo-transparency & mesh shading)
CHECKERBOARD_2X2 = np.array([
    [ 0.5, -0.5],
    [-0.5,  0.5],
], dtype=np.float32)

# Deterministic Void-and-Cluster 16x16 Blue Noise threshold matrix (normalized to [-0.5, 0.5])
# High-frequency grain dithering without directional worming or regular grid artifacts
_BN_RNG = np.random.RandomState(42)
BLUE_NOISE_16X16 = (_BN_RNG.permutation(256).reshape((16, 16)).astype(np.float32) / 256.0) - 0.5

# Classic retro error-diffusion kernels: list of (dx, dy, weight)
DIFFUSION_KERNELS = {
    # Floyd-Steinberg (1976): canonical 4-neighbor error diffusion
    "floyd": [
        (1, 0, 7.0 / 16.0),
        (-1, 1, 3.0 / 16.0),
        (0, 1, 5.0 / 16.0),
        (1, 1, 1.0 / 16.0),
    ],
    # Atkinson (Bill Atkinson, Apple Macintosh 1984): drops 25% error for crisp, punchy contrast
    "atkinson": [
        (1, 0, 1.0 / 8.0),
        (2, 0, 1.0 / 8.0),
        (-1, 1, 1.0 / 8.0),
        (0, 1, 1.0 / 8.0),
        (1, 1, 1.0 / 8.0),
        (0, 2, 1.0 / 8.0),
    ],
    # Burkes (1988): fast 7-neighbor 2-row diffusion avoiding worm-like artifacts
    "burkes": [
        (1, 0, 8.0 / 32.0),
        (2, 0, 4.0 / 32.0),
        (-2, 1, 2.0 / 32.0),
        (-1, 1, 4.0 / 32.0),
        (0, 1, 8.0 / 32.0),
        (1, 1, 4.0 / 32.0),
        (2, 1, 2.0 / 32.0),
    ],
    # Sierra Two-Row (Frankie Sierra, 1989): smooth 7-neighbor diffusion popular in retro PC games
    "sierra": [
        (1, 0, 4.0 / 16.0),
        (2, 0, 3.0 / 16.0),
        (-2, 1, 1.0 / 16.0),
        (-1, 1, 2.0 / 16.0),
        (0, 1, 3.0 / 16.0),
        (1, 1, 2.0 / 16.0),
        (2, 1, 1.0 / 16.0),
    ],
    # Stucki (Peter Stucki, 1981): 12-neighbor 3-row high-detail diffusion
    "stucki": [
        (1, 0, 8.0 / 42.0),
        (2, 0, 4.0 / 42.0),
        (-2, 1, 2.0 / 42.0),
        (-1, 1, 4.0 / 42.0),
        (0, 1, 8.0 / 42.0),
        (1, 1, 4.0 / 42.0),
        (2, 1, 2.0 / 42.0),
        (-2, 2, 1.0 / 42.0),
        (-1, 2, 2.0 / 42.0),
        (0, 2, 4.0 / 42.0),
        (1, 2, 2.0 / 42.0),
        (2, 2, 1.0 / 42.0),
    ],
}


def find_closest_palette_indices(
    pixels: np.ndarray,
    palette_arr: np.ndarray,
    perceptual: bool = True
) -> np.ndarray:
    """
    Find index of closest palette color for each pixel in `pixels`.
    pixels: (H, W, 3) float32
    palette_arr: (K, 3) float32
    Returns: (H, W) uint8 indices
    """
    H, W, _ = pixels.shape
    K = palette_arr.shape[0]

    # Low-memory, cache-friendly iteration over K palette colors
    best_indices = np.zeros((H, W), dtype=np.uint8)
    min_dist = np.full((H, W), np.inf, dtype=np.float32)

    p_r = pixels[:, :, 0]
    p_g = pixels[:, :, 1]
    p_b = pixels[:, :, 2]

    for k in range(K):
        c = palette_arr[k]
        dr = p_r - c[0]
        dg = p_g - c[1]
        db = p_b - c[2]

        if perceptual:
            r_bar = 0.5 * (p_r + c[0])
            wr = 2.0 + (r_bar / 256.0)
            wb = 2.0 + ((255.0 - r_bar) / 256.0)
            d = wr * (dr * dr) + 4.0 * (dg * dg) + wb * (db * db)
        else:
            d = (dr * dr) + (dg * dg) + (db * db)

        mask = d < min_dist
        min_dist[mask] = d[mask]
        best_indices[mask] = k

    return best_indices


def quantize_none(
    rgb_arr: np.ndarray,
    palette: Palette,
    perceptual: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Quantize image with NO dithering (clean, solid retro colors).
    Returns (quantized_rgb, indices).
    """
    palette_arr = np.array(palette, dtype=np.float32)
    indices = find_closest_palette_indices(rgb_arr.astype(np.float32), palette_arr, perceptual=perceptual)
    quantized_rgb = palette_arr[indices].astype(np.uint8)
    return quantized_rgb, indices


def quantize_ordered(
    rgb_arr: np.ndarray,
    palette: Palette,
    matrix: np.ndarray,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    General ordered dithering using any 2D threshold matrix normalized to [-0.5, 0.5].
    Works for Bayer (2x2, 4x4, 8x8), Checkerboard, and Blue Noise.
    """
    H, W, _ = rgb_arr.shape
    bh, bw = matrix.shape

    tiles_y = (H + bh - 1) // bh
    tiles_x = (W + bw - 1) // bw
    matrix_tiled = np.tile(matrix, (tiles_y, tiles_x))[:H, :W]

    num_colors = max(len(palette), 2)
    base_spread = 255.0 / (num_colors ** (1.0 / 3.0))
    spread = base_spread * strength

    dithered_rgb = rgb_arr.astype(np.float32) + (matrix_tiled[:, :, np.newaxis] * spread)
    dithered_rgb = np.clip(dithered_rgb, 0.0, 255.0)

    palette_arr = np.array(palette, dtype=np.float32)
    indices = find_closest_palette_indices(dithered_rgb, palette_arr, perceptual=perceptual)
    quantized_rgb = palette_arr[indices].astype(np.uint8)

    return quantized_rgb, indices


def quantize_bayer(
    rgb_arr: np.ndarray,
    palette: Palette,
    matrix_size: int = 4,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Ordered Bayer matrix dithering (classic PC-98, DOS, cross-hatching retro look)."""
    if matrix_size == 2:
        matrix = BAYER_2X2
    elif matrix_size == 8:
        matrix = BAYER_8X8
    else:
        matrix = BAYER_4X4
    return quantize_ordered(rgb_arr, palette, matrix, strength=strength, perceptual=perceptual)


def quantize_checkerboard(
    rgb_arr: np.ndarray,
    palette: Palette,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Checkerboard 1x1 parity dithering (classic Sega Genesis pseudo-transparency & mesh shading)."""
    return quantize_ordered(rgb_arr, palette, CHECKERBOARD_2X2, strength=strength, perceptual=perceptual)


def quantize_blue_noise(
    rgb_arr: np.ndarray,
    palette: Palette,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Blue Noise void-and-cluster dithering (organic, high-frequency film grain look)."""
    return quantize_ordered(rgb_arr, palette, BLUE_NOISE_16X16, strength=strength, perceptual=perceptual)


def quantize_error_diffusion(
    rgb_arr: np.ndarray,
    palette: Palette,
    kernel_name: str = "floyd",
    alpha_mask: Optional[np.ndarray] = None,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Error-diffusion dithering supporting multiple classic retro algorithms:
    - floyd (Floyd-Steinberg 4-neighbor)
    - atkinson (Bill Atkinson Apple Macintosh 1984)
    - burkes (Burkes 7-neighbor 2-row)
    - sierra (Frankie Sierra 7-neighbor 2-row)
    - stucki (Peter Stucki 12-neighbor 3-row)
    """
    H, W, _ = rgb_arr.shape
    palette_arr = np.array(palette, dtype=np.float32)

    work_rgb = rgb_arr.astype(np.float32).copy()
    indices = np.zeros((H, W), dtype=np.uint8)
    quantized_rgb = np.zeros((H, W, 3), dtype=np.uint8)

    kernel = DIFFUSION_KERNELS.get(kernel_name.lower().strip(), DIFFUSION_KERNELS["floyd"])
    scaled_kernel = [(dx, dy, w * strength) for dx, dy, w in kernel]

    for y in range(H):
        for x in range(W):
            if alpha_mask is not None and not alpha_mask[y, x]:
                continue

            current_color = np.clip(work_rgb[y, x], 0.0, 255.0)

            diff = current_color - palette_arr
            if perceptual:
                r_bar = 0.5 * (current_color[0] + palette_arr[:, 0])
                wr = 2.0 + (r_bar / 256.0)
                wb = 2.0 + ((255.0 - r_bar) / 256.0)
                dist_sq = wr * (diff[:, 0] ** 2) + 4.0 * (diff[:, 1] ** 2) + wb * (diff[:, 2] ** 2)
            else:
                dist_sq = np.sum(diff ** 2, axis=1)

            best_idx = int(np.argmin(dist_sq))
            chosen_color = palette_arr[best_idx]

            indices[y, x] = best_idx
            quantized_rgb[y, x] = chosen_color

            err = current_color - chosen_color

            for dx, dy, weight in scaled_kernel:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    if alpha_mask is None or alpha_mask[ny, nx]:
                        work_rgb[ny, nx] += err * weight

    return quantized_rgb, indices


def quantize_floyd_steinberg(
    rgb_arr: np.ndarray,
    palette: Palette,
    alpha_mask: Optional[np.ndarray] = None,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Error-diffusion Floyd-Steinberg dithering."""
    return quantize_error_diffusion(
        rgb_arr, palette, kernel_name="floyd", alpha_mask=alpha_mask, strength=strength, perceptual=perceptual
    )


def quantize_atkinson(
    rgb_arr: np.ndarray,
    palette: Palette,
    alpha_mask: Optional[np.ndarray] = None,
    strength: float = 1.0,
    perceptual: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Error-diffusion Atkinson dithering (Apple Macintosh 1984)."""
    return quantize_error_diffusion(
        rgb_arr, palette, kernel_name="atkinson", alpha_mask=alpha_mask, strength=strength, perceptual=perceptual
    )
