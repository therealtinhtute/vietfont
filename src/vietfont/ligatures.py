"""Ligature lập trình: ghép từ font nguồn vào font đích, snap lưới, sửa pitch.

Ligature của bản cộng đồng (``danicaj3w/departure-mono``) vẽ đúng dáng nhưng mắc
đúng hai lỗi mà maintainer nêu ở issue #12: **không snap về lưới pixel** và **sai
pitch monospace**. Đo trên 26 glyph: 24 glyph có điểm lệch lưới, 25 glyph có
advance khác bội số của ô.

Module này không vẽ lại — nó nhận dáng của bản cộng đồng rồi sửa hai lỗi đó:

- mọi điểm contour kéo về bội số của ``grid.pitch``;
- advance đặt bằng ``pitch × cols × số ký tự`` mà ligature thay thế.

Nhờ vậy ligature không phá lưới pixel lẫn nhịp monospace. Feature ``liga`` sinh
từ chính pack rồi gắn bằng ``fontforge.mergeFeature()`` — cách này giữ nguyên 19
feature sẵn có của font gốc, khác với bản dựng tay ``DepartureMonoLigaZ`` chỉ còn
đúng 1 feature.
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

    def fea(self) -> str:
        """Sinh feature file cho ``fontforge.mergeFeature()``.

        Phải khai cả ``latn``: chỉ khai ``DFLT`` thì feature ``liga`` không được
        đăng ký dưới script Latin, và trình duyệt/renderer dùng ``latn`` cho
        ``==``, ``=>`` nên ligature không bao giờ chạy.
        """
        lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", ""]
        lines.append("feature liga {")
        lines += [f"    sub {' '.join(r.source)} by {r.target};" for r in self.rules]
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
    #: Glyph -> (advance nguồn, advance đã đặt).
    advances: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.missing


def snap(contours: list[Contour], pitch: int) -> tuple[list[Contour], int]:
    """Kéo mọi điểm về bội số của ``pitch``.

    Trả về ``(contour đã snap, số điểm phải dịch)``.
    """
    moved = 0
    out: list[Contour] = []
    for points in contours:
        snapped: Contour = []
        for x, y in points:
            sx, sy = round(x / pitch) * pitch, round(y / pitch) * pitch
            if (sx, sy) != (x, y):
                moved += 1
            snapped.append((float(sx), float(sy)))
        out.append(snapped)
    return out, moved


def add_ligatures(
    font, pack: LigaturePack, base_dir: str | Path, grid
) -> LigatureReport:
    """Ghép ligature của ``pack`` vào ``font``, rồi gắn feature ``liga``.

    ``base_dir`` là thư mục chứa ``pack.source``. ``grid`` quyết định pitch và số ô.
    """
    report = LigatureReport()
    source = fontforge.open(str(Path(base_dir) / pack.source))
    advance = grid.pitch * grid.cols

    for rule in pack.rules:
        if rule.target not in source:
            report.missing.append(rule.target)
            continue
        snapped, moved = snap(read_contours(source[rule.target]), grid.pitch)
        if rule.target not in font:
            font.createChar(-1, rule.target)
        target = font[rule.target]
        before = int(target.width)
        set_contours(target, snapped, width=advance * rule.cells)
        report.added.append(rule.target)
        if moved:
            report.snapped[rule.target] = moved
        if before != advance * rule.cells:
            report.advances[rule.target] = (before, advance * rule.cells)

    source.close()

    with tempfile.NamedTemporaryFile(
        "w", suffix=".fea", encoding="utf-8", delete=False
    ) as handle:
        handle.write(pack.fea())
        fea_path = handle.name
    try:
        font.mergeFeature(fea_path)
    finally:
        Path(fea_path).unlink(missing_ok=True)

    return report
