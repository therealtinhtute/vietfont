"""Lưới pixel của font.

Font pixel vẽ mọi thứ trên một lưới đều: ``pitch`` đơn vị mỗi ô, ``cols`` ô
ngang, ``rows`` ô dọc, ô trên cùng kết thúc ở ``top``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from math import gcd


@dataclass(frozen=True)
class Grid:
    pitch: int
    cols: int
    rows: int
    top: int

    @property
    def bottom(self) -> int:
        return self.top - self.rows * self.pitch

    @property
    def width(self) -> int:
        return self.cols * self.pitch

    def cell_rect(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Hộp ``(x0, y0, x1, y1)`` của ô ``(row, col)``, gốc trên-trái."""
        return (
            col * self.pitch,
            self.top - (row + 1) * self.pitch,
            (col + 1) * self.pitch,
            self.top - row * self.pitch,
        )

    def cell_center(self, row: int, col: int) -> tuple[float, float]:
        x0, y0, x1, y1 = self.cell_rect(row, col)
        return (x0 + x1) / 2, (y0 + y1) / 2

    @classmethod
    def detect(cls, font) -> Grid:
        """Suy ra lưới từ chính font: pitch = gcd mọi toạ độ, biên từ typo metrics."""
        top = int(font.os2_typoascent)
        bottom = int(font.os2_typodescent)
        pitch = _detect_pitch(font)
        rows = round((top - bottom) / pitch)
        advance = int(font["a"].width) if ord("a") in font else int(font["A"].width)
        cols = round(advance / pitch)
        return cls(pitch=pitch, cols=cols, rows=rows, top=top)


def _detect_pitch(font) -> int:
    """gcd của mọi toạ độ điểm và mọi advance width trong font."""
    values: list[int] = []
    for glyph in font.glyphs():
        for contour in glyph.foreground:
            for point in contour:
                values.append(int(point.x))
                values.append(int(point.y))
        if glyph.width:
            values.append(int(glyph.width))
    values = [abs(v) for v in values if v]
    if not values:
        raise ValueError("không suy được pitch: font không có contour nào")
    return reduce(gcd, values)
