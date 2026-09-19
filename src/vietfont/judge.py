"""Jev judge: hỏi TypeSafe về tone mark của glyph.

**Đọc trước khi dùng.** Jev KHÔNG đọc được glyph pixel đủ tin cậy để làm cổng verify.
Accuracy tốt nhất đo được là **80%** (crop sát vùng mark, ổn định qua 3 lần chạy);
mọi cách hỏi khác đều tệ hơn, có cách gần mức đoán mò. Số liệu đầy đủ:
``docs/research/jev-verification-limits.md``.

Vì vậy module này chỉ để **xếp hạng** glyph cho người xem trước — không dùng để chặn.
Cổng verify là kiểm tra tất định: coverage, giữ contour, phát hiện va chạm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typesafe_sdk import Choice, TypeSafeClient

from vietfont import charset as cs
from vietfont.compose import compose
from vietfont.glyph import Contour, bounds, contours as read_contours
from vietfont.grid import Grid
from vietfont.marks import MarkPack
from vietfont.render import rasterize

#: Thanh điệu -> combining mark trong font.
TONE_MARKS: dict[str, int] = {
    "acute": 0x0301,
    "grave": 0x0300,
    "tilde": 0x0303,
    "dot_below": 0x0323,
}

DEFAULT_MODEL = "jev-latest"
DEFAULT_BATCH = 40

#: Ngưỡng confidence để coi một phán đoán là đáng tin.
ADVISORY_THRESHOLD = 0.6


@dataclass(frozen=True)
class Vocabulary:
    """Lưới text của từng tone mark, render ở vị trí tự nhiên của nó."""

    tones: dict[str, str]

    @classmethod
    def from_font(cls, font, grid: Grid, pack: MarkPack) -> "Vocabulary":
        def render(contours: list[Contour]) -> str:
            return "\n".join(rasterize(contours, grid))

        tones = {"none": render([])}
        for name, codepoint in TONE_MARKS.items():
            if codepoint in font:
                tones[name] = render(read_contours(font[codepoint]))
        hook = pack.mark("hook_above")
        if hook is not None:
            tones["hook_above"] = render(hook)
        return cls(tones=tones)


@dataclass
class MarkJudgment:
    """Jev đọc tone mark từ vùng mark đã crop."""

    char: str
    expected: str
    tone: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)

    @property
    def agrees(self) -> bool:
        return self.tone == self.expected

    @property
    def trustworthy(self) -> bool:
        return self.confidence >= ADVISORY_THRESHOLD


def verify_marks(
    font,
    grid: Grid,
    pack: MarkPack,
    chars: list[str] | None = None,
    *,
    model: str = DEFAULT_MODEL,
    batch: int = DEFAULT_BATCH,
    client: TypeSafeClient | None = None,
) -> list[MarkJudgment]:
    """Hỏi Jev về tone mark của từng ký tự có thanh điệu trong ``chars``."""
    chars = [c for c in (chars if chars is not None else cs.charset()) if cs.decompose(c)[2] != "none"]
    vocabulary = Vocabulary.from_font(font, grid, pack)
    owns_client = client is None
    client = client or TypeSafeClient()

    results: list[MarkJudgment] = []
    try:
        for start in range(0, len(chars), batch):
            results.extend(
                _verify_batch(client, font, grid, pack, vocabulary, chars[start : start + batch], model)
            )
    finally:
        if owns_client:
            client.close()
    return results


def mark_crop(font, grid: Grid, pack: MarkPack, char: str) -> str:
    """Cắt glyph xuống đúng các hàng mà tone mark chiếm.

    Đây là biểu diễn cho kết quả tốt nhất (80%) — đưa cả glyph vào làm nhiễu
    phán đoán, còn cắt sát quá thì mark mất thông tin shape.
    """
    composition = compose(font, char, pack, grid)
    box = bounds(composition.mark_contours)
    if box is None:
        return ""
    rows = [
        row
        for row in range(grid.rows)
        if box[1] < grid.cell_rect(row, 0)[3] and box[3] > grid.cell_rect(row, 0)[1]
    ]
    lines = rasterize(read_contours(font[ord(char)]), grid)
    return "\n".join(lines[row] for row in rows)


def _verify_batch(client, font, grid, pack, vocabulary, chars, model) -> list[MarkJudgment]:
    state = {
        "font": f"pixel font, {grid.cols} wide x {grid.rows} tall grid, '#' = ink, '.' = empty",
        "tones": vocabulary.tones,
        "glyphs": [
            {"id": f"g{i}", "crop": mark_crop(font, grid, pack, char)} for i, char in enumerate(chars)
        ],
    }
    questions = {
        f"tone_{i}": Choice(
            instructions=(
                f"`glyphs[{i}].crop` is the mark region cropped from a Vietnamese letter. "
                "Which tone mark from `tones` is it?"
            ),
            criteria={name: None for name in vocabulary.tones},
        )
        for i in range(len(chars))
    }

    response = client.system_one(state=state, questions=questions, model=model)

    return [
        MarkJudgment(
            char=char,
            expected=cs.decompose(char)[2],
            tone=response.choices[f"tone_{i}"].choice,
            confidence=response.choices[f"tone_{i}"].confidence,
            probabilities=dict(response.choices[f"tone_{i}"].probabilities),
        )
        for i, char in enumerate(chars)
    ]
