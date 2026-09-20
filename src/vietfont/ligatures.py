"""Ligature lập trình: nhập từ font nguồn, snap lưới, sửa pitch.

**Đọc trước khi dùng.** Nguồn duy nhất hiện có là bản cộng đồng
(``danicaj3w/departure-mono``), và nó **chưa được duyệt** — maintainer đã từ chối ở
issue #12. Đo trên 26 glyph: 24 glyph lệch lưới, 25 glyph sai advance, ``>=`` và
``<=`` thiếu hẳn thành phần ``=``, ``****``/``***`` rối ở cỡ nhỏ.

Module này sửa được hai lỗi **hình học**:

- mọi điểm contour kéo về bội số của ``grid.pitch``;
- advance đặt bằng ``pitch × cols × số ký tự`` mà ligature thay thế.

Nó **không** sửa được lỗi thiết kế. Snap một glyph hỏng ra vẫn là glyph hỏng. Đừng
coi output của module này là artwork dùng được — xem
``docs/research/ligature-audit.md`` trước khi bật vào bản phát hành.

Feature ``liga`` sinh từ chính pack rồi gắn bằng ``fontforge.mergeFeature()`` — cách
này giữ nguyên 19 feature sẵn có của font gốc, khác bản dựng tay ``DepartureMonoLigaZ``
chỉ còn đúng 1 feature.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import fontforge

from vietfont.glyph import Contour
from vietfont.glyph import contours as read_contours
from vietfont.glyph import set_contours


@dataclass(frozen=True)
class Rule:
    """Một quy tắc thay thế: dãy ký tự nguồn -> glyph ligature."""

    source: tuple[str, ...]
    target: str

    @property
    def cells(self) -> int:
        """Số ô monospace mà ligature chiếm."""
        return len(self.source)


@dataclass
class LigaturePack:
    """Bộ ligature: font nguồn + danh sách quy tắc."""

    source: str
    rules: list[Rule]

    @classmethod
    def load(cls, path: str | Path) -> LigaturePack:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            source=raw["source"],
            rules=[Rule(tuple(r["from"]), r["to"]) for r in raw["rules"]],
        )

    def fea(self, only: set[str] | None = None) -> str:
        """Sinh feature file cho ``fontforge.mergeFeature()``.

        ``only`` giới hạn quy tắc được ghi — dùng khi một phần glyph không nhập
        được, để feature file không trỏ tới glyph không tồn tại.

        Phải khai cả ``latn``: chỉ khai ``DFLT`` thì feature ``liga`` không được
        đăng ký dưới script Latin, và trình duyệt/renderer dùng ``latn`` cho
        ``==``, ``=>`` nên ligature không bao giờ chạy.
        """
        rules = [r for r in self.rules if only is None or r.target in only]
        lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", ""]
        lines.append("feature liga {")
        lines += [f"    sub {' '.join(r.source)} by {r.target};" for r in rules]
        lines += ["} liga;", ""]
        return "\n".join(lines)


@dataclass
class LigatureReport:
    """Kết quả ghép ligature."""

    added: list[str] = field(default_factory=list)
    #: Glyph không có trong font nguồn.
    missing: list[str] = field(default_factory=list)
    #: Glyph -> số điểm phải dịch để về lưới.
    snapped: dict[str, int] = field(default_factory=dict)
    #: Glyph -> số contour bị bỏ vì teo thành điểm sau khi snap.
    dropped: dict[str, int] = field(default_factory=dict)
    #: Glyph không còn contour nào sau khi snap.
    empty: list[str] = field(default_factory=list)
    #: Glyph -> (advance nguồn, advance đã đặt).
    advances: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.empty)


def snap(contours: list[Contour], pitch: int) -> tuple[list[Contour], int, int]:
    """Kéo mọi điểm về bội số của ``pitch``, rồi dọn contour hỏng.

    Làm tròn đơn thuần là chưa đủ: hai đỉnh kề nhau có thể rơi vào **cùng một ô**, để
    lại contour diện tích 0 — fontforge vẽ ra hư không, mà ảnh raster lại che mất.
    Nên sau khi snap phải gộp đỉnh trùng kề nhau và bỏ contour còn dưới 3 đỉnh.

    Trả về ``(contour đã snap, số điểm phải dịch, số contour bị bỏ)``.
    """
    moved = 0
    dropped = 0
    out: list[Contour] = []
    for points in contours:
        snapped: Contour = []
        for x, y in points:
            sx, sy = round(x / pitch) * pitch, round(y / pitch) * pitch
            if (sx, sy) != (x, y):
                moved += 1
            point = (float(sx), float(sy))
            if snapped and snapped[-1] == point:
                continue
            snapped.append(point)
        # contour khép kín: đỉnh cuối trùng đỉnh đầu cũng là thừa
        while len(snapped) > 1 and snapped[0] == snapped[-1]:
            snapped.pop()
        if len(snapped) < 3:
            dropped += 1
            continue
        out.append(snapped)
    return out, moved, dropped


def add_ligatures(
    font, pack: LigaturePack, base_dir: str | Path, grid
) -> LigatureReport:
    """Ghép ligature của ``pack`` vào ``font``, rồi gắn feature ``liga``.

    ``base_dir`` là thư mục chứa ``pack.source``. ``grid`` quyết định pitch và số ô.

    Kiểm tra trước rồi mới sửa: pack thiếu glyph nguồn thì dừng ngay, không mutate
    font và không gọi ``mergeFeature`` — nếu không, feature file vẫn chứa quy tắc
    trỏ tới glyph không tồn tại và lỗi sẽ nổ bên trong fontforge thay vì trả về
    ``LigatureReport.missing``.
    """
    report = LigatureReport()
    source = fontforge.open(str(Path(base_dir) / pack.source))
    try:
        missing = [r.target for r in pack.rules if r.target not in source]
        if missing:
            report.missing = missing
            return report

        advance = grid.pitch * grid.cols
        for rule in pack.rules:
            snapped, moved, dropped = snap(read_contours(source[rule.target]), grid.pitch)
            if not snapped:
                report.empty.append(rule.target)
                continue
            if rule.target not in font:
                font.createChar(-1, rule.target)
            target = font[rule.target]
            before = int(target.width)
            set_contours(target, snapped, width=advance * rule.cells)
            report.added.append(rule.target)
            if moved:
                report.snapped[rule.target] = moved
            if dropped:
                report.dropped[rule.target] = dropped
            if before != advance * rule.cells:
                report.advances[rule.target] = (before, advance * rule.cells)
    finally:
        source.close()

    if not report.added:
        return report

    with tempfile.NamedTemporaryFile(
        "w", suffix=".fea", encoding="utf-8", delete=False
    ) as handle:
        handle.write(pack.fea(only=set(report.added)))
        fea_path = handle.name
    try:
        font.mergeFeature(fea_path)
    finally:
        Path(fea_path).unlink(missing_ok=True)

    return report
