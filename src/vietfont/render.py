"""Rasterize glyph thành lưới text.

Đây là cầu nối duy nhất giữa font và Jev (model chỉ nhận text). Phải rasterize
thật bằng quy tắc nonzero winding — **không** được fill bounding box, vì làm vậy
sẽ biến mọi chữ có contour nhiều điểm thành khối đặc.
"""

from __future__ import annotations

from vietfont.glyph import Contour
from vietfont.grid import Grid


def inside(px: float, py: float, contours: list[Contour]) -> bool:
    """Điểm ``(px, py)`` có nằm trong vùng mực không, theo quy tắc nonzero winding."""
    winding = 0
    for points in contours:
        count = len(points)
        for i in range(count):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % count]
            if y0 <= py < y1:
                if (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) > 0:
                    winding += 1
            elif y1 <= py < y0:
                if (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) < 0:
                    winding -= 1
    return winding != 0


def cells(contours: list[Contour], grid: Grid) -> set[tuple[int, int]]:
    """Tập ô ``(row, col)`` có mực, lấy mẫu tại tâm mỗi ô."""
    return {
        (row, col)
        for row in range(grid.rows)
        for col in range(grid.cols)
        if inside(*grid.cell_center(row, col), contours)
    }


def rasterize(contours: list[Contour], grid: Grid, ink: str = "#", blank: str = ".") -> list[str]:
    """Lưới text của glyph, mỗi phần tử là một hàng."""
    filled = cells(contours, grid)
    return [
        "".join(ink if (row, col) in filled else blank for col in range(grid.cols))
        for row in range(grid.rows)
    ]


def format_grid(lines: list[str], indent: str = "   ") -> str:
    """Lưới text kèm chỉ số hàng, để đọc và để đưa vào state cho Jev."""
    width = len(str(len(lines) - 1))
    return "\n".join(f"{indent}{i:>{width}} {' '.join(line)}" for i, line in enumerate(lines))
