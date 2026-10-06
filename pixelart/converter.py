"""Core pipeline for transforming high-resolution images into authentic retro pixel art."""

from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

from .palettes import (
    Palette,
    RGBColor,
    get_palette_by_name,
    parse_custom_palette,
    extract_adaptive_palette,
)
from .dither import (
    quantize_none,
    quantize_bayer,
    quantize_floyd_steinberg,
)


RESAMPLE_METHODS = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "box": Image.Resampling.BOX,
    "nearest": Image.Resampling.NEAREST,
}


def preprocess_image(
    img: Image.Image,
    contrast: float = 1.2,
    saturation: float = 1.2,
    sharpness: float = 1.3,
) -> Image.Image:
    """
    Enhance contrast, saturation, and sharpness to prevent washed-out,
    muddy colors when downscaling to low retro resolutions.
    """
    processed = img
    if contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)
    if saturation != 1.0 and processed.mode in ("RGB", "RGBA"):
        processed = ImageEnhance.Color(processed).enhance(saturation)
    if sharpness != 1.0:
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness)
    return processed


def calculate_target_size(
    orig_w: int,
    orig_h: int,
    target_w: Optional[int] = None,
    target_h: Optional[int] = None,
    downscale_factor: Optional[int] = None,
    max_dimension: Optional[int] = None,
) -> Tuple[int, int]:
    """Calculate target (width, height) maintaining aspect ratio where appropriate."""
    if downscale_factor and downscale_factor > 1:
        new_w = max(1, orig_w // downscale_factor)
        new_h = max(1, orig_h // downscale_factor)
        return new_w, new_h

    if target_w is not None and target_h is not None:
        return target_w, target_h

    if target_w is not None:
        new_h = max(1, int(orig_h * (target_w / orig_w)))
        return target_w, new_h

    if target_h is not None:
        new_w = max(1, int(orig_w * (target_h / orig_h)))
        return new_w, target_h

    if max_dimension is not None:
        if orig_w >= orig_h:
            new_w = max_dimension
            new_h = max(1, int(orig_h * (max_dimension / orig_w)))
        else:
            new_h = max_dimension
            new_w = max(1, int(orig_w * (max_dimension / orig_h)))
        return new_w, new_h

    # Default to 64x64 bounding box maintaining aspect ratio
    return calculate_target_size(orig_w, orig_h, max_dimension=64)


def apply_sprite_outline(
    rgb_arr: np.ndarray,
    alpha_mask: np.ndarray,
    outline_color: RGBColor = (0, 0, 0),
) -> np.ndarray:
    """
    Add a crisp 1-pixel retro outline along the sprite contour where
    opaque pixels border transparent pixels.
    """
    H, W = alpha_mask.shape
    outlined = rgb_arr.copy()

    # Find inner border: opaque pixels that have at least one transparent 4-neighbor
    padded = np.pad(alpha_mask, pad_width=1, mode='constant', constant_values=False)
    # Check 4-neighbors
    has_transparent_neighbor = (
        (~padded[:-2, 1:-1])  # up
        | (~padded[2:, 1:-1])  # down
        | (~padded[1:-1, :-2])  # left
        | (~padded[1:-1, 2:])  # right
    )
    is_border = alpha_mask & has_transparent_neighbor

    outlined[is_border] = outline_color
    return outlined


def convert_to_pixel_art(
    img: Image.Image,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    downscale_factor: Optional[int] = None,
    max_dimension: Optional[int] = 64,
    palette_name_or_spec: str = "pico8",
    num_adaptive_colors: int = 16,
    dither_mode: str = "none",
    dither_strength: float = 1.0,
    bayer_matrix_size: int = 4,
    resample_method: str = "lanczos",
    contrast: float = 1.2,
    saturation: float = 1.2,
    sharpness: float = 1.3,
    alpha_threshold: int = 128,
    add_outline: bool = False,
    outline_color: RGBColor = (0, 0, 0),
    perceptual: bool = True,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[Image.Image, np.ndarray, Palette]:
    """
    Full pipeline to turn an image into authentic retro pixel art.
    crop_box: Optional (x, y, width, height) to crop region of interest.
    
    Returns:
        (pixel_art_image, palette_indices, final_palette)
    """
    # 0. Apply crop if requested (x, y, width, height)
    if crop_box is not None:
        cx, cy, cw, ch = crop_box
        img = img.crop((cx, cy, cx + cw, cy + ch))

    # 1. Determine target dimensions
    orig_w, orig_h = img.size
    w, h = calculate_target_size(
        orig_w, orig_h,
        target_w=target_width,
        target_h=target_height,
        downscale_factor=downscale_factor,
        max_dimension=max_dimension,
    )

    # 2. Check alpha transparency
    has_alpha = img.mode in ("RGBA", "LA") or ("transparency" in img.info)
    if has_alpha:
        img_rgba = img.convert("RGBA")
    else:
        img_rgba = img.convert("RGB")

    # 3. Preprocess contrast, saturation, sharpness
    preprocessed = preprocess_image(
        img_rgba,
        contrast=contrast,
        saturation=saturation,
        sharpness=sharpness,
    )

    # 4. Downscale to retro pixel dimensions
    resample_filter = RESAMPLE_METHODS.get(resample_method.lower(), Image.Resampling.LANCZOS)
    low_res_img = preprocessed.resize((w, h), resample=resample_filter)

    # 5. Extract alpha mask if transparent
    alpha_mask = None
    if has_alpha:
        low_res_rgba = np.array(low_res_img)
        alpha_channel = low_res_rgba[:, :, 3]
        alpha_mask = alpha_channel >= alpha_threshold
        low_res_rgb = low_res_rgba[:, :, :3]
    else:
        low_res_rgb = np.array(low_res_img.convert("RGB"))

    # 6. Resolve Palette
    palette: Palette
    palette_lower = palette_name_or_spec.lower().strip()
    if palette_lower in ("adaptive", "custom-k", "auto"):
        palette = extract_adaptive_palette(low_res_img, num_colors=num_adaptive_colors)
    else:
        preset = get_palette_by_name(palette_lower)
        if preset is not None:
            palette = preset
        else:
            palette = parse_custom_palette(palette_name_or_spec)

    # 7. Apply Quantization & Dithering
    dither_clean = dither_mode.lower().strip()
    if dither_clean.startswith("bayer"):
        # e.g. bayer, bayer-2x2, bayer-4x4, bayer-8x8
        matrix_sz = bayer_matrix_size
        if "2" in dither_clean:
            matrix_sz = 2
        elif "8" in dither_clean:
            matrix_sz = 8
        quantized_rgb, indices = quantize_bayer(
            low_res_rgb,
            palette,
            matrix_size=matrix_sz,
            strength=dither_strength,
            perceptual=perceptual,
        )
    elif dither_clean in ("floyd", "floyd-steinberg", "fs"):
        quantized_rgb, indices = quantize_floyd_steinberg(
            low_res_rgb,
            palette,
            alpha_mask=alpha_mask,
            strength=dither_strength,
            perceptual=perceptual,
        )
    else:
        # No dithering (flat retro cel-shading)
        quantized_rgb, indices = quantize_none(
            low_res_rgb,
            palette,
            perceptual=perceptual,
        )

    # 8. Apply Outline if requested and sprite has alpha
    if add_outline and alpha_mask is not None:
        quantized_rgb = apply_sprite_outline(quantized_rgb, alpha_mask, outline_color=outline_color)

    # 9. Reconstruct final image (RGB or RGBA)
    if alpha_mask is not None:
        final_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        final_rgba[:, :, :3] = quantized_rgb
        final_rgba[:, :, 3] = np.where(alpha_mask, 255, 0)
        result_img = Image.fromarray(final_rgba, mode="RGBA")
    else:
        result_img = Image.fromarray(quantized_rgb, mode="RGB")

    return result_img, indices, palette


def upscale_nearest(img: Image.Image, scale: int = 8) -> Image.Image:
    """
    Scale pixel art up by an integer factor using Nearest-Neighbor.
    Maintains 100% crisp, razor-sharp square pixels for modern displays.
    """
    if scale <= 1:
        return img
    w, h = img.size
    return img.resize((w * scale, h * scale), resample=Image.Resampling.NEAREST)
