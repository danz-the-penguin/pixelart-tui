"""Preset retro gaming palettes and palette generation utilities."""

from typing import List, Tuple, Dict, Optional
from PIL import Image
import numpy as np

RGBColor = Tuple[int, int, int]
Palette = List[RGBColor]


def hex_to_rgb(hex_code: str) -> RGBColor:
    """Convert hex string (e.g. '#1D2B53' or '1D2B53' or '#FFF') to (R, G, B)."""
    hex_code = hex_code.strip().lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    if len(hex_code) != 6:
        raise ValueError(f"Invalid hex color: {hex_code}")
    return (
        int(hex_code[0:2], 16),
        int(hex_code[2:4], 16),
        int(hex_code[4:6], 16),
    )


def rgb_to_hex(rgb: RGBColor) -> str:
    """Convert (R, G, B) to uppercase hex string."""
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


# Preset Retro Hardware Palettes
PALETTES: Dict[str, Palette] = {
    # Nintendo Game Boy (Original DMG-01 4-shade Pea Soup Green)
    "gameboy": [
        (15, 56, 15),     # Darkest green
        (48, 98, 48),     # Dark green
        (139, 172, 15),   # Light green
        (155, 188, 15),   # Lightest green
    ],
    # Nintendo Game Boy Pocket (4-shade Neutral Grey)
    "gameboy-pocket": [
        (20, 20, 20),
        (84, 84, 84),
        (168, 168, 168),
        (240, 240, 240),
    ],
    # PICO-8 Fantasy Console (16 colors)
    "pico8": [
        (0, 0, 0),        # 0 Black
        (29, 43, 83),     # 1 Dark Blue
        (126, 37, 83),    # 2 Dark Purple
        (0, 135, 81),     # 3 Dark Green
        (171, 82, 54),    # 4 Brown
        (95, 87, 79),     # 5 Dark Grey
        (194, 195, 199),  # 6 Light Grey
        (255, 241, 232),  # 7 White
        (255, 0, 77),     # 8 Red
        (255, 163, 0),    # 9 Orange
        (255, 236, 39),   # 10 Yellow
        (0, 228, 54),     # 11 Green
        (41, 173, 255),   # 12 Blue
        (131, 118, 156),  # 13 Indigo
        (255, 119, 168),  # 14 Pink
        (255, 204, 170),  # 15 Peach
    ],
    # Commodore 64 (16 colors, Pepto standard)
    "c64": [
        (0, 0, 0),        # Black
        (255, 255, 255),  # White
        (136, 0, 0),      # Red
        (170, 255, 238),  # Cyan
        (204, 68, 204),   # Purple
        (0, 204, 85),     # Green
        (0, 0, 170),      # Blue
        (238, 238, 119),  # Yellow
        (221, 136, 85),   # Orange
        (102, 68, 0),     # Brown
        (255, 119, 119),  # Light Red
        (51, 51, 51),     # Dark Grey
        (119, 119, 119),  # Grey
        (170, 255, 102),  # Light Green
        (0, 136, 255),    # Light Blue
        (187, 187, 187),  # Light Grey
    ],
    # IBM PC CGA Mode 1 (High Intensity)
    "cga-mode1": [
        (0, 0, 0),        # Black
        (85, 255, 255),   # Bright Cyan
        (255, 85, 255),   # Bright Magenta
        (255, 255, 255),  # White
    ],
    # IBM PC CGA Mode 0 (High Intensity)
    "cga-mode0": [
        (0, 0, 0),        # Black
        (85, 255, 85),    # Bright Green
        (255, 85, 85),    # Bright Red
        (255, 255, 85),   # Bright Yellow
    ],
    # ZX Spectrum (15 colors, standard Sinclair)
    "zx-spectrum": [
        (0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
        (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215),
        (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0),
        (0, 255, 255), (255, 255, 0), (255, 255, 255),
    ],
    # Nintendo NES (Canonical 2C02 54-color hardware palette)
    "nes": [
        (124, 124, 124), (0, 0, 252), (0, 0, 188), (68, 40, 188),
        (148, 0, 132), (168, 0, 32), (168, 16, 0), (136, 20, 0),
        (80, 48, 0), (0, 120, 0), (0, 104, 0), (0, 88, 0),
        (0, 64, 88), (0, 0, 0), (188, 188, 188), (0, 120, 248),
        (0, 88, 248), (104, 68, 252), (216, 0, 204), (228, 0, 88),
        (248, 56, 0), (228, 92, 16), (172, 124, 0), (0, 184, 0),
        (0, 168, 0), (0, 168, 68), (0, 136, 136), (248, 248, 248),
        (60, 188, 252), (104, 136, 252), (152, 120, 248), (248, 120, 248),
        (248, 88, 152), (248, 120, 88), (252, 160, 68), (248, 184, 0),
        (184, 248, 24), (88, 216, 84), (88, 248, 152), (0, 232, 216),
        (120, 120, 120), (252, 252, 252), (164, 228, 252), (184, 184, 248),
        (216, 184, 248), (248, 184, 248), (248, 164, 192), (240, 208, 176),
        (252, 224, 168), (248, 216, 120), (216, 248, 120), (184, 248, 184),
        (184, 248, 216), (0, 252, 252),
    ],
    # 1-bit Monochrome (Classic Macintosh 1984 / Nokia 3310)
    "1bit": [
        (0, 0, 0),
        (255, 255, 255),
    ],
    # Cyberpunk / Neon Synthwave
    "cyberpunk": [
        (13, 2, 33),      # Void Navy
        (0, 255, 245),    # Neon Cyan
        (255, 0, 127),    # Neon Pink
        (113, 25, 232),   # Deep Purple
        (255, 235, 59),   # High Voltage Yellow
        (255, 255, 255),  # Pure White
    ],
}


def get_palette_by_name(name: str) -> Optional[Palette]:
    """Retrieve preset palette by case-insensitive name."""
    normalized = name.lower().strip()
    return PALETTES.get(normalized)


def parse_custom_palette(spec: str) -> Palette:
    """Parse comma-separated hex codes or a palette file."""
    # Check if spec is a file path
    import os
    if os.path.exists(spec):
        palette = []
        with open(spec, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("# "):
                    continue
                # Handle GIMP .gpl format (R G B name) or hex list
                parts = line.split()
                if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                    palette.append((int(parts[0]), int(parts[1]), int(parts[2])))
                elif line.startswith("#") or len(line) in (3, 6):
                    try:
                        palette.append(hex_to_rgb(line))
                    except ValueError:
                        pass
        if palette:
            return palette

    # Otherwise treat as comma-separated hex colors (e.g. #000,#ff0000,#ffffff)
    colors = []
    for item in spec.split(","):
        cleaned = item.strip()
        if cleaned:
            colors.append(hex_to_rgb(cleaned))
    if not colors:
        raise ValueError(f"Could not parse any valid colors from: {spec}")
    return colors


def extract_adaptive_palette(img: Image.Image, num_colors: int = 16) -> Palette:
    """
    Extract an adaptive N-color palette from an image using Median Cut.
    Ideal for SNES / GBA sprites where each sprite has a custom 16-color palette.
    """
    rgb_img = img.convert("RGB")
    quantized = rgb_img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    pal_data = quantized.getpalette()[:num_colors * 3]
    palette = [
        (pal_data[i], pal_data[i + 1], pal_data[i + 2])
        for i in range(0, len(pal_data), 3)
    ]
    return palette


def palette_to_pil_image(palette: Palette) -> Image.Image:
    """Create a 1x1 PIL 'P' mode image containing the palette data (for PIL quantize)."""
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for r, g, b in palette:
        flat_palette.extend([r, g, b])
    # Pad to 256 colors (768 ints)
    if len(flat_palette) < 768:
        flat_palette.extend([0] * (768 - len(flat_palette)))
    pal_img.putpalette(flat_palette[:768])
    return pal_img
