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
- **Live Terminal Canvas & Dual Tabs**: True-color ANSI rendering using Unicode half-blocks (`▀` and `▄`) with tabs to toggle between **👾 Pixel Art** and **✂️ Cropped Source**.
- **Interactive Cropping & Panning D-Pad**: Move and pan the crop window across high-res art using `▲`, `▼`, `◄`, `►` buttons or Arrow Keys (`↑`, `↓`, `←`, `→`).
- **Custom Crop Dimensions**: Type your exact wanted Width & Height, or use quick presets (`1:1 Square`, `Center`, `Reset Full`).
- **Instant Previews**: Adjust resolution, switch retro palettes, toggle outlines, and see results update in real-time.
- **One-Click Game Exports**: Save upscaled preview PNGs, native 1x sprites, C headers (`.h`), and PICO-8 hex sprites with a single click.

---

## 🌟 Core Engine Features

- **Hardware-Accurate Palettes (26+ Systems)**:
  - **Nintendo SNES** (Curated 16 colors & 15-bit hardware grid snap `snes-adaptive`)
  - **Sega Genesis / Mega Drive** (16 colors & 9-bit hardware grid snap `genesis-adaptive`)
  - **Nintendo Game Boy Advance** (GBA curated 16-color palette)
  - **Nintendo NES** (Canonical 54-color 2C02 hardware palette)
  - **Nintendo Game Boy** (DMG-01 4-shade green, Game Boy Pocket monochrome, GBC 16-color)
  - **Commodore 64 & Amiga OCS** (C64 16 Pepto colors, Amiga 16 Copper colors)
  - **NEC PC-9801** (16 Japanese retro computer colors)
  - **Apple II** (16 Wozniak composite NTSC colors)
  - **Amstrad CPC** (16 hardware colors)
  - **Sega Master System & Game Gear** (16 colors each)
  - **Atari 2600 VCS** (16 NTSC arcade colors)
  - **PICO-8 & TIC-80** (PICO-8 16 standard, PICO-8 32 extended secret colors, TIC-80 Sweetie 16)
  - **IBM PC CGA** (Mode 0 & Mode 1 high-intensity)
  - **ZX Spectrum** (15 standard Sinclair colors)
  - **CRT Terminals & 1-bit** (IBM 5151 green phosphor, amber CRT terminal, 1-bit B&W)
  - **Endesga 32 & Cyberpunk** (Modern indie pixel art palettes)
  - **Adaptive Palette**: Automatically extracts optimal N-color palettes (--colors N)
  - **Custom Palettes**: Supports comma-separated hex colors (e.g. `--palette '#000,#ff0055,#ffffff'`) or `.gpl`/text palette files.
- **Authentic Dithering Modes (11 Algorithms)**:
  - `none`: Crisp, clean cel-shaded retro look.
  - `bayer-2x2`, `bayer-4x4`, `bayer-8x8`: Classic ordered crosshatch dithering.
  - `checkerboard`: 1x1 alternating parity mesh shading (Sega Genesis pseudo-transparency).
  - `blue-noise`: Organic, high-frequency void-and-cluster grain dithering (*Return of the Obra Dinn*).
  - `floyd`: Canonical Floyd-Steinberg error diffusion.
  - `atkinson`: Bill Atkinson Apple Macintosh 1984 dithering (drops 25% error for punchy high contrast).
  - `burkes`: Fast 7-neighbor 2-row error diffusion avoiding worm artifacts.
  - `sierra`: Frankie Sierra smooth two-row error diffusion.
  - `stucki`: High-fidelity 12-neighbor 3-row error diffusion.
- **Rich Color Enhancements & Presets**:
  - **Contrast, Saturation & Sharpness**: Boost clarity and prevent washed-out colors.
  - **Brightness & Gamma Correction**: Simulate vintage CRT monitor gamma curves.
  - **Color Warmth**: Shift color temperature from cool cyber blue to warm incandescent amber.
  - **Retro CRT Tints**: Green phosphor (`crt-green`), amber terminal (`crt-amber`), vintage sepia (`sepia`), and monochrome (`monochrome`).
- **Game Engine & Asset Pipeline Friendly**:
  - **Alpha Transparency Support**: Accurately preserves transparent PNG backgrounds without ugly fringe or color bleeding.
  - **Sprite Outlining**: Adds a 1-pixel dark outline around sprite silhouettes to make characters pop against backgrounds.
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
| Dither Algorithm | `--dither` | `none`, `bayer-2x2`, `bayer-4x4`, `bayer-8x8`, `checkerboard`, `blue-noise`, `floyd`, `atkinson`, `burkes`, `sierra`, `stucki` | `none` |
| Dither Strength | `--dither-strength`| Multiplier for dithering spread | `1.0` |
| Upscale Factor | `--scale` | Nearest-neighbor multiplier for modern display | `8` |
| Save Raw Sprite | `--save-raw` | Also output the 1x native retro sprite (e.g. `32x32.png`) | `False` |
| Sprite Outline | `--outline` | Adds 1-pixel dark contour around sprite | `False` |
| Outline Color | `--outline-color` | Hex color code for outline | `#000000` |
| Contrast Boost | `--contrast` | Multiplier for contrast enhancement before resize | `1.25` |
| Saturation Boost | `--saturation` | Multiplier for color saturation before resize | `1.25` |
| Sharpness Boost | `--sharpness` | Multiplier for edge sharpness before resize | `1.30` |
| Brightness Boost | `--brightness` | Multiplier for brightness adjustment | `1.0` |
| Gamma Correction | `--gamma` | Gamma exponent (`<1.0` lifts shadows, `>1.0` darkens) | `1.0` |
| Color Warmth | `--warmth` | Color temperature balance (`-1.0` cool cyber to `+1.0` warm amber) | `0.0` |
| Retro CRT Tint | `--tint` | Retro monitor tint: `none`, `crt-green`, `crt-amber`, `sepia`, `monochrome` | `none` |
| Export C Header | `--export-c` | Outputs `.h` header with palette and index arrays | `False` |
| Export PICO-8 | `--export-pico8` | Outputs hex text ready for PICO-8 cartridge | `False` |
| Export Palette | `--export-palette` | Outputs palette as JSON file | `False` |
| Sub-region Crop | `--crop X Y W H` | Crops a sub-region from the source before conversion | None |
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
