"""Ghi glyph vào font và xuất file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from vietfont.analyze import analyze
from vietfont.compose import ComposeError, compose
from vietfont.glyph import Contour, set_contours
from vietfont.grid import reference_advance
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


def collisions(font, pack: MarkPack) -> dict[str, int]:
    """Quét glyph còn thiếu và trả về những cái có dấu đè lên chữ nền (không sửa font)."""
    analysis = analyze(font)
    found: dict[str, int] = {}
    for char in analysis.missing:
        try:
            result = compose(font, char, pack, analysis.grid)
        except ComposeError:
            continue
        if result.collisions:
            found[char] = len(result.collisions)
    return found


def rename(
    path: str | Path, family: str, *, style: str = "Regular", note: str | None = None
) -> None:
    """Ghi lại name table của file font để bản phái sinh không đè lên font gốc.

    Cài hai font cùng tên family vào một máy là hỏng: hệ điều hành chỉ giữ một.
    Phải sửa cả nameID 16 (typographic family) — fontforge chỉ đặt nameID 1, nên
    macOS vẫn hiện family cũ.

    Font gốc là SIL OFL 1.1: giữ nguyên thông báo bản quyền, chỉ thêm ghi chú phái sinh.
    """
    from fontTools.ttLib import TTFont

    font = TTFont(str(path))
    postscript = f"{family.replace(' ', '')}-{style}"
    updates = {
        1: family,  # Family
        2: style,  # Subfamily
        3: f"1.500;UKWN;{postscript}",  # Unique ID
        4: f"{family} {style}",  # Full name
        6: postscript,  # PostScript name
        16: family,  # Typographic family
        17: style,  # Typographic subfamily
    }
    if note:
        for record in font["name"].names:
            if record.nameID == 0:
                updates[0] = f"{record.toUnicode()}. {note}"

    for record in list(font["name"].names):
        if record.nameID in updates:
            font["name"].setName(
                updates[record.nameID],
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID,
            )
    font.save(str(path))


def save(font, path: str | Path) -> None:
    """Xuất font ra file."""
    font.generate(str(path))


def _reference_width(font) -> float:
    """Bề rộng chuẩn của font (monospace) — lấy từ glyph có sẵn."""
    return float(reference_advance(font))
