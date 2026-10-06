"""Image to Pixel Art conversion library, CLI, and TUI."""

from .converter import convert_to_pixel_art, upscale_nearest
from .palettes import PALETTES, get_palette_by_name, parse_custom_palette, extract_adaptive_palette
from .exporters import export_c_header, export_pico8_spritesheet, export_palette_json
from .tui import run_tui, PixelArtStudio

__version__ = "0.2.0"
__all__ = [
    "convert_to_pixel_art",
    "upscale_nearest",
    "PALETTES",
    "get_palette_by_name",
    "parse_custom_palette",
    "extract_adaptive_palette",
    "export_c_header",
    "export_pico8_spritesheet",
    "export_palette_json",
    "run_tui",
    "PixelArtStudio",
]
