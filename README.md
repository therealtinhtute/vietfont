# vietfont

Việt hoá font pixel/bitmap: code dựng glyph, [Jev](https://docs.typesafe.ai) phán, người duyệt ca khó.

## Ý tưởng

Font pixel render ra text được (lưới `#`/`.`). Jev là model text-only — nên lưới pixel
chính là interface tự nhiên giữa font và model. Code trích shape mark từ chính font,
Jev match glyph với vocabulary đó.

Đo thật: hỏi thẳng "đây là chữ nào?" → **1/6**. Cho vocabulary của font → **10/10**.
Tách 3 câu độc lập (letter / modifier / tone) trên 24 glyph khó → **24/24 · 21/24 · 23/24**,
miss có confidence 0.16–0.38 (route cho người duyệt được). Chi tiết: `docs/research/`.

## Pipeline

```
analyze → extract → plan → compose → render → JEV judge → apply → build → proof
```

- **Code** sở hữu toàn bộ control flow: coverage diff, trích mark, dựng candidate, ghi font.
- **Jev** chỉ làm phán đoán thị giác: chọn candidate, verify từng glyph, phát hiện va chạm.
- **Người** duyệt ca confidence thấp qua proof sheet.

## Trạng thái

Plan đã lock: [`docs/plans/active/vietfont-v1.md`](docs/plans/active/vietfont-v1.md).
Phase 0, 1 xong. Phase 2 xong với **kết quả âm tính**. Phase 3 cần thiết kế lại.

**Phase 1** đạt **134/134 ký tự** và **134/134 glyph giữ nguyên shape chữ nền** — bản dựng tay
chỉ đạt 70/134 vì pipeline cũ flatten base letter (xem `docs/research/ground-truth-flattening.md`).

**Phase 2** đo được: Jev đọc glyph pixel chỉ đạt **62%** trên toàn bộ glyph có thanh điệu
(80% trên mẫu lowercase nhỏ). Không đủ để làm cổng verify. Đã thử 10 cách hỏi khác nhau —
số liệu đầy đủ ở `docs/research/jev-verification-limits.md`.

→ Cổng verify là **kiểm tra tất định** (coverage, giữ contour, phát hiện va chạm).
Jev chỉ còn là tín hiệu tham khảo. Người duyệt qua proof sheet là chốt cuối.

Bối cảnh: [departure-mono#21](https://github.com/rektdeckard/departure-mono/issues/21) —
feature request Việt hoá còn mở; bản dựng tay trong repo này đã chứng minh grid 7×14 đủ chỗ.

## Cấu trúc

```
docs/plans/active/          plan đã lock
docs/research/              nhật ký thí nghiệm Jev + bối cảnh upstream
fonts/departure-mono-viet/  font project (font-src, legacy scripts, build)
src/vietfont/               tool
```

## Chạy

```bash
uv venv --python /opt/homebrew/bin/python3 --system-site-packages .venv
VIRTUAL_ENV=.venv uv pip install -e .
.venv/bin/vietfont --version
```

Bốn lệnh:

```bash
vietfont analyze <font>                          # đo độ phủ tiếng Việt
vietfont add <font> -o <out> --marks <pack> --family "Departure Mono Viet"
vietfont verify <out> --source <font> --marks <pack>   # kiểm: coverage, shape, mực
vietfont proof <out> -o proof.html --layout columns    # proof sheet để duyệt bằng mắt
```

`verify` là cổng: exit code khác 0 khi font thiếu ký tự, bị flatten chữ nền, lệch mực,
hoặc có dấu đè chữ nền.

`--family` đổi tên family của font xuất. **Cần dùng khi cài song song font gốc** — hai font
cùng tên family thì hệ điều hành chỉ giữ một. Lệnh ghi lại cả nameID 16 (typographic family),
không chỉ nameID 1.

Font gốc là **SIL OFL 1.1**: bản phái sinh giữ nguyên thông báo bản quyền và giấy phép,
chỉ thêm một dòng ghi chú phái sinh.

`fontforge` là module hệ thống (không cài qua pip) — venv phải tạo bằng
`--system-site-packages` từ python homebrew.

## Stack

Python 3.14 (homebrew) · venv `--system-site-packages` · `fontforge` · `fontTools` · `typesafe-sdk`
