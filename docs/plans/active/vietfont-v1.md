# vietfont v1 — Việt hoá font pixel bằng Jev

**Status**: locked · 2026-09-19 · kết quả brainstorm
**Slug**: `vietfont-v1`

## 1. Mục tiêu

CLI nhận một font pixel/bitmap → xuất font đã có đủ bộ ký tự Việt, do Jev verify,
ca không chắc chắn được đánh dấu cho người duyệt.

**Code sở hữu pipeline. Jev cung cấp phán đoán thị giác. Không có agent trong v1.**

**Bối cảnh upstream**: [departure-mono#21](https://github.com/rektdeckard/departure-mono/issues/21)
— feature request Việt hoá, còn mở từ 2025-05. Tác giả font lo *"the grid is big enough to
accommodate stacking diacritics"*; bản dựng tay 134/134 trong repo này đã trả lời là **đủ**.
Issue kèm danh sách ký tự chuẩn (khớp bộ 134 của ta, chỉ khác 12 chữ ASCII đã có sẵn và một
typo `ũ`→`Ũ`) và ảnh tham chiếu Fixedsys Excelsior. Chi tiết: `docs/research/upstream-issue-21.md`.

## 2. Bằng chứng thiết kế

Đo thật trên `DepartureMono-Viet.otf` (ground truth, 134/134 ký tự Việt), render glyph
thành lưới text 7×14 rồi hỏi Jev. Chi tiết + request shape: `docs/research/jev-glyph-experiments.md`.

| Cách hỏi | Kết quả |
|---|---|
| "Đây là chữ nào?" — 6 glyph, không vocabulary | **1/6**, conf 0.13–0.32 |
| Vocabulary = mark shapes của chính font — 5 glyph `a` | **10/10**, conf 0.97–1.00 |
| 24 glyph khó (`ơ ư ê ă` × 5 tone): base-variant + tone | tone **24/24**, base **15/24** |
| Tách 3 câu độc lập: letter / modifier / tone | letter **24/24**, modifier **21/24**, tone **23/24**, cả 3 **20/24** |

Ba kết luận chi phối thiết kế:

1. **Jev đọc được glyph pixel, nhưng chỉ khi `state` chứa vocabulary của chính font đó.**
   Code trích shape từ font, Jev match → pattern "select instead of generate".
2. **Tách câu hỏi theo chiều độc lập làm accuracy nhảy vọt** (base 15→24/24 khi tách khỏi modifier).
   Fail còn lại là lỗi *trích xuất vocabulary của code*, không phải lỗi model.
3. **Confidence hiệu chỉnh tốt**: miss conf 0.16–0.38, hit 0.9+ → route ca khó cho người duyệt.

Chi phí: 72 câu ≈ 7k input token ≈ **$0.0003** (output free). Pass 134 glyph ≈ $0.001.

> **Cảnh báo về ground truth** (phát hiện ở Phase 1): `DepartureMono-Viet.otf` **không phải
> tham chiếu đúng**. Toàn bộ 76 glyph do pipeline tay tạo ra đã bị **flatten base letter**
> — `rects_of()` lấy bounding box của contour rồi vẽ lại thành hình chữ nhật, phá shape của
> mọi base có contour không phải hình chữ nhật (`a` mất 55% diện tích, `e i u A E I đ` tương tự).
> `ả` trong bản tay làm là một **khối đặc**, không phải chữ `a` có móc.
> Chi tiết + cách kiểm: `docs/research/ground-truth-flattening.md`.
>
> Hệ quả: ground truth vẫn dùng được làm **nguồn quyết định thiết kế** (shape mark, vị trí đặt)
> và **baseline để vượt**, nhưng không dùng làm chuẩn đúng. Các thí nghiệm Jev ở trên render
> bằng bbox-fill nên phần nhận diện *base letter* chạy trên khối đặc — kết quả nhận diện
> *tone mark* vẫn giá trị (mark là hình chữ nhật), nhưng phải chạy lại bằng rasterizer thật
> ở Phase 2.

## 3. Kiến trúc

```
font.otf
  │
  ├─ analyze ──► coverage diff (bộ ký tự Việt), inventory part đã có, detect pixel grid
  ├─ extract ──► mark shapes (acute/grave/tilde/hook_above/dot_below)
  │              + modifiers (breve/circumflex/horn)
  ├─ plan ─────► mỗi glyph thiếu: recipe (base + modifier + tone + offset)
  ├─ compose ──► N candidate / glyph
  ├─ render ───► text grid 7×14 / candidate
  ├─ judge ────► Jev: verify (3 câu/glyph) + select (Choice) + collision (Noul)
  ├─ apply ────► ghi glyph vào font
  ├─ build ────► .otf / .ttf
  └─ proof ────► proof sheet + review queue (conf thấp)
```

| module | trách nhiệm | phụ thuộc |
|---|---|---|
| `analyze.py` | cmap diff vs bộ ký tự Việt; inventory base/modifier/tone; detect grid (pitch, rows, cols) | fontTools |
| `extract.py` | trích mark/modifier shape bằng **region-based**, không dùng subtraction | fontforge |
| `compose.py` | dựng candidate từ base + modifier + tone; snap grid; sinh offset variants | fontforge |
| `render.py` | glyph → text grid | fontforge |
| `judge.py` | TypeSafe client; build questions; batch; confidence routing | typesafe-sdk |
| `build.py` | ghi glyph, generate font | fontforge |
| `proof.py` | HTML proof sheet + review queue | — |
| `cli.py` | `vietfont add <font> -o <out>` | — |

**Stack** (đã validate): Python 3.14 (homebrew) · venv `--system-site-packages` ·
`fontforge` 20251009 · `fontTools` 4.65 · `typesafe-sdk` 0.7.

## 4. Thiết kế câu hỏi

**Verify — 3 câu độc lập mỗi glyph** (đo trên 24 glyph khó: 24/24 · 21/24 · 23/24):

| id | type | hỏi | vocabulary trong state |
|---|---|---|---|
| `letter_i` | Choice | base letter nào, bỏ qua mọi mark? | plain letters (`a e o u …`) |
| `mod_i` | Choice | modifier nào? | modifier shapes (`breve circumflex horn none`) |
| `tone_i` | Choice | tone mark nào? | tone marks (`acute grave hook_above tilde dot_below none`) |

**Select** — 1 Choice/glyph trên candidate ids.
**Collision** — Noul: mark có chạm/đè base? mark có vượt ascender?
**Routing** — conf < ngưỡng → review queue; ngưỡng calibrate trên ground truth.

### Ca khó bắt buộc phải đúng

Ảnh tham chiếu trong [issue #21](https://github.com/rektdeckard/departure-mono/issues/21) khoanh đỏ
đúng chỗ một font pixel tham chiếu (Fixedsys Excelsior) làm hỏng: **tone mark xếp trên modifier**,
cụ thể `hook_above` và `tilde` trên `ă â ê ô`:

```
ẳ Ẳ   (breve + hook_above)      ỗ Ỗ   (circumflex + tilde)
ể Ể   (circumflex + hook_above)
```

Đây là 12 glyph (6 lower + 6 upper) trong nhóm 2-mark. Phase 1 và 3 phải verify riêng nhóm này,
không chỉ tính pass rate tổng — nếu nhóm này fail thì font hỏng đúng chỗ người dùng nhìn thấy.

**Phase 1 xác nhận: nhóm HOA không đủ chỗ.** Tool dựng đúng contour nhưng phát hiện
**10 glyph HOA bị dấu đè lên chữ nền**:

```
Ắ Ằ Ẳ Ẵ   (Ă + thanh)      Ẩ Ẫ   (Â + thanh)
Ể Ễ        (Ê + thanh)      Ổ Ỗ   (Ô + thanh)
```

Nguyên nhân: chữ HOA chiếm row 3–10, modifier chiếm row 0–1, chỉ còn **1 row trống** (row 2)
trong khi tone mark cần 2 row. Không có chỗ hợp lệ — đây là bài toán thiết kế thật, không
phải lỗi code. Phase 2/3 phải giải: vẽ mark nhỏ hơn, hạ modifier xuống, hay chấp nhận merge.

## 5. Phases

### Phase 0 — Repo + migrate ✅
- [x] migrate `departure-mono-viet` → `fonts/departure-mono-viet/` (`font-src/`, `research/`, `build/`, `scripts/` → `legacy/`)
- [x] `pyproject.toml` + venv + deps
- **Kết quả**: legacy pipeline tái lập ground truth chính xác (134 glyph, 0 differ);
  `vietfont --version` chạy; stack fontforge + fontTools + typesafe-sdk OK

### Phase 1 — Deterministic core (chưa AI) ✅
- [x] `analyze`: coverage diff + inventory + grid detect
- [x] `marks`: mark pack cho mark/modifier mà font thiếu
- [x] `compose` + `build`: dựng 76 glyph thiếu, **giữ nguyên contour gốc của base**
- **Kết quả**: coverage **134/134**; **134/134** glyph giữ nguyên contour carrier.
  Bản dựng tay chỉ đạt **70/134** (64 glyph bị flatten base).
  Lưới tự suy được từ font: 7×14 ô, pitch 50, đỉnh 550.
- **Phát hiện mới**: 10 glyph HOA 2-mark có dấu **đè lên chữ nền** — xem mục "Ca khó" ở §4.

### Phase 2 — Jev judge
- [ ] `judge.py`: client + question builders + batching
- [ ] verify pass trên ground truth → đo agreement với bản tay làm
- [ ] calibrate ngưỡng confidence
- **Acceptance**: verify trên font tay làm đạt ≥ 90% all-three; miss có conf thấp hơn hit (tách được)

### Phase 3 — Candidate selection loop
- [ ] sinh N candidate/glyph; Jev select + verify; fail → escalate
- **Acceptance**: tool tự ra font đạt verify rate ≥ bản tay làm

### Phase 4 — Proof sheet + review
- [ ] HTML proof sheet: 134 ký tự, conf, flag
- [ ] review queue
- **Acceptance**: mở proof sheet thấy rõ ca cần duyệt

### Phase 5 — Generalize
- [ ] chạy trên font pixel thứ 2
- **Acceptance**: pipeline chạy không sửa code cho font mới (chỉ đổi tham số grid)

## 6. Rủi ro

| rủi ro | giảm thiểu |
|---|---|
| horn extraction sai (đo được: ra đúng 1 pixel) | region-based extraction; verify riêng modifier |
| font thiếu Latin-1 precomposed → không có mark để trích | v1 báo lỗi rõ + dừng; thiết kế mark để v2 |
| outline font | ngoài scope v1 |
| grid detection sai | cho override bằng CLI flag |
| Jev đọc sai ở resolution thấp | confidence routing + proof sheet |

## 7. Ngoài scope v1

- outline font (rasterize để judge, compose bằng fontTools)
- agent tự viết recipe / triage
- thiết kế mark mới khi font thiếu hoàn toàn
