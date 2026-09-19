"""Mô hình contour của glyph: đọc, ghi, biến đổi.

Contour được giữ nguyên **toàn bộ điểm**. Không bao giờ thay contour bằng
bounding box — làm vậy sẽ phá shape của mọi chữ có contour không phải hình chữ
nhật (xem ``docs/research/ground-truth-flattening.md``).
"""

from __future__ import annotations

Point = tuple[float, float]
Contour = list[Point]


def contours(glyph) -> list[Contour]:
    """Đọc contour của một glyph fontforge, giữ nguyên mọi điểm."""
    return [[(p.x, p.y) for p in c] for c in glyph.foreground]


def set_contours(glyph, contours: list[Contour], width: float | None = None) -> None:
    """Ghi contour vào glyph fontforge, giữ nguyên số điểm."""
    glyph.clear()
    pen = glyph.glyphPen()
    for points in contours:
        pen.moveTo(*points[0])
        for point in points[1:]:
            pen.lineTo(*point)
        pen.closePath()
    pen = None
    if width is not None:
        glyph.width = int(width)


def translate(contours: list[Contour], dx: float = 0, dy: float = 0) -> list[Contour]:
    """Dịch contour theo ``(dx, dy)``."""
    return [[(x + dx, y + dy) for (x, y) in points] for points in contours]


def bounds(contours: list[Contour]) -> tuple[float, float, float, float] | None:
    """Hộp bao ``(x0, y0, x1, y1)`` của toàn bộ contour, ``None`` nếu rỗng."""
    xs = [x for points in contours for (x, _) in points]
    ys = [y for points in contours for (_, y) in points]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def is_rectangular(contours: list[Contour]) -> bool:
    """True nếu mọi contour đều là hình chữ nhật 4 điểm.

    Dùng để phát hiện glyph bị flatten: contour nhiều điểm bị vẽ lại thành 4 điểm.
    """
    return all(len(points) == 4 for points in contours)
