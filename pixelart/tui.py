"""Interactive Terminal User Interface (TUI) for ImageToPixelArt using Textual."""

from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
from PIL import Image

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Button,
    Input,
    Select,
    Switch,
    Label,
    Static,
    Rule,
    DirectoryTree,
)
from textual.reactive import reactive
from rich.text import Text
from rich.style import Style

from .converter import convert_to_pixel_art, upscale_nearest, calculate_target_size
from .palettes import PALETTES, hex_to_rgb, rgb_to_hex
from .exporters import export_c_header, export_pico8_spritesheet, export_palette_json


def resolve_image_path(raw_str: str) -> Optional[Path]:
    """
    Robustly resolve an image path string from terminal input.
    Handles quotes ('path', "path"), escaped spaces (path\\ with\\ spaces),
    tilde expansion (~/...), relative paths, and missing extensions (.png, .jpg).
    """
    if not raw_str or not raw_str.strip():
        return None

    cleaned = raw_str.strip()

    # Strip outer single or double quotes (added by macOS Terminal drag & drop)
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()

    # Unescape escaped spaces
    cleaned = cleaned.replace(r"\ ", " ")

    # Expand tilde and user variables
    p = Path(cleaned).expanduser()

    # Direct check
    if p.is_file():
        return p.resolve()

    # Relative to current working directory
    if not p.is_absolute():
        cwd_p = (Path.cwd() / cleaned).resolve()
        if cwd_p.is_file():
            return cwd_p

    # Try matching common image extensions if user typed name without extension
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

    # Filter out generated test exports to keep list clean
    for item in sorted(cwd.iterdir()):
        if item.is_file() and item.suffix.lower() in exts:
            name = item.name
            if name.startswith("output_") or name.endswith("_pico8.png"):
                continue
            images.append((f"🖼️ {name}", str(item.resolve())))

    if not images:
        images.append(("None found in folder", ""))

    return images


def render_image_to_rich_text(img: Image.Image) -> Text:
    """
    Render a PIL image to Rich Text using Unicode half-blocks (▀ and ▄).
    Each terminal row renders 2 vertical image pixels in full 24-bit RGB.
    """
    rgba = np.array(img.convert("RGBA"))
    h, w, _ = rgba.shape
    text = Text()

    for y in range(0, h, 2):
        for x in range(w):
            top = rgba[y, x]
            bot = rgba[y + 1, x] if y + 1 < h else np.array([0, 0, 0, 0], dtype=np.uint8)

            top_visible = top[3] >= 128
            bot_visible = bot[3] >= 128

            if not top_visible and not bot_visible:
                text.append(" ")
            elif top_visible and not bot_visible:
                text.append("▀", style=Style(color=f"rgb({top[0]},{top[1]},{top[2]})"))
            elif not top_visible and bot_visible:
                text.append("▄", style=Style(color=f"rgb({bot[0]},{bot[1]},{bot[2]})"))
            else:
                text.append(
                    "▀",
                    style=Style(
                        color=f"rgb({top[0]},{top[1]},{top[2]})",
                        bgcolor=f"rgb({bot[0]},{bot[1]},{bot[2]})",
                    ),
                )
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
        background: #11141c;
        border: round #3b4252;
    }
    """


class PixelArtStudio(App):
    """Interactive Retro Pixel Art Studio TUI."""

    TITLE = "PixelArt Studio 🕹️"
    SUB_TITLE = "Retro Game Sprite Converter"
    CSS = """
    Screen {
        background: #0d1117;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #sidebar {
        width: 46;
        height: 100%;
        background: #161b22;
        border-right: solid #30363d;
        padding: 1 2;
    }

    #preview-area {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }

    .section-title {
        text-style: bold;
        color: #58a6ff;
        margin-top: 1;
        margin-bottom: 0;
    }

    .field-label {
        color: #8b949e;
        margin-top: 1;
    }

    .action-btn {
        width: 100%;
        margin-top: 1;
    }

    #status-bar {
        height: 3;
        background: #1f242c;
        color: #7ee787;
        padding: 0 1;
        content-align: left middle;
        border: round #30363d;
        margin-top: 1;
    }

    #info-bar {
        height: 3;
        background: #1c2128;
        color: #e6edf3;
        content-align: center middle;
        text-style: bold;
        border: round #30363d;
        margin-bottom: 1;
    }

    .button-row {
        height: auto;
        margin-top: 1;
    }

    .button-row Button {
        width: 1fr;
        margin-right: 1;
    }

    .button-row Button:last-of-type {
        margin-right: 0;
    }

    Switch {
        margin-top: 1;
    }

    Horizontal.switch-row {
        height: auto;
        align: left middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "browse_files", "Browse Files"),
        ("s", "save_preview", "Save PNG"),
        ("c", "export_c", "Export C"),
        ("p", "export_pico8", "Export PICO-8"),
    ]

    current_image_path: reactive[Optional[str]] = reactive(None)
    current_source_img: Optional[Image.Image] = None
    processed_sprite: Optional[Image.Image] = None
    last_indices: Optional[np.ndarray] = None
    last_palette: Optional[list] = None

    def __init__(self, initial_image: Optional[str] = None):
        super().__init__()
        self.initial_image = initial_image

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            # Left Control Sidebar
            with VerticalScroll(id="sidebar"):
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
                    value=self.initial_image or "sample_input.png",
                )

                with Horizontal(classes="button-row"):
                    yield Button("Load", id="btn-load", variant="primary")
                    yield Button("📂 Browse...", id="btn-browse", variant="default")

                yield Rule()
                yield Label("SPRITE SETTINGS", classes="section-title")

                yield Label("Target Resolution:", classes="field-label")
                yield Select(
                    [
                        ("16 px (Tiny Icon)", "16"),
                        ("24 px (Classic RPG)", "24"),
                        ("32 px (Standard Sprite)", "32"),
                        ("48 px (Detailed Character)", "48"),
                        ("64 px (Portrait / Boss)", "64"),
                        ("96 px (Large Scene)", "96"),
                        ("128 px (High Res Retro)", "128"),
                    ],
                    value="32",
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
                    ("Game Boy DMG (4 Greens)", "gameboy"),
                    ("Game Boy Pocket (4 Greys)", "gameboy-pocket"),
                    ("PICO-8 (16 Colors)", "pico8"),
                    ("Commodore 64 (16 Colors)", "c64"),
                    ("NES (54 Colors)", "nes"),
                    ("CGA Mode 1 (Cyan/Magenta)", "cga-mode1"),
                    ("CGA Mode 0 (Green/Red)", "cga-mode0"),
                    ("ZX Spectrum (15 Colors)", "zx-spectrum"),
                    ("1-Bit Monochrome (B&W)", "1bit"),
                    ("Cyberpunk Synthwave", "cyberpunk"),
                    ("Adaptive (Auto 16-color)", "adaptive"),
                ]
                yield Select(palette_options, value="pico8", id="select-palette", allow_blank=False)

                yield Label("Dithering Method:", classes="field-label")
                dither_options = [
                    ("None (Cel-Shaded / Clean)", "none"),
                    ("Bayer 4x4 (Classic Crosshatch)", "bayer-4x4"),
                    ("Bayer 2x2 (Coarse Crosshatch)", "bayer-2x2"),
                    ("Bayer 8x8 (Fine Ordered)", "bayer-8x8"),
                    ("Floyd-Steinberg (Diffusion)", "floyd"),
                ]
                yield Select(dither_options, value="none", id="select-dither", allow_blank=False)

                with Horizontal(classes="switch-row"):
                    yield Label("Sprite Dark Outline: ", classes="field-label")
                    yield Switch(value=False, id="switch-outline")

                yield Label("Color Enhancement:", classes="field-label")
                yield Select(
                    [
                        ("Neutral (1.0x)", "1.0"),
                        ("Vibrant / Punchy (1.25x)", "1.25"),
                        ("High Contrast (1.5x)", "1.5"),
                    ],
                    value="1.25",
                    id="select-enhance",
                    allow_blank=False,
                )

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

            # Right Preview Area
            with Vertical(id="preview-area"):
                yield Static("No Image Loaded", id="info-bar")
                yield CanvasWidget(id="canvas")
                yield Static("Ready", id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Load initial image upon launch."""
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

    def set_status(self, message: str, is_error: bool = False) -> None:
        """Update bottom status banner and trigger visual notification toast."""
        status_bar = self.query_one("#status-bar", Static)
        prefix = "❌ " if is_error else "✨ "
        status_bar.update(f"{prefix}{message}")

    def load_image(self, file_path_str: str) -> None:
        """Robustly resolve and load an image from user string."""
        resolved = resolve_image_path(file_path_str)
        if not resolved:
            self.set_status(f"File not found: '{file_path_str}'", is_error=True)
            self.notify(f"Could not find: '{file_path_str}'. Check file name or path.", title="File Not Found", severity="error")
            return

        try:
            self.current_source_img = Image.open(resolved)
            self.current_image_path = str(resolved)

            # Update input field display
            inp = self.query_one("#input-path", Input)
            inp.value = resolved.name

            # Also sync select-quick-image if this file is in options
            quick_select = self.query_one("#select-quick-image", Select)
            for _, val in quick_select._options:
                if val and str(val) == str(resolved):
                    if quick_select.value != val:
                        quick_select.value = val
                    break

            msg = f"Loaded {resolved.name} ({self.current_source_img.width}x{self.current_source_img.height})"
            self.set_status(msg)
            self.notify(msg, title="Image Loaded", severity="information")
            self.reprocess_pixel_art()
        except Exception as e:
            err_msg = f"Error opening image: {e}"
            self.set_status(err_msg, is_error=True)
            self.notify(err_msg, title="Image Error", severity="error")

    def reprocess_pixel_art(self) -> None:
        """Re-run conversion pipeline and update canvas."""
        if self.current_source_img is None:
            return

        try:
            # Query control values
            res_val = int(self.query_one("#select-resolution", Select).value)
            aspect_mode = str(self.query_one("#select-aspect", Select).value)
            palette_val = str(self.query_one("#select-palette", Select).value)
            dither_val = str(self.query_one("#select-dither", Select).value)
            outline_val = bool(self.query_one("#switch-outline", Switch).value)
            enhance_val = float(self.query_one("#select-enhance", Select).value)

            # Aspect ratio calculation
            if aspect_mode == "fit":
                target_w, target_h = calculate_target_size(
                    self.current_source_img.width,
                    self.current_source_img.height,
                    max_dimension=res_val,
                )
            else:
                target_w, target_h = res_val, res_val

            sprite, indices, palette = convert_to_pixel_art(
                self.current_source_img,
                target_width=target_w,
                target_height=target_h,
                palette_name_or_spec=palette_val,
                dither_mode=dither_val,
                add_outline=outline_val,
                contrast=enhance_val,
                saturation=enhance_val,
            )

            self.processed_sprite = sprite
            self.last_indices = indices
            self.last_palette = palette

            # Render in terminal canvas
            rich_renderable = render_image_to_rich_text(sprite)
            self.query_one("#canvas", CanvasWidget).update(rich_renderable)

            # Update info bar
            info_bar = self.query_one("#info-bar", Static)
            info_bar.update(
                f"Sprite: {sprite.width}x{sprite.height} | "
                f"Palette: {palette_val} ({len(palette)} colors) | "
                f"Dither: {dither_val} | "
                f"Outline: {'ON' if outline_val else 'OFF'}"
            )
        except Exception as e:
            self.set_status(f"Processing error: {e}", is_error=True)

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
        elif btn_id == "btn-save-preview":
            self.action_save_preview()
        elif btn_id == "btn-save-raw":
            self.save_raw_sprite()
        elif btn_id == "btn-export-c":
            self.action_export_c()
        elif btn_id == "btn-export-pico8":
            self.action_export_pico8()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-quick-image":
            if not event.select.is_blank() and event.value:
                val_str = str(event.value)
                if val_str != str(self.current_image_path):
                    self.load_image(val_str)
        else:
            self.reprocess_pixel_art()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        self.reprocess_pixel_art()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-path":
            self.load_image(event.value.strip())

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
        in_path = Path(self.current_image_path)
        pal_name = str(self.query_one("#select-palette", Select).value)
        out_name = f"{in_path.stem}_{pal_name}_{scale}x.png"
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
        out_name = f"{in_path.stem}_{pal_name}_{w}x{h}.png"
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
        out_name = f"{in_path.stem}_{self.last_indices.shape[1]}x{self.last_indices.shape[0]}.h"
        out_path = in_path.parent / out_name

        export_c_header(self.last_indices, self.last_palette, name=in_path.stem, output_path=str(out_path))
        msg = f"Exported C header: {out_name}"
        self.set_status(msg)
        self.notify(msg, title="Export Complete", severity="information")

    def action_export_pico8(self) -> None:
        if self.last_indices is None or not self.current_image_path:
            self.set_status("No processed sprite to export", is_error=True)
            self.notify("No processed sprite to export", severity="warning")
            return

        in_path = Path(self.current_image_path)
        out_name = f"{in_path.stem}_pico8.txt"
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
