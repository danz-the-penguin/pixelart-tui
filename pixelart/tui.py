"""Interactive Terminal User Interface (TUI) for ImageToPixelArt using Textual."""

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from rich.style import Style
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Input,
    Label,
    Rule,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from .converter import calculate_target_size, convert_to_pixel_art, upscale_nearest
from .exporters import export_c_header, export_pico8_spritesheet

MIN_TERMINAL_WIDTH = 100
MIN_TERMINAL_HEIGHT = 28

ENHANCEMENT_PRESETS = {
    "default": {"contrast": 1.25, "saturation": 1.25, "sharpness": 1.30, "brightness": 1.0, "gamma": 1.0, "warmth": 0.0, "tint": None},
    "vibrant": {"contrast": 1.35, "saturation": 1.55, "sharpness": 1.35, "brightness": 1.05, "gamma": 1.1, "warmth": 0.1, "tint": None},
    "contrast": {"contrast": 1.55, "saturation": 1.20, "sharpness": 1.35, "brightness": 0.95, "gamma": 1.2, "warmth": 0.0, "tint": None},
    "warm-crt": {"contrast": 1.25, "saturation": 1.30, "sharpness": 1.25, "brightness": 1.05, "gamma": 1.1, "warmth": 0.6, "tint": None},
    "cool-cyber": {"contrast": 1.30, "saturation": 1.35, "sharpness": 1.35, "brightness": 1.0, "gamma": 1.05, "warmth": -0.6, "tint": None},
    "crt-green": {"contrast": 1.30, "saturation": 1.0, "sharpness": 1.40, "brightness": 1.1, "gamma": 1.15, "warmth": 0.0, "tint": "crt-green"},
    "crt-amber": {"contrast": 1.30, "saturation": 1.0, "sharpness": 1.40, "brightness": 1.1, "gamma": 1.15, "warmth": 0.0, "tint": "crt-amber"},
    "sepia": {"contrast": 1.20, "saturation": 1.0, "sharpness": 1.20, "brightness": 1.0, "gamma": 1.0, "warmth": 0.3, "tint": "sepia"},
    "muted": {"contrast": 1.10, "saturation": 0.85, "sharpness": 1.20, "brightness": 1.05, "gamma": 0.95, "warmth": 0.0, "tint": None},
    "sharp": {"contrast": 1.30, "saturation": 1.25, "sharpness": 1.70, "brightness": 1.0, "gamma": 1.0, "warmth": 0.0, "tint": None},
    "flat": {"contrast": 1.0, "saturation": 1.0, "sharpness": 1.0, "brightness": 1.0, "gamma": 1.0, "warmth": 0.0, "tint": None},
}


def resolve_image_path(raw_str: str) -> Optional[Path]:
    """
    Robustly resolve an image path string from terminal input.
    Handles quotes ('path', "path"), escaped spaces (path\\ with\\ spaces),
    tilde expansion (~/...), relative paths, and missing extensions (.png, .jpg).
    """
    if not raw_str or not raw_str.strip():
        return None

    cleaned = raw_str.strip()

    # Strip outer single or double quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()

    # Unescape escaped spaces
    cleaned = cleaned.replace(r"\ ", " ")

    # Expand tilde
    p = Path(cleaned).expanduser()

    # Direct check
    if p.is_file():
        return p.resolve()

    # Relative to cwd
    if not p.is_absolute():
        cwd_p = (Path.cwd() / cleaned).resolve()
        if cwd_p.is_file():
            return cwd_p

    # Try matching common image extensions
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
        cand = p.with_suffix(ext)
        if cand.is_file():
            return cand.resolve()
        cand_cwd = (Path.cwd() / cleaned).with_suffix(ext).resolve()
        if cand_cwd.is_file():
            return cand_cwd

    return None


def get_available_local_images() -> List[Tuple[str, str]]:
    """Scan current directory for user images to populate quick-select dropdown."""
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    cwd = Path.cwd()
    images = []

    for item in sorted(cwd.iterdir()):
        if item.is_file() and item.suffix.lower() in exts:
            name = item.name
            if name.startswith("output_") or name.endswith("_pico8.png"):
                continue
            images.append((f"🖼️ {name}", str(item.resolve())))

    if not images:
        images.append(("None found in folder", ""))

    return images


def calculate_target_box(
    orig_w: int,
    orig_h: int,
    max_w: int = 68,
    max_h: int = 38,
) -> Tuple[int, int]:
    """Calculate target size fitting completely within (max_w, max_h) maintaining aspect ratio."""
    scale = min(max_w / max(1, orig_w), max_h / max(1, orig_h))
    tw = max(2, int(round(orig_w * scale)))
    th = max(2, int(round(orig_h * scale)))
    if th % 2 != 0:
        th += 1
    return tw, th


def create_viewfinder_image(
    source_img: Image.Image,
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
    crop_enabled: bool = True,
    max_w: int = 68,
    max_h: int = 38,
) -> Image.Image:
    """
    Render full source image with an elegant, non-intrusive camera viewfinder HUD.
    Features subtle outer dimming, crisp 1-pixel amber crop boundary, and corner ticks
    WITHOUT obscuring the subject inside the crop window.
    """
    orig_w, orig_h = source_img.size
    tw, th = calculate_target_box(orig_w, orig_h, max_w=max_w, max_h=max_h)

    # Use LANCZOS for crystal-clear preview resolution
    display_img = source_img.resize((tw, th), resample=Image.Resampling.LANCZOS).convert("RGBA")

    # If crop is disabled or covers full image
    if not crop_enabled or (crop_w >= orig_w and crop_h >= orig_h and crop_x == 0 and crop_y == 0):
        draw = ImageDraw.Draw(display_img)
        draw.rectangle([0, 0, tw - 1, th - 1], outline=(88, 166, 255, 180), width=1)
        return display_img

    scale_x = tw / orig_w
    scale_y = th / orig_h

    dx = max(0, min(round(crop_x * scale_x), tw - 1))
    dy = max(0, min(round(crop_y * scale_y), th - 1))
    dw = max(2, min(round(crop_w * scale_x), tw - dx))
    dh = max(2, min(round(crop_h * scale_y), th - dy))

    # 1. Soft darkening outside the crop box (35% opacity) so the surround is visible
    overlay = Image.new("RGBA", (tw, th), (0, 0, 0, 90))
    mask = Image.new("L", (tw, th), 255)
    mask_draw = ImageDraw.Draw(mask)
    # The inside of the crop is completely transparent in mask (100% bright image)
    mask_draw.rectangle([dx, dy, dx + dw - 1, dy + dh - 1], fill=0)
    display_img.paste(overlay, (0, 0), mask)

    # 2. Draw crisp 1-pixel bright gold/amber boundary
    draw = ImageDraw.Draw(display_img)
    if dx > 0 and dy > 0 and (dx + dw) < tw and (dy + dh) < th:
        draw.rectangle([dx - 1, dy - 1, dx + dw, dy + dh], outline=(0, 0, 0, 160), width=1)
    draw.rectangle([dx, dy, dx + dw - 1, dy + dh - 1], outline=(255, 215, 0, 255), width=1)

    # 3. Subtle corner ticks (length: 2-3px)
    c_len = min(3, max(2, dw // 4), max(2, dh // 4))
    cyan = (0, 240, 255, 255)
    # Top-left
    draw.line([(dx, dy), (dx + c_len, dy)], fill=cyan, width=1)
    draw.line([(dx, dy), (dx, dy + c_len)], fill=cyan, width=1)
    # Top-right
    draw.line([(dx + dw - 1, dy), (dx + dw - 1 - c_len, dy)], fill=cyan, width=1)
    draw.line([(dx + dw - 1, dy), (dx + dw - 1, dy + c_len)], fill=cyan, width=1)
    # Bottom-left
    draw.line([(dx, dy + dh - 1), (dx + c_len, dy + dh - 1)], fill=cyan, width=1)
    draw.line([(dx, dy + dh - 1), (dx, dy + dh - 1 - c_len)], fill=cyan, width=1)
    # Bottom-right
    draw.line([(dx + dw - 1, dy + dh - 1), (dx + dw - 1 - c_len, dy + dh - 1)], fill=cyan, width=1)
    draw.line([(dx + dw - 1, dy + dh - 1), (dx + dw - 1, dy + dh - 1 - c_len)], fill=cyan, width=1)

    return display_img


SAFE_MAX_RENDER_W = 320
SAFE_MAX_RENDER_H = 240


def render_image_to_rich_text(
    img: Image.Image,
    zoom_mode: str = "native",
    max_w: int = 68,
    max_h: int = 38,
    checker_bg: bool = False,
) -> Text:
    """
    Render a PIL image to Rich Text using Unicode half-blocks (▀ and ▄).
    zoom_mode:
        - 'native' / '1x': 100% pixel-perfect 1:1 scale (zero downsampling, zero Moiré)
        - 'fit': fits inside (max_w, max_h) maintaining aspect ratio
        - '2x', '3x', '4x': crisp nearest-neighbor integer zoom
    Equipped with a hard safety clamp to prevent terminal DOM freezes on massive images,
    style caching, and Run-Length Encoding (RLE) to group consecutive identical character runs.
    """
    work_img = img

    if zoom_mode in ("2x", "3x", "4x"):
        scale = int(zoom_mode[0])
        work_img = work_img.resize(
            (work_img.width * scale, work_img.height * scale),
            resample=Image.Resampling.NEAREST,
        )
    elif zoom_mode == "fit":
        if work_img.width > max_w or work_img.height > max_h:
            w, h = calculate_target_box(work_img.width, work_img.height, max_w=max_w, max_h=max_h)
            work_img = work_img.resize((w, h), resample=Image.Resampling.NEAREST)
    else:  # "native" or "1x"
        pass

    # Hard safety clamp: Never send more than SAFE_MAX_RENDER_W x SAFE_MAX_RENDER_H into terminal cells
    if work_img.width > SAFE_MAX_RENDER_W or work_img.height > SAFE_MAX_RENDER_H:
        w, h = calculate_target_box(work_img.width, work_img.height, max_w=SAFE_MAX_RENDER_W, max_h=SAFE_MAX_RENDER_H)
        work_img = work_img.resize((w, h), resample=Image.Resampling.NEAREST)

    # Ensure height is even for half-blocks
    if work_img.height % 2 != 0:
        w, h = work_img.width, work_img.height + 1
        padded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        padded.paste(work_img, (0, 0))
        work_img = padded

    rgba = np.array(work_img.convert("RGBA"))
    h, w, _ = rgba.shape
    text = Text(no_wrap=True)

    style_cache: dict = {}

    for y in range(0, h, 2):
        curr_char = ""
        curr_style = None
        curr_run = 0

        for x in range(w):
            top = rgba[y, x]
            bot = rgba[y + 1, x] if y + 1 < h else np.array([0, 0, 0, 0], dtype=np.uint8)

            top_visible = top[3] >= 128
            bot_visible = bot[3] >= 128

            if not top_visible and not bot_visible:
                if checker_bg:
                    bg_top = (18, 22, 30) if ((x + y) % 2 == 0) else (12, 15, 22)
                    bg_bot = (18, 22, 30) if ((x + y + 1) % 2 == 0) else (12, 15, 22)
                    cell_char = "▀"
                    key = ("chk", bg_top, bg_bot)
                    if key not in style_cache:
                        style_cache[key] = Style(
                            color=f"rgb({bg_top[0]},{bg_top[1]},{bg_top[2]})",
                            bgcolor=f"rgb({bg_bot[0]},{bg_bot[1]},{bg_bot[2]})",
                        )
                    cell_style = style_cache[key]
                else:
                    cell_char = " "
                    cell_style = None
            elif top_visible and not bot_visible:
                cell_char = "▀"
                key = ("top", int(top[0]), int(top[1]), int(top[2]))
                if key not in style_cache:
                    style_cache[key] = Style(color=f"rgb({top[0]},{top[1]},{top[2]})")
                cell_style = style_cache[key]
            elif not top_visible and bot_visible:
                cell_char = "▄"
                key = ("bot", int(bot[0]), int(bot[1]), int(bot[2]))
                if key not in style_cache:
                    style_cache[key] = Style(color=f"rgb({bot[0]},{bot[1]},{bot[2]})")
                cell_style = style_cache[key]
            else:
                cell_char = "▀"
                key = ("both", int(top[0]), int(top[1]), int(top[2]), int(bot[0]), int(bot[1]), int(bot[2]))
                if key not in style_cache:
                    style_cache[key] = Style(
                        color=f"rgb({top[0]},{top[1]},{top[2]})",
                        bgcolor=f"rgb({bot[0]},{bot[1]},{bot[2]})",
                    )
                cell_style = style_cache[key]

            if cell_char == curr_char and cell_style == curr_style:
                curr_run += 1
            else:
                if curr_run > 0:
                    text.append(curr_char * curr_run, style=curr_style)
                curr_char = cell_char
                curr_style = cell_style
                curr_run = 1

        if curr_run > 0:
            text.append(curr_char * curr_run, style=curr_style)

        if y + 2 < h:
            text.append("\n")

    return text


class FilePickerModal(ModalScreen[Optional[Path]]):
    """Visual file tree modal to browse and select image files."""

    CSS = """
    FilePickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #picker-dialog {
        width: 84;
        height: 32;
        border: thick #58a6ff;
        background: #161b22;
        padding: 1 2;
    }

    #tree-container {
        height: 1fr;
        border: round #30363d;
        margin: 1 0;
        background: #0d1117;
    }

    #modal-actions {
        height: auto;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label("📂 Browse & Select Image", classes="section-title")
            with VerticalScroll(id="tree-container"):
                yield DirectoryTree(str(Path.cwd()), id="dir-tree")
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = Path(event.path)
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
            self.dismiss(path)
        else:
            self.notify(f"Selected file is not a supported image: {path.name}", severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)


class CanvasWidget(Static):
    """Widget displaying the live pixel art sprite in terminal cells."""

    DEFAULT_CSS = """
    CanvasWidget {
        width: 100%;
        height: 1fr;
        content-align: center middle;
        overflow: auto auto;
        background: #05060a;
        border: double #00f0ff;
    }
    """


class RetroHeader(Static):
    """Arcade marquee retro header banner."""

    DEFAULT_CSS = """
    RetroHeader {
        height: 3;
        dock: top;
        content-align: center middle;
        text-style: bold;
        background: #0c0f17;
        color: #00f0ff;
        border-bottom: heavy #00f0ff;
    }
    """

    def render(self) -> Text:
        banner = Text()
        banner.append("🕹️  P I X E L A R T   S T U D I O   v 2 . 0  ", style="bold #00f5ff")
        banner.append("══╡ ", style="bold #ff007f")
        banner.append("ARCADE SPRITE ENGINE", style="bold #ffd700")
        banner.append(" ╞══ ", style="bold #ff007f")
        banner.append("[● LIVE RETRO TUI]", style="bold #39ff14")
        return banner


class PixelArtStudio(App):
    """Interactive Retro Pixel Art Studio TUI with live Cropping & Panning."""

    TITLE = "PixelArt Studio 🕹️"
    SUB_TITLE = "Retro Sprite Converter & Live Cropping Studio"
    CSS = """
    Screen {
        background: #07080d;
    }

    /* Warning overlay when terminal is too small */
    #warning-screen {
        width: 100%;
        height: 100%;
        align: center middle;
        background: #07080d;
        color: #e6edf3;
        display: none;
    }

    #warning-box {
        width: 72;
        height: auto;
        border: thick #f85149;
        background: #111420;
        padding: 2 3;
        align: center middle;
        text-align: center;
    }

    .warn-title {
        color: #f85149;
        text-style: bold;
        margin-bottom: 1;
    }

    .warn-dim {
        color: #58a6ff;
        text-style: bold;
        margin: 1 0;
    }

    .warn-tip {
        color: #8b949e;
        margin-top: 1;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #sidebar {
        width: 44;
        height: 100%;
        background: #0c0f17;
        border-right: double #00f0ff;
        padding: 1 2;
    }

    #preview-area {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }

    .section-title {
        text-style: bold;
        color: #00f0ff;
        margin-top: 1;
        margin-bottom: 0;
    }

    .field-label {
        color: #8b949e;
        margin-top: 0;
        margin-bottom: 0;
    }

    Rule {
        margin: 0;
    }

    .switch-row {
        height: auto;
        margin-top: 0;
        align: left middle;
    }

    .action-btn {
        width: 100%;
        margin-top: 1;
    }

    #status-bar {
        height: 3;
        background: #0c0f17;
        color: #39ff14;
        padding: 0 1;
        content-align: left middle;
        border: double #39ff14;
        margin-top: 1;
        text-style: bold;
    }

    #info-bar {
        height: 3;
        background: #0c0f17;
        color: #ffd700;
        content-align: center middle;
        text-style: bold;
        border: double #ffd700;
        margin-bottom: 1;
    }

    #viewfinder-hud, #slice-hud {
        height: 3;
        background: #0c0f17;
        color: #00f0ff;
        content-align: center middle;
        text-style: bold;
        border: double #00f0ff;
        margin-bottom: 0;
    }

    #zoom-bar {
        height: 3;
        align: left middle;
        padding: 0 1;
        margin-bottom: 0;
        background: #0c0f17;
        border: double #ffb000;
    }

    .zoom-lbl {
        content-align: left middle;
        text-style: bold;
        color: #ffb000;
        margin-right: 1;
    }

    .zoom-btn {
        height: 1;
        min-width: 8;
        padding: 0 1;
        margin-right: 1;
        background: #1a2234;
        color: #8b949e;
        border: none;
    }

    .zoom-btn.active-zoom {
        background: #ffb000;
        color: #07080d;
        text-style: bold;
    }

    .button-row {
        height: auto;
        margin-top: 1;
    }

    .button-row Button {
        width: 1fr;
        min-width: 0;
        margin-right: 1;
    }

    .button-row Button:last-of-type {
        margin-right: 0;
    }

    .dim-row {
        height: 3;
        margin-top: 0;
        align: left middle;
    }

    .dim-row .dim-lbl {
        width: 3;
        content-align: left middle;
        text-style: bold;
        color: #00f0ff;
    }

    .dim-row Input {
        width: 1fr;
        min-width: 0;
        margin-right: 1;
    }

    .dim-row Button {
        width: 6;
        min-width: 0;
        margin-right: 1;
        padding: 0;
    }

    .dim-row Button:last-of-type {
        margin-right: 0;
    }

    .crop-row {
        height: auto;
        margin-top: 1;
    }

    .crop-row Input {
        width: 1fr;
        min-width: 0;
        margin-right: 1;
    }

    .crop-row Input:last-of-type {
        margin-right: 0;
    }

    .dpad-container {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    .dpad-row {
        height: auto;
        align: center middle;
    }

    .dpad-row Button {
        min-width: 6;
        margin: 0 1;
    }

    Switch {
        margin-top: 1;
    }

    Horizontal.switch-row {
        height: auto;
        align: left middle;
    }

    #preview-tabs {
        height: 1fr;
    }

    TabPane {
        padding: 0;
        height: 1fr;
    }

    /* THEME: Arcade Neon (Default) */
    .theme-arcade Screen {
        background: #07080d;
    }
    .theme-arcade #sidebar {
        background: #0c0f17;
        border-right: double #00f0ff;
    }
    .theme-arcade CanvasWidget {
        border: double #00f0ff;
        background: #05060a;
    }
    .theme-arcade RetroHeader {
        background: #0c0f17;
        color: #00f0ff;
        border-bottom: heavy #00f0ff;
    }
    .theme-arcade #zoom-bar {
        background: #0c0f17;
        border: double #ffb000;
    }

    /* THEME: MS-DOS Commander */
    .theme-dos Screen {
        background: #000080;
    }
    .theme-dos #sidebar {
        background: #0000a8;
        border-right: double #00ffff;
    }
    .theme-dos .section-title {
        color: #ffff00;
    }
    .theme-dos Button {
        background: #00aaaa;
        color: #000000;
    }
    .theme-dos CanvasWidget {
        border: double #00ffff;
        background: #000050;
    }
    .theme-dos #status-bar {
        background: #00aaaa;
        color: #000000;
        border: double #00ffff;
    }
    .theme-dos #info-bar {
        background: #0000a8;
        color: #ffff00;
        border: double #00ffff;
    }
    .theme-dos RetroHeader {
        background: #000080;
        color: #ffff00;
        border-bottom: heavy #00ffff;
    }
    .theme-dos #zoom-bar {
        background: #0000a8;
        border: double #00ffff;
    }

    /* THEME: CRT Amber Phosphor */
    .theme-amber Screen {
        background: #080400;
    }
    .theme-amber #sidebar {
        background: #140a00;
        border-right: double #ff9000;
    }
    .theme-amber .section-title {
        color: #ffb000;
    }
    .theme-amber Button {
        background: #2a1500;
        color: #ffb000;
    }
    .theme-amber CanvasWidget {
        border: double #ffb000;
        background: #0a0500;
    }
    .theme-amber #status-bar {
        background: #140a00;
        color: #ffb000;
        border: double #ff9000;
    }
    .theme-amber #info-bar {
        background: #140a00;
        color: #ffd060;
        border: double #ffb000;
    }
    .theme-amber RetroHeader {
        background: #140a00;
        color: #ffb000;
        border-bottom: heavy #ff9000;
    }
    .theme-amber #zoom-bar {
        background: #140a00;
        border: double #ff9000;
    }

    /* THEME: CRT Green Matrix */
    .theme-green Screen {
        background: #000a02;
    }
    .theme-green #sidebar {
        background: #001505;
        border-right: double #00ff41;
    }
    .theme-green .section-title {
        color: #39ff14;
    }
    .theme-green Button {
        background: #002509;
        color: #00ff41;
    }
    .theme-green CanvasWidget {
        border: double #00ff41;
        background: #000e03;
    }
    .theme-green #status-bar {
        background: #001505;
        color: #39ff14;
        border: double #00ff41;
    }
    .theme-green #info-bar {
        background: #001505;
        color: #70ff70;
        border: double #00ff41;
    }
    .theme-green RetroHeader {
        background: #001505;
        color: #39ff14;
        border-bottom: heavy #00ff41;
    }
    .theme-green #zoom-bar {
        background: #001505;
        border: double #00ff41;
    }

    /* THEME: Game Boy DMG */
    .theme-dmg Screen {
        background: #0f380f;
    }
    .theme-dmg #sidebar {
        background: #306230;
        border-right: double #8bac0f;
    }
    .theme-dmg .section-title {
        color: #9bbc0f;
    }
    .theme-dmg Button {
        background: #0f380f;
        color: #9bbc0f;
    }
    .theme-dmg CanvasWidget {
        border: double #9bbc0f;
        background: #0f380f;
    }
    .theme-dmg #status-bar {
        background: #306230;
        color: #9bbc0f;
        border: double #8bac0f;
    }
    .theme-dmg #info-bar {
        background: #306230;
        color: #9bbc0f;
        border: double #8bac0f;
    }
    .theme-dmg RetroHeader {
        background: #306230;
        color: #9bbc0f;
        border-bottom: heavy #8bac0f;
    }
    .theme-dmg #zoom-bar {
        background: #306230;
        border: double #8bac0f;
    }

    /* THEME: Cyberpunk Synthwave */
    .theme-cyberpunk Screen {
        background: #0d0221;
    }
    .theme-cyberpunk #sidebar {
        background: #17073b;
        border-right: double #ff007f;
    }
    .theme-cyberpunk .section-title {
        color: #00fff5;
    }
    .theme-cyberpunk Button {
        background: #260a5e;
        color: #ff007f;
    }
    .theme-cyberpunk CanvasWidget {
        border: double #00fff5;
        background: #080117;
    }
    .theme-cyberpunk #status-bar {
        background: #17073b;
        color: #00fff5;
        border: double #00fff5;
    }
    .theme-cyberpunk #info-bar {
        background: #17073b;
        color: #ff007f;
        border: double #ff007f;
    }
    .theme-cyberpunk RetroHeader {
        background: #17073b;
        color: #ff007f;
        border-bottom: heavy #ff007f;
    }
    .theme-cyberpunk #zoom-bar {
        background: #17073b;
        border: double #ff007f;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "browse_files", "Browse Files"),
        ("s", "save_preview", "Save PNG"),
        ("c", "export_c", "Export C"),
        ("p", "export_pico8", "Export PICO-8"),
        ("z", "cycle_zoom", "Cycle Zoom"),
        ("t", "cycle_theme", "Cycle Theme"),
        ("up", "crop_up", "Pan Up"),
        ("down", "crop_down", "Pan Down"),
        ("left", "crop_left", "Pan Left"),
        ("right", "crop_right", "Pan Right"),
        ("1", "tab_pixel", "Pixel Art"),
        ("2", "tab_viewfinder", "Viewfinder"),
        ("3", "tab_slice", "Cropped Slice"),
    ]

    THEMES = ["arcade", "dos", "amber", "green", "dmg", "cyberpunk"]
    ZOOM_MODES = ["native", "fit", "2x", "3x", "4x"]

    preview_zoom: reactive[str] = reactive("native")
    ui_retro_theme: reactive[str] = reactive("arcade")

    current_image_path: reactive[Optional[str]] = reactive(None)
    current_source_img: Optional[Image.Image] = None
    processed_sprite: Optional[Image.Image] = None
    last_indices: Optional[np.ndarray] = None
    last_palette: Optional[list] = None

    # Crop state
    crop_enabled: bool = False
    crop_x: int = 0
    crop_y: int = 0
    crop_w: int = 0
    crop_h: int = 0
    crop_step: int = 10
    _updating_inputs: bool = False
    _updating_theme: bool = False
    _updating_controls: bool = False
    _was_too_small: bool = False
    _initialized: bool = False

    def __init__(self, initial_image: Optional[str] = None):
        super().__init__()
        self.initial_image = initial_image
        self._initialized = False

    def compose(self) -> ComposeResult:
        yield RetroHeader(id="retro-marquee")

        # Full-screen Warning for Small Terminal
        with Container(id="warning-screen"):
            with Vertical(id="warning-box"):
                yield Label("⚠️  PLEASE MAXIMIZE TERMINAL", classes="warn-title")
                yield Label(
                    "PixelArt Studio requires a larger terminal window\n"
                    "for side-by-side retro rendering and image controls."
                )
                yield Label("Current Size: 80 x 24 | Required: 100 x 28", id="warn-size-lbl", classes="warn-dim")
                yield Label(
                    "💡 Please maximize or expand your terminal window\n"
                    "(Press ⌃⌘F on macOS or drag the window edge to full screen)",
                    classes="warn-tip"
                )

        # Main Studio Layout
        with Horizontal(id="main-container"):
            # Left Control Sidebar
            with VerticalScroll(id="sidebar"):
                yield Label("🕹️ RETRO UI THEME", classes="section-title")
                theme_options = [
                    ("Arcade Neon (Default)", "arcade"),
                    ("MS-DOS Commander (1990)", "dos"),
                    ("CRT Amber Phosphor", "amber"),
                    ("CRT Green Matrix", "green"),
                    ("Game Boy DMG-01", "dmg"),
                    ("Cyberpunk Synthwave", "cyberpunk"),
                ]
                yield Select(theme_options, value="arcade", id="select-ui-theme", allow_blank=False)

                yield Rule()
                yield Label("SOURCE IMAGE", classes="section-title")

                # Quick pick dropdown
                local_images = get_available_local_images()
                yield Label("Quick Select in Folder:", classes="field-label")
                yield Select(
                    local_images,
                    prompt="Choose image in current directory...",
                    id="select-quick-image",
                    allow_blank=True,
                )

                yield Label("Or Enter / Paste Path:", classes="field-label")
                yield Input(
                    placeholder="e.g. rome.png or /path/to/img",
                    id="input-path",
                    value=self.initial_image or "rome.png",
                )

                with Horizontal(classes="button-row"):
                    yield Button("Load", id="btn-load", variant="primary")
                    yield Button("📂 Browse...", id="btn-browse", variant="default")

                yield Rule()
                # ✂️ CROP & FRAMING SECTION
                yield Label("✂️ LIVE CROP & FRAMING", classes="section-title")
                with Horizontal(classes="switch-row"):
                    yield Label("Enable Cropping: ", classes="field-label")
                    yield Switch(value=False, id="switch-crop")

                yield Label("Original: 0 x 0 px", id="label-crop-info", classes="field-label")

                yield Label("Crop Dimensions:", classes="field-label")
                with Horizontal(classes="dim-row"):
                    yield Label("W:", classes="dim-lbl")
                    yield Input(placeholder="Width", id="input-crop-w")
                    yield Button("−", id="btn-shrink-w")
                    yield Button("+", id="btn-grow-w")

                with Horizontal(classes="dim-row"):
                    yield Label("H:", classes="dim-lbl")
                    yield Input(placeholder="Height", id="input-crop-h")
                    yield Button("−", id="btn-shrink-h")
                    yield Button("+", id="btn-grow-h")

                yield Label("Offset Position (X, Y):", classes="field-label")
                with Horizontal(classes="crop-row"):
                    yield Input(placeholder="X", id="input-crop-x")
                    yield Input(placeholder="Y", id="input-crop-y")

                yield Label("Nudge Step:", classes="field-label")
                yield Select(
                    [
                        ("1 px (Pixel Precision)", "1"),
                        ("5 px", "5"),
                        ("10 px (Default)", "10"),
                        ("25 px", "25"),
                        ("50 px (Fast)", "50"),
                    ],
                    value="10",
                    id="select-crop-step",
                    allow_blank=False,
                )

                # D-Pad for panning
                with Vertical(classes="dpad-container"):
                    with Horizontal(classes="dpad-row"):
                        yield Button("▲ Up", id="btn-crop-up")
                    with Horizontal(classes="dpad-row"):
                        yield Button("◄ Left", id="btn-crop-left")
                        yield Button("🎯 Center", id="btn-crop-center")
                        yield Button("Right ►", id="btn-crop-right")
                    with Horizontal(classes="dpad-row"):
                        yield Button("▼ Down", id="btn-crop-down")

                with Horizontal(classes="button-row"):
                    yield Button("1:1 Square", id="btn-crop-square")
                    yield Button("Reset Full", id="btn-crop-full")

                yield Rule()
                # SPRITE SETTINGS
                yield Label("SPRITE SETTINGS", classes="section-title")

                yield Label("Target Resolution:", classes="field-label")
                yield Select(
                    [
                        ("Original / Crop Size (100% Native 1:1)", "original"),
                        ("Half Size (50%)", "half"),
                        ("128 px (High-Res Retro)", "128"),
                        ("96 px (Large Scene)", "96"),
                        ("64 px (Portrait / Boss)", "64"),
                        ("48 px (Detailed Character)", "48"),
                        ("32 px (Standard Sprite)", "32"),
                        ("24 px (Classic RPG)", "24"),
                        ("16 px (Tiny Icon)", "16"),
                    ],
                    value="original",
                    id="select-resolution",
                    allow_blank=False,
                )

                yield Label("Aspect Ratio Mode:", classes="field-label")
                yield Select(
                    [
                        ("Fit Proportional (Recommended)", "fit"),
                        ("Force Square (NxN)", "square"),
                    ],
                    value="fit",
                    id="select-aspect",
                    allow_blank=False,
                )

                yield Label("Hardware Palette:", classes="field-label")
                palette_options = [
                    ("Modern Full Color (24-bit TrueColor)", "full-color"),
                    ("Adaptive 16 Colors (SNES / GBA Best)", "adaptive"),
                    ("Modern Adaptive 256 Colors (Rich / VGA)", "adaptive-256"),
                    ("Endesga 64 (Modern 64 Colors)", "endesga64"),
                    ("Resurrect 64 (Indie 64 Colors)", "resurrect64"),
                    ("Endesga 32 (Modern Pixel Art)", "endesga32"),
                    ("SNES Curated (16 Classic Colors)", "snes"),
                    ("SNES Adaptive (15-bit Hardware Snap)", "snes-adaptive"),
                    ("Sega Genesis / Mega Drive (16 Colors)", "genesis"),
                    ("Genesis Adaptive (9-bit Hardware Snap)", "genesis-adaptive"),
                    ("GBA Curated (16 Colors)", "gba"),
                    ("NES (54 Colors)", "nes"),
                    ("Game Boy DMG (4 Greens)", "gameboy"),
                    ("Game Boy Pocket (4 Greys)", "gameboy-pocket"),
                    ("Game Boy Color (16 Colors)", "gbc"),
                    ("Commodore 64 (16 Colors)", "c64"),
                    ("NEC PC-9801 (16 Colors)", "pc98"),
                    ("Amiga OCS (16 Colors)", "amiga"),
                    ("Apple II (16 Colors)", "apple2"),
                    ("Amstrad CPC (16 Colors)", "amstrad-cpc"),
                    ("Sega Master System (16 Colors)", "mastersystem"),
                    ("Sega Game Gear (16 Colors)", "gamegear"),
                    ("Atari 2600 VCS (16 Colors)", "atari2600"),
                    ("PICO-8 (16 Colors)", "pico8"),
                    ("PICO-8 Secret (32 Colors)", "pico8-secret"),
                    ("TIC-80 (Sweetie 16)", "tic80"),
                    ("CGA Mode 1 (Cyan/Magenta)", "cga-mode1"),
                    ("CGA Mode 0 (Green/Red)", "cga-mode0"),
                    ("ZX Spectrum (15 Colors)", "zx-spectrum"),
                    ("Cyberpunk Synthwave", "cyberpunk"),
                    ("1-Bit Monochrome (B&W)", "1bit"),
                    ("CRT Phosphor Green (Terminal)", "crt-green"),
                    ("CRT Amber Phosphor (Terminal)", "crt-amber"),
                ]
                yield Select(palette_options, value="adaptive", id="select-palette", allow_blank=False)

                yield Label("Dithering Method:", classes="field-label")
                dither_options = [
                    ("None (Cel-Shaded / Clean)", "none"),
                    ("Bayer 4x4 (Classic Crosshatch)", "bayer-4x4"),
                    ("Bayer 2x2 (Coarse Crosshatch)", "bayer-2x2"),
                    ("Bayer 8x8 (Fine Ordered)", "bayer-8x8"),
                    ("Checkerboard (1x1 Genesis Mesh)", "checkerboard"),
                    ("Blue Noise (Organic Grain / Obra Dinn)", "blue-noise"),
                    ("Floyd-Steinberg (Error Diffusion)", "floyd"),
                    ("Atkinson (Apple Mac 1984 Crisp)", "atkinson"),
                    ("Burkes (Fast Error Diffusion)", "burkes"),
                    ("Sierra (Two-Row Smooth Diffusion)", "sierra"),
                    ("Stucki (High-Detail Error Diffusion)", "stucki"),
                ]
                yield Select(dither_options, value="none", id="select-dither", allow_blank=False)

                with Horizontal(classes="switch-row"):
                    yield Label("Sprite Dark Outline: ", classes="field-label")
                    yield Switch(value=False, id="switch-outline")

                yield Label("Color Enhancement:", classes="field-label")
                enhance_options = [
                    ("Default Balanced (1.25x)", "default"),
                    ("Vibrant Arcade (Punchy Saturation)", "vibrant"),
                    ("High Contrast (Dramatic Shadows)", "contrast"),
                    ("Warm CRT Glow (Amber Warmth)", "warm-crt"),
                    ("Cool Cyberpunk (Cyan/Blue Shift)", "cool-cyber"),
                    ("CRT Green Phosphor (Matrix Terminal)", "crt-green"),
                    ("CRT Amber Terminal (Phosphor Amber)", "crt-amber"),
                    ("Sepia Nostalgia (Vintage Tone)", "sepia"),
                    ("Muted / Pastel (Soft Indie Style)", "muted"),
                    ("Crisp Edge Detail (Sharp Pixels)", "sharp"),
                    ("Natural / Flat (1.0x Neutral)", "flat"),
                ]
                yield Select(enhance_options, value="default", id="select-enhance", allow_blank=False)

                yield Rule()
                yield Label("EXPORT ASSETS", classes="section-title")

                yield Label("Preview Upscale Factor:", classes="field-label")
                yield Select(
                    [
                        ("1x (Native Game Size)", "1"),
                        ("4x Scale", "4"),
                        ("8x Scale (Recommended)", "8"),
                        ("16x Scale (High DPI)", "16"),
                    ],
                    value="8",
                    id="select-scale",
                    allow_blank=False,
                )

                yield Button("💾 Save Preview PNG", id="btn-save-preview", variant="success", classes="action-btn")
                yield Button("📦 Save Native 1x Sprite", id="btn-save-raw", variant="default", classes="action-btn")
                yield Button("🕹️ Export C Header (.h)", id="btn-export-c", variant="default", classes="action-btn")
                yield Button("👾 Export PICO-8 String", id="btn-export-pico8", variant="default", classes="action-btn")

            # Right Preview Area with Stable Tabs
            with Vertical(id="preview-area"):
                yield Static("No Image Loaded", id="info-bar")
                with TabbedContent(id="preview-tabs"):
                    with TabPane("👾 Pixel Art", id="tab-pixel"):
                        with Horizontal(id="zoom-bar"):
                            yield Label("🔍 ZOOM:", classes="zoom-lbl")
                            yield Button("1x Native", id="btn-zoom-native", classes="zoom-btn active-zoom")
                            yield Button("Fit Screen", id="btn-zoom-fit", classes="zoom-btn")
                            yield Button("2x", id="btn-zoom-2x", classes="zoom-btn")
                            yield Button("3x", id="btn-zoom-3x", classes="zoom-btn")
                            yield Button("4x", id="btn-zoom-4x", classes="zoom-btn")
                        yield CanvasWidget(id="canvas-pixel")
                    with TabPane("✂️ Viewfinder (Full)", id="tab-source"):
                        yield Static("📷 Viewfinder: Full Frame", id="viewfinder-hud")
                        yield CanvasWidget(id="canvas-source")
                    with TabPane("🔍 Cropped Slice", id="tab-crop-slice"):
                        yield Static("✂️ Cropped Slice", id="slice-hud")
                        yield CanvasWidget(id="canvas-slice")
                yield Static("Ready", id="status-bar")

        yield Footer()

    def check_terminal_size(self, width: int, height: int) -> None:
        """Check terminal dimensions and toggle warning screen."""
        too_small = width < MIN_TERMINAL_WIDTH or height < MIN_TERMINAL_HEIGHT
        warn_screen = self.query_one("#warning-screen", Container)
        main_ui = self.query_one("#main-container", Horizontal)

        warn_screen.display = too_small
        main_ui.display = not too_small

        if too_small:
            warn_lbl = self.query_one("#warn-size-lbl", Label)
            warn_lbl.update(
                f"Current Size: {width} x {height} | Required Minimum: {MIN_TERMINAL_WIDTH} x {MIN_TERMINAL_HEIGHT}"
            )
            self._was_too_small = True
        else:
            if self._was_too_small and self._initialized and self.current_source_img:
                self._was_too_small = False
                self.reprocess_pixel_art()

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal window resize dynamically."""
        self.check_terminal_size(event.size.width, event.size.height)

    def on_mount(self) -> None:
        """Load initial image upon launch and verify terminal size."""
        self.apply_theme(self.ui_retro_theme, notify=False)
        self.check_terminal_size(self.size.width, self.size.height)

        initial_path = self.initial_image
        if not initial_path:
            if Path("rome.png").exists():
                initial_path = "rome.png"
            elif Path("sample_input.png").exists():
                initial_path = "sample_input.png"
            else:
                local_images = get_available_local_images()
                if local_images and local_images[0][1]:
                    initial_path = local_images[0][1]
        if initial_path:
            self.load_image(str(initial_path))
        self._initialized = True

    def set_status(self, message: str, is_error: bool = False) -> None:
        """Update bottom status banner and trigger visual notification toast."""
        try:
            status_bar = self.query_one("#status-bar", Static)
            prefix = "❌ " if is_error else "✨ "
            status_bar.update(f"{prefix}{message}")
        except Exception:
            pass

    def load_image(self, file_path_str: str) -> None:
        """Robustly resolve and load an image from user string."""
        resolved = resolve_image_path(file_path_str)
        if not resolved:
            self.set_status(f"File not found: '{file_path_str}'", is_error=True)
            self.notify(f"Could not find: '{file_path_str}'. Check file name or path.", title="File Not Found", severity="error")
            return

        self._updating_controls = True
        try:
            self.current_source_img = Image.open(resolved)
            self.current_image_path = str(resolved)

            # Update input field display
            inp = self.query_one("#input-path", Input)
            inp.value = resolved.name

            # Reset crop to full image bounds or centered framing for large images
            orig_w, orig_h = self.current_source_img.size
            max_dim = max(orig_w, orig_h)
            if not self.crop_enabled:
                if max_dim <= 256:
                    self.crop_x = 0
                    self.crop_y = 0
                    self.crop_w = orig_w
                    self.crop_h = orig_h
                else:
                    crop_dim = min(orig_w, orig_h, 256)
                    self.crop_w = crop_dim
                    self.crop_h = crop_dim
                    self.crop_x = (orig_w - crop_dim) // 2
                    self.crop_y = (orig_h - crop_dim) // 2
            else:
                self.crop_w = min(self.crop_w or orig_w, orig_w)
                self.crop_h = min(self.crop_h or orig_h, orig_h)
                self.crop_x = min(self.crop_x, orig_w - self.crop_w)
                self.crop_y = min(self.crop_y, orig_h - self.crop_h)

            self.update_crop_input_fields()

            # Set resolution dropdown appropriately
            try:
                res_select = self.query_one("#select-resolution", Select)
                if max_dim <= 256:
                    if res_select.value != "original":
                        res_select.value = "original"
                else:
                    if res_select.value != "128":
                        res_select.value = "128"
            except Exception:
                pass

            # Proportional nudge step for large images
            if max_dim >= 1024:
                self.crop_step = 25
                try:
                    self.query_one("#select-crop-step", Select).value = "25"
                except Exception:
                    pass
            elif max_dim >= 512:
                self.crop_step = 10
                try:
                    self.query_one("#select-crop-step", Select).value = "10"
                except Exception:
                    pass

            # Sync select-quick-image if this file is in options
            quick_select = self.query_one("#select-quick-image", Select)
            for _, val in quick_select._options:
                if val and str(val) == str(resolved):
                    if quick_select.value != val:
                        quick_select.value = val
                    break

            msg = f"Loaded {resolved.name} ({orig_w}x{orig_h})"
            self.set_status(msg)
            self.notify(msg, title="Image Loaded", severity="information")
        except Exception as e:
            err_msg = f"Error opening image: {e}"
            self.set_status(err_msg, is_error=True)
            self.notify(err_msg, title="Image Error", severity="error")
        finally:
            self._updating_controls = False

        self.reprocess_pixel_art()

    def update_crop_input_fields(self) -> None:
        """Update crop input values in sidebar."""
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self._updating_inputs = True
        try:
            self.query_one("#input-crop-w", Input).value = str(self.crop_w)
            self.query_one("#input-crop-h", Input).value = str(self.crop_h)
            self.query_one("#input-crop-x", Input).value = str(self.crop_x)
            self.query_one("#input-crop-y", Input).value = str(self.crop_y)
        finally:
            self._updating_inputs = False

        info_lbl = self.query_one("#label-crop-info", Label)
        pct = int((self.crop_w * self.crop_h) / (orig_w * orig_h) * 100) if (orig_w * orig_h) > 0 else 100
        info_lbl.update(f"Orig: {orig_w}x{orig_h} | Crop: {self.crop_w}x{self.crop_h} ({pct}%)")

    @work(exclusive=True, thread=True)
    def reprocess_pixel_art(self) -> None:
        """Re-run conversion pipeline in background worker without blocking UI event loop."""
        if self.current_source_img is None:
            return

        try:
            orig_w, orig_h = self.current_source_img.size

            # Capture crop coordinates
            crop_enabled = self.crop_enabled
            crop_x, crop_y = self.crop_x, self.crop_y
            crop_w, crop_h = self.crop_w, self.crop_h

            if crop_enabled:
                crop_box = (crop_x, crop_y, crop_w, crop_h)
                source_to_render = self.current_source_img.crop((
                    crop_x,
                    crop_y,
                    crop_x + crop_w,
                    crop_y + crop_h
                ))
            else:
                crop_box = None
                source_to_render = self.current_source_img

            # Query control values safely
            res_val = str(self.query_one("#select-resolution", Select).value)
            aspect_mode = str(self.query_one("#select-aspect", Select).value)
            palette_val = str(self.query_one("#select-palette", Select).value)
            dither_val = str(self.query_one("#select-dither", Select).value)
            outline_val = bool(self.query_one("#switch-outline", Switch).value)
            # Resolve color enhancement preset
            enhance_key = str(self.query_one("#select-enhance", Select).value).lower()
            if enhance_key in ENHANCEMENT_PRESETS:
                ep = ENHANCEMENT_PRESETS[enhance_key]
                con_val = ep["contrast"]
                sat_val = ep["saturation"]
                shp_val = ep["sharpness"]
                bri_val = ep["brightness"]
                gam_val = ep["gamma"]
                wrm_val = ep["warmth"]
                tnt_val = ep["tint"]
            else:
                try:
                    num = float(enhance_key)
                    con_val = sat_val = num
                except ValueError:
                    con_val = sat_val = 1.25
                shp_val = 1.30
                bri_val = gam_val = 1.0
                wrm_val = 0.0
                tnt_val = None

            # Resolution calculation with retro hardware limits
            effective_w, effective_h = source_to_render.size
            if res_val == "original":
                if crop_enabled:
                    target_w = min(effective_w, 320)
                    target_h = min(effective_h, 240)
                else:
                    if max(effective_w, effective_h) > 256:
                        target_w, target_h = calculate_target_size(
                            effective_w,
                            effective_h,
                            max_dimension=256,
                        )
                    else:
                        target_w, target_h = min(effective_w, 320), min(effective_h, 240)
            elif res_val == "half":
                target_w = max(1, min(effective_w // 2, 256))
                target_h = max(1, min(effective_h // 2, 240))
            else:
                target_dim = int(res_val)
                if aspect_mode == "fit":
                    target_w, target_h = calculate_target_size(
                        effective_w,
                        effective_h,
                        max_dimension=target_dim,
                    )
                else:
                    target_w, target_h = target_dim, target_dim

            sprite, indices, palette = convert_to_pixel_art(
                self.current_source_img,
                target_width=target_w,
                target_height=target_h,
                palette_name_or_spec=palette_val,
                dither_mode=dither_val,
                add_outline=outline_val,
                contrast=con_val,
                saturation=sat_val,
                sharpness=shp_val,
                brightness=bri_val,
                gamma=gam_val,
                warmth=wrm_val,
                tint=tnt_val,
                crop_box=crop_box,
            )

            # 1. Render converted pixel art cleanly constrained to canvas display
            rich_pixel = render_image_to_rich_text(
                sprite,
                zoom_mode=self.preview_zoom,
                max_w=68,
                max_h=38,
            )

            # 2. Render razor-sharp camera viewfinder
            viewfinder_img = create_viewfinder_image(
                self.current_source_img,
                crop_x if crop_enabled else 0,
                crop_y if crop_enabled else 0,
                crop_w if crop_enabled else orig_w,
                crop_h if crop_enabled else orig_h,
                crop_enabled=crop_enabled,
                max_w=68,
                max_h=38,
            )
            rich_viewfinder = render_image_to_rich_text(viewfinder_img, zoom_mode="fit", max_w=68, max_h=38)

            # 3. Render cropped slice (high-detail preview)
            if crop_enabled:
                slice_img = self.current_source_img.crop((
                    crop_x,
                    crop_y,
                    crop_x + crop_w,
                    crop_y + crop_h,
                ))
                slice_hud = f"✂️ Cropped Slice: {crop_w}x{crop_h} px (Offset: X={crop_x}, Y={crop_y})"
                pct = int((crop_w * crop_h) / (orig_w * orig_h) * 100) if (orig_w * orig_h) > 0 else 100
                vf_hud = f"📷 Source: {orig_w}x{orig_h} | ✂️ Crop Box: {crop_w}x{crop_h} at ({crop_x}, {crop_y}) [{pct}% of frame]"
            else:
                slice_img = self.current_source_img
                slice_hud = f"🖼️ Full Source Image: {orig_w}x{orig_h} px (Sub-region crop disabled)"
                vf_hud = f"📷 Source: {orig_w}x{orig_h} | ✂️ Full Frame (Sub-region crop disabled in sidebar)"

            rich_slice = render_image_to_rich_text(slice_img, zoom_mode="fit", max_w=68, max_h=38)

            # Update info bar text
            crop_str = f"Crop: {crop_w}x{crop_h}" if crop_enabled else "Full Size"
            palette_disp = "24-bit TrueColor" if palette_val == "full-color" else f"{palette_val} ({len(palette)}c)"
            info_text = (
                f"Sprite: {sprite.width}x{sprite.height} | {crop_str} | "
                f"Palette: {palette_disp} | Dither: {dither_val}"
            )

            self.call_from_thread(
                self._apply_reprocessed_result,
                sprite,
                indices,
                palette,
                rich_pixel,
                rich_viewfinder,
                rich_slice,
                vf_hud,
                slice_hud,
                info_text,
            )
        except Exception as e:
            self.call_from_thread(self.set_status, f"Processing error: {e}", True)

    def _apply_reprocessed_result(
        self,
        sprite: Image.Image,
        indices: np.ndarray,
        palette: list,
        rich_pixel: Text,
        rich_viewfinder: Text,
        rich_slice: Text,
        vf_hud: str,
        slice_hud: str,
        info_text: str,
    ) -> None:
        """Apply rendered sprites to UI widgets on main thread."""
        self.processed_sprite = sprite
        self.last_indices = indices
        self.last_palette = palette

        self.query_one("#canvas-pixel", CanvasWidget).update(rich_pixel)
        self.query_one("#canvas-source", CanvasWidget).update(rich_viewfinder)
        self.query_one("#canvas-slice", CanvasWidget).update(rich_slice)
        self.query_one("#viewfinder-hud", Static).update(vf_hud)
        self.query_one("#slice-hud", Static).update(slice_hud)
        self.query_one("#info-bar", Static).update(info_text)

    # Tab switching actions
    def action_tab_pixel(self) -> None:
        self.query_one("#preview-tabs", TabbedContent).active = "tab-pixel"

    def action_tab_viewfinder(self) -> None:
        self.query_one("#preview-tabs", TabbedContent).active = "tab-source"

    def action_tab_slice(self) -> None:
        self.query_one("#preview-tabs", TabbedContent).active = "tab-crop-slice"

    # Crop manipulation actions
    def action_crop_up(self) -> None:
        if not self.current_source_img:
            return
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True
        self.crop_y = max(0, self.crop_y - self.crop_step)
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def action_crop_down(self) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True
        self.crop_y = min(max(0, orig_h - self.crop_h), self.crop_y + self.crop_step)
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def action_crop_left(self) -> None:
        if not self.current_source_img:
            return
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True
        self.crop_x = max(0, self.crop_x - self.crop_step)
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def action_crop_right(self) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True
        self.crop_x = min(max(0, orig_w - self.crop_w), self.crop_x + self.crop_step)
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def resize_crop(self, delta_w: int, delta_h: int) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True

        new_w = max(4, min(self.crop_w + delta_w, orig_w))
        new_h = max(4, min(self.crop_h + delta_h, orig_h))

        if self.crop_x + new_w > orig_w:
            self.crop_x = max(0, orig_w - new_w)
        if self.crop_y + new_h > orig_h:
            self.crop_y = max(0, orig_h - new_h)

        self.crop_w = new_w
        self.crop_h = new_h
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def center_crop(self) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self.crop_x = max(0, (orig_w - self.crop_w) // 2)
        self.crop_y = max(0, (orig_h - self.crop_h) // 2)
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def make_square_crop(self) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        side = min(orig_w, orig_h)
        self.crop_w = side
        self.crop_h = side
        self.crop_x = (orig_w - side) // 2
        self.crop_y = (orig_h - side) // 2
        self.crop_enabled = True
        self.query_one("#switch-crop", Switch).value = True
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def reset_full_crop(self) -> None:
        if not self.current_source_img:
            return
        orig_w, orig_h = self.current_source_img.size
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = orig_w
        self.crop_h = orig_h
        self.update_crop_input_fields()
        self.reprocess_pixel_art()

    def apply_manual_crop_inputs(self) -> None:
        """Parse user-typed crop width, height, x, and y in real-time."""
        if not self.current_source_img or self._updating_inputs:
            return
        orig_w, orig_h = self.current_source_img.size

        try:
            w_str = self.query_one("#input-crop-w", Input).value.strip()
            h_str = self.query_one("#input-crop-h", Input).value.strip()
            x_str = self.query_one("#input-crop-x", Input).value.strip()
            y_str = self.query_one("#input-crop-y", Input).value.strip()

            new_w = max(1, min(int(w_str), orig_w)) if w_str else self.crop_w
            new_h = max(1, min(int(h_str), orig_h)) if h_str else self.crop_h
            new_x = max(0, min(int(x_str), orig_w - new_w)) if x_str else self.crop_x
            new_y = max(0, min(int(y_str), orig_h - new_h)) if y_str else self.crop_y

            self.crop_w = new_w
            self.crop_h = new_h
            self.crop_x = new_x
            self.crop_y = new_y

            info_lbl = self.query_one("#label-crop-info", Label)
            pct = int((self.crop_w * self.crop_h) / (orig_w * orig_h) * 100) if (orig_w * orig_h) > 0 else 100
            info_lbl.update(f"Orig: {orig_w}x{orig_h} | Crop: {self.crop_w}x{self.crop_h} ({pct}%)")

            self.reprocess_pixel_art()
        except ValueError:
            pass

    # Event handlers
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-load":
            path_input = self.query_one("#input-path", Input).value.strip()
            if not path_input:
                quick_sel = self.query_one("#select-quick-image", Select)
                if not quick_sel.is_blank() and quick_sel.value:
                    path_input = str(quick_sel.value)
            if path_input:
                self.load_image(path_input)
            else:
                self.notify("Please enter a path or pick an image", severity="warning")
        elif btn_id == "btn-browse":
            self.action_browse_files()
        elif btn_id == "btn-crop-up":
            self.action_crop_up()
        elif btn_id == "btn-crop-down":
            self.action_crop_down()
        elif btn_id == "btn-crop-left":
            self.action_crop_left()
        elif btn_id == "btn-crop-right":
            self.action_crop_right()
        elif btn_id == "btn-grow-w":
            self.resize_crop(self.crop_step, 0)
        elif btn_id == "btn-shrink-w":
            self.resize_crop(-self.crop_step, 0)
        elif btn_id == "btn-grow-h":
            self.resize_crop(0, self.crop_step)
        elif btn_id == "btn-shrink-h":
            self.resize_crop(0, -self.crop_step)
        elif btn_id == "btn-crop-center":
            self.center_crop()
        elif btn_id == "btn-crop-square":
            self.make_square_crop()
        elif btn_id == "btn-crop-full":
            self.reset_full_crop()
        elif btn_id == "btn-save-preview":
            self.action_save_preview()
        elif btn_id == "btn-save-raw":
            self.save_raw_sprite()
        elif btn_id == "btn-export-c":
            self.action_export_c()
        elif btn_id == "btn-export-pico8":
            self.action_export_pico8()
        elif btn_id == "btn-zoom-native":
            self.set_zoom_mode("native")
        elif btn_id == "btn-zoom-fit":
            self.set_zoom_mode("fit")
        elif btn_id == "btn-zoom-2x":
            self.set_zoom_mode("2x")
        elif btn_id == "btn-zoom-3x":
            self.set_zoom_mode("3x")
        elif btn_id == "btn-zoom-4x":
            self.set_zoom_mode("4x")

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._initialized or self._updating_controls:
            return
        if event.select.id == "select-quick-image":
            if not event.select.is_blank() and event.value:
                val_str = str(event.value)
                if val_str != str(self.current_image_path):
                    self.load_image(val_str)
        elif event.select.id == "select-ui-theme":
            if not self._updating_theme and not event.select.is_blank() and event.value:
                self.apply_theme(str(event.value))
        elif event.select.id == "select-crop-step":
            if not event.select.is_blank() and event.value:
                self.crop_step = int(event.value)
        else:
            self.reprocess_pixel_art()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if not self._initialized:
            return
        if event.switch.id == "switch-crop":
            self.crop_enabled = bool(event.value)
            if self.crop_enabled and self.current_source_img:
                orig_w, orig_h = self.current_source_img.size
                if self.crop_w == orig_w and self.crop_h == orig_h and (orig_w > 256 or orig_h > 256):
                    crop_dim = min(orig_w, orig_h, 256)
                    self.crop_w = crop_dim
                    self.crop_h = crop_dim
                    self.crop_x = (orig_w - crop_dim) // 2
                    self.crop_y = (orig_h - crop_dim) // 2
                    self.update_crop_input_fields()
            self.reprocess_pixel_art()
        else:
            self.reprocess_pixel_art()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live updates as user types crop dimensions or offsets."""
        if event.input.id in ("input-crop-w", "input-crop-h", "input-crop-x", "input-crop-y"):
            if event.input.has_focus:
                self.crop_enabled = True
                self.query_one("#switch-crop", Switch).value = True
                self.apply_manual_crop_inputs()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-path":
            self.load_image(event.value.strip())
        elif event.input.id in ("input-crop-w", "input-crop-h", "input-crop-x", "input-crop-y"):
            self.crop_enabled = True
            self.query_one("#switch-crop", Switch).value = True
            self.apply_manual_crop_inputs()

    # Theme and Zoom Management
    def apply_theme(self, theme_name: str, notify: bool = True) -> None:
        """Apply one of the vintage retro themes dynamically."""
        if theme_name not in self.THEMES or self._updating_theme:
            return
        self._updating_theme = True
        try:
            for t in self.THEMES:
                self.remove_class(f"theme-{t}")
            self.add_class(f"theme-{theme_name}")
            self.ui_retro_theme = theme_name

            try:
                theme_sel = self.query_one("#select-ui-theme", Select)
                if theme_sel.value != theme_name:
                    theme_sel.value = theme_name
            except Exception:
                pass

            if notify:
                msg = f"Theme switched to: {theme_name.upper()}"
                self.set_status(msg)
                self.notify(msg, title="Retro Theme", severity="information")
        finally:
            self._updating_theme = False

    def action_cycle_theme(self) -> None:
        """Cycle to next retro theme with 't' key."""
        curr_idx = self.THEMES.index(self.ui_retro_theme) if self.ui_retro_theme in self.THEMES else 0
        next_theme = self.THEMES[(curr_idx + 1) % len(self.THEMES)]
        self.apply_theme(next_theme)

    def set_zoom_mode(self, mode: str) -> None:
        """Set preview zoom mode ('native', 'fit', '2x', '3x', '4x')."""
        if mode not in self.ZOOM_MODES:
            return
        self.preview_zoom = mode

        # Update button highlights
        btn_map = {
            "native": "#btn-zoom-native",
            "fit": "#btn-zoom-fit",
            "2x": "#btn-zoom-2x",
            "3x": "#btn-zoom-3x",
            "4x": "#btn-zoom-4x",
        }
        for z_key, btn_id in btn_map.items():
            try:
                b = self.query_one(btn_id, Button)
                if z_key == mode:
                    b.add_class("active-zoom")
                else:
                    b.remove_class("active-zoom")
            except Exception:
                pass

        if self.processed_sprite is not None:
            rich_pixel = render_image_to_rich_text(
                self.processed_sprite,
                zoom_mode=self.preview_zoom,
                max_w=68,
                max_h=38,
            )
            self.query_one("#canvas-pixel", CanvasWidget).update(rich_pixel)

        msg = f"Preview zoom set to: {mode.upper()}"
        self.set_status(msg)
        self.notify(msg, title="Sprite Zoom", severity="information")

    def action_cycle_zoom(self) -> None:
        """Cycle preview zoom mode with 'z' key."""
        curr_idx = self.ZOOM_MODES.index(self.preview_zoom) if self.preview_zoom in self.ZOOM_MODES else 0
        next_zoom = self.ZOOM_MODES[(curr_idx + 1) % len(self.ZOOM_MODES)]
        self.set_zoom_mode(next_zoom)

    # Actions
    def action_browse_files(self) -> None:
        """Open visual file picker modal."""
        def handle_file_choice(chosen_path: Optional[Path]) -> None:
            if chosen_path is not None:
                self.load_image(str(chosen_path))

        self.push_screen(FilePickerModal(), handle_file_choice)

    def action_save_preview(self) -> None:
        if self.processed_sprite is None or not self.current_image_path:
            self.set_status("No processed sprite to save", is_error=True)
            self.notify("No processed sprite to save", severity="warning")
            return

        scale = int(self.query_one("#select-scale", Select).value)
        # Protect against gigapixel images when exporting large sprites
        max_dim = max(self.processed_sprite.width, self.processed_sprite.height)
        if max_dim * scale > 4096:
            scale = max(1, 4096 // max_dim)

        in_path = Path(self.current_image_path)
        pal_name = str(self.query_one("#select-palette", Select).value)
        crop_tag = f"_crop_{self.crop_w}x{self.crop_h}" if self.crop_enabled else ""
        out_name = f"{in_path.stem}_{pal_name}{crop_tag}_{scale}x.png"
        out_path = in_path.parent / out_name

        upscaled = upscale_nearest(self.processed_sprite, scale=scale)
        upscaled.save(out_path)
        msg = f"Saved preview ({upscaled.width}x{upscaled.height}): {out_name}"
        self.set_status(msg)
        self.notify(msg, title="Export Complete", severity="information")

    def save_raw_sprite(self) -> None:
        if self.processed_sprite is None or not self.current_image_path:
            self.set_status("No processed sprite to save", is_error=True)
            self.notify("No processed sprite to save", severity="warning")
            return

        in_path = Path(self.current_image_path)
        pal_name = str(self.query_one("#select-palette", Select).value)
        w, h = self.processed_sprite.size
        crop_tag = f"_crop_{self.crop_w}x{self.crop_h}" if self.crop_enabled else ""
        out_name = f"{in_path.stem}_{pal_name}{crop_tag}_{w}x{h}.png"
        out_path = in_path.parent / out_name

        self.processed_sprite.save(out_path)
        msg = f"Saved 1x native sprite ({w}x{h}): {out_name}"
        self.set_status(msg)
        self.notify(msg, title="Export Complete", severity="information")

    def action_export_c(self) -> None:
        if self.last_indices is None or self.last_palette is None or not self.current_image_path:
            self.set_status("No processed sprite to export", is_error=True)
            self.notify("No processed sprite to export", severity="warning")
            return

        in_path = Path(self.current_image_path)
        crop_tag = "_crop" if self.crop_enabled else ""
        out_name = f"{in_path.stem}{crop_tag}_{self.last_indices.shape[1]}x{self.last_indices.shape[0]}.h"
        out_path = in_path.parent / out_name

        export_c_header(self.last_indices, self.last_palette, name=f"{in_path.stem}{crop_tag}", output_path=str(out_path))
        msg = f"Exported C header: {out_name}"
        self.set_status(msg)
        self.notify(msg, title="Export Complete", severity="information")

    def action_export_pico8(self) -> None:
        if self.last_indices is None or not self.current_image_path:
            self.set_status("No processed sprite to export", is_error=True)
            self.notify("No processed sprite to export", severity="warning")
            return

        in_path = Path(self.current_image_path)
        crop_tag = "_crop" if self.crop_enabled else ""
        out_name = f"{in_path.stem}{crop_tag}_pico8.txt"
        out_path = in_path.parent / out_name

        export_pico8_spritesheet(self.last_indices, output_path=str(out_path))
        msg = f"Exported PICO-8 sprite data: {out_name}"
        self.set_status(msg)
        self.notify(msg, title="Export Complete", severity="information")


def run_tui(initial_image: Optional[str] = None):
    """Launch the interactive TUI."""
    app = PixelArtStudio(initial_image=initial_image)
    app.run()


if __name__ == "__main__":
    run_tui()
