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


def signed_area(points: Contour) -> float:
    """Diện tích có dấu. Âm = chiều kim đồng hồ, dương = ngược lại."""
    total = 0.0
    count = len(points)
    for i in range(count):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % count]
        total += x0 * y1 - x1 * y0
    return total / 2


def is_clockwise(contours: list[Contour]) -> bool:
    """Chiều quay của contour lớn nhất — quy ước chiều của cả glyph."""
    if not contours:
        return True
    biggest = max(contours, key=lambda points: abs(signed_area(points)))
    return signed_area(biggest) < 0


def ensure_winding(contours: list[Contour], clockwise: bool = True) -> list[Contour]:
    """Đảo chiều contour nếu cần để khớp quy ước của glyph đích.

    Quan trọng khi contour chồng lên nhau: quy tắc nonzero winding triệt tiêu
    phần chồng nếu hai contour quay ngược chiều, làm mất mực (xem
    ``docs/research/mark-pack-winding.md``).
    """
    out = []
    for points in contours:
        if (signed_area(points) < 0) != clockwise:
            out.append(list(reversed(points)))
        else:
            out.append(points)
    return out
