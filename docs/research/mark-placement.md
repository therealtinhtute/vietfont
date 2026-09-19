# Quy tắc đặt dấu: chừa 1 hàng, và chữ `i` là ngoại lệ

Ngày: 2026-09-19 · Trạng thái: đã sửa

## Vấn đề

Dấu (mũ, sắc, huyền, hỏi, ngã) dính sát chữ nền. Đo trên 134 glyph:

| nhóm | gap |
|---|---|
| font gốc: `á à ã`, `ă â ê`, `Á À Ã`, `Ă Â Ê` | **1** |
| tool dựng: chữ thường 1 dấu, chữ thường 2 dấu | **1** |
| tool dựng: `Ả Ẻ Ỉ Ỏ Ủ Ỷ` (HOA + hook) | **0** |
| tool dựng: `Ắ Ằ Ẳ Ẵ`, `Ẩ Ẫ Ể Ễ Ổ Ỗ` (HOA 2 dấu) | **0** |

## Convention thật của font

Không phải "cách chữ nền N hàng" — mà là **dải cố định theo chữ hoa/thường**:

| loại | hàng của dấu |
|---|---|
| chữ thường, 1 dấu | 2–3 |
| chữ hoa, 1 dấu | 0–1 |

Kiểm trên toàn bộ glyph tác giả vẽ (`á à ã é è í ì ó ò ú ù ý ỳ` → hàng 2–3;
`Á À Ã É È Í Ì Ó Ò Ú Ù Ý Ỳ` → hàng 0–1). Không có ngoại lệ.

Diễn đạt theo metric: **đáy dấu = x-height (hoặc cap-height) + 1 hàng**.

```
x-height = 300, cap-height = 400, pitch = 50
chữ thường: 300 + 50 = 350  → hàng 2–3
chữ hoa  : 400 + 50 = 450  → hàng 0–1
```

## Chữ `i` — chỗ suýt sửa sai

Công thức đầu tiên là "đáy dấu = **mực trên cùng** của chữ nền + 1 hàng". Nó đúng với
`a e o u y` nhưng sai với `i`: chữ `i` có **dấu chấm ở hàng 3**, cao hơn x-height (hàng 5).
Công thức đó đẩy dấu của `ỉ` lên hàng 0–1, trong khi font gốc đặt dấu của `í ì ĩ` ở hàng 2–3
— lệch 2 hàng, nhìn ra ngay.

Phải dùng **x-height/cap-height**, không dùng mực trên cùng.

## Hệ quả phụ: contour trùng khít

Đặt dấu của `ỉ` xuống hàng 2–3 thì pixel dưới cùng của dấu **trùng đúng ô với dấu chấm của
`i`**. Font gốc gộp hai thứ làm một contour; tool thêm contour thứ hai trùng khít →
fontforge coi là contour lồng nhau, lật chiều, mất mực.

Sửa: bỏ contour của dấu nếu nó trùng khít với contour đã có trong chữ nền (`_dedupe`).

Việc này **sửa thêm 6 glyph ngoài dự kiến**: `Ẩ Ẫ Ể Ễ Ổ Ỗ` trước đó rơi vào nhánh
"modifier thu gọn" vì dấu chồng lên modifier; sau khi dedupe, dấu và modifier **xen kẽ**
nhau (không chồng) nên giữ được modifier đầy đủ và có gap 1.

## Công thức cuối

```
vật_cản = đỉnh modifier            nếu glyph có modifier
        = x-height / cap-height    nếu glyph 1 dấu
đáy_dấu = vật_cản + 1 hàng
shift   = clamp(đáy_dấu − đáy_dấu_tự_nhiên, 0, headroom)
```

`headroom` chặn dấu vượt đỉnh lưới — nhờ nó mà nhóm HOA 2 dấu không tràn ra ngoài.

## Kết quả

Số đo bằng `vietfont verify` (120 glyph có dấu):

| | trước | sau |
|---|---|---|
| glyph có gap 1 | 76/120 | **88/120** |
| mực khớp thiết kế | 99/120 | **120/120** |
| base letter giữ contour | 134/134 | **134/134** |
| coverage | 134/134 | **134/134** |

Còn 32 glyph gap 0, chia làm ba nhóm — cả ba đều đúng, không phải lỗi:

- **24 glyph horn** (`ơ ư ớ ờ ở ỡ ợ ứ ừ ử ữ ự` + HOA): horn dính liền chữ, đúng thiết kế.
- **4 glyph `Ắ Ằ Ẳ Ẵ`**: chữ HOA chiếm hàng 3–10, phía trên còn 3 hàng, cần 4. Hết chỗ thật.
- **4 glyph `ì í ĩ ỉ`**: đúng convention của font cho chữ `i` (dấu ngang hàng dấu chấm).
