"""Bộ ký tự tiếng Việt và cách phân rã thành base / modifier / tone.

Bộ ký tự được sinh từ dữ liệu Unicode (tích Descartes của nguyên âm × thanh điệu,
chuẩn hoá NFC), không hardcode danh sách.
"""

from __future__ import annotations

import unicodedata

#: Nguyên âm cơ sở của tiếng Việt (đã gồm các biến thể có modifier).
BASES = "aăâeêioôơuưy"

#: Thanh điệu -> codepoint tổ hợp.
TONES: dict[str, str] = {
    "none": "",
    "acute": "\u0301",
    "grave": "\u0300",
    "hook_above": "\u0309",
    "tilde": "\u0303",
    "dot_below": "\u0323",
}

#: Modifier -> codepoint tổ hợp.
MODIFIERS: dict[str, str] = {
    "none": "",
    "breve": "\u0306",
    "circumflex": "\u0302",
    "horn": "\u031b",
}

_TONE_BY_COMBINING = {v: k for k, v in TONES.items() if v}
_MODIFIER_BY_COMBINING = {v: k for k, v in MODIFIERS.items() if v}

#: Chữ cái ngoài tích nguyên âm × thanh điệu.
EXTRA = "đ"


def charset() -> list[str]:
    """Trả về bộ ký tự tiếng Việt (134 ký tự, cả hoa và thường).

    Sinh bằng tích Descartes ``BASES × TONES`` rồi chuẩn hoá NFC, bỏ các ký tự
    ASCII thuần (font nào cũng đã có), thêm ``EXTRA``, rồi nhân đôi cho chữ hoa.
    """
    lower: list[str] = []
    for base in BASES:
        for combining in TONES.values():
            composed = unicodedata.normalize("NFC", base + combining)
            if len(composed) == 1 and not composed.isascii():
                lower.append(composed)
    lower.extend(EXTRA)
    return lower + [c.upper() for c in lower]


def decompose(char: str) -> tuple[str, str, str]:
    """Phân rã một ký tự thành ``(base, modifier, tone)``.

    ``base`` là chữ cái nền (có thể là ``đ``), ``modifier`` và ``tone`` là tên
    trong :data:`MODIFIERS` / :data:`TONES`, mặc định ``"none"``.
    """
    parts = unicodedata.normalize("NFD", char)
    base = parts[0]
    modifier = "none"
    tone = "none"
    for mark in parts[1:]:
        if mark in _MODIFIER_BY_COMBINING:
            modifier = _MODIFIER_BY_COMBINING[mark]
        elif mark in _TONE_BY_COMBINING:
            tone = _TONE_BY_COMBINING[mark]
    return base, modifier, tone


def compose_name(base: str, modifier: str) -> str:
    """Ký tự của ``base + modifier`` (không thanh điệu), dùng để tìm carrier."""
    return unicodedata.normalize("NFC", base + MODIFIERS[modifier])
