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
    ensure_winding,
    is_clockwise,
    translate,
)
from vietfont.glyph import (
    contours as read_contours,
)
from vietfont.grid import Grid
from vietfont.marks import MarkPack
from vietfont.render import cells


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
    collisions: list[tuple[tuple[float, ...], tuple[float, ...]]] = field(
        default_factory=list
    )


def compose(font, char: str, pack: MarkPack, grid: Grid) -> Composition:
    """Dựng contour cho ``char`` từ những gì font và pack cung cấp."""
    base, modifier, tone = cs.decompose(char)
    carrier, carrier_source = _carrier(font, base, modifier, pack)
    mark, tone_source = _tone(font, tone, pack)

    # Mark phải quay cùng chiều với carrier, nếu không phần chồng sẽ bị quy tắc
    # nonzero winding triệt tiêu và mất mực.
    if mark:
        mark = ensure_winding(mark, clockwise=is_clockwise(carrier))

    # Với glyph 1 dấu, vật cản là x-height/cap-height của chữ nền; với glyph 2 dấu,
    # vật cản là chính modifier nên dùng đỉnh mực của carrier.
    obstacle = _letter_top(font, base) if modifier == "none" else _ink_top(carrier)

    # Chữ HOA chỉ còn 2 hàng phía trên cap-height. Mark đầy đủ (dấu hỏi 4 hàng) không
    # vừa thì dùng bản thu gọn, thay vì để `_tone_shift` kẹp lại rồi dấu đè lên nhau.
    if mark and obstacle is not None and not _fits(mark, obstacle, grid):
        compact_mark = pack.compact_mark(tone)
        if compact_mark is not None:
            mark = ensure_winding(compact_mark, clockwise=is_clockwise(carrier))
            tone_source = f"{tone_source}+compact"

    shift = _tone_shift(carrier, mark, tone, grid, obstacle) if mark else 0.0
    shifted, carrier = (
        _dedupe(translate(mark, 0, shift), carrier) if mark else ([], carrier)
    )

    # Hết chỗ: chữ HOA chiếm row 3-10, modifier row 0-1, chỉ còn 1 row trống mà
    # tone mark cần 2. Thu gọn modifier xuống 1 row để nhường chỗ cho tone.
    if mark and modifier != "none" and _shares_rows(carrier, shifted, grid):
        compact = _compact_carrier(font, base, modifier, pack)
        if compact is not None:
            carrier = ensure_winding(compact, clockwise=is_clockwise(carrier))
            carrier_source = f"{carrier_source}+compact"
            shift = _tone_shift(carrier, mark, tone, grid, _ink_top(carrier))
            shifted, carrier = _dedupe(translate(mark, 0, shift), carrier)

    return Composition(
        char=char,
        contours=carrier + shifted,
        mark_contours=shifted,
        carrier_source=carrier_source,
        tone_source=tone_source,
        shift=shift,
        collisions=_collisions(carrier, shifted),
    )


def _compact_carrier(
    font, base: str, modifier: str, pack: MarkPack
) -> list[Contour] | None:
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


def _carrier(
    font, base: str, modifier: str, pack: MarkPack
) -> tuple[list[Contour], str]:
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
        raise ComposeError(
            f"thiếu mark {tone!r}: font không có U+{ord(combining):04X} và pack không khai báo"
        )
    return mark, "pack"


def _glyph_contours(font, char: str) -> list[Contour]:
    if ord(char) not in font:
        raise ComposeError(f"font không có {char!r} (U+{ord(char):04X})")
    return read_contours(font[ord(char)])


def _ink_top(contours: list[Contour]) -> float | None:
    """Đỉnh mực của một nhóm contour."""
    box = bounds(contours)
    return box[3] if box is not None else None


def _fits(mark: list[Contour], obstacle_top: float, grid: Grid) -> bool:
    """Mark có đủ chỗ nằm trên vật cản, chừa 1 hàng lưới, mà không vượt đỉnh lưới."""
    box = bounds(mark)
    if box is None:
        return True
    need = obstacle_top + grid.pitch - box[1]
    room = grid.top - box[3]
    return need <= room


def _tone_shift(
    carrier: list[Contour],
    mark: list[Contour],
    tone: str,
    grid: Grid,
    obstacle_top: float | None = None,
) -> float:
    """Dịch mark lên để chừa đúng 1 hàng lưới trên vật cản nằm dưới nó.

    Vật cản là modifier (glyph 2 dấu) hoặc đỉnh chữ nền (glyph 1 dấu). Với glyph
    1 dấu, đỉnh phải là x-height/cap-height chứ không phải mực trên cùng: chữ ``i``
    có dấu chấm cao hơn x-height, và font gốc đặt dấu trên ``i`` ngang hàng với dấu
    chấm chứ không phải trên nó. Không vượt đỉnh lưới.
    """
    if tone == "dot_below":
        return 0.0

    mark_box = bounds(mark)
    if mark_box is None:
        return 0.0

    if obstacle_top is None:
        carrier_box = bounds(carrier)
        if carrier_box is None:
            return 0.0
        obstacle_top = carrier_box[3]

    lift = obstacle_top + grid.pitch - mark_box[1]
    headroom = grid.top - mark_box[3]
    return max(0.0, min(lift, headroom))


def _letter_top(font, base: str) -> float | None:
    """Đỉnh mà tone mark phải vượt với glyph 1 dấu: x-height hoặc cap-height."""
    value = font.os2_xheight if base.islower() else font.os2_capheight
    return float(value) if value else None


def _dedupe(
    mark: list[Contour], carrier: list[Contour]
) -> tuple[list[Contour], list[Contour]]:
    """Gộp mark vào carrier: bỏ contour trùng khít, và bỏ contour carrier nằm lọt trong mark.

    Chữ ``i`` có dấu chấm nằm đúng dải của mark. Font gốc gộp hai thứ làm một; nếu để
    cả hai thì fontforge coi là contour lồng nhau, lật chiều, và mất mực. Nên mark
    **nuốt** luôn dấu chấm: contour nào của carrier nằm trọn trong một contour của mark
    thì bị bỏ, thay vì để chúng chồng nhau.

    Trả về ``(mark, carrier)`` đã lọc.
    """
    carrier_keys = {frozenset(points) for points in carrier}
    kept_mark = [p for p in mark if frozenset(p) not in carrier_keys]

    mark_boxes = [b for b in (bounds([p]) for p in kept_mark) if b is not None]
    kept_carrier = []
    for contour in carrier:
        box = bounds([contour])
        inside = box is not None and any(
            mb[0] <= box[0] and box[2] <= mb[2] and mb[1] <= box[1] and box[3] <= mb[3]
            for mb in mark_boxes
        )
        if not inside:
            kept_carrier.append(contour)

    return kept_mark, kept_carrier


def _shares_rows(carrier: list[Contour], mark: list[Contour], grid: Grid) -> bool:
    """Mark có nằm chung hàng lưới với carrier không.

    Đây mới là phép kiểm đúng cho glyph 2 dấu. Kiểm hộp bao chồng nhau là không đủ:
    dấu sắc và dấu mũ trên ``Â`` chen kẽ nhau theo cột nên hộp bao chỉ chạm chứ không
    chồng, trong khi thực tế chúng nằm cùng hàng và hoà thành một khối — ``Ấ`` và
    ``Ẩ`` ra cùng một hình, ``Ẫ`` mất hẳn dấu mũ.
    """
    carrier_rows = {row for row, _ in cells(carrier, grid)}
    mark_rows = {row for row, _ in cells(mark, grid)}
    return bool(carrier_rows & mark_rows)


def _collisions(
    carrier: list[Contour], mark: list[Contour]
) -> list[tuple[tuple[float, ...], tuple[float, ...]]]:
    """Các cặp contour chồng nhau — dấu hiệu mark đè lên chữ nền."""
    out = []
    for a in carrier:
        box_a = bounds([a])
        for b in mark:
            box_b = bounds([b])
            if box_a is None or box_b is None:
                continue
            if (
                box_a[0] < box_b[2]
                and box_b[0] < box_a[2]
                and box_a[1] < box_b[3]
                and box_b[1] < box_a[3]
            ):
                out.append((box_a, box_b))
    return out
