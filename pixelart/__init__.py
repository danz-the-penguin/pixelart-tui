"""Image to Pixel Art conversion library, CLI, and TUI."""

from .converter import convert_to_pixel_art, upscale_nearest
from .dither import DITHER_METHODS
from .exporters import export_c_header, export_palette_json, export_pico8_spritesheet
from .palettes import (
    PALETTES,
    extract_adaptive_palette,
    get_palette_by_name,
    parse_custom_palette,
)
from .tui import PixelArtStudio, run_tui

__version__ = "0.2.0"
__all__ = [
    "DITHER_METHODS",
    "PALETTES",
    "PixelArtStudio",
    "convert_to_pixel_art",
    "export_c_header",
    "export_palette_json",
    "export_pico8_spritesheet",
    "extract_adaptive_palette",
    "get_palette_by_name",
    "parse_custom_palette",
    "run_tui",
    "upscale_nearest",
]
