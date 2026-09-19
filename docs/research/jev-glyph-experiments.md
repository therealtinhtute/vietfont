# Jev đọc glyph pixel — nhật ký thí nghiệm

Ngày: 2026-09-19 · Model: `jev-latest` (= `jev-1.13.0`) · Endpoint: `POST /v1/systemone`

Mục đích: kiểm chứng giả định lõi của `vietfont` — **Jev có "nhìn" được glyph của font
pixel không?** Nếu không, toàn bộ kiến trúc judge sụp.

## Setup

Font test: `DepartureMono-Viet.otf` (ground truth, 134/134 ký tự Việt, do người dựng tay).

Render glyph → lưới text 7×14, `#` = mực, `.` = trống:

```python
PX, TOP_Y, ROWS, COLS = 50, 550, 14, 7   # Departure Mono: 50 units/pixel
def rects_to_grid(rects):
    grid = [[False]*COLS for _ in range(ROWS)]
    for (x0,y0,x1,y1) in rects:
        for r in range(int((TOP_Y-y1)//PX), int((TOP_Y-y0)//PX)):
            for c in range(int(x0//PX), int(x1//PX)):
                grid[r][c] = True
    return grid
```

Ví dụ `ả` (U+1EA3):

```
.......
.......
....#..
..##...
.......
..###..
..####.
..####.
.#####.
.#####.
..####.
.......
.......
.......
```

## Thí nghiệm 1 — hỏi thẳng, không vocabulary

State: 6 lưới glyph. Câu hỏi: Choice "đây là chữ nào?" (5–6 lựa chọn).

**Kết quả: 1/6.** Confidence 0.13–0.32.

| glyph | đáp án | Jev | conf |
|---|---|---|---|
| ế | ế | ề | 0.13 |
| ả | ả | á | 0.24 |
| ã | ã | á | 0.13 |
| ạ | ạ | ạ ✅ | 0.72 |
| ơ | ơ | ô | 0.32 |
| ư | ư | ô | 0.05 |

→ Lưới pixel thô là out-of-distribution với model text. **Hỏi thẳng thì hỏng.**

## Thí nghiệm 2 — cho vocabulary của chính font

State thêm `mark_shapes` = shape mark trích từ font:

```json
{"acute": "....#..\n...#...", "grave": "..#....\n...#...",
 "tilde": "...#.#.\n..#.#..", "hook_above": "....#..\n..##...",
 "dot_below": "...#..."}
```

Câu hỏi: "Trong `glyphs[i].grid`, mark nào từ `mark_shapes` được vẽ?"

**Kết quả: 10/10** (5 glyph × 2 cách hỏi: full grid và mark region). Confidence 0.97–1.00.

→ **State design quyết định tất cả.** Cùng model, cùng glyph, chỉ đổi vocabulary: 1/6 → 10/10.

## Thí nghiệm 3 — scale lên 24 glyph khó

24 glyph `ơ ớ ờ ở ỡ ợ ư ứ ừ ử ữ ự ê ế ề ể ễ ệ ă ắ ằ ẳ ẵ ặ` (nhóm 2 mark).
State: `base_variants` (10 lưới `a ă â e ê o ô ơ u ư`) + `tone_marks` + 24 glyph.
2 câu/glyph: base-variant, tone.

**Kết quả: tone 24/24 · base 15/24.** Confidence min 0.29, mean 0.68.

Fail có hệ thống:
- **Toàn bộ `ơ`** (6/6) → nhận là `o`. Horn là append bên phải, dễ bị bỏ qua.
- `ể ễ ệ` → nhận là `â`. Nhầm base `e` ↔ `a` khi có tone mark.

## Thí nghiệm 4 — tách 3 câu độc lập

Tách base-variant thành 2 chiều: `letter` (plain base) + `modifier` (breve/circumflex/horn/none).
Modifier shape trích bằng hiệu lưới: `breve = ă − a`, `circumflex = ê − e`, `horn = ơ − o`.

**Kết quả: letter 24/24 · modifier 21/24 · tone 23/24 · cả ba 20/24.** Confidence min 0.16, mean 0.68.

| miss | letter | modifier | tone |
|---|---|---|---|
| ờ | o ✅ (0.89) | horn→none (0.30) | grave ✅ (0.96) |
| ỡ | o ✅ (0.96) | horn→circumflex (0.38) | tilde ✅ (0.98) |
| ệ | e ✅ (0.29) | circumflex ✅ (0.34) | dot_below→none (0.31) |
| ắ | a ✅ (0.73) | breve→horn (0.21) | acute ✅ (0.86) |

→ Tách chiều làm letter 15→24/24. **Miss còn lại là lỗi trích xuất, không phải lỗi model:**
`horn = ơ − o` ra đúng **1 pixel** (horn đè lên thân `o`), nên vocabulary vô dụng.

## Kết luận

1. **Jev đọc được glyph pixel — với điều kiện `state` chứa vocabulary của chính font đó.**
   Đây là pattern "select instead of generate": code trích shape, Jev match.
2. **Tách câu hỏi theo chiều độc lập** (letter / modifier / tone) tăng accuracy mạnh.
3. **Confidence hiệu chỉnh tốt**: miss 0.16–0.38, hit 0.9+ → route ca khó cho người duyệt.
4. **Chất lượng vocabulary là trách nhiệm của code.** Extraction region-based, không subtraction.

## Chi phí

| thí nghiệm | câu hỏi | input tokens | chi phí |
|---|---|---|---|
| 3 (2 câu × 24 glyph) | 48 | 6,719 | $0.00028 |
| 4 (3 câu × 24 glyph) | 72 | 7,171 | $0.00030 |

Giá Jev 1.13: **$42/Btok input, output free**. Pass 134 glyph ≈ $0.001. Không đáng kể.

## Tái lập

```bash
# render glyph → JSON lưới
fontforge -script render_json.py build/DepartureMono-Viet.otf "ơớờởỡợưứừửữựêếềểễệăắằẳẵặ" > grids.json

# hỏi Jev (SDK)
TYPESAFE_API_KEY=... python -c "
from typesafe_sdk import TypeSafeClient, Choice
with TypeSafeClient() as c:
    r = c.system_one(state={...}, questions={...})
    print(r.choices['tone_0'].choice, r.choices['tone_0'].confidence)
"
```

Lưu ý SDK: `client.system_one(state=..., questions=...)` → `r.choices[id]`, `r.nouls[id]`,
`r.scores[id]`, `r.usage`. (Không phải `client.questions.ask`.)
