"""Dựng trang so sánh các bản Việt hoá.

Tự dựng đủ bốn bản từ font gốc rồi nhúng thẳng vào HTML dưới dạng data URI — trang
mở được ở đâu cũng chạy, không cần cài font. Cách cài font rồi trông vào hệ điều
hành đã thử và không đáng tin: macOS bỏ qua font đổi tên, còn fontconfig thì thấy.

    python scripts/make-demo.py
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from vietfont import charset as cs
from vietfont.build import rename

SOURCE = ROOT / "fonts/departure-mono-viet/font-src/DepartureMono-Regular.otf"
PACK = ROOT / "fonts/departure-mono-viet/marks.json"
BUILT = ROOT / "fonts/departure-mono-viet/build/DepartureMonoViet-Regular.otf"
OUT = ROOT / "fonts/departure-mono-viet/demo.html"

#: Bản đầu tiên sau khi sửa lỗi trùng hình — móc còn 2 hàng.
OLD_PACK_REV = "HEAD~5"

SAMPLE = "Tôi yêu tiếng nước tôi từ khi mới ra đời"


def build_variants(tmp: Path) -> list[tuple[str, Path, str, str]]:
    """Dựng bốn bản font để đem so."""
    cli = ROOT / ".venv/bin/vietfont"

    def run(*args: str) -> None:
        subprocess.run([str(cli), *args], check=True, capture_output=True)

    old_pack = tmp / "pack-old.json"
    old_pack.write_text(
        subprocess.run(
            ["git", "show", f"{OLD_PACK_REV}:fonts/departure-mono-viet/marks.json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    variants = [
        (
            "v0",
            tmp / "v0.otf",
            "Bản gốc",
            "Chưa Việt hoá — 58/134 ký tự, phần thiếu rơi về font dự phòng",
        ),
        (
            "v1",
            tmp / "v1.otf",
            "Móc 2 hàng",
            "Đã đủ 134 ký tự, nhưng dấu hỏi còn là tick trên thanh ngang",
        ),
        (
            "v2",
            tmp / "v2.otf",
            "Móc 4 hàng",
            "Dấu hỏi đủ dáng móc; chữ hoa chỉ 2 hàng vì hết chỗ",
        ),
        (
            "v3",
            BUILT,
            "Bản cuối",
            "Mọi dấu hỏi từ 3 hàng trở lên — đổi lại dòng giãn 14%",
        ),
    ]

    run("add", str(SOURCE), "-o", str(tmp / "v1.otf"), "--marks", str(old_pack))
    run("add", str(SOURCE), "-o", str(tmp / "v2.otf"), "--marks", str(PACK))

    # Bản gốc chưa Việt hoá: đổi tên để không lẫn với font đang cài.
    shutil.copy(SOURCE, tmp / "v0.otf")
    rename(str(tmp / "v0.otf"), "Departure Mono Goc")

    return variants


def faces(variants) -> str:
    out = []
    for key, path, _, _ in variants:
        b64 = base64.b64encode(path.read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'{key}';"
            f"src:url(data:font/otf;base64,{b64}) format('opentype')}}"
        )
    return "\n".join(out)


def rows(variants, css: str, content: str) -> str:
    return "\n".join(
        f"""<div class="row {key}">
  <div class="lab"><b>{label}</b><span>{note}</span></div>
  <div class="demo" style="font-family:'{key}';{css}">{content}</div>
</div>"""
        for key, _, label, note in variants
    )


def section(title: str, note: str, body: str) -> str:
    return f'<section><h2>{title}</h2><p class="note">{note}</p>{body}</section>'


def main() -> int:
    hook = [c for c in cs.charset() if cs.decompose(c)[2] == "hook_above"]
    low = " ".join(c for c in hook if c.islower())
    up = " ".join(c for c in hook if c.isupper())
    everything = " ".join(cs.charset())

    with tempfile.TemporaryDirectory() as tmpdir:
        variants = build_variants(Path(tmpdir))
        font_faces = faces(variants)

    html = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Departure Mono Viet — so sánh</title><style>
{font_faces}
*{{box-sizing:border-box}}
body{{margin:0;padding:34px 40px 60px;background:#0b0b0d;color:#e8e8ea;
     font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}
h1{{font-size:20px;font-weight:600;margin:0 0 4px}}
.lede{{color:#7a7a82;margin:0 0 30px;max-width:74ch}}
section{{margin-bottom:38px}}
h2{{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#7a7a82;
    margin:0 0 4px;padding-bottom:7px;border-bottom:1px solid #232329}}
.note{{color:#5f5f68;font-size:12px;margin:8px 0 16px;max-width:74ch}}
.row{{display:flex;gap:22px;align-items:flex-start;padding:14px 0;border-bottom:1px solid #17171c}}
.row:last-child{{border-bottom:0}}
.lab{{flex:0 0 168px;padding-top:4px}}
.lab b{{display:block;font-size:12px;color:#c8c8d0}}
.lab span{{display:block;font-size:11px;color:#5f5f68;line-height:1.45;margin-top:3px}}
.demo{{flex:1;min-width:0;overflow:hidden}}
.v0 .demo{{color:#6a6a72}}
.v1 .demo{{color:#e0c07e}}
.v2 .demo{{color:#9ec9e0}}
.v3 .demo{{color:#7ee08a}}
</style></head><body>
<h1>Departure Mono Viet — so sánh</h1>
<p class="lede">Bốn bản font nhúng thẳng vào trang, render cùng một nội dung. Không cần
cài gì — mở file là xem được.</p>
{section("Độ phủ tiếng Việt", "Bản gốc thiếu 76 ký tự nên phần có dấu rơi về font dự phòng — cả dòng đổi typeface.", rows(variants, "font-size:30px", SAMPLE))}
{section("Dấu hỏi — 24 ký tự", "Hàng trên chữ thường, hàng dưới chữ hoa.", rows(variants, "font-size:74px", f"{low}<br>{up}"))}
{section("Chiều cao dòng", "Cùng cỡ chữ, line-height mặc định của font. Bản cuối giãn 14% để chữ hoa có chỗ cho dấu.", rows(variants, "font-size:26px;line-height:normal", "dòng một<br>dòng hai<br>dòng ba"))}
{section("Toàn bộ 134 ký tự", "Bộ ký tự tiếng Việt đầy đủ.", rows(variants, "font-size:22px;line-height:1.5", everything))}
</body></html>"""

    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}  {len(html) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
