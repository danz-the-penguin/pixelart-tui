# 👾 ImageToPixelArt — CLI & Interactive TUI Studio

A command-line tool, interactive terminal studio (TUI), and Python library built for retro game developers to convert modern high-resolution images, concept art, and illustrations into authentic retro pixel art sprites.

---

## 🖥️ Interactive TUI Studio

Launch the full-screen terminal interface with live unicode 24-bit half-block sprite rendering, real-time palette swapping, dithering toggles, and asset export:

```bash
# Launch interactive TUI Studio
uv run pixelart-tui

# Or with an initial image:
uv run pixelart-tui sample_input.png
# Or via CLI flag:
uv run python main.py --tui
```

### ✨ TUI Features
- **Live Terminal Canvas**: True-color ANSI rendering using Unicode half-blocks (`▀` and `▄`) right inside your terminal.
- **Instant Previews**: Adjust resolution, switch retro palettes, toggle outlines, and see results update in real-time.
- **One-Click Game Exports**: Save upscaled preview PNGs, native 1x sprites, C headers (`.h`), and PICO-8 hex sprites with a single click.

---

## 🌟 Core Engine Features

- **Hardware-Accurate Palettes**:
  - **Nintendo Game Boy** (DMG-01 4-shade green & Game Boy Pocket monochrome)
  - **Nintendo NES** (Canonical 54-color 2C02 palette)
  - **PICO-8** (16 fantasy console colors)
  - **Commodore 64** (16 Pepto colors)
  - **IBM PC CGA** (Mode 0 & Mode 1)
  - **ZX Spectrum** (15 colors)
  - **Adaptive Palette**: Automatically extracts optimal N-color palettes (ideal for SNES / GBA 16-color sprites)
  - **Custom Palettes**: Supports comma-separated hex colors (e.g. `--palette '#000,#ff0055,#ffffff'`) or `.gpl`/text palette files.
- **Authentic Dithering Modes**:
  - `none`: Crisp, clean cel-shaded retro look (great for modern indie pixel art like *Celeste* or *Shovel Knight*).
  - `bayer-2x2`, `bayer-4x4`, `bayer-8x8`: Ordered cross-hatch dithering characteristic of DOS, PC-98, and arcade games.
  - `floyd`: Error diffusion dithering for smooth color transitions.
- **Game Engine & Asset Pipeline Friendly**:
  - **Alpha Transparency Support**: Accurately preserves transparent PNG backgrounds without ugly fringe or color bleeding.
  - **Sprite Outlining**: Adds a 1-pixel dark outline around sprite silhouettes to make characters pop against backgrounds.
  - **Pre-processing Boost**: Automatic contrast, saturation, and edge sharpness enhancement to prevent downsampled art from looking washed out.
  - **Dual Output**: Save both native 1x low-res sprite (`--save-raw`) and upscaled nearest-neighbor preview (`--scale 8`).
  - **Direct Game Dev Exports**:
    - `--export-c`: Generates a C/C++ header (`.h`) with palette and index arrays (ready for GBDK, devkitARM, NES cc65, Arduboy, Raylib, SDL).
    - `--export-pico8`: Generates PICO-8 hex sprite string (`.txt`) for cartridge `__gfx__`.
    - `--export-palette`: Generates a JSON color map.

---

## 🚀 Quickstart

### 1. Installation

Requires Python 3.9+. Install dependencies with `uv` or `pip`:

```bash
# Using uv (recommended)
uv sync

# Or using standard pip
pip install -e .
```

### 2. CLI Usage Examples

```bash
# Basic conversion (PICO-8 palette, 64px max, 8x upscaled preview):
uv run python main.py hero.png -o hero_pixel.png

# Game Boy (32x32 native sprite, Bayer ordered dithering, save raw sprite):
uv run python main.py monster.png --palette gameboy -w 32 -H 32 --dither bayer-4x4 --scale 8 --save-raw

# SNES/GBA style (48x48, 16-color adaptive palette, sprite outline, export C header):
uv run python main.py character.png --palette adaptive --colors 16 -w 48 -H 48 --outline --export-c

# Export PICO-8 cartridge sprite format:
uv run python main.py item.png -w 16 -H 16 --palette pico8 --export-pico8

# List all available retro palettes:
uv run python main.py --list-palettes
```

---

## 🛠️ CLI Options Reference

| Option | Flag | Description | Default |
|---|---|---|---|
| Target Width | `-w, --width` | Fixed width in pixels | Auto |
| Target Height | `-H, --height` | Fixed height in pixels | Auto |
| Max Dimension | `-s, --size` | Max bounding box (keeps aspect ratio) | `64` |
| Downscale Divisor | `-d, --downscale` | Divides width/height by integer factor (e.g. 4, 8) | None |
| Palette | `-p, --palette` | `pico8`, `gameboy`, `nes`, `c64`, `cga-mode1`, `adaptive`, etc. | `pico8` |
| Adaptive Colors | `-c, --colors` | Number of colors when using `--palette adaptive` | `16` |
| Dither Algorithm | `--dither` | `none`, `bayer-2x2`, `bayer-4x4`, `bayer-8x8`, `floyd` | `none` |
| Dither Strength | `--dither-strength`| Multiplier for dithering spread | `1.0` |
| Upscale Factor | `--scale` | Nearest-neighbor multiplier for modern display | `8` |
| Save Raw Sprite | `--save-raw` | Also output the 1x native retro sprite (e.g. `32x32.png`) | `False` |
| Sprite Outline | `--outline` | Adds 1-pixel dark contour around sprite | `False` |
| Outline Color | `--outline-color` | Hex color code for outline | `#000000` |
| Contrast Boost | `--contrast` | Multiplier for contrast enhancement before resize | `1.25` |
| Saturation Boost | `--saturation` | Multiplier for color saturation before resize | `1.25` |
| Sharpness Boost | `--sharpness` | Multiplier for edge sharpness before resize | `1.30` |
| Export C Header | `--export-c` | Outputs `.h` header with palette and index arrays | `False` |
| Export PICO-8 | `--export-pico8` | Outputs hex text ready for PICO-8 cartridge | `False` |
| Export Palette | `--export-palette` | Outputs palette as JSON file | `False` |
| Interactive TUI | `--tui` | Launches interactive Textual TUI studio | `False` |

---

## 🐍 Python Library Usage

```python
from PIL import Image
from pixelart import convert_to_pixel_art, upscale_nearest, export_c_header

img = Image.open("dragon.png")

# Transform into 32x32 Game Boy pixel art
pixel_img, indices, palette = convert_to_pixel_art(
    img,
    target_width=32,
    target_height=32,
    palette_name_or_spec="gameboy",
    dither_mode="bayer-4x4",
    add_outline=True,
)

# 1. Save 1x native sprite for your game engine
pixel_img.save("dragon_32x32.png")

# 2. Save 8x nearest-neighbor upscaled preview
upscale_nearest(pixel_img, scale=8).save("dragon_preview.png")

# 3. Export C header for GBDK / devkitARM
export_c_header(indices, palette, name="dragon", output_path="dragon.h")
```
