# Chữ hoa hai dấu: dấu thanh nuốt dấu mũ

Người dùng báo chữ in hoa "chưa đúng lắm". Đo ra thì đúng là sai, và sai nặng hơn
tưởng: **6 nhóm ký tự chữ hoa ra cùng một hình**.

```
Ã Ẫ      Ấ Ẩ      Ẽ Ễ      Ế Ể      Õ Ỗ      Ố Ổ
```

`Ẫ` mất hẳn dấu mũ và trùng khít `Ã`. `Ấ` (sắc) và `Ẩ` (hỏi) không phân biệt được.

## Vì sao

Chữ hoa chỉ có **3 hàng lưới** phía trên cap-height: cap đỉnh ở hàng 3, lưới đỉnh ở
hàng 0. Một glyph hai dấu cần dấu thanh (2 hàng) **cộng** modifier (1–2 hàng) — vừa
khít 3 hàng, không dư hàng nào.

`_tone_shift` neo **đáy** dấu thanh vào `đỉnh vật cản + 1 hàng`, nhưng không vượt
`grid.top`. Khi hết chỗ, nó trả về dịch nhỏ hơn cần thiết — dấu thanh dừng lại
**ngay trên modifier**, hai thứ nằm chung hàng và hoà làm một.

## Vì sao phép kiểm cũ không bắt được

`compose` cũ chỉ chạy fallback thu gọn modifier khi `_collisions(carrier, shifted)`
báo có cặp contour chồng hộp bao. Hai lỗi ở đó:

1. **Kiểm sau `_dedupe`.** `_dedupe` bỏ contour của mark trùng khít contour của
   carrier trước, nên phần chồng biến mất trước khi được kiểm.
2. **Hộp bao không đủ.** Dấu sắc và dấu mũ trên `Â` **chen kẽ nhau theo cột** —
   sắc ở cột 4 hàng 0 và cột 3 hàng 1, mũ ở cột 3 hàng 0 và cột 2,4 hàng 1. Hộp bao
   của chúng chỉ chạm nhau chứ không chồng, nên phép kiểm trả về 0.

Hệ quả: nhóm `Ă` (dấu mũ ngắn) tình cờ kích hoạt được fallback nên đúng, còn nhóm
`Â`, `Ê`, `Ô` thì không — cùng một lỗi mà biểu hiện khác nhau.

## Cách sửa

Thay phép kiểm hộp bao bằng phép kiểm **hàng lưới** (`_shares_rows`): mark và
carrier không được chiếm chung hàng nào. Đây mới là điều kiện đúng — hai dấu nằm
cùng hàng thì mắt đọc thành một khối, bất kể pixel có chồng hay không.

```python
carrier_rows = {row for row, _ in cells(carrier, grid)}
mark_rows = {row for row, _ in cells(mark, grid)}
return bool(carrier_rows & mark_rows)
```

Khi phát hiện chung hàng, modifier được thu gọn xuống 1 hàng và đặt ngay trên cap,
nhường 2 hàng trên cùng cho dấu thanh:

```
hàng 0   dấu thanh (đỉnh)
hàng 1   dấu thanh (đáy)
hàng 2   modifier thu gọn
hàng 3   cap-height
```

## Phép kiểm mới: `trùng hình`

`verify` giờ so hình rasterized của cả 134 ký tự và báo nhóm nào ra cùng một hình.
Đây là phép kiểm bắt được lỗi này — kiểm va chạm theo hộp bao thì không.

Chạy trên font cũ: **6 nhóm trùng**, exit 1. Trên font mới: 0 nhóm.

## Cái giá

Modifier thu gọn là 1 hàng thay vì 2, nên nét dấu mũ/dấu móc ngắn hơn bản gốc một
hàng. Số glyph có khoảng cách 0 hàng tăng từ 32 lên 44 — tất cả là glyph chữ hoa
hai dấu, nơi modifier thu gọn nằm liền trên cap theo đúng thiết kế của
`_compact_carrier`.

Đổi lại: **không còn ký tự nào trùng hình**, và mọi dấu đều đọc được.
