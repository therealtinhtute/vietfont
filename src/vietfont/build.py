"""Ghi glyph vào font và xuất file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from vietfont import charset as cs
from vietfont.analyze import analyze
from vietfont.compose import ComposeError, compose
from vietfont.glyph import Contour, set_contours
from vietfont.marks import MarkPack


@dataclass
class BuildReport:
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    #: Ký tự -> số cặp contour chồng nhau giữa chữ nền và dấu.
    collisions: dict[str, int] = field(default_factory=dict)
    #: Ký tự -> nguồn carrier/mark, để truy vết.
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed


def add_glyph(font, char: str, contours: list[Contour], width: float) -> None:
    """Tạo (nếu cần) và ghi contour cho ``char``."""
    codepoint = ord(char)
    if codepoint not in font:
        font.createChar(codepoint, f"uni{codepoint:04X}")
    set_contours(font[codepoint], contours, width)


def extend(font, pack: MarkPack, report: BuildReport | None = None) -> BuildReport:
    """Dựng toàn bộ ký tự tiếng Việt còn thiếu trong ``font`` (sửa font tại chỗ)."""
    report = report if report is not None else BuildReport()
    analysis = analyze(font)
    width = _reference_width(font)

    for char in analysis.missing:
        try:
            result = compose(font, char, pack, analysis.grid)
        except ComposeError as error:
            report.failed[char] = str(error)
            continue
        add_glyph(font, char, result.contours, width)
        report.added.append(char)
        report.sources[char] = f"{result.carrier_source}/{result.tone_source}"
        if result.collisions:
            report.collisions[char] = len(result.collisions)

    report.skipped = list(analysis.present)
    return report


def save(font, path: str | Path) -> None:
    """Xuất font ra file."""
    font.generate(str(path))


def _reference_width(font) -> float:
    """Bề rộng chuẩn của font (monospace) — lấy từ glyph có sẵn."""
    for char in "aoO":
        if ord(char) in font:
            return float(font[ord(char)].width)
    raise ValueError("không tìm được glyph tham chiếu để lấy bề rộng")
