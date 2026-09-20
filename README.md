# vietfont

Việt hoá font pixel/bitmap: code dựng glyph, [Jev](https://docs.typesafe.ai) phán, người duyệt ca khó.

Kết quả cụ thể trong repo: **Departure Mono Viet** — bản Việt hoá của
[Departure Mono](https://departuremono.com), đủ **134/134 ký tự Việt**, giữ nguyên contour
của **134/134** chữ nền.

## Font gốc

| | |
|---|---|
| Font | **Departure Mono** — [departuremono.com](https://departuremono.com) |
| Mã nguồn | [github.com/rektdeckard/departure-mono](https://github.com/rektdeckard/departure-mono) |
| Tác giả | Helena Zhang |
| Giấy phép **font** | **SIL OFL 1.1** — [LICENSE gốc](https://github.com/rektdeckard/departure-mono/blob/main/public/assets/LICENSE) |
| Giấy phép **site upstream** | MIT — [LICENSE gốc](https://github.com/rektdeckard/departure-mono/blob/main/LICENSE) |
| Issue | [departure-mono#21 — Support Vietnamese characters](https://github.com/rektdeckard/departure-mono/issues/21) |

> ⚠️ **Font là OFL 1.1, không phải MIT.** Repo upstream đặt MIT ở `LICENSE` gốc — đó là giấy
> phép của *website*, không phải của font. Font nằm ở `public/assets/LICENSE` và là
> **SIL OFL 1.1**. Bản phái sinh trong repo này vì vậy cũng là OFL 1.1 — xem
> [Giấy phép](#giấy-phép).

Bối cảnh: issue mở từ 2025-05, tác giả font chưa làm vì lo *"the grid is big enough to
accommodate stacking diacritics"*. Repo này trả lời: **đủ**. Issue kèm danh sách ký tự chuẩn
(khớp bộ 134 ở đây, chỉ khác 12 chữ ASCII font gốc đã có và một typo `ũ`→`Ũ`) và ảnh tham
chiếu [Fixedsys Excelsior](https://github.com/kika/fixedsys), khoanh đỏ đúng chỗ font pixel
hay hỏng: `hook_above`/`tilde` xếp trên `ă â ê ô` (`ẳ Ẳ ỗ Ỗ ể Ể`). Chi tiết:
[`docs/research/upstream-issue-21.md`](docs/research/upstream-issue-21.md).

## Mental model

**Font pixel đã là text.** Mỗi glyph là một lưới `#`/`.` 7 cột × 14 hàng (bản Việt hoá dùng
15 hàng vì `--ascent 600`) — không cần rasterize thành ảnh để đưa cho model. Đây là điểm
mấu chốt của cả dự án: interface giữa font và model không phải hình ảnh, mà là **text**.

```
ả  →  .......     ← 3 hàng đầu: dấu hỏi (hook above)
      .......
      ..###..
      ....#..
      ...#...
      .......     ← 1 hàng trống: đáy dấu = x-height + 1 hàng
      ..###..     ← chữ nền `a`, contour gốc giữ nguyên
      .....#.
      ..####.
      .#...#.
      .#..##.
      ..##.#.
      .......
      .......
      .......
```

Bốn hệ quả, và chúng chi phối toàn bộ thiết kế:

1. **Jev là model text-only — và thế là đủ để bắt đầu.** Lưới pixel là interface tự nhiên,
   không cần vision model. Nhưng "đủ để bắt đầu" không phải "đủ để làm cổng" — xem dưới.
2. **Model không *sinh* glyph, nó *chọn*.** Code trích shape mark từ chính font đang xử lý,
   render chúng thành lưới, rồi đưa vào `state` làm vocabulary. Jev match glyph với
   vocabulary đó. Pattern là *select instead of generate* — và nó là thứ đưa accuracy từ
   **1/6** lên **10/10** ở thí nghiệm đầu.
3. **Tách câu hỏi theo chiều độc lập.** Hỏi gộp "đây là chữ gì" thì model phải giải đồng
   thời base + modifier + tone. Tách thành 3 câu độc lập (letter / modifier / tone) làm
   accuracy nhảy vọt: base **15/24 → 24/24**.
4. **Phân chia trách nhiệm theo thứ mỗi bên làm tốt.** Code sở hữu control flow và mọi phép
   kiểm tất định (coverage, giữ contour, va chạm). Jev chỉ phán thị giác. Người duyệt là chốt cuối.

Bài học lớn nhất, và là thứ đổi hướng dự án: **Jev không đọc được glyph pixel đủ tin cậy để
làm cổng verify** (đo được 62% trên toàn bộ glyph có thanh điệu). Cổng verify vì vậy là
**kiểm tra tất định**, không phải model. Jev tụt xuống vai trò tín hiệu tham khảo.

## Jev dùng để làm gì

| | |
|---|---|
| **Dùng để** | đọc tone mark từ vùng crop của glyph; **xếp hạng** glyph cho người xem trước |
| **KHÔNG dùng để** | chặn (làm cổng verify); chọn candidate |
| Model | `jev-latest` (`jev-1.13.0`) |
| Ngưỡng tin cậy | `ADVISORY_THRESHOLD = 0.6` |
| Lệnh | `vietfont judge <font> --marks <pack>` |

**Số đo thật** (60–78 glyph, rasterizer thật, lưới 7×14):

| cách hỏi | accuracy |
|---|---|
| 3 câu tuyệt đối: letter / modifier / tone | 18% |
| chỉ tone, có `none` | 41–58% |
| chỉ tone, **bỏ `none`** | 77–80% |
| **crop sát vùng mark + vocabulary đầy đủ** | **80%** (ổn định 3/3 lần chạy) |
| *trên toàn bộ 120 glyph có thanh điệu* | ***62%*** |

Cấu hình tốt nhất — crop glyph xuống đúng các hàng mà tone mark chiếm, vocabulary là mark
render ở vị trí tự nhiên của nó:

```python
crop = các hàng của glyph phủ bbox của mark
state = {"tones": {tên: lưới_đầy_đủ}, "glyphs": [{"crop": crop}]}
# Choice trên 5 mark + none
```

**Bốn cái bẫy đã đo được:**

- **`none` là cái bẫy.** Thêm lựa chọn "không có mark" làm accuracy rơi **80% → 43%**.
  Jev mặc định về `none`.
- **Phóng to làm tệ đi.** 2× và 3× đều tệ hơn 1× — model làm việc tốt với lưới 7 ký tự
  rộng hơn là với khối to.
- **Noul không dùng được.** Xác suất các mark đều nằm 0.2–0.5, không tách được mark nào có mặt.
- **`dot_below` hỏng có hệ thống.** Crop của nó là 1 pixel đơn — 12/12 miss ở cấu hình tốt nhất.

Số liệu đầy đủ 10 cách hỏi đã thử:
[`docs/research/jev-verification-limits.md`](docs/research/jev-verification-limits.md).

## Pipeline

```
analyze → extract → plan → compose → build → verify → proof
                                              │         │
                                              │         └─ người duyệt (chốt cuối)
                                              └─ cổng tất định (chặn được)

judge — nhánh phụ tùy chọn: xếp hạng glyph, không chặn
```

- **Code** sở hữu toàn bộ control flow: coverage diff, trích mark, dựng candidate, ghi font,
  và **mọi phép kiểm** — coverage, giữ contour, mực, va chạm.
- **`judge`** là nhánh phụ tùy chọn, **không nằm trên đường đi của bản dựng**: Jev đọc tone
  mark để xếp hạng glyph cho người xem trước. Không chặn, không chọn candidate — xem mục
  [Jev dùng để làm gì](#jev-dùng-để-làm-gì).
- **Người** duyệt proof sheet. Đây là bước verify thật sự, không phải "duyệt ca khó".

## Cấu trúc

```
docs/plans/active/          plan đã lock
docs/research/              nhật ký thí nghiệm Jev + bối cảnh upstream
fonts/departure-mono-viet/  font project
  font-src/                 font gốc (Departure Mono, OFL 1.1)
  marks.json                mark pack: shape của mark/modifier mà font gốc thiếu
  build/                    font xuất — xem "Bản dựng" bên dưới
  legacy/                   pipeline dựng tay (bản tham chiếu, không phải code của tool)
  demo.html                 trang so sánh 4 bản, font nhúng dạng data URI
src/vietfont/               tool
scripts/make-demo.py        dựng demo.html
```

| module | trách nhiệm |
|---|---|
| `analyze.py` | cmap diff vs bộ ký tự Việt; inventory base/modifier/tone; detect grid |
| `grid.py` | lưới pixel: pitch, số hàng/cột, x-height, cap-height, ascent |
| `charset.py` | bộ 134 ký tự Việt mục tiêu |
| `marks.py` | mark pack: shape mark/modifier font thiếu, bản đầy đủ + bản thu gọn |
| `compose.py` | dựng candidate từ base + modifier + tone; snap grid; chọn bản vừa lưới |
| `render.py` | glyph → lưới text `#`/`.` |
| `judge.py` | TypeSafe client; build câu hỏi; batch; ngưỡng confidence |
| `ligatures.py` | Ligature lập trình: copy glyph nguồn, snap lưới, sửa advance, gắn `liga` |
| `build.py` | ghi glyph, đổi tên family, nâng ascent, generate font |
| `verify.py` | cổng tất định: coverage, giữ contour, mực, va chạm |
| `proof.py` | proof sheet HTML + review queue |
| `cli.py` | `vietfont <analyze\|add\|judge\|proof\|verify>` |

### Bản dựng

| file | dùng được? |
|---|---|
| `build/DepartureMonoViet-Regular.otf` | ✅ **bản chính** — tool dựng, 134/134 |
| `build/DepartureMono-Viet.otf` | ⚠️ bản dựng tay — **hỏng shape**, xem dưới |
| `build/DepartureMonoLigaZ-Regular.{otf,ttf}` | bản có ligature |

> ⚠️ `build/DepartureMono-Viet.otf` **không dùng được làm chuẩn đúng**: cả 76 glyph do
> pipeline tay tạo ra đã bị **flatten base letter** — `rects_of()` lấy bounding box của
> contour rồi vẽ lại thành hình chữ nhật, phá shape của mọi chữ có contour không phải hình
> chữ nhật. `ả` trong bản này là một khối đặc, không phải chữ `a` có móc.
>
> | | giữ nguyên contour carrier |
> |---|---|
> | bản tay làm | 70/134 |
> | `vietfont` | **134/134** |
>
> Chi tiết: [`docs/research/ground-truth-flattening.md`](docs/research/ground-truth-flattening.md).

## Trạng thái

Plan đã lock: [`docs/plans/active/vietfont-v1.md`](docs/plans/active/vietfont-v1.md).
Phase 0, 1 xong. Phase 2 xong với **kết quả âm tính**. Phase 3 cần thiết kế lại.

**Phase 1** đạt **134/134 ký tự** và **134/134 glyph giữ nguyên shape chữ nền** — bản dựng tay
chỉ đạt 70/134 vì pipeline cũ flatten base letter.

**Phase 2** đo được: Jev đọc glyph pixel chỉ đạt **62%** trên toàn bộ glyph có thanh điệu
(80% trên mẫu lowercase nhỏ). Không đủ để làm cổng verify. Đã thử 10 cách hỏi khác nhau.

→ Cổng verify là **kiểm tra tất định** (coverage, giữ contour, phát hiện va chạm).
Jev chỉ còn là tín hiệu tham khảo. Người duyệt qua proof sheet là chốt cuối.

## Chạy

```bash
uv venv --python /opt/homebrew/bin/python3 --system-site-packages .venv
VIRTUAL_ENV=.venv uv pip install -e .
.venv/bin/vietfont --version
```

Năm lệnh:

```bash
vietfont analyze <font>                          # đo độ phủ tiếng Việt
vietfont add <font> -o <out> --marks <pack> --family "Departure Mono Viet"
vietfont judge <out> --marks <pack>              # Jev đọc tone mark — tín hiệu tham khảo
vietfont verify <out> --source <font> --marks <pack>   # kiểm: coverage, shape, mực
vietfont proof <out> -o proof.html --layout columns    # proof sheet để duyệt bằng mắt
```

`verify` là cổng: exit code khác 0 khi font thiếu ký tự, bị flatten chữ nền, lệch mực,
trùng hình, hoặc có dấu đè chữ nền.

`--family` đổi tên family của font xuất. **Cần dùng khi cài song song font gốc** — hai font
cùng tên family thì hệ điều hành chỉ giữ một. Lệnh ghi lại cả nameID 16 (typographic family),
không chỉ nameID 1.

`--ascent` nâng ascent để chừa thêm hàng lưới cho dấu. **Đổi chiều cao dòng của cả font** —
chỉ dùng khi dấu cần chỗ mà lưới đã hết. Bản Departure Mono Viet dùng `--ascent 600`
(gốc 550) để chữ hoa đủ chỗ cho dấu hỏi 3 hàng.

`--ligatures` ghép ligature lập trình từ một font nguồn: copy glyph, **snap về lưới**, đặt
advance theo số ô, rồi gắn feature `liga`. Bản phát hành **chưa bật** — glyph của bản cộng
đồng chưa đạt (24/26 lệch lưới, 25/26 sai nhịp, `>=` `<=` thiếu thành phần `=`). Xem
[`docs/research/ligature-audit.md`](docs/research/ligature-audit.md).

## Demo

```bash
python scripts/make-demo.py     # -> fonts/departure-mono-viet/demo.html
```

Trang so sánh bốn bản: font gốc chưa Việt hoá, bản móc 2 hàng, bản móc 4 hàng, và bản
cuối. Font nhúng thẳng dạng data URI nên mở file là xem được, không cần cài gì.

## Giấy phép

Repo này có **hai** giấy phép, theo đúng nguồn gốc của từng phần:

| phần | giấy phép | file |
|---|---|---|
| **Font Software** — font binaries + font design data: `fonts/*/font-src/`, `fonts/*/research/`, `fonts/*/build/`, `fonts/*/marks.json` | **SIL OFL 1.1** | [`LICENSE`](LICENSE) · [`fonts/departure-mono-viet/OFL.txt`](fonts/departure-mono-viet/OFL.txt) |
| **Phần còn lại** — tool (`src/`, `scripts/`, `legacy/`), tài liệu (`docs/`, README), demo page | MIT | [`LICENSE-MIT`](LICENSE-MIT) |

Ghi chú phái sinh — font gốc, phần đã sửa, phạm vi từng giấy phép: [`NOTICE`](NOTICE).

Font gốc là **SIL OFL 1.1** (© 2022–2024 Helena Zhang) — *không phải MIT*. Bản phái sinh giữ
nguyên thông báo bản quyền và giấy phép trong name table (nameID 0, 13, 14). OFL 1.1 không
đặt Reserved Font Name, nên tên "Departure Mono Viet" dùng được.

## Stack

Python 3.14 (homebrew) · venv `--system-site-packages` · `fontforge` · `fontTools` · `typesafe-sdk`

`fontforge` là module hệ thống (không cài qua pip) — venv phải tạo bằng
`--system-site-packages` từ python homebrew.
