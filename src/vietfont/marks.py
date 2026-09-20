"""Mark pack: shape của mark và modifier mà font không có sẵn.

Font thường đã có sẵn các combining mark (acute, grave, tilde, dot below) và các
glyph ``base+modifier`` (``ă â ê ô ư``). Phần thiếu — ví dụ dấu hỏi (hook above)
hoặc horn trên ``o`` — phải lấy từ pack.

Pack là dữ liệu, không phải code: shape do người thiết kế quyết định, tool chỉ áp
dụng nhất quán. Định dạng JSON, contour là danh sách các điểm ``[x, y]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from vietfont.glyph import Contour


@dataclass
class MarkPack:
    #: Tên thanh điệu -> contour của mark.
    marks: dict[str, list[Contour]] = field(default_factory=dict)
    #: Mark thu gọn, dùng khi lưới hết chỗ (chữ HOA).
    compact_marks: dict[str, list[Contour]] = field(default_factory=dict)
    #: Tên modifier -> ký tự base -> contour của modifier.
    modifiers: dict[str, dict[str, list[Contour]]] = field(default_factory=dict)
    #: Modifier thu gọn 1 hàng, dùng khi lưới hết chỗ (chữ HOA 2-mark).
    compact_modifiers: dict[str, list[Contour]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> MarkPack:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            marks={name: _to_contours(cs) for name, cs in raw.get("marks", {}).items()},
            compact_marks={
                name: _to_contours(cs)
                for name, cs in raw.get("compact_marks", {}).items()
            },
            modifiers={
                mod: {base: _to_contours(cs) for base, cs in bases.items()}
                for mod, bases in raw.get("modifiers", {}).items()
            },
            compact_modifiers={
                mod: _to_contours(cs)
                for mod, cs in raw.get("compact_modifiers", {}).items()
            },
        )

    def save(self, path: str | Path) -> None:
        payload = {
            "marks": {name: _from_contours(cs) for name, cs in self.marks.items()},
            "compact_marks": {
                name: _from_contours(cs) for name, cs in self.compact_marks.items()
            },
            "modifiers": {
                mod: {base: _from_contours(cs) for base, cs in bases.items()}
                for mod, bases in self.modifiers.items()
            },
            "compact_modifiers": {
                mod: _from_contours(cs) for mod, cs in self.compact_modifiers.items()
            },
        }
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def mark(self, tone: str) -> list[Contour] | None:
        return self.marks.get(tone)

    def compact_mark(self, tone: str) -> list[Contour] | None:
        return self.compact_marks.get(tone)

    def modifier(self, modifier: str, base: str) -> list[Contour] | None:
        return self.modifiers.get(modifier, {}).get(base)

    def compact_modifier(self, modifier: str) -> list[Contour] | None:
        return self.compact_modifiers.get(modifier)


def _to_contours(raw: list) -> list[Contour]:
    return [[(float(x), float(y)) for x, y in points] for points in raw]


def _from_contours(contours: list[Contour]) -> list:
    return [[[x, y] for x, y in points] for points in contours]
