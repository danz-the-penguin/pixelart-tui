"""Command-line interface for converting images to retro pixel art."""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image

from .converter import convert_to_pixel_art, upscale_nearest
from .palettes import PALETTES, hex_to_rgb, rgb_to_hex
from .exporters import export_c_header, export_pico8_spritesheet, export_palette_json
from . import __version__


def format_palette_list() -> str:
    """Format available palettes into a readable terminal table."""
    lines = ["Available Retro Palettes:"]
    lines.append("-" * 60)
    for name, colors in PALETTES.items():
        sample_hex = " ".join([rgb_to_hex(c) for c in colors[:4]])
        if len(colors) > 4:
            sample_hex += " ..."
        lines.append(f"  • {name:<16} ({len(colors):>2} colors) : {sample_hex}")
    lines.append("  • adaptive         (N colors)  : Auto-extracts from image (--colors N)")
    lines.append("-" * 60)
    lines.append("Tip: You can also pass custom hex values: --palette '#000,#ff0055,#ffffff'")
    lines.append("     Or a palette file: --palette ./mypalette.gpl")
    return "\n".join(lines)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="pixelart",
        description="Transform modern images into authentic retro pixel art sprites.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Basic conversion (PICO-8 palette, 64px max, 8x upscaled preview):
  pixelart character.png -o character_pixel.png

  # Game Boy sprite (32x32 native, 4-shade green, Bayer dithering):
  pixelart monster.png --palette gameboy -w 32 -H 32 --dither bayer-4x4 --scale 8 --save-raw

  # SNES/GBA style 16-color adaptive palette with black outline:
  pixelart hero.png --palette adaptive --colors 16 -w 48 --outline --scale 10

  # Export C header and PICO-8 sprite format for game engines:
  pixelart item.png -w 16 -H 16 --palette pico8 --export-c --export-pico8

  # List all built-in retro palettes:
  pixelart --list-palettes
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input image file (PNG, JPG, WebP, etc.)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Path for output image. If omitted, defaults to '<name>_pixel.png'",
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        help="Target retro sprite width in pixels (e.g. 16, 32, 64)",
    )
    parser.add_argument(
        "-H", "--height",
        type=int,
        help="Target retro sprite height in pixels (e.g. 16, 32, 64)",
    )
    parser.add_argument(
        "-s", "--size", "--max-dim",
        dest="max_dimension",
        type=int,
        default=64,
        help="Maximum bounding box dimension in pixels when width/height not set (default: 64)",
    )
    parser.add_argument(
        "-d", "--downscale",
        type=int,
        help="Downscale factor divisor (e.g. 4 for 1/4th size, 8 for 1/8th size)",
    )
    parser.add_argument(
        "-p", "--palette",
        default="pico8",
        help="Palette name (gameboy, nes, pico8, c64, cga-mode1, 1bit, adaptive, etc.) or comma-separated hex colors (default: pico8)",
    )
    parser.add_argument(
        "-c", "--colors",
        type=int,
        default=16,
        help="Number of colors when using --palette adaptive (default: 16)",
    )
    parser.add_argument(
        "--dither",
        default="none",
        choices=[
            "none", "bayer-2x2", "bayer-4x4", "bayer-8x8",
            "checkerboard", "blue-noise", "floyd", "atkinson",
            "burkes", "sierra", "stucki"
        ],
        help="Dithering algorithm: none, bayer-4x4, checkerboard, blue-noise, floyd, atkinson, burkes, sierra, stucki (default: none)",
    )
    parser.add_argument(
        "--dither-strength",
        type=float,
        default=1.0,
        help="Dither intensity multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=8,
        help="Upscale factor using Nearest-Neighbor for crisp preview on modern screens (default: 8, use 1 for raw sprite size)",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Also save the 1x native retro resolution sprite alongside the preview",
    )
    parser.add_argument(
        "--outline",
        action="store_true",
        help="Add 1-pixel dark outline along sprite boundary (best for transparent PNGs)",
    )
    parser.add_argument(
        "--outline-color",
        default="#000000",
        help="Hex color for sprite outline (default: #000000)",
    )
    parser.add_argument(
        "--contrast",
        type=float,
        default=1.25,
        help="Contrast boost before downscaling (default: 1.25)",
    )
    parser.add_argument(
        "--saturation",
        type=float,
        default=1.25,
        help="Color saturation boost before downscaling (default: 1.25)",
    )
    parser.add_argument(
        "--sharpness",
        type=float,
        default=1.3,
        help="Sharpness boost before downscaling (default: 1.3)",
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=1.0,
        help="Brightness adjustment before downscaling (default: 1.0)",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=1.0,
        help="CRT gamma curve adjustment (default: 1.0)",
    )
    parser.add_argument(
        "--warmth",
        type=float,
        default=0.0,
        help="Color temperature shift from -1.0 (cool cyber) to +1.0 (warm CRT glow) (default: 0.0)",
    )
    parser.add_argument(
        "--tint",
        choices=["none", "crt-green", "crt-amber", "sepia", "monochrome"],
        default="none",
        help="Retro CRT monitor tint filter (none, crt-green, crt-amber, sepia, monochrome)",
    )
    parser.add_argument(
        "--resample",
        default="lanczos",
        choices=["lanczos", "bicubic", "bilinear", "box", "nearest"],
        help="Downsampling resampling filter (default: lanczos)",
    )
    parser.add_argument(
        "--export-c",
        action="store_true",
        help="Export C/C++ header (.h) with sprite pixel indices and palette array",
    )
    parser.add_argument(
        "--export-pico8",
        action="store_true",
        help="Export PICO-8 sprite string (.txt) for fantasy console cartridges",
    )
    parser.add_argument(
        "--crop",
        nargs=4,
        type=int,
        metavar=("X", "Y", "WIDTH", "HEIGHT"),
        help="Crop a sub-region from the source image before conversion",
    )
    parser.add_argument(
        "--export-palette",
        action="store_true",
        help="Export JSON palette file with hex and RGB values",
    )
    parser.add_argument(
        "--list-palettes",
        action="store_true",
        help="List all built-in retro palettes and exit",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the interactive terminal user interface (TUI) studio",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pixelart {__version__}",
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.list_palettes:
        print(format_palette_list())
        sys.exit(0)

    # Launch interactive TUI if requested or if run without input args in a terminal
    if args.tui or (not args.input and sys.stdin.isatty()):
        from .tui import run_tui
        run_tui(initial_image=args.input)
        return

    if not args.input:
        print("Error: Input image path required. Run 'pixelart --help' or 'pixelart --tui'.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        source_img = Image.open(input_path)
    except Exception as e:
        print(f"Error opening image '{input_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_pixel.png"

    # Outline color parsing
    try:
        outline_rgb = hex_to_rgb(args.outline_color)
    except ValueError as e:
        print(f"Error: Invalid outline color: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"🎮 Transforming: {input_path.name} ({source_img.width}x{source_img.height})")

    # Run conversion
    try:
        pixel_img, indices, palette = convert_to_pixel_art(
            source_img,
            target_width=args.width,
            target_height=args.height,
            downscale_factor=args.downscale,
            max_dimension=args.max_dimension if not (args.width or args.height or args.downscale) else None,
            palette_name_or_spec=args.palette,
            num_adaptive_colors=args.colors,
            dither_mode=args.dither,
            dither_strength=args.dither_strength,
            resample_method=args.resample,
            contrast=args.contrast,
            saturation=args.saturation,
            sharpness=args.sharpness,
            brightness=args.brightness,
            gamma=args.gamma,
            warmth=args.warmth,
            tint=args.tint,
            add_outline=args.outline,
            outline_color=outline_rgb,
            crop_box=tuple(args.crop) if args.crop else None,
        )
    except Exception as e:
        print(f"Error during pixel art conversion: {e}", file=sys.stderr)
        sys.exit(1)

    pw, ph = pixel_img.size
    print(f"👾 Native retro resolution: {pw}x{ph} | Palette: {args.palette} ({len(palette)} colors)")

    # Save raw low-res sprite if requested
    if args.save_raw:
        raw_path = output_path.parent / f"{output_path.stem}_{pw}x{ph}{output_path.suffix}"
        pixel_img.save(raw_path)
        print(f"💾 Saved native sprite: {raw_path}")

    # Generate upscaled preview
    if args.scale > 1:
        final_img = upscale_nearest(pixel_img, scale=args.scale)
        print(f"🔍 Upscaling {args.scale}x with Nearest-Neighbor -> {final_img.width}x{final_img.height}")
    else:
        final_img = pixel_img

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    print(f"✨ Output saved to: {output_path}")

    # Game engine exports
    stem = output_path.stem
    if args.export_c:
        c_path = output_path.parent / f"{stem}.h"
        export_c_header(indices, palette, name=input_path.stem, output_path=str(c_path))
        print(f"🕹️  Exported C header: {c_path}")

    if args.export_pico8:
        p8_path = output_path.parent / f"{stem}_pico8.txt"
        export_pico8_spritesheet(indices, output_path=str(p8_path))
        print(f"🕹️  Exported PICO-8 sprite data: {p8_path}")

    if args.export_palette:
        pal_path = output_path.parent / f"{stem}_palette.json"
        export_palette_json(palette, output_path=str(pal_path))
        print(f"🎨 Exported palette JSON: {pal_path}")


if __name__ == "__main__":
    main()
