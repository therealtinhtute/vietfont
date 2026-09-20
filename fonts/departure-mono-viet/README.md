# Departure Mono Việt

Bản Việt hoá của [Departure Mono](https://departuremono.com) — font pixel 7×14, 50 units/pixel.

## Nguồn

| file | vai trò |
|---|---|
| `font-src/DepartureMono-Regular.otf` | font gốc — 58/134 ký tự Việt |
| `research/DepartureMonoLigatures-Regular.otf` | bản có ligature, nguồn để copy glyph ligature |
| `build/DepartureMono-Viet.otf` | **ground truth** — bản Việt hoá dựng tay, 134/134 |
| `build/DepartureMono-Viet.sfd` | source FontForge của bản trên |

## Upstream

[departure-mono#21 — Feature Request: Support Vietnamese characters](https://github.com/rektdeckard/departure-mono/issues/21)
(mở 2025-05, còn mở). Tác giả font chưa làm vì lo *"the grid is big enough to accommodate
stacking diacritics"* — bản dựng tay trong repo này chứng minh grid 7×14 **đủ**.

Issue kèm danh sách ký tự chuẩn và ảnh tham chiếu Fixedsys Excelsior, khoanh đỏ đúng chỗ
font pixel hay hỏng: `hook_above`/`tilde` xếp trên `ă â ê ô` (`ẳ Ẳ ỗ Ỗ ể Ể`).
Chi tiết: `docs/research/upstream-issue-21.md`.

## Pipeline cũ (`legacy/`)

Chạy từ thư mục này, theo đúng thứ tự:

```bash
fontforge -script legacy/build_easy.py           # ohorn/Ohorn, hookabovecomb, composite hook-above, dotbelow y/Y
fontforge -script legacy/scaffold_hard.py        # scaffold 2-mark composites (đánh dấu TODO màu cam)
fontforge -script legacy/finish_hard.py          # thêm tone mark vào glyph đã scaffold
fontforge -script legacy/copy_ligature_glyphs.py # copy ligature glyph từ bản ligature
```

Xem trước glyph trong terminal (lưới 7×14, ký tự block):

```bash
fontforge -script legacy/preview.py a ă â ế ơ ư
```

`legacy/` là **bản tham chiếu**, không phải code của tool. `vietfont` tái tạo kết quả này
bằng pipeline tất định, cổng verify riêng — xem `docs/plans/active/vietfont-v1.md`.

## Dùng tool

```bash
vietfont analyze font-src/DepartureMono-Regular.otf
vietfont add font-src/DepartureMono-Regular.otf -o build/DepartureMono-Viet-tool.otf --marks marks.json
```

`marks.json` chứa shape của mark/modifier mà font gốc không có: dấu hỏi (`hook_above`)
và horn trên `o`/`O`. Giá trị trong đó lấy từ thiết kế tay trong `legacy/build_easy.py`.

## ⚠️ Bản dựng tay bị hỏng shape

`build/DepartureMono-Viet.otf` **không dùng được làm chuẩn đúng**: cả 76 glyph do pipeline
tay tạo ra đã bị **flatten base letter** — `rects_of()` lấy bounding box của contour rồi vẽ
lại thành hình chữ nhật, phá shape của mọi chữ có contour không phải hình chữ nhật.
`ả` trong bản này là một khối đặc, không phải chữ `a` có móc.

| | giữ nguyên contour carrier |
|---|---|
| bản tay làm | 70/134 |
| `vietfont` | **134/134** |

Chi tiết + cách kiểm: `docs/research/ground-truth-flattening.md`.
