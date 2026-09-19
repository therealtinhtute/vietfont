"""Lưới pixel của font.

Font pixel vẽ mọi thứ trên một lưới đều: ``pitch`` đơn vị mỗi ô, ``cols`` ô
ngang, ``rows`` ô dọc, ô trên cùng kết thúc ở ``top``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import reduce
from math import gcd

#: Tỉ lệ toạ độ tối thiểu phải chia hết cho pitch để coi là hợp lệ.
_COVERAGE = 0.95


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
        """Suy ra lưới từ chính font: biên từ typo metrics, pitch từ toạ độ."""
        top = int(font.os2_typoascent)
        bottom = int(font.os2_typodescent)
        advance = reference_advance(font)
        pitch = _detect_pitch(font, advance)
        return cls(
            pitch=pitch,
            cols=round(advance / pitch),
            rows=round((top - bottom) / pitch),
            top=top,
        )


def reference_advance(font) -> int:
    """Bề rộng chuẩn của font (monospace) — lấy từ glyph có sẵn."""
    for char in "aoO":
        if ord(char) in font:
            return int(font[ord(char)].width)
    raise ValueError("không tìm được glyph tham chiếu để lấy bề rộng")


def _detect_pitch(font, advance: int) -> int:
    """Ước lớn nhất của ``advance`` mà gần như mọi toạ độ đều chia hết.

    Không dùng gcd của toàn bộ toạ độ: chỉ cần vài toạ độ lệch (do sửa tay) là gcd
    sập về 1, lưới phình thành hàng trăm nghìn ô, và mọi phép rasterize thành vô dụng.
    """
    counts = _coordinate_counts(font)
    if not counts:
        raise ValueError("không suy được pitch: font không có contour nào")

    total = sum(counts.values())
    for candidate in sorted(_divisors(advance), reverse=True):
        covered = sum(n for value, n in counts.items() if value % candidate == 0)
        if covered >= _COVERAGE * total:
            return candidate
    return reduce(gcd, counts)


def _coordinate_counts(font) -> Counter[int]:
    """Đếm tần suất từng toạ độ (và bề rộng) trong font."""
    counts: Counter[int] = Counter()
    for glyph in font.glyphs():
        for contour in glyph.foreground:
            for point in contour:
                counts[abs(int(point.x))] += 1
                counts[abs(int(point.y))] += 1
        if glyph.width:
            counts[abs(int(glyph.width))] += 1
    counts.pop(0, None)
    return counts


def _divisors(value: int) -> list[int]:
    return [d for d in range(1, value + 1) if value % d == 0]
