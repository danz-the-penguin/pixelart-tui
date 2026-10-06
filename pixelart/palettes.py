"""Preset retro gaming palettes and palette generation utilities."""

from typing import List, Tuple, Dict, Optional
from PIL import Image

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
    # Super Nintendo (SNES - Curated 16-color authentic sprite palette)
    "snes": [
        (0, 0, 0),        # 0 Black
        (255, 255, 255),  # 1 White
        (156, 156, 156),  # 2 Light Grey
        (74, 74, 74),     # 3 Dark Grey
        (222, 41, 41),    # 4 Red
        (132, 16, 16),    # 5 Dark Red
        (247, 148, 41),   # 6 Orange
        (247, 222, 41),   # 7 Yellow
        (58, 181, 58),    # 8 Green
        (25, 107, 25),    # 9 Dark Green
        (41, 148, 222),   # 10 Blue
        (16, 49, 148),    # 11 Navy Blue
        (173, 74, 222),   # 12 Purple
        (247, 148, 189),  # 13 Pink / Skin light
        (173, 90, 41),    # 14 Brown
        (99, 49, 16),     # 15 Dark Brown
    ],
    # Nintendo Game Boy Advance (GBA - 16-color vibrant sprite palette)
    "gba": [
        (8, 8, 8),        (248, 248, 248),  (160, 160, 160),  (80, 80, 80),
        (232, 56, 56),    (144, 24, 24),    (248, 152, 48),   (248, 224, 56),
        (56, 192, 56),    (24, 112, 24),    (56, 152, 232),   (24, 56, 152),
        (184, 80, 232),   (248, 160, 192),  (184, 104, 48),   (112, 56, 24),
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
    # Sega Genesis / Mega Drive (16-color iconic Sonic/Mega Drive palette)
    "genesis": [
        (0, 0, 0),        (255, 255, 255),  (182, 182, 182),  (73, 73, 73),
        (36, 73, 219),    (0, 146, 255),    (219, 36, 36),    (255, 109, 73),
        (255, 219, 0),    (255, 146, 0),    (0, 182, 0),      (0, 109, 0),
        (146, 73, 0),     (219, 146, 73),   (146, 36, 182),   (73, 0, 109),
    ],
    # NEC PC-9801 (16-color Japanese retro PC hardware palette)
    "pc98": [
        (0, 0, 0),        (0, 0, 255),      (255, 0, 0),      (255, 0, 255),
        (0, 255, 0),      (0, 255, 255),    (255, 255, 0),    (255, 255, 255),
        (128, 128, 128),  (0, 0, 128),      (128, 0, 0),      (128, 0, 128),
        (0, 128, 0),      (0, 128, 128),    (128, 128, 0),    (64, 64, 64),
    ],
    # Commodore Amiga OCS (16-color iconic Copper/DeluxePaint palette)
    "amiga": [
        (0, 0, 0),        (255, 255, 255),  (170, 170, 170),  (85, 85, 85),
        (34, 68, 153),    (68, 136, 221),   (136, 204, 255),  (187, 34, 34),
        (238, 102, 68),   (255, 170, 51),   (255, 238, 85),   (34, 136, 34),
        (85, 204, 68),    (153, 238, 119),  (102, 51, 17),    (170, 102, 34),
    ],
    # Apple II (16-color Wozniak composite NTSC palette)
    "apple2": [
        (0, 0, 0),        (114, 38, 64),    (64, 50, 133),    (228, 92, 255),
        (15, 86, 62),     (128, 128, 128),  (27, 154, 241),   (183, 193, 255),
        (81, 66, 0),      (235, 109, 32),   (192, 192, 192),  (255, 172, 197),
        (39, 172, 17),    (204, 211, 87),   (146, 221, 201),  (255, 255, 255),
    ],
    # Game Boy Color (GBC - 16-color adventure palette)
    "gbc": [
        (8, 8, 16),       (248, 248, 248),  (168, 168, 176),  (88, 88, 96),
        (248, 56, 56),    (152, 24, 24),    (248, 160, 48),   (248, 224, 56),
        (40, 184, 48),    (16, 96, 24),     (48, 144, 248),   (24, 48, 160),
        (168, 72, 224),   (248, 144, 184),  (168, 96, 40),    (96, 48, 16),
    ],
    # Sega Game Gear (16-color vibrant handheld palette)
    "gamegear": [
        (0, 0, 0),        (255, 255, 255),  (170, 170, 170),  (85, 85, 85),
        (0, 102, 238),    (0, 187, 255),    (238, 34, 34),    (255, 119, 51),
        (255, 221, 34),   (0, 170, 51),     (85, 221, 85),    (136, 51, 187),
        (238, 102, 187),  (153, 85, 34),    (221, 153, 85),   (68, 34, 17),
    ],
    # Sega Master System (16-color 6-bit hardware palette)
    "mastersystem": [
        (0, 0, 0),        (255, 255, 255),  (170, 170, 170),  (85, 85, 85),
        (0, 85, 255),     (85, 170, 255),   (255, 0, 0),      (255, 85, 85),
        (255, 170, 0),    (255, 255, 85),   (0, 170, 0),      (85, 255, 85),
        (170, 0, 255),    (255, 85, 255),   (170, 85, 0),     (85, 85, 0),
    ],
    # Amstrad CPC (16-color classic European computer palette)
    "amstrad-cpc": [
        (0, 0, 0),        (0, 0, 128),      (0, 0, 255),      (128, 0, 0),
        (128, 0, 128),    (128, 0, 255),    (255, 0, 0),      (255, 0, 128),
        (255, 0, 255),    (0, 128, 0),      (0, 255, 0),      (0, 255, 255),
        (255, 255, 0),    (255, 255, 128),  (128, 128, 128),  (255, 255, 255),
    ],
    # Atari 2600 VCS (16-color NTSC arcade palette)
    "atari2600": [
        (0, 0, 0),        (68, 68, 68),     (148, 148, 148),  (252, 252, 252),
        (184, 40, 40),    (180, 76, 24),    (148, 116, 24),   (92, 140, 24),
        (36, 148, 36),    (24, 140, 92),    (24, 116, 148),   (24, 76, 180),
        (40, 40, 184),    (92, 24, 180),    (140, 24, 148),   (180, 24, 92),
    ],
    # TIC-80 (Sweetie 16 fantasy console palette)
    "tic80": [
        (26, 28, 44),     (93, 39, 93),     (177, 62, 83),    (239, 125, 87),
        (255, 205, 117),  (167, 240, 112),  (56, 183, 100),   (37, 113, 121),
        (41, 54, 111),    (59, 93, 201),    (65, 166, 246),   (115, 239, 247),
        (244, 244, 244),  (148, 176, 194),  (86, 108, 134),   (51, 60, 87),
    ],
    # Endesga 32 (Ed's celebrated 32-color modern pixel art palette)
    "endesga32": [
        (190, 74, 47),    (215, 118, 67),   (234, 212, 170),  (228, 166, 114),
        (184, 111, 80),   (115, 62, 57),    (62, 39, 49),     (162, 38, 51),
        (228, 59, 68),    (247, 118, 34),   (254, 174, 52),   (254, 231, 97),
        (99, 199, 77),    (62, 137, 72),    (38, 92, 66),     (25, 60, 62),
        (18, 78, 137),    (0, 153, 219),    (44, 232, 245),   (255, 255, 255),
        (192, 203, 220),  (139, 155, 180),  (90, 105, 136),   (58, 68, 102),
        (38, 43, 68),     (24, 20, 37),     (255, 0, 68),     (254, 231, 97),
        (153, 100, 249),  (94, 52, 194),    (65, 32, 143),    (36, 18, 86),
    ],
    # PICO-8 Extended (all 32 colors: original 16 + 16 secret colors)
    "pico8-secret": [
        (0, 0, 0),        (29, 43, 83),     (126, 37, 83),    (0, 135, 81),
        (171, 82, 54),    (95, 87, 79),     (194, 195, 199),  (255, 241, 232),
        (255, 0, 77),     (255, 163, 0),    (255, 236, 39),   (0, 228, 54),
        (41, 173, 255),   (131, 118, 156),  (255, 119, 168),  (255, 204, 170),
        (41, 24, 20),     (17, 29, 53),     (66, 33, 54),     (18, 83, 89),
        (116, 47, 41),    (73, 51, 59),     (162, 136, 121),  (243, 239, 125),
        (190, 18, 80),    (255, 108, 36),   (168, 231, 46),   (0, 181, 67),
        (6, 90, 181),     (117, 70, 101),   (255, 110, 89),   (255, 157, 129),
    ],
    # CRT Phosphor Green (IBM 5151 / Apple II Green Monitor)
    "crt-green": [
        (0, 0, 0),
        (16, 64, 16),
        (32, 160, 32),
        (64, 255, 64),
    ],
    # CRT Amber Terminal (P3 Amber Phosphor)
    "crt-amber": [
        (0, 0, 0),
        (100, 50, 0),
        (200, 120, 0),
        (255, 176, 0),
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


def snap_color_snes_15bit(rgb: RGBColor) -> RGBColor:
    """Snap an 8-bit RGB color to the SNES 15-bit (5-bit per channel) hardware color grid."""
    r = round(round(rgb[0] * 31 / 255) * 255 / 31)
    g = round(round(rgb[1] * 31 / 255) * 255 / 31)
    b = round(round(rgb[2] * 31 / 255) * 255 / 31)
    return (int(r), int(g), int(b))


def snap_color_genesis_9bit(rgb: RGBColor) -> RGBColor:
    """Snap an 8-bit RGB color to the Sega Genesis 9-bit (3-bit per channel, 8 levels) hardware color grid."""
    r = round(round(rgb[0] * 7 / 255) * 255 / 7)
    g = round(round(rgb[1] * 7 / 255) * 255 / 7)
    b = round(round(rgb[2] * 7 / 255) * 255 / 7)
    return (int(r), int(g), int(b))


def extract_adaptive_palette(
    img: Image.Image,
    num_colors: int = 16,
    snap_snes: bool = False,
    snap_genesis: bool = False,
) -> Palette:
    """
    Extract an adaptive N-color palette from an image using Median Cut.
    Ideal for SNES / Genesis / GBA sprites where each sprite has a custom 16-color palette.
    """
    rgb_img = img.convert("RGB")
    quantized = rgb_img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    pal_data = quantized.getpalette()[:num_colors * 3]
    palette = [
        (pal_data[i], pal_data[i + 1], pal_data[i + 2])
        for i in range(0, len(pal_data), 3)
    ]
    if snap_snes:
        palette = [snap_color_snes_15bit(c) for c in palette]
    elif snap_genesis:
        palette = [snap_color_genesis_9bit(c) for c in palette]
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
