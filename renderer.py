"""
Crosshair rendering engine for preview and overlay display.
Generates pixel-accurate Valorant style crosshairs.
"""

from typing import Tuple, List, Optional
from PIL import Image, ImageDraw
from crosshair_config import CrosshairConfig


def hex_to_rgba(hex_color: str, opacity: float = 1.0) -> Tuple[int, int, int, int]:
    """Convert hex string (e.g. '#00FF00') to RGBA tuple (0-255)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        hex_color = "00FF00"
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(max(0.0, min(1.0, opacity)) * 255)
    return (r, g, b, a)


def get_spoke_coords(cx: int, cy: int, thickness: int, length: int, offset: int, direction: str) -> Tuple[int, int, int, int]:
    """Calculate integer pixel coordinates [x1, y1, x2, y2] for a spoke."""
    half_t = thickness // 2
    if thickness % 2 == 1:
        tx1 = cx - half_t
        tx2 = cx + half_t
    else:
        tx1 = cx - half_t
        tx2 = cx + half_t - 1

    if direction == "top":
        x1, x2 = tx1, tx2
        y1 = cy - offset - length
        y2 = cy - offset - 1
    elif direction == "bottom":
        x1, x2 = tx1, tx2
        y1 = cy + offset
        y2 = cy + offset + length - 1
    elif direction == "left":
        y1, y2 = tx1, tx2
        x1 = cx - offset - length
        x2 = cx - offset - 1
    elif direction == "right":
        y1, y2 = tx1, tx2
        x1 = cx + offset
        x2 = cx + offset + length - 1
    else:
        return (cx, cy, cx, cy)

    return (x1, y1, x2, y2)


def get_dot_coords(cx: int, cy: int, size: int) -> Tuple[int, int, int, int]:
    """Calculate integer pixel coordinates [x1, y1, x2, y2] for center dot."""
    half_s = size // 2
    if size % 2 == 1:
        x1, y1 = cx - half_s, cy - half_s
        x2, y2 = cx + half_s, cy + half_s
    else:
        x1, y1 = cx - half_s, cy - half_s
        x2, y2 = cx + half_s - 1, cy + half_s - 1
    return (x1, y1, x2, y2)


def render_crosshair_image(config: CrosshairConfig, canvas_size: int = 120) -> Image.Image:
    """Renders the crosshair onto a 32-bit RGBA PIL Image at 1x resolution."""
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = canvas_size // 2, canvas_size // 2

    outline_thick = config.outline_thickness if config.outlines_enabled else 0
    outline_col = hex_to_rgba(config.outline_color, config.outline_opacity)

    inner_col = hex_to_rgba(config.inner_line_color, config.inner_line_opacity)
    outer_col = hex_to_rgba(config.outer_line_color, config.outer_line_opacity)
    dot_col = hex_to_rgba(config.center_dot_color, config.center_dot_opacity)

    directions = ["top", "bottom", "left", "right"]

    outer_boxes: List[Tuple[int, int, int, int]] = []
    inner_boxes: List[Tuple[int, int, int, int]] = []
    dot_box: Optional[Tuple[int, int, int, int]] = None

    if config.outer_lines_enabled and config.outer_line_length > 0 and config.outer_line_thickness > 0:
        for d in directions:
            box = get_spoke_coords(cx, cy, config.outer_line_thickness, config.outer_line_length, config.outer_line_offset, d)
            outer_boxes.append(box)

    if config.inner_lines_enabled and config.inner_line_length > 0 and config.inner_line_thickness > 0:
        for d in directions:
            box = get_spoke_coords(cx, cy, config.inner_line_thickness, config.inner_line_length, config.inner_line_offset, d)
            inner_boxes.append(box)

    if config.center_dot_enabled and config.center_dot_thickness > 0:
        dot_box = get_dot_coords(cx, cy, config.center_dot_thickness)

    # 1. DRAW ALL OUTLINES FIRST (Outer -> Inner -> Dot)
    if outline_thick > 0 and outline_col[3] > 0:
        for box in outer_boxes:
            draw.rectangle(
                [box[0] - outline_thick, box[1] - outline_thick, box[2] + outline_thick, box[3] + outline_thick],
                fill=outline_col
            )
        for box in inner_boxes:
            draw.rectangle(
                [box[0] - outline_thick, box[1] - outline_thick, box[2] + outline_thick, box[3] + outline_thick],
                fill=outline_col
            )
        if dot_box:
            draw.rectangle(
                [dot_box[0] - outline_thick, dot_box[1] - outline_thick, dot_box[2] + outline_thick, dot_box[3] + outline_thick],
                fill=outline_col
            )

    # 2. DRAW OUTER LINES FILL
    if outer_col[3] > 0:
        for box in outer_boxes:
            draw.rectangle(box, fill=outer_col)

    # 3. DRAW INNER LINES FILL
    if inner_col[3] > 0:
        for box in inner_boxes:
            draw.rectangle(box, fill=inner_col)

    # 4. DRAW CENTER DOT FILL
    if dot_box and dot_col[3] > 0:
        draw.rectangle(dot_box, fill=dot_col)

    return img


def render_preview_image(
    config: CrosshairConfig,
    preview_size: int = 240,
    zoom: int = 4,
    bg_mode: str = "Dark Gray",
    show_grid: bool = True
) -> Image.Image:
    """Renders an enlarged preview image with custom background and optional pixel grid."""
    base_size = preview_size // zoom
    raw_crosshair = render_crosshair_image(config, canvas_size=base_size)

    bg_colors = {
        "Dark Gray": (22, 26, 32, 255),
        "Valorant Slate": (15, 25, 35, 255),
        "Pitch Black": (0, 0, 0, 255),
        "Bright White": (245, 245, 245, 255),
        "Combat Tan (Bind)": (148, 128, 98, 255),
        "Ice Blue (Icebox)": (110, 145, 175, 255),
        "Green Screen": (0, 255, 0, 255),
    }
    bg_rgba = bg_colors.get(bg_mode, (22, 26, 32, 255))

    base_img = Image.new("RGBA", (base_size, base_size), bg_rgba)
    base_img.alpha_composite(raw_crosshair)

    zoomed = base_img.resize((preview_size, preview_size), Image.Resampling.NEAREST)

    if show_grid and zoom >= 4:
        grid_draw = ImageDraw.Draw(zoomed)
        grid_color = (255, 255, 255, 25) if bg_rgba[0] < 128 else (0, 0, 0, 25)
        for i in range(0, preview_size, zoom):
            grid_draw.line([(i, 0), (i, preview_size)], fill=grid_color)
            grid_draw.line([(0, i), (preview_size, i)], fill=grid_color)

        cx, cy = preview_size // 2, preview_size // 2
        center_marker_color = (255, 255, 255, 60) if bg_rgba[0] < 128 else (0, 0, 0, 60)
        grid_draw.rectangle([cx - zoom // 2, cy - zoom // 2, cx + zoom // 2 - 1, cy + zoom // 2 - 1], outline=center_marker_color)

    return zoomed


def composite_for_overlay(raw_crosshair: Image.Image, chroma_color: Tuple[int, int, int] = (1, 1, 1)) -> Image.Image:
    """Composites the RGBA crosshair onto an RGB image with chroma key background."""
    bg = Image.new("RGBA", raw_crosshair.size, (*chroma_color, 255))
    composited = Image.alpha_composite(bg, raw_crosshair)
    return composited.convert("RGB")
