"""Phân tích font: độ phủ tiếng Việt và kiểm kê thành phần có sẵn."""

from __future__ import annotations

from dataclasses import dataclass

from vietfont import charset as cs
from vietfont.grid import Grid


@dataclass(frozen=True)
class Analysis:
    grid: Grid
    present: list[str]
    missing: list[str]
    #: Ký tự ``base+modifier`` cần nhưng font không có (ví dụ ``ơ``).
    missing_carriers: list[str]
    #: Tên thanh điệu không có combining mark trong font (ví dụ ``hook_above``).
    missing_marks: list[str]

    @property
    def complete(self) -> bool:
        return not self.missing


def analyze(font) -> Analysis:
    """Đo độ phủ và kiểm kê những gì font còn thiếu để dựng đủ tiếng Việt."""
    target = cs.charset()
    present = [c for c in target if ord(c) in font]
    missing = [c for c in target if ord(c) not in font]

    needed_carriers: set[str] = set()
    needed_marks: set[str] = set()
    for char in missing:
        base, modifier, tone = cs.decompose(char)
        if modifier != "none":
            needed_carriers.add(cs.compose_name(base, modifier))
        if tone != "none":
            needed_marks.add(tone)

    return Analysis(
        grid=Grid.detect(font),
        present=present,
        missing=missing,
        missing_carriers=sorted(c for c in needed_carriers if ord(c) not in font),
        missing_marks=sorted(m for m in needed_marks if ord(cs.TONES[m]) not in font),
    )
