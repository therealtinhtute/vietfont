# Ground truth bị flatten base letter

Phát hiện: 2026-09-19 (Phase 1) · Mức độ: **nghiêm trọng** — bản dựng tay không dùng được làm chuẩn đúng

## Tóm tắt

`build/DepartureMono-Viet.otf` (bản Việt hoá dựng tay, 134/134) có **toàn bộ 76 glyph do
pipeline tay tạo ra bị hỏng shape**: base letter bị thay bằng bounding box của nó.

`ả` trong bản này là một **khối đặc**, không phải chữ `a` có dấu móc.

## Bằng chứng

Rasterize thật (nonzero winding, lưới 7×14) — `font-src` vs `build`:

```
source 'a'              ground-truth 'ả'
.......                 .......
.......                 ....#..
.......                 ..##...
.......                 .......
.......                 ..###..
..###..                 ..####.
.....#.                 ..####.
..####.                 .#####.
.#...#.                 .#####.
.#..##.                 ..####.
..##.#.                 .......
.......                 .......
.......                 .......
```

`a` gốc có counter (`.....#.`, `.#...#.`, `.#..##.`); `ả` mất sạch, thành khối.

Đo diện tích contour của `a` trong font gốc:

| | diện tích |
|---|---|
| polygon thật (12 điểm) | 22,500 |
| bounding box (200×250) | 50,000 |
| **mất** | **55%** |

## Nguyên nhân

`legacy/build_easy.py` và `legacy/finish_hard.py` dùng:

```python
def rects_of(name):
    return [c.boundingBox() for c in f[name].foreground]   # bbox, KHÔNG phải shape

def set_glyph(name, rects):
    for (x0,y0,x1,y1) in rects:
        pen.moveTo(x0,y0); pen.lineTo(x1,y0); pen.lineTo(x1,y1); pen.lineTo(x0,y1); pen.closePath()
```

`boundingBox()` trả về hộp bao, không phải đường bao. Với contour là hình chữ nhật thì
hai thứ trùng nhau; với contour nhiều điểm thì vẽ lại bbox = **phá shape**.

`legacy/scaffold_hard.py` làm **đúng** (copy toàn bộ điểm qua `pen.lineTo`), nhưng
`finish_hard.py` chạy sau đó ghi đè bằng `set_glyph` → hỏng lại.

## Phạm vi

Base letter có contour không phải hình chữ nhật (kiểm trên font gốc):

| base | điểm/contour | bbox |
|---|---|---|
| `a ă â` | 12 | (100,0,300,250) |
| `e ê` | 10 | (50,50,300,250) |
| `i` | 10 | (50,0,300,300) |
| `u ư` | 8 | (200,0,300,300) |
| `A Ă Â` | 12 | (50,0,300,300) |
| `E Ê I` | 12 | (50,0,300,400) |
| `đ Đ` | 16 | — |

`o O` là hình chữ nhật nên `ơ Ơ` không bị ảnh hưởng.

**76/76 glyph tạo mới đều đi qua `set_glyph`** → đều bị flatten. 58 glyph có sẵn trong
font gốc không bị đụng.

## Hệ quả

1. **Ground truth không phải chuẩn đúng.** Vẫn dùng được làm:
   - nguồn *quyết định thiết kế* (shape mark, vị trí đặt horn) — mark là hình chữ nhật nên không hỏng;
   - baseline để vượt.
2. **Phase 1 acceptance đổi**: "134/134 **và** không glyph nào bị flatten base".
   Tool phải **giữ nguyên contour gốc** — đây là thắng lợi thật đầu tiên so với làm tay.
3. **Renderer phải rasterize thật** (nonzero winding), không được fill bbox.
   Nếu không, Jev sẽ phán trên khối đặc thay vì chữ thật.
4. **Thí nghiệm Jev cũ phải chạy lại**: `docs/research/jev-glyph-experiments.md` render
   bằng bbox-fill trên chính font hỏng này. Kết quả nhận diện *tone mark* vẫn giá trị
   (mark là hình chữ nhật, không bị ảnh hưởng), nhưng phần *base letter* chạy trên khối
   đặc — độ khó khác, cần đo lại ở Phase 2.

## Cách kiểm (tái lập)

```python
# rasterize thật, không dùng boundingBox
def inside(px, py, contours):        # nonzero winding
    w = 0
    for pts in contours:
        for i in range(len(pts)):
            x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
            if y0 <= py < y1:
                if (x1-x0)*(py-y0) - (px-x0)*(y1-y0) > 0: w += 1
            elif y1 <= py < y0:
                if (x1-x0)*(py-y0) - (px-x0)*(y1-y0) < 0: w -= 1
    return w != 0
```

Đếm điểm mỗi contour cũng đủ: contour 4 điểm = hình chữ nhật; >4 điểm mà bị vẽ lại
thành 4 điểm = đã flatten.
