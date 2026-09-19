"""Dựng glyph tiếng Việt từ base + modifier + tone.

Nguyên tắc: **giữ nguyên contour gốc**. Carrier lấy nguyên contour từ font (không
qua bounding box), mark chỉ được dịch chứ không bị vẽ lại. Nhờ vậy shape của chữ
nền không bị phá — đây chính là chỗ pipeline làm tay hỏng.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vietfont import charset as cs
from vietfont.glyph import (
    Contour,
    bounds,
    contours as read_contours,
    ensure_winding,
    is_clockwise,
    translate,
)
from vietfont.grid import Grid
from vietfont.marks import MarkPack


class ComposeError(Exception):
    """Không dựng được glyph vì thiếu nguyên liệu."""


@dataclass
class Composition:
    char: str
    contours: list[Contour]
    #: Contour của riêng tone mark, đã áp dịch — dùng để crop vùng mark khi hỏi Jev.
    mark_contours: list[Contour]
    #: Nguồn của carrier: ``font`` (glyph base+modifier có sẵn) hoặc ``pack``.
    carrier_source: str
    #: Nguồn của tone mark: ``font``, ``pack``, hoặc ``none``.
    tone_source: str
    #: Dịch dọc đã áp cho tone mark.
    shift: float
    #: Các cặp contour của carrier và mark chồng lên nhau (lỗi thiết kế cần xử lý).
    collisions: list[tuple[tuple[float, ...], tuple[float, ...]]] = field(default_factory=list)


def compose(font, char: str, pack: MarkPack, grid: Grid) -> Composition:
    """Dựng contour cho ``char`` từ những gì font và pack cung cấp."""
    base, modifier, tone = cs.decompose(char)
    carrier, carrier_source = _carrier(font, base, modifier, pack)
    mark, tone_source = _tone(font, tone, pack)

    # Mark phải quay cùng chiều với carrier, nếu không phần chồng sẽ bị quy tắc
    # nonzero winding triệt tiêu và mất mực.
    if mark:
        mark = ensure_winding(mark, clockwise=is_clockwise(carrier))

    shift = _tone_shift(carrier, mark, tone, grid) if mark else 0.0
    shifted = translate(mark, 0, shift) if mark else []

    # Hết chỗ: chữ HOA chiếm row 3-10, modifier row 0-1, chỉ còn 1 row trống mà
    # tone mark cần 2. Thu gọn modifier xuống 1 row để nhường chỗ cho tone.
    if mark and _collisions(carrier, shifted):
        compact = _compact_carrier(font, base, modifier, pack)
        if compact is not None:
            carrier = ensure_winding(compact, clockwise=is_clockwise(carrier))
            carrier_source = f"{carrier_source}+compact"
            shift = _tone_shift(carrier, mark, tone, grid)
            shifted = translate(mark, 0, shift)

    return Composition(
        char=char,
        contours=carrier + shifted,
        mark_contours=shifted,
        carrier_source=carrier_source,
        tone_source=tone_source,
        shift=shift,
        collisions=_collisions(carrier, shifted),
    )


def _compact_carrier(font, base: str, modifier: str, pack: MarkPack) -> list[Contour] | None:
    """Dựng lại carrier với modifier thu gọn 1 hàng, đặt ngay trên mực chữ nền."""
    compact = pack.compact_modifier(modifier)
    if compact is None:
        return None
    base_contours = _glyph_contours(font, base)
    base_box = bounds(base_contours)
    modifier_box = bounds(compact)
    if base_box is None or modifier_box is None:
        return None
    return base_contours + translate(compact, 0, base_box[3] - modifier_box[1])


def _carrier(font, base: str, modifier: str, pack: MarkPack) -> tuple[list[Contour], str]:
    if modifier == "none":
        return _glyph_contours(font, base), "font"

    carrier_char = cs.compose_name(base, modifier)
    if ord(carrier_char) in font:
        return _glyph_contours(font, carrier_char), "font"

    extra = pack.modifier(modifier, base)
    if extra is None:
        raise ComposeError(
            f"thiếu {modifier!r} cho {base!r}: font không có {carrier_char!r} và pack không khai báo"
        )
    return _glyph_contours(font, base) + extra, "pack"


def _tone(font, tone: str, pack: MarkPack) -> tuple[list[Contour], str]:
    if tone == "none":
        return [], "none"

    combining = cs.TONES[tone]
    if ord(combining) in font:
        return _glyph_contours(font, combining), "font"

    mark = pack.mark(tone)
    if mark is None:
        raise ComposeError(f"thiếu mark {tone!r}: font không có U+{ord(combining):04X} và pack không khai báo")
    return mark, "pack"


def _glyph_contours(font, char: str) -> list[Contour]:
    if ord(char) not in font:
        raise ComposeError(f"font không có {char!r} (U+{ord(char):04X})")
    return read_contours(font[ord(char)])


def _tone_shift(carrier: list[Contour], mark: list[Contour], tone: str, grid: Grid) -> float:
    """Dịch mark lên vừa đủ để nằm trên mực của carrier, không vượt đỉnh lưới."""
    if tone == "dot_below":
        return 0.0

    carrier_box = bounds(carrier)
    mark_box = bounds(mark)
    if carrier_box is None or mark_box is None:
        return 0.0

    lift = carrier_box[3] - mark_box[1]
    headroom = grid.top - mark_box[3]
    return max(0.0, min(lift, headroom))


def _collisions(carrier: list[Contour], mark: list[Contour]) -> list[tuple[tuple[float, ...], tuple[float, ...]]]:
    """Các cặp contour chồng nhau — dấu hiệu mark đè lên chữ nền."""
    out = []
    for a in carrier:
        box_a = bounds([a])
        for b in mark:
            box_b = bounds([b])
            if box_a is None or box_b is None:
                continue
            if box_a[0] < box_b[2] and box_b[0] < box_a[2] and box_a[1] < box_b[3] and box_b[1] < box_a[3]:
                out.append((box_a, box_b))
    return out
