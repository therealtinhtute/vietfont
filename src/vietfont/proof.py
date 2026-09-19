"""Proof sheet: render font đã Việt hoá thành trang HTML để người duyệt xem.

Đây là bước verify thật sự của dự án — Jev không đọc nổi glyph (xem
``docs/research/jev-verification-limits.md``), nên mắt người là chốt cuối.

Font được nhúng thẳng vào HTML dạng data URI nên trang tự chứa, mở ở đâu cũng được.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path

from vietfont import charset as cs

#: Câu mẫu để xem font trong ngữ cảnh thật.
SAMPLE_LINES = [
    "Tôi yêu tiếng nước tôi từ khi mới ra đời",
    "Đường phố Hà Nội đông nghẹt người và xe cộ",
    "Ăn quả nhớ kẻ trồng cây, uống nước nhớ nguồn",
    "Thử thách lớn nhất: ắ ẵ ặ ể ễ ệ ổ ỗ ộ ợ ự ỹ",
    "0123456789 — điều ước, đổi mới, tương lai",
]

#: Nhóm ký tự hiển thị thành lưới, theo trật tự dễ soi lỗi.
GRID_ROWS = [
    "a á à ả ã ạ   ă ắ ằ ẳ ẵ ặ   â ấ ầ ẩ ẫ ậ",
    "e é è ẻ ẽ ẹ   ê ế ề ể ễ ệ   i í ì ỉ ĩ ị",
    "o ó ò ỏ õ ọ   ô ố ồ ổ ỗ ộ   ơ ớ ờ ở ỡ ợ",
    "u ú ù ủ ũ ụ   ư ứ ừ ử ữ ự   y ý ỳ ỷ ỹ ỵ   đ",
    "A Á À Ả Ã Ạ   Ă Ắ Ằ Ẳ Ẵ Ặ   Â Ấ Ầ Ẩ Ẫ Ậ",
    "E É È Ẻ Ẽ Ẹ   Ê Ế Ề Ể Ễ Ệ   I Í Ì Ỉ Ĩ Ị",
    "O Ó Ò Ỏ Õ Ọ   Ô Ố Ồ Ổ Ỗ Ộ   Ơ Ớ Ờ Ở Ỡ Ợ",
    "U Ú Ù Ủ Ũ Ụ   Ư Ứ Ừ Ử Ữ Ự   Y Ý Ỳ Ỷ Ỹ Ỵ   Đ",
]

#: Các kiểu trình bày.
LAYOUTS = ("stack", "columns", "focus")


@dataclass
class ProofFont:
    """Một font đưa vào proof sheet."""

    label: str
    path: str | Path
    note: str = ""


@dataclass
class ProofSheet:
    title: str
    fonts: list[ProofFont]
    flagged: list[str] = field(default_factory=list)
    layout: str = "stack"

    def __post_init__(self) -> None:
        if self.layout not in LAYOUTS:
            raise ValueError(f"layout không hợp lệ: {self.layout!r} (chọn {LAYOUTS})")

    def html(self) -> str:
        return _TEMPLATE.format(
            title=self.title,
            layout=self.layout,
            faces="\n".join(_font_face(font, i) for i, font in enumerate(self.fonts)),
            body=_BODIES[self.layout](self),
            flagged=_flagged_section(self.flagged),
            coverage=len(cs.charset()),
        )

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.html(), encoding="utf-8")
        return target


def _font_face(font: ProofFont, index: int) -> str:
    data = base64.b64encode(Path(font.path).read_bytes()).decode("ascii")
    return (
        f"@font-face {{ font-family: 'proof{index}'; "
        f"src: url(data:font/otf;base64,{data}) format('opentype'); }}"
    )


def _grid(font_index: int, cls: str = "grid") -> str:
    rows = "\n".join(f"<div class='grid-row'>{row}</div>" for row in GRID_ROWS)
    return f"<div class='{cls}' style=\"font-family:'proof{font_index}'\">{rows}</div>"


def _samples(font_index: int, cls: str = "sample") -> str:
    return "\n".join(
        f"<p class='{cls}' style=\"font-family:'proof{font_index}'\">{line}</p>"
        for line in SAMPLE_LINES
    )


def _body_stack(sheet: ProofSheet) -> str:
    grid = "\n".join(
        f"<div class='block'><h3>{font.label}</h3>{_grid(i)}</div>"
        for i, font in enumerate(sheet.fonts)
    )
    samples = "\n".join(
        f"<div class='block'><h3>{font.label}</h3>{_samples(i)}</div>"
        for i, font in enumerate(sheet.fonts)
    )
    return f"<h2>Bảng ký tự</h2>{grid}<h2>Câu mẫu</h2>{samples}"


def _body_columns(sheet: ProofSheet) -> str:
    header = "".join(f"<th>{font.label}</th>" for font in sheet.fonts)
    grid_rows = "".join(
        "<tr><th class='rowlabel'>{}</th>{}</tr>".format(
            index + 1,
            "".join(f"<td>{_grid(i, 'grid grid--tight')}</td>" for i in range(len(sheet.fonts))),
        )
        for index in range(1)
    )
    return (
        f"<h2>So sánh trực tiếp</h2>"
        f"<table class='compare'><thead><tr><th></th>{header}</tr></thead>"
        f"<tbody>{grid_rows}</tbody></table>"
        f"<h2>Câu mẫu</h2>"
        f"<table class='compare'><tbody><tr>{''.join(f'<td>{_samples(i)}</td>' for i in range(len(sheet.fonts)))}</tr></tbody></table>"
    )


def _body_focus(sheet: ProofSheet) -> str:
    font = sheet.fonts[0]
    return (
        f"<h2>{font.label} — soi chi tiết</h2>"
        f"<div class='block'>{_grid(0, 'grid grid--huge')}</div>"
        f"<h2>Câu mẫu cỡ đọc</h2>"
        f"<div class='block'>{_samples(0, 'sample sample--big')}</div>"
    )


_BODIES = {"stack": _body_stack, "columns": _body_columns, "focus": _body_focus}


def _flagged_section(flagged: list[str]) -> str:
    if not flagged:
        return "<p class='ok'>Không có glyph nào bị đánh dấu.</p>"
    chips = "".join(f"<span class='chip'>{char}</span>" for char in flagged)
    return (
        f"<p class='warn'>{len(flagged)} glyph có dấu đè lên chữ nền — "
        f"nhóm HOA 2-mark không đủ chỗ trong lưới 7×14:</p><div class='chips'>{chips}</div>"
    )


_TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{faces}
:root {{ --bg: #0b0b0d; --fg: #e8e8ea; --dim: #7a7a82; --line: #232329; --warn: #ffb454; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 40px 48px 72px; background: var(--bg); color: var(--fg);
        font: 14px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; }}
h1 {{ font-size: 20px; font-weight: 600; margin: 0 0 4px; letter-spacing: -0.01em; }}
h2 {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em;
      color: var(--dim); margin: 44px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }}
h3 {{ font-size: 12px; font-weight: 500; color: var(--dim); margin: 0 0 10px; }}
.sub {{ color: var(--dim); margin: 0 0 8px; }}
.block {{ margin-bottom: 28px; }}
.grid {{ font-size: 26px; line-height: 1.5; letter-spacing: 0.02em; }}
.grid--tight {{ font-size: 17px; line-height: 1.45; }}
.grid--huge {{ font-size: 40px; line-height: 1.6; }}
.grid-row {{ white-space: pre; }}
.sample {{ font-size: 22px; margin: 0 0 6px; }}
.sample--big {{ font-size: 30px; margin: 0 0 10px; }}
table.compare {{ border-collapse: collapse; width: 100%; }}
table.compare th {{ text-align: left; font-size: 12px; font-weight: 500; color: var(--dim);
                    padding: 0 20px 10px 0; vertical-align: bottom; }}
table.compare td {{ vertical-align: top; padding: 0 20px 0 0; }}
.rowlabel {{ color: var(--dim); font-weight: 400; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }}
.chip {{ border: 1px solid var(--line); border-radius: 4px; padding: 2px 8px; font-size: 18px; }}
.warn {{ color: var(--warn); margin: 0; }}
.ok {{ color: var(--dim); margin: 0; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="sub">Proof sheet · layout <b>{layout}</b> · {coverage} ký tự tiếng Việt. Duyệt bằng mắt — Jev không đọc nổi glyph.</p>
{body}
<h2>Glyph cần xem</h2>
{flagged}
</body>
</html>
"""
