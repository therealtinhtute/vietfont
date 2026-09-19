# Contour lồng nhau bị fontforge lật chiều — và cách sửa

Ngày: 2026-09-19 · Mức độ: nghiêm trọng (mất mực) · Trạng thái: đã sửa

## Triệu chứng

`Ẳ` dựng ra bị **mất một phần dấu**:

```
Ắ (đúng)        Ẳ (sai)
.#..##.         .#..##.
..###..         ....#..     ← mất 2 pixel của dấu breve
.......         .......
...#...         ...#...
```

Cùng một breve, cùng vị trí — nhưng `Ắ` giữ được, `Ẳ` thì không. Khác biệt duy nhất:
`Ắ` dùng acute (lấy từ font), `Ẳ` dùng hook above (lấy từ mark pack).

## Nguyên nhân

Hai tầng:

**1. Mark pack quay contour ngược chiều với font.** Contour trong font quay theo chiều
kim đồng hồ (diện tích có dấu âm); contour trong `marks.json` quay ngược lại. Với quy tắc
nonzero winding, hai contour chồng nhau mà ngược chiều thì **triệt tiêu nhau** — mất mực.

**2. fontforge tự lật chiều contour lồng nhau khi `generate()`.** Kể cả sau khi đã chuẩn
hoá chiều ở tầng code, `font.generate()` vẫn coi contour nằm trong contour khác là **lỗ
(hole)** và lật chiều nó. Đo được:

```
sau set_contours (trong bộ nhớ):  hook areas = [-2500, -2500, -2500]   ← đúng
sau generate, đọc lại từ file  :  hook areas = [ 2500,  2500,  2500]   ← bị lật
```

Nên **chuẩn hoá chiều một mình không đủ**. Gốc rễ là **contour chồng lên nhau**.

## Cách sửa

**Tránh chồng lấn bằng thiết kế**, không phải bằng winding.

Bài toán chỗ: chữ HOA chiếm row 3–10, modifier chiếm row 0–1 → chỉ còn **1 row trống**
(row 2), mà tone mark cần 2 row. Không đủ chỗ nên mark buộc phải đè lên modifier.

Giải pháp: **thu gọn modifier xuống 1 row** cho nhóm HOA 2-mark, nhường 2 row trên cùng
cho tone mark.

```
trước (đè nhau)          sau (xếp tầng)
row 0  .#..##.  ← breve+tone   ....#..  ← tone
row 1  ..###..                 ..##...
row 2  .......                 ..###..  ← modifier thu gọn
row 3  ...#...                 ...#...
```

Modifier thu gọn = lấy đúng hàng dưới của modifier đầy đủ:

| modifier | đầy đủ (2 row) | thu gọn (1 row) |
|---|---|---|
| breve | `.#...#.` / `..###..` | `..###..` |
| circumflex | `...#...` / `..#.#..` | `..#.#..` |

Vì sao thu gọn **modifier** mà không thu gọn **tone**: acute và grave nén xuống 1 row đều
thành một pixel đơn — không phân biệt được. Breve và circumflex nén xuống vẫn khác nhau
(3 pixel thẳng vs 2 pixel chữ V).

## Cài đặt

- `marks.json` thêm khoá `compact_modifiers` (breve, circumflex).
- `compose()` kiểm tra chồng lấn sau khi đặt mark; nếu có, dựng lại carrier bằng modifier
  thu gọn đặt ngay trên mực chữ nền, rồi đặt lại mark.
- `glyph.ensure_winding()` chuẩn hoá chiều contour của mark theo carrier — vẫn giữ, vì nó
  đúng và bảo vệ khi mark chồng lên contour không lồng nhau.

## Kiểm chứng

| | trước | sau |
|---|---|---|
| glyph HOA 2-mark có cặp contour chồng nhau | 10 | **0** |
| base letter giữ nguyên contour | 134/134 | **134/134** |
| coverage | 134/134 | **134/134** |

## Bài học

1. **Kiểm tra chồng lấn phải là một phần của compose**, không phải cảnh báo suông —
   chồng lấn không chỉ xấu về thiết kế mà còn **mất mực** khi render.
2. **Đừng tin trạng thái trong bộ nhớ của fontforge.** `generate()` chuẩn hoá lại contour;
   muốn biết font thật sự chứa gì thì phải đọc lại từ file.
3. **fontforge cache theo đường dẫn.** `fontforge.open()` cùng một path trả về object cũ —
   khi kiểm tra output phải copy sang path mới hoặc mở bằng tiến trình mới.
