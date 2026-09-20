"""Kiểm tra font đã Việt hoá: coverage, giữ shape chữ nền, không mất mực.

Ba tiêu chí này là hợp đồng của tool. Chúng từng chỉ kiểm được bằng script ad-hoc,
và đúng ba chỗ đó đã để lọt ba bug thật (flatten 64 glyph, contour chồng nhau,
mất mực ở ``Ẳ``) — nên chúng được đóng thành lệnh.

``source`` và ``pack`` là tuỳ chọn: thiếu chúng thì chỉ kiểm được coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vietfont import charset as cs
from vietfont.compose import ComposeError, compose
from vietfont.glyph import contours as read_contours
from vietfont.grid import Grid
from vietfont.marks import MarkPack
from vietfont.render import cells


@dataclass
class VerifyReport:
    total: int
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    #: Glyph mất contour của chữ nền — dấu hiệu bị flatten.
    flattened: list[str] = field(default_factory=list)
    #: Glyph có mực khác với thiết kế: ký tự -> (số pixel mất, số pixel thêm).
    ink_diff: dict[str, tuple[int, int]] = field(default_factory=dict)
    #: Glyph có dấu đè lên chữ nền: ký tự -> số cặp contour chồng.
    collisions: dict[str, int] = field(default_factory=dict)
    #: Nhóm ký tự ra cùng một hình — dấu này nuốt dấu kia.
    duplicates: list[list[str]] = field(default_factory=list)
    #: Phân bố khoảng cách dấu–chữ nền: số hàng -> số glyph.
    gaps: dict[int, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.flattened
            or self.ink_diff
            or self.collisions
            or self.duplicates
        )


def verify(font, *, source=None, pack: MarkPack | None = None) -> VerifyReport:
    """Kiểm tra ``font``. Truyền ``source`` (và ``pack``) để kiểm sâu hơn."""
    target = cs.charset()
    report = VerifyReport(
        total=len(target),
        present=[c for c in target if ord(c) in font],
        missing=[c for c in target if ord(c) not in font],
    )

    if source is not None:
        report.flattened = _flattened(font, source, report.present)
        report.gaps = _gaps(font, report.present)
        report.duplicates = _duplicates(font, report.present)

    if source is not None and pack is not None:
        grid = Grid.detect(source)
        report.ink_diff = _ink_diff(font, source, pack, grid, report.present)
        report.collisions = _collisions(source, pack, grid, report.present)

    return report


def _flattened(font, source, present: list[str]) -> list[str]:
    """Glyph không còn giữ mực của chữ nền.

    Contour của chữ nền phải còn nguyên, hoặc được mark phủ trọn. Chữ ``i`` rơi vào
    trường hợp sau: dấu chấm nằm đúng dải của mark nên mark nuốt nó — mực vẫn còn,
    chỉ là contour đã gộp. Kiểm bằng contour đơn thuần sẽ báo nhầm là flatten.
    """
    grid = Grid.detect(source)
    out = []
    for char in present:
        base = cs.decompose(char)[0]
        if ord(base) not in source:
            continue
        have = read_contours(font[ord(char)])
        have_cells = cells(have, grid)
        for contour in read_contours(source[ord(base)]):
            if contour in have or cells([contour], grid) <= have_cells:
                continue
            out.append(char)
            break
    return out


def _duplicates(font, present: list[str]) -> list[list[str]]:
    """Nhóm ký tự ra cùng một hình.

    Dấu thanh và dấu mũ có thể chen kẽ nhau theo cột mà không chồng hộp bao, nên
    phép kiểm va chạm không bắt được: ``Ấ`` và ``Ẩ`` ra cùng một hình, ``Ẫ`` mất hẳn
    dấu mũ và trùng khít ``Ã``. So hình rasterized mới thấy.
    """
    grid = Grid.detect(font)
    seen: dict[frozenset[tuple[int, int]], list[str]] = {}
    for char in present:
        key = frozenset(cells(read_contours(font[ord(char)]), grid))
        seen.setdefault(key, []).append(char)
    return [group for group in seen.values() if len(group) > 1]


def _ink_diff(
    font, source, pack: MarkPack, grid: Grid, present: list[str]
) -> dict[str, tuple[int, int]]:
    """So mực thật trong font với mực mà bộ dựng thiết kế.

    Chỉ xét glyph do tool dựng — glyph có sẵn trong font gốc không bị đụng.
    """
    out: dict[str, tuple[int, int]] = {}
    for char in present:
        if ord(char) in source:
            continue
        try:
            expected = cells(compose(source, char, pack, grid).contours, grid)
        except ComposeError:
            continue
        actual = cells(read_contours(font[ord(char)]), grid)
        if expected != actual:
            out[char] = (len(expected - actual), len(actual - expected))
    return out


def _collisions(
    source, pack: MarkPack, grid: Grid, present: list[str]
) -> dict[str, int]:
    """Glyph mà dấu đè lên chữ nền khi dựng lại từ font gốc."""
    out: dict[str, int] = {}
    for char in present:
        if ord(char) in source:
            continue
        try:
            result = compose(source, char, pack, grid)
        except ComposeError:
            continue
        if result.collisions:
            out[char] = len(result.collisions)
    return out


def _gaps(font, present: list[str]) -> dict[int, int]:
    """Phân bố số hàng trống giữa dấu thấp nhất và mực trên cùng của chữ nền."""
    from vietfont.render import cells as cells_of

    grid = Grid.detect(font)
    histogram: dict[int, int] = {}
    for char in present:
        base, modifier, tone = cs.decompose(char)
        if tone == "none" and modifier == "none":
            continue
        rows = {r for (r, _) in cells_of(read_contours(font[ord(char)]), grid)}
        base_rows = {r for (r, _) in cells_of(read_contours(font[ord(base)]), grid)}
        if not base_rows:
            continue
        top = min(base_rows)
        above = [r for r in rows if r < top]
        if not above:
            continue
        gap = top - max(above) - 1
        histogram[gap] = histogram.get(gap, 0) + 1
    return histogram
