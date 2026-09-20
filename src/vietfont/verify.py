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
    #: Ligature hỏng: glyph -> lý do (thiếu, lệch lưới, sai advance).
    ligatures: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.flattened
            or self.ink_diff
            or self.collisions
            or self.duplicates
            or self.ligatures
        )


def verify(
    font, *, source=None, pack: MarkPack | None = None, ligatures=None, path=None
) -> VerifyReport:
    """Kiểm tra ``font``. Truyền ``source`` (và ``pack``) để kiểm sâu hơn.

    ``path`` là đường dẫn file của ``font`` — cần khi kiểm ligature, vì phép kiểm
    đó phải đọc bảng GSUB của file đã lưu.
    """
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
        # Lưới của font **xuất**, không phải font gốc: nâng ascent đổi số hàng, và
        # bộ dựng đã chạy trên lưới mới. Lấy lưới gốc thì thiết kế lệch hàng.
        grid = Grid.detect(font)
        report.ink_diff = _ink_diff(font, source, pack, grid, report.present)
        report.collisions = _collisions(source, pack, grid, report.present)

    if ligatures is not None:
        if path is None:
            raise ValueError("kiểm ligature cần đường dẫn file font (path=)")
        report.ligatures = _ligatures(font, ligatures, Grid.detect(font), path)

    return report


def _flattened(font, source, present: list[str]) -> list[str]:
    """Glyph không còn giữ mực của chữ nền.

    Contour của chữ nền phải còn nguyên, hoặc được mark phủ trọn. Chữ ``i`` rơi vào
    trường hợp sau: dấu chấm nằm đúng dải của mark nên mark nuốt nó — mực vẫn còn,
    chỉ là contour đã gộp. Kiểm bằng contour đơn thuần sẽ báo nhầm là flatten.
    """
    grid = Grid.detect(font)
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


#: Script mà ligature lập trình phải chạy được. Kiểm riêng từng cái, không gộp.
REQUIRED_SCRIPTS = ("DFLT", "latn")


def _liga_substitutions(path) -> tuple[dict[tuple[str, ...], str], set[str]]:
    """Dãy glyph nguồn -> glyph ligature, cùng các script KHÔNG bật ``liga``.

    Kiểm theo **default LangSys của từng script được yêu cầu**, không gộp chung:
    ``mergeFeature`` có thể đăng ký ``liga`` dưới ``DFLT`` mà quên ``latn``, hoặc chỉ
    bật nó cho một LangSys phụ như ``latn/TRK``. Gộp ``DefaultLangSys`` với mọi
    ``LangSysRecord`` sẽ che mất cả hai ca đó — trong khi văn bản Latin thường vẫn
    không ligate.

    ``hb-shape --script=latn`` là phép thử bắt được lỗi này.
    """
    from fontTools.ttLib import TTFont

    font = TTFont(str(path))
    gsub = font.get("GSUB")
    if gsub is None:
        return {}, set(REQUIRED_SCRIPTS)
    table = gsub.table
    liga = {
        i
        for i, record in enumerate(table.FeatureList.FeatureRecord)
        if record.FeatureTag == "liga"
    }

    by_tag = {script.ScriptTag: script.Script for script in table.ScriptList.ScriptRecord}
    missing: set[str] = set()
    per_script: dict[str, set[int]] = {}
    for tag in REQUIRED_SCRIPTS:
        script = by_tag.get(tag)
        default = script.DefaultLangSys if script is not None else None
        enabled = {i for i in default.FeatureIndex if i in liga} if default else set()
        per_script[tag] = enabled
        if not enabled:
            missing.add(tag)

    common = set.intersection(*per_script.values()) if per_script else set()

    lookups: set[int] = set()
    for i in common:
        lookups.update(table.FeatureList.FeatureRecord[i].Feature.LookupListIndex)

    out: dict[tuple[str, ...], str] = {}
    for index in lookups:
        for sub in table.LookupList.Lookup[index].SubTable:
            for first, ligatures in getattr(sub, "ligatures", {}).items():
                for ligature in ligatures:
                    out[(first, *ligature.Component)] = ligature.LigGlyph
    return out, missing


def _ligatures(font, pack, grid: Grid, path) -> dict[str, str]:
    """Ligature phải được GSUB thay thế, có mặt, nằm trên lưới, đúng nhịp.

    Ba nhóm lỗi thật đã gặp: bản cộng đồng lệch lưới (24/26) và sai advance (25/26);
    ``mergeFeature`` gắn ``liga`` thiếu script ``latn``.
    """
    out: dict[str, str] = {}
    advance = grid.pitch * grid.cols
    substitutions, missing_scripts = _liga_substitutions(path)

    if missing_scripts:
        return {
            "liga": f"feature không bật cho script {', '.join(sorted(missing_scripts))}"
        }

    for rule in pack.rules:
        key = tuple(rule.source)
        if key not in substitutions:
            out[rule.target] = "GSUB không thay thế dãy này"
            continue
        if substitutions[key] != rule.target:
            out[rule.target] = f"GSUB trỏ sai: {substitutions[key]}"
            continue
        if rule.target not in font:
            out[rule.target] = "thiếu glyph"
            continue
        glyph = font[rule.target]
        points = [(x, y) for c in read_contours(glyph) for (x, y) in c]
        if not points:
            out[rule.target] = "glyph rỗng"
            continue
        off = [p for p in points if p[0] % grid.pitch or p[1] % grid.pitch]
        if off:
            out[rule.target] = f"{len(off)}/{len(points)} điểm lệch lưới"
            continue
        want = advance * rule.cells
        if int(glyph.width) != want:
            out[rule.target] = f"advance {int(glyph.width)} != {want}"
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
