# Upstream: departure-mono#21 — Feature Request: Support Vietnamese characters

<https://github.com/rektdeckard/departure-mono/issues/21> · mở 2025-05-30 · còn mở (cập nhật 2026-09-16)

## Diễn biến

| ai | nói gì |
|---|---|
| @haunt98 (mở issue) | xin hỗ trợ tiếng Việt, trỏ tới vietnamesetypography.com |
| @minoraxis (tác giả font) | *"I would love to support Vietnamese. It would take some investigation first as I'm not sure the grid is big enough to accommodate stacking diacritics."* |
| @auduongtuan, @huaquanghan | hỏi tiến độ |
| @NNBnh | đăng danh sách ký tự đầy đủ + ảnh tham chiếu + repo test |

**Câu hỏi mở của tác giả font — "grid 7×14 có đủ chỗ cho diacritic xếp tầng không" — đã có
câu trả lời trong repo này: đủ.** Bản dựng tay `build/DepartureMono-Viet.otf` đạt 134/134.

## Danh sách ký tự chuẩn (từ comment của @NNBnh)

```
a á à ả ã ạ   o ó ò ỏ õ ọ   e é è ẻ ẽ ẹ   u ú ù ủ ũ ụ
A Á À Ả Ã Ạ   O Ó Ò Ỏ Õ Ọ   E É È Ẻ Ẽ Ẹ   U Ú Ù Ủ ũ Ụ

ă ắ ằ ẳ ẵ ặ   ô ố ồ ổ ỗ ộ   ê ế ề ể ễ ệ   ư ứ ừ ử ữ ự
Ă Ắ Ằ Ẳ Ẵ Ặ   Ô Ố Ồ Ổ Ỗ Ộ   Ê Ế Ề Ể Ễ Ệ   Ư Ứ Ừ Ử Ữ Ự

â ấ ầ ẩ ẫ ậ   ơ ớ ờ ở ỡ ợ   i í ì ỉ ĩ ị   y ỳ ý ỷ ỹ ỵ   đ
Â Ấ Ầ Ẩ Ẫ Ậ   Ơ Ớ Ờ Ở Ỡ Ợ   I Í Ì Ỉ Ĩ Ị   Y Ỳ Ý Ỷ Ỹ Ỵ   Đ
```

**Đối chiếu với bộ 134 của `vietfont`** (đã kiểm bằng script):

- Issue: 145 ký tự. Bộ của ta: 134.
- Chênh lệch: issue có thêm 12 chữ ASCII thuần (`AEIOUYaeiouy`) — font gốc đã có sẵn, không cần dựng.
- Issue có 1 typo: hàng `U` ghi `ũ` (thường) thay vì `Ũ` (hoa). Bộ của ta đúng.
- 145 − 12 = 133, +1 (sửa typo) = **134** ✅ khớp.

## Ảnh tham chiếu — chỗ nào một font pixel hay hỏng

Ảnh trong issue so sánh với [Fixedsys Excelsior](https://github.com/kika/fixedsys), khoanh đỏ
các ca hỏng. Đọc ảnh: **tất cả ca bị khoanh đều là tone mark xếp trên modifier**:

| ca | modifier | tone |
|---|---|---|
| `ẳ` `Ẳ` | breve | hook above |
| `ỗ` `Ỗ` | circumflex | tilde |
| `ể` `Ể` | circumflex | hook above |

→ Đây là **12 glyph** (6 thường + 6 hoa) trong nhóm 2-mark, và là tiêu chí chất lượng thật sự:
pass rate tổng có thể đẹp trong khi nhóm này hỏng. Phase 1/3 phải verify riêng nhóm này.

## Tài nguyên test

- <https://codeberg.org/NNB/vietnamese_font_test> — Unicode test page cho tiếng Việt
- [WAZU JAPAN — Vietnamese Comprehensive Unicode Test Page](https://www.wazu.jp/gallery/Test_Vietnamese.html) — nguồn của trang trên
- [Fixedsys Excelsior](https://github.com/kika/fixedsys) — font pixel tham chiếu (có Việt hoá)

## Hệ quả cho `vietfont`

1. Bộ ký tự mục tiêu đã được xác nhận độc lập — không cần tự suy diễn.
2. Nhóm `hook_above`/`tilde` trên `ă â ê ô` là acceptance test bắt buộc, không phải nice-to-have.
3. Có font pixel tham chiếu để so — dùng làm đối chứng khi calibrate.
