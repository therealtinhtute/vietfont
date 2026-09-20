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

## Dáng cuối — 3 hàng

```
ả  (3 hàng)        Ả  (3 hàng)
   ..###..            ..###..
   ....#..            ....#..
   ...#...            ...#...
```

Thanh ngang 3 ô ở trên, rủ xuống bên phải, rồi khoáy vào trong về bên trái. Giữ đúng
cấu trúc của Fixedsys (vòng móc trên-trái, nét xuống bên phải, đuôi khoáy vào) nhưng
mỗi đoạn 1 pixel.

Thanh trên rộng 3 ô là chỗ cân lại phần đuôi bị mất so với bản 4 hàng — không có nó
thì dấu trông như chữ "C" hơn là vòng xoáy.

## Vì sao 3 hàng chứ không 4

Bản 4 hàng (`..##...` / `.#..#..` / `....#..` / `...#...`) đẹp hơn khi soi ở cỡ lớn,
nhưng đòi ascent 650 — chiều cao dòng +14% cho **cả font**.

| móc | ascent | chiều cao dòng |
|---|---|---|
| 4 hàng | 650 | 800 (+14%) |
| **3 hàng** | **600** | **750 (+7%)** |
| 3 hàng | 550 | 700 (gốc) — **KHÔNG ĐẠT**, `Ẳ` bị dấu đè |

Chữ hoa 2 dấu cần 4 hàng (3 hàng dấu + 1 hàng dấu mũ), nên không về được mức gốc 550.
Nhưng 3 hàng cắt được một nửa cái giá so với 4 hàng, mà dấu vẫn đọc ra móc.

Chữ `i` cũng được 3 hàng: hàng đuôi của móc trùng khít dấu chấm nên `_dedupe` gộp
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
"marks":         { "hook_above": [ ... 3 hàng ... ] },
"compact_marks": { "hook_above": [ ... 3 hàng ... ] }
```

Không còn cách nào khác ngoài **nâng ascent**: lưới cao thêm thì chữ hoa mới có chỗ.

`--ascent 600` (gốc 550) cho lưới 15 hàng thay vì 14.

**Cái giá**: chiều cao dòng tăng 7% cho **cả font**, kể cả các glyph gốc. Đây là đánh
đổi thật, không phải chi tiết kỹ thuật — chữ sẽ giãn dòng hơn ở mọi nơi dùng font này.
Bản 4 hàng đòi 650 (+14%); hạ móc xuống 3 hàng cắt được một nửa cái giá đó.

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
