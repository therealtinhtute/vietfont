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
bằng pipeline có Jev verify — xem `docs/plans/active/vietfont-v1.md`.
