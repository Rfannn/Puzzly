"""
puzzle_maker.py - Core puzzle generation logic.
Supports both grid-cut and jigsaw-cut puzzles.
"""

import os
import hashlib
import random
from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Jigsaw tab/blank curve generators
# ---------------------------------------------------------------------------


# tab_style scales: (height_factor, head_factor)
_TAB_STYLES = {
    "classic": (0.22, 0.38),      # pronounced interlocking tabs
    "rounded": (0.16, 0.55),      # softer, rounder tabs for small kids
    "minimal": (0.04, 0.12),      # barely-there tabs, almost straight cuts
}


def _tab_horizontal(x1, x2, y, d=1, tab_style="classic"):
    """Classic jigsaw tab on a horizontal edge from (x1,y) to (x2,y).
    d=1: tab goes down, d=-1: tab goes up (blank/inward)."""
    L = x2 - x1
    if L <= 0:
        return [(x1, y), (x2, y)]
    hf, headf = _TAB_STYLES.get(tab_style, _TAB_STYLES["classic"])
    mid = (x1 + x2) / 2
    h = L * hf * d
    head = L * headf
    return [
        (x1, y),
        (x1 + L * 0.30, y),
        (x1 + L * 0.30, y - h * 0.1),
        (mid - head / 2, y - h * 0.4),
        (mid - head / 2, y - h * 0.8),
        (mid - head / 3, y - h),
        (mid, y - h),
        (mid + head / 3, y - h),
        (mid + head / 2, y - h * 0.8),
        (mid + head / 2, y - h * 0.4),
        (x2 - L * 0.30, y - h * 0.1),
        (x2 - L * 0.30, y),
        (x2, y),
    ]


def _tab_vertical(x, y1, y2, d=1, tab_style="classic"):
    """Classic jigsaw tab on a vertical edge from (x,y1) to (x,y2).
    d=1: tab goes right, d=-1: tab goes left (blank)."""
    L = y2 - y1
    if L <= 0:
        return [(x, y1), (x, y2)]
    hf, headf = _TAB_STYLES.get(tab_style, _TAB_STYLES["classic"])
    mid = (y1 + y2) / 2
    h = L * hf * d
    head = L * headf
    return [
        (x, y1),
        (x, y1 + L * 0.30),
        (x + h * 0.1, y1 + L * 0.30),
        (x + h * 0.4, mid - head / 2),
        (x + h * 0.8, mid - head / 2),
        (x + h, mid - head / 3),
        (x + h, mid),
        (x + h, mid + head / 3),
        (x + h * 0.8, mid + head / 2),
        (x + h * 0.4, mid + head / 2),
        (x + h * 0.1, y2 - L * 0.30),
        (x, y2 - L * 0.30),
        (x, y2),
    ]


def _trace_piece(row, col, rows, cols, cell_w, cell_h, h_edges, v_edges, tab_style="classic"):
    """Trace the boundary of a jigsaw piece. Returns closed polygon."""
    x1 = col * cell_w
    y1 = row * cell_h
    x2 = (col + 1) * cell_w
    y2 = (row + 1) * cell_h
    points = []

    # Top edge: left to right
    if row == 0:
        points.extend([(x1, y1), (x2, y1)])
    else:
        # Use the SAME sign as the bottom neighbour's bottom edge so the
        # tab on one piece matches the blank (notch) on the adjacent piece.
        d = h_edges[row - 1][col]
        points.extend(_tab_horizontal(x1, x2, y1, d, tab_style))

    # Right edge: top to bottom
    if col == cols - 1:
        points.append((x2, y2))
    else:
        pts = _tab_vertical(x2, y1, y2, v_edges[row][col], tab_style)
        points.extend(pts[1:])

    # Bottom edge: right to left
    if row == rows - 1:
        points.append((x1, y2))
    else:
        pts = _tab_horizontal(x1, x2, y2, h_edges[row][col], tab_style)
        points.extend(list(reversed(pts))[1:])

    # Left edge: bottom to top
    if col == 0:
        points.append((x1, y1))
    else:
        # Use the SAME sign as the right neighbour's right edge so the
        # tab on one piece matches the blank (notch) on the adjacent piece.
        pts = _tab_vertical(x1, y1, y2, v_edges[row][col - 1], tab_style)
        points.extend(list(reversed(pts))[1:])

    return points


def _edge_seed(image_path, rows, cols, puzzle_type="jigsaw", tab_style="classic"):
    """Stable seed so generated pieces, previews, and templates agree."""
    identity = f"{puzzle_type}:{tab_style}:{rows}:{cols}:"
    if image_path:
        try:
            stat = os.stat(image_path)
            identity += f"{os.path.abspath(image_path)}:{stat.st_size}:{stat.st_mtime_ns}"
        except OSError:
            identity += os.path.abspath(image_path)
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _make_edge_maps(rows, cols, seed=None, tab_style="classic"):
    rng = random.Random(seed)
    h_edges = [[rng.choice([-1, 1]) for _ in range(cols)] for _ in range(rows - 1)]
    v_edges = [[rng.choice([-1, 1]) for _ in range(cols - 1)] for _ in range(rows)]
    return h_edges, v_edges


def _offset_points(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


def _rounded_picture_board(img, border_width=3):
    """Clip an image to a rounded physical puzzle-board silhouette."""
    radius = max(12, int(min(img.size) * 0.045))
    rgba = img.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, rgba.width - 1, rgba.height - 1],
        radius=radius,
        fill=255,
    )
    rounded = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
    rounded.paste(rgba, (0, 0), mask)
    board = Image.new("RGB", rgba.size, (255, 255, 255))
    board.paste(rounded, (0, 0), mask)
    draw = ImageDraw.Draw(board)
    draw.rounded_rectangle(
        [1, 1, board.width - 2, board.height - 2],
        radius=radius,
        outline=(0, 0, 0),
        width=max(2, border_width),
    )
    return board


def _frame_box(width, height, border_width=3):
    """Shared geometry for the framed board / template.

    The outer ~8% on each side is the picture-colour frame; the inner area
    is the play surface where the cut lines live."""
    frame_bw = max(20, int(min(width, height) * 0.08))
    corner_r = max(6, int(min(width, height) * 0.035))
    return {
        "frame_bw": frame_bw,
        "corner_r": corner_r,
        "inner_x1": frame_bw,
        "inner_y1": frame_bw,
        "inner_x2": width - 1 - frame_bw,
        "inner_y2": height - 1 - frame_bw,
    }


def _draw_inner_frame(draw, box, border_width):
    sep = max(2, border_width)
    draw.rounded_rectangle(
        [
            box["inner_x1"] - sep,
            box["inner_y1"] - sep,
            box["inner_x2"] + sep,
            box["inner_y2"] + sep,
        ],
        radius=box["corner_r"] + sep,
        outline=(0, 0, 0),
        width=sep * 2,
    )


def _draw_outer_frame(draw, width, height, box, border_width):
    draw.rounded_rectangle(
        [2, 2, width - 3, height - 3],
        radius=box["corner_r"] + 2,
        outline=(0, 0, 0),
        width=max(4, border_width * 2),
    )


def _draw_piece_lines_in_box(
    draw, rows, cols, puzzle_type, box, border_width, image_path=None, color=(120, 120, 120), tab_style="classic"
):
    inner_x1 = box["inner_x1"]
    inner_y1 = box["inner_y1"]
    inner_x2 = box["inner_x2"]
    inner_y2 = box["inner_y2"]
    cell_w = (inner_x2 - inner_x1) / cols
    cell_h = (inner_y2 - inner_y1) / rows

    if puzzle_type == "jigsaw":
        h_edges, v_edges = _make_edge_maps(
            rows, cols, _edge_seed(image_path, rows, cols, tab_style=tab_style), tab_style=tab_style
        )
        for row in range(rows):
            for col in range(cols):
                polygon = _trace_piece(
                    row, col, rows, cols, cell_w, cell_h, h_edges, v_edges, tab_style
                )
                polygon = _offset_points(polygon, inner_x1, inner_y1)
                draw.polygon(polygon, outline=color, width=border_width)
        return

    for r in range(1, rows):
        y = int(inner_y1 + r * cell_h)
        draw.line([(inner_x1, y), (inner_x2, y)], fill=color, width=border_width)
    for c in range(1, cols):
        x = int(inner_x1 + c * cell_w)
        draw.line([(x, inner_y1), (x, inner_y2)], fill=color, width=border_width)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _int_to_rgba(img):
    if img.mode == "RGBA":
        return img
    return img.convert("RGBA")


def preview_thumbnail(image_path, size=800):
    """Return a path to a cached, downscaled copy of `image_path`.

    Previews are rendered from this so a large source image does not trigger
    full-resolution work on every option change. The thumbnail is reused
    across preview calls (keyed by path + size)."""
    src = Image.open(image_path)
    thumb_path = f"{image_path}.thumb{size}.jpg"
    try:
        if os.path.exists(thumb_path) and os.path.getmtime(thumb_path) >= os.path.getmtime(
            image_path
        ):
            return thumb_path
    except OSError:
        pass
    w, h = src.size
    scale = min(1.0, size / max(w, h))
    tw, th = max(1, int(w * scale)), max(1, int(h * scale))
    thumb = src.convert("RGB").resize((tw, th), Image.LANCZOS)
    try:
        thumb.save(thumb_path, format="JPEG", quality=85)
    except OSError:
        return image_path
    return thumb_path


def create_template_image(
    rows, cols, puzzle_type, width, height, border_width=3, image_path=None, tab_style="classic"
):
    """Placement template with a proportional picture frame.

    When `image_path` is given the outer ~8% border on each side IS the
    original picture — a colour frame showing kids what the edge pieces
    should look like. The inner area is white with rounded corners,
    light-gray piece cut-lines, and a thick black outline."""
    # NOTE: image_path is always provided in the live app (previews pass it).
    # The plain-white-only branch is kept for standalone / unit-call use.
    if image_path:
        src = Image.open(image_path).convert("RGB").resize((width, height), Image.LANCZOS)
        img = _rounded_picture_board(src, border_width)
        draw = ImageDraw.Draw(img)
        box = _frame_box(width, height, border_width)

        # White play area with rounded corners, then frame separators/borders.
        draw.rounded_rectangle(
            [box["inner_x1"], box["inner_y1"], box["inner_x2"], box["inner_y2"]],
            radius=box["corner_r"],
            fill=(255, 255, 255),
        )
        _draw_inner_frame(draw, box, border_width)
        _draw_outer_frame(draw, width, height, box, border_width)

        # Inner cut-lines on the white area (shared with the framed board).
        _draw_piece_lines_in_box(
            draw, rows, cols, puzzle_type, box, border_width, image_path, color=(120, 120, 120), tab_style=tab_style
        )
        return img

    # No picture frame: plain white board with rounded corners.
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [1, 1, width - 2, height - 2],
        radius=max(6, int(min(width, height) * 0.035)),
        outline=(0, 0, 0),
        width=max(4, border_width * 2),
    )
    box = {
        "inner_x1": 0,
        "inner_y1": 0,
        "inner_x2": width,
        "inner_y2": height,
        "corner_r": 0,
    }
    if puzzle_type == "jigsaw":
        h_edges, v_edges = _make_edge_maps(rows, cols, tab_style=tab_style)
        for row in range(rows):
            for col in range(cols):
                polygon = _trace_piece(
                    row, col, rows, cols, width / cols, height / rows, h_edges, v_edges, tab_style
                )
                draw.polygon(polygon, outline=(180, 180, 180), width=border_width)
    else:
        for r in range(1, rows):
            y = int(r * height / rows)
            draw.line([(0, y), (width, y)], fill=(180, 180, 180), width=border_width)
        for c in range(1, cols):
            x = int(c * width / cols)
            draw.line([(x, 0), (x, height)], fill=(180, 180, 180), width=border_width)
    return img


def _add_jigsaw_border(piece_img, polygon, bbox, border_width):
    """Draw a thick black border along the jigsaw piece outline."""
    bw = border_width
    padded = Image.new(
        "RGBA", (piece_img.width + bw * 2, piece_img.height + bw * 2), (0, 0, 0, 0)
    )
    padded.paste(piece_img, (bw, bw))
    shifted = [(p[0] - bbox[0] + bw, p[1] - bbox[1] + bw) for p in polygon]
    ImageDraw.Draw(padded).polygon(shifted, outline=(0, 0, 0, 255), width=bw)
    return padded


# ---------------------------------------------------------------------------
# Public API: piece generation
# ---------------------------------------------------------------------------


def generate_grid_pieces(image_path, rows, cols, border_width=3):
    """Cut image into a simple grid of rectangular pieces.
    Returns list of PIL RGBA images in row-major order."""
    img = _int_to_rgba(Image.open(image_path))
    w, h = img.size
    cell_w = w / cols
    cell_h = h / rows
    pieces = []

    for row in range(rows):
        for col in range(cols):
            box = (
                int(col * cell_w),
                int(row * cell_h),
                int((col + 1) * cell_w),
                int((row + 1) * cell_h),
            )
            piece = img.crop(box)
            bw = border_width
            bordered = Image.new(
                "RGBA", (piece.width + bw * 2, piece.height + bw * 2), (0, 0, 0, 0)
            )
            bordered.paste(piece, (bw, bw))
            radius = max(4, min(bordered.width, bordered.height) // 12)
            ImageDraw.Draw(bordered).rounded_rectangle(
                [
                    bw // 2,
                    bw // 2,
                    bordered.width - bw // 2 - 1,
                    bordered.height - bw // 2 - 1,
                ],
                radius=radius,
                outline=(0, 0, 0, 255),
                width=bw,
            )
            pieces.append(bordered)
    return pieces


def generate_jigsaw_pieces(image_path, rows, cols, border_width=3, supersample=2, tab_style="classic"):
    """Cut image into jigsaw-style pieces with interlocking tabs/blanks.
    Returns list of PIL RGBA images. Pieces are rendered at `supersample`
    scale and downscaled for smooth, anti-aliased edges."""
    img = _int_to_rgba(Image.open(image_path))
    w, h = img.size
    SS = max(1, int(supersample))

    h_edges, v_edges = _make_edge_maps(rows, cols, _edge_seed(image_path, rows, cols, tab_style=tab_style), tab_style=tab_style)

    pieces = []
    for row in range(rows):
        for col in range(cols):
            # Work in supersampled coordinates for crisp edges.
            cell_w = (w * SS) / cols
            cell_h = (h * SS) / rows
            polygon = _trace_piece(
                row, col, rows, cols, cell_w, cell_h, h_edges, v_edges, tab_style
            )

            mask = Image.new("L", (w * SS, h * SS), 0)
            ImageDraw.Draw(mask).polygon(polygon, fill=255)

            big = img.resize((w * SS, h * SS), Image.LANCZOS)
            piece = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
            piece.paste(big, (0, 0), mask)

            bbox = mask.getbbox()
            if bbox:
                piece = piece.crop(bbox)
                # border width scaled to match the supersampled space
                piece = _add_jigsaw_border(piece, polygon, bbox, border_width * SS)

            # Downscale back to original resolution for smooth edges.
            if SS > 1:
                piece = piece.resize(
                    (max(1, piece.width // SS), max(1, piece.height // SS)),
                    Image.LANCZOS,
                )
            pieces.append(piece)
    return pieces


def create_preview(image_path, rows, cols, puzzle_type="grid", border_width=3, tab_style="classic"):
    """Preview image with cut lines overlaid. Returns PIL RGB image."""
    img = Image.open(image_path).convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    cell_w = w / cols
    cell_h = h / rows

    if puzzle_type == "jigsaw":
        return _rounded_picture_board(
            _draw_jigsaw_overlay(img, rows, cols, border_width, image_path=image_path, tab_style=tab_style),
            border_width,
        )

    if puzzle_type == "grid":
        for r in range(1, rows):
            y = int(r * cell_h)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0), width=border_width)
        for c in range(1, cols):
            x = int(c * cell_w)
            draw.line([(x, 0), (x, h)], fill=(0, 0, 0), width=border_width)

    return _rounded_picture_board(img, border_width)


def _draw_jigsaw_overlay(
    base_rgb,
    rows,
    cols,
    line_width,
    outline_color=(0, 0, 0),
    supersample=2,
    image_path=None,
    tab_style="classic",
):
    """Return a copy of base_rgb with a smooth, anti-aliased jigsaw outline.
    The outline is drawn at `supersample` scale then downscaled for crisp edges."""
    SS = max(1, int(supersample))
    w, h = base_rgb.size
    big = base_rgb.resize((w * SS, h * SS), Image.LANCZOS)
    draw = ImageDraw.Draw(big)
    cell_w = (w * SS) / cols
    cell_h = (h * SS) / rows

    h_edges, v_edges = _make_edge_maps(
        rows, cols, _edge_seed(image_path, rows, cols, tab_style=tab_style), tab_style=tab_style
    )
    for row in range(rows):
        for col in range(cols):
            polygon = _trace_piece(
                row, col, rows, cols, cell_w, cell_h, h_edges, v_edges, tab_style
            )
            draw.polygon(polygon, outline=outline_color, width=line_width * SS)

    return big.resize((w, h), Image.LANCZOS)


def create_single_page_image(
    image_path, rows, cols, puzzle_type="grid", border_width=3, tab_style="classic"
):
    """Full assembled picture with thick cut lines so it can be printed
    and cut in place on a single page."""
    img = Image.open(image_path).convert("RGB").copy()
    if puzzle_type == "jigsaw":
        return _rounded_picture_board(
            _draw_jigsaw_overlay(img, rows, cols, border_width, image_path=image_path, tab_style=tab_style),
            border_width,
        )
    draw = ImageDraw.Draw(img)
    w, h = img.size
    cell_w = w / cols
    cell_h = h / rows

    if puzzle_type == "grid":
        for r in range(1, rows):
            y = int(r * cell_h)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0), width=border_width)
        for c in range(1, cols):
            x = int(c * cell_w)
            draw.line([(x, 0), (x, h)], fill=(0, 0, 0), width=border_width)

    return _rounded_picture_board(img, border_width)


def create_framed_puzzle_image(
    image_path, rows, cols, puzzle_type="grid", border_width=3, width=None, height=None, tab_style="classic"
):
    """Full assembled picture framed like the template board, but the inner
    play area shows the actual picture with cut lines (the assembled puzzle).

    This is the 'framed puzzle board' page: picture-colour outer frame, thick
    black borders, and the piece cut lines drawn over the picture."""
    src = Image.open(image_path).convert("RGB")
    if width is None or height is None:
        width, height = src.size
    else:
        src = src.resize((width, height), Image.LANCZOS)

    img = _rounded_picture_board(src, border_width)
    draw = ImageDraw.Draw(img)
    box = _frame_box(width, height, border_width)

    # Cut lines over the picture (the assembled pieces).
    _draw_piece_lines_in_box(
        draw, rows, cols, puzzle_type, box, border_width, image_path, color=(0, 0, 0), tab_style=tab_style
    )

    # Thick black separator between the picture frame and the play area.
    _draw_inner_frame(draw, box, border_width)
    # Thick black outer border.
    _draw_outer_frame(draw, width, height, box, border_width)
    return img


def create_reference_image(image_path, rows, cols, puzzle_type="grid", tab_style="classic"):
    """Reference/guide image matching the chosen cut style."""
    img = Image.open(image_path).convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    cell_w = w / cols
    cell_h = h / rows

    if puzzle_type == "jigsaw":
        return _rounded_picture_board(
            _draw_jigsaw_overlay(
                img,
                rows,
                cols,
                2,
                outline_color=(255, 0, 0),
                image_path=image_path,
                tab_style=tab_style,
            ),
            2,
        )

    if puzzle_type == "grid":
        for r in range(1, rows):
            y = int(r * cell_h)
            draw.line([(0, y), (w, y)], fill=(255, 0, 0), width=2)
        for c in range(1, cols):
            x = int(c * cell_w)
            draw.line([(x, 0), (x, h)], fill=(255, 0, 0), width=2)

    return _rounded_picture_board(img, 2)
