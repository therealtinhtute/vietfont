# Dấu hỏi: dáng móc, và chỗ lưới hết chỗ

Ngày: 2026-09-20 · Trạng thái: đã sửa

## Vấn đề

Người dùng báo dấu hỏi "giống cái móc câu hơn" là dấu hỏi. Model thị giác mô tả dáng cũ
là *"a tick resting on a horizontal bar"* — một pixel ở góc phải, rồi thanh ngang bên
dưới-trái. Hai mảng chỉ **dính chéo** nhau nên mắt tách rời, không ra một nét.

```
cũ:  ....#..      mới:  ..##...
     ..##...            .#.##..
                        ...##..
                        ..##...
```

## Dáng đúng

Tham chiếu là **Fixedsys Excelsior** — font pixel đã Việt hoá, chính là font trong ảnh
của issue gốc. Outline lấy từ `FSEX.ttx` (repo `kika/fixedsys`), `unitsPerEm=160`,
lưới 10 đơn vị/pixel:

```
ả  (Fixedsys, 4 hàng)
   ...##...
   ..#.##..
   ....##..
   ...##...
```

Đặc điểm: **vòng móc ở trên-trái, nét chạy xuống bên phải, đuôi khoáy về trái ở dưới**.

## Bản 4 hàng đầu tiên sai — quá đậm

Bản đầu bám sát Fixedsys, nhưng Fixedsys vẽ nét **2 pixel rộng**, còn các dấu của
Departure Mono đều **1 pixel**:

```
sắc   ....#..      hỏi (bản sai)   ..##...
      ...#...                      .#.##..   ← hai nét dọc song song
                                   ...##..
                                   ..##...
```

Nhìn ra ngay là lạc lõng: dấu hỏi thành một khối, các dấu khác là nét mảnh. Người dùng
bắt đúng chỗ này — *"không nên có 2 dọc 1 lần, chỉ là đường nét đơn như các dấu khác"*.

## Dáng cuối — vòng xoáy nét mảnh

```
ả  (4 hàng)        Ả  (4 hàng)
   ..##...            ..##...
   .#..#..            .#..#..
   ....#..            ....#..
   ...#...            ...#...
```

Thanh ngang trên, hai bên rủ xuống, rồi khoáy vào trong. Giữ đúng cấu trúc của
Fixedsys (vòng móc trên-trái, nét xuống bên phải, đuôi khoáy vào) nhưng **mỗi đoạn
1 pixel** — mảnh như `á à ã`.

Bản thu gọn 3 hàng bỏ hàng đuôi cuối, dùng khi chữ hoa 2 dấu hết chỗ.

Chữ `i` chỉ được 3 hàng: hàng đuôi của móc trùng khít dấu chấm nên `_dedupe` gộp
chúng làm một — đúng convention của font gốc.

## Chỗ lưới hết chỗ — và cách nới

| | dải dấu | hàng trống phía trên | dáng dùng được |
|---|---|---|---|
| chữ thường | 2–3 | 0–1 | **4 hàng** |
| chữ hoa | 0–1 | không còn | **2 hàng** |

Chữ hoa chỉ có 3 hàng trên cap-height, mà glyph 2 dấu cần dấu thanh + modifier. Nên
mark đầy đủ không vừa — `_tone_shift` kẹp lại và dấu đè lên nhau.

Bản đầu sửa bằng `compact_marks`: mark pack có thêm bản thu gọn, `compose` chọn bản
thu gọn khi `_fits()` báo bản đầy đủ không nằm được trên vật cản mà không vượt đỉnh lưới.

```json
"marks":         { "hook_above": [ ... 4 hàng ... ] },
"compact_marks": { "hook_above": [ ... 3 hàng ... ] }
```

Nhưng bản thu gọn vẫn chỉ 2 hàng, và người dùng muốn **mọi dấu hỏi từ 3 hàng trở lên**.
Không còn cách nào khác ngoài **nâng ascent**: lưới cao thêm thì chữ hoa mới có chỗ.

`--ascent 650` (gốc 550) cho lưới 16 hàng thay vì 14. Kết quả:

| ascent | chiều cao dòng | móc 3 hàng | móc 4 hàng |
|---|---|---|---|
| 550 (gốc) | 700 | — | 12 thường |
| 600 | 750 (+7%) | 16 | 8 |
| **650** | **800 (+14%)** | **10** | **14** |

Chọn 650: nhiều glyph được móc đủ 4 hàng hơn, và khoảng cách dấu tốt hơn
(91 glyph gap 1 so với 82).

**Cái giá**: chiều cao dòng tăng 14% cho **cả font**, kể cả các glyph gốc. Đây là đánh
đổi thật, không phải chi tiết kỹ thuật — chữ sẽ giãn dòng hơn ở mọi nơi dùng font này.

## Verify phải đổi theo

`verify` trước đây lấy `Grid.detect(source)` để tính thiết kế. Nâng ascent làm số hàng
lưới đổi, nên thiết kế tính trên lưới gốc lệch hàng so với bản dựng thật → báo nhầm
"mực lệch thiết kế" ở 33 glyph. Sửa: dùng lưới của font **xuất**, đúng cái mà bộ dựng
đã chạy.

## Chữ `i` — mark nuốt dấu chấm

Đuôi móc 4 hàng rộng 2 ô, mà dấu chấm của `i` nằm đúng một trong hai ô đó. Để cả hai
thì fontforge coi là contour lồng nhau, lật chiều, mất mực.

`_dedupe` giờ làm hai việc: bỏ contour của mark trùng khít với carrier, **và** bỏ
contour của carrier nằm trọn trong một contour của mark. Mark hấp thụ dấu chấm thay vì
chồng lên nó — đúng convention của font gốc, nơi dấu và dấu chấm vốn là một.

Hệ quả: `_flattened` phải chấp nhận contour chữ nền **được mark phủ trọn**, không chỉ
contour còn nguyên. Nếu không nó báo nhầm `ỉ` là flatten. Phép kiểm vẫn bắt được font
cũ (mất mực thật), nên không bị yếu đi.

## Kết quả

```
coverage : 134/134
shape    : 134/134 glyph giữ contour chữ nền
trùng hình: không có
mực      : khớp thiết kế
va chạm  : không có
ĐẠT
```
