"""Dithering algorithms and color quantization for retro pixel art."""

from typing import List, Tuple
import numpy as np
from PIL import Image

RGBColor = Tuple[int, int, int]
Palette = List[RGBColor]

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

    # Vectorized distance computation
    # diff: (H, W, K, 3)
    diff = pixels[:, :, np.newaxis, :] - palette_arr[np.newaxis, np.newaxis, :, :]

    if perceptual:
        # Redmean perceptual color distance approximation:
        # weights R, G, B according to human eye sensitivity
        # r_bar = (r1 + r2) / 2
        r1 = pixels[:, :, np.newaxis, 0]
        r2 = palette_arr[np.newaxis, np.newaxis, :, 0]
        r_bar = 0.5 * (r1 + r2)

        weight_r = 2.0 + (r_bar / 256.0)
        weight_g = 4.0
        weight_b = 2.0 + ((255.0 - r_bar) / 256.0)

        dist_sq = (
            weight_r * (diff[:, :, :, 0] ** 2)
            + weight_g * (diff[:, :, :, 1] ** 2)
            + weight_b * (diff[:, :, :, 2] ** 2)
        )
    else:
        # Standard Euclidean RGB distance
        dist_sq = np.sum(diff ** 2, axis=-1)

    return np.argmin(dist_sq, axis=-1).astype(np.uint8)


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


def quantize_bayer(
    rgb_arr: np.ndarray,
    palette: Palette,
    matrix_size: int = 4,
    strength: float = 1.0,
    perceptual: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Ordered Bayer matrix dithering (classic PC-98, DOS, cross-hatching retro look).
    matrix_size: 2, 4, or 8
    strength: scaling factor for dithering spread
    """
    if matrix_size == 2:
        bayer = BAYER_2X2
    elif matrix_size == 8:
        bayer = BAYER_8X8
    else:
        bayer = BAYER_4X4

    H, W, _ = rgb_arr.shape
    bh, bw = bayer.shape

    # Tile matrix across image dimensions
    tiles_y = (H + bh - 1) // bh
    tiles_x = (W + bw - 1) // bw
    bayer_tiled = np.tile(bayer, (tiles_y, tiles_x))[:H, :W]

    # Calculate spread: smaller palettes need larger spread to bridge colors
    num_colors = max(len(palette), 2)
    base_spread = 255.0 / (num_colors ** (1.0 / 3.0))
    spread = base_spread * strength

    # Add dithering offset to RGB
    dithered_rgb = rgb_arr.astype(np.float32) + (bayer_tiled[:, :, np.newaxis] * spread)
    dithered_rgb = np.clip(dithered_rgb, 0.0, 255.0)

    palette_arr = np.array(palette, dtype=np.float32)
    indices = find_closest_palette_indices(dithered_rgb, palette_arr, perceptual=perceptual)
    quantized_rgb = palette_arr[indices].astype(np.uint8)

    return quantized_rgb, indices


def quantize_floyd_steinberg(
    rgb_arr: np.ndarray,
    palette: Palette,
    alpha_mask: np.ndarray = None,
    strength: float = 1.0,
    perceptual: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Error-diffusion Floyd-Steinberg dithering.
    Alpha-mask aware: transparent pixels do NOT diffuse error into visible sprite pixels!
    """
    H, W, _ = rgb_arr.shape
    palette_arr = np.array(palette, dtype=np.float32)

    work_rgb = rgb_arr.astype(np.float32).copy()
    indices = np.zeros((H, W), dtype=np.uint8)
    quantized_rgb = np.zeros((H, W, 3), dtype=np.uint8)

    # Weights for Floyd-Steinberg: right, down-left, down, down-right
    # (7/16, 3/16, 5/16, 1/16)
    w_r = (7.0 / 16.0) * strength
    w_dl = (3.0 / 16.0) * strength
    w_d = (5.0 / 16.0) * strength
    w_dr = (1.0 / 16.0) * strength

    for y in range(H):
        for x in range(W):
            # Skip transparent pixels if alpha mask provided
            if alpha_mask is not None and not alpha_mask[y, x]:
                continue

            current_color = np.clip(work_rgb[y, x], 0.0, 255.0)

            # Find closest palette color
            if perceptual:
                r_bar = 0.5 * (current_color[0] + palette_arr[:, 0])
                wr = 2.0 + (r_bar / 256.0)
                wg = 4.0
                wb = 2.0 + ((255.0 - r_bar) / 256.0)
                diff = current_color - palette_arr
                dist_sq = wr * (diff[:, 0] ** 2) + wg * (diff[:, 1] ** 2) + wb * (diff[:, 2] ** 2)
            else:
                dist_sq = np.sum((current_color - palette_arr) ** 2, axis=1)

            best_idx = int(np.argmin(dist_sq))
            chosen_color = palette_arr[best_idx]

            indices[y, x] = best_idx
            quantized_rgb[y, x] = chosen_color

            # Quantization error
            err = current_color - chosen_color

            # Distribute error to neighboring pixels (only if neighbor is visible)
            if x + 1 < W and (alpha_mask is None or alpha_mask[y, x + 1]):
                work_rgb[y, x + 1] += err * w_r
            if y + 1 < H:
                if x > 0 and (alpha_mask is None or alpha_mask[y + 1, x - 1]):
                    work_rgb[y + 1, x - 1] += err * w_dl
                if alpha_mask is None or alpha_mask[y + 1, x]:
                    work_rgb[y + 1, x] += err * w_d
                if x + 1 < W and (alpha_mask is None or alpha_mask[y + 1, x + 1]):
                    work_rgb[y + 1, x + 1] += err * w_dr

    return quantized_rgb, indices
