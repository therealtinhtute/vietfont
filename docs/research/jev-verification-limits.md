# Giới hạn của Jev khi verify glyph

Ngày: 2026-09-19 (Phase 2) · Model: `jev-latest` (= `jev-1.13.0`) · Kết luận: **âm tính**

## Tóm tắt

**Jev không đọc được glyph pixel đủ tin cậy để làm cổng verify.** Trên 60 glyph tiếng Việt
dựng bởi `vietfont`, cách hỏi tốt nhất đạt **80%** (ổn định qua 3 lần chạy); mọi cách hỏi
khác đều tệ hơn, có cách gần mức đoán mò.

Kết quả 10/10 ở `jev-glyph-experiments.md` **không giữ được ở quy mô lớn** — mẫu đó chỉ có
5 glyph và render bằng bbox-fill (khối đặc, ít chi tiết gây nhiễu hơn).

## Các cách hỏi đã thử

Sample: 60–78 glyph tiếng Việt, render bằng rasterizer thật (nonzero winding), lưới 7×14.

| cách hỏi | accuracy | conf | ghi chú |
|---|---|---|---|
| 3 câu tuyệt đối: letter / modifier / tone | **18%** | 0.40 | tệ nhất |
| 2 câu: carrier + tone | 47–56% | 0.50 | batch 1/8/24 như nhau |
| chỉ tone, có `none` | 41–58% | 0.49 | |
| chỉ tone, **bỏ `none`** | **77–80%** | 0.58 | khá nhất cho glyph có tone |
| crop vùng mark (6 hàng đầu) | 58–77% | 0.55 | không ổn định |
| Noul riêng từng mark (5 Noul/glyph) | 53% | 0.57 | xác suất nhoè 0.2–0.5 |
| so sánh cặp (đúng vs sai) | 57% | 0.08 | gần mức đoán mò (50%) |
| phóng to 2× / 3× | 31–36% | 0.19 | **phóng to làm tệ đi** |
| **crop sát vùng mark + vocab đủ** | **80%** | 0.77 | tốt nhất, ổn định 3/3 lần |
| crop sát + vocab cắt sát | 55% | 0.40 | vocab mất thông tin shape |

## Vì sao hỏng

1. **`none` là cái bẫy.** Thêm lựa chọn "không có mark" làm accuracy rơi từ 80% → 43%.
   Jev mặc định về `none`. Đúng như tài liệu jaggedness cảnh báo về "literal reading".
2. **Phóng to không giúp.** 2× và 3× đều tệ hơn 1× — model làm việc tốt hơn với lưới
   7 ký tự rộng, không phải với khối to hơn.
3. **So sánh cặp gần mức đoán mò.** Choice được cho là mạnh ở phán đoán *tương đối*, nhưng
   ở đây hai bản render khác nhau 2–4 pixel nên tín hiệu quá nhỏ.
4. **Noul không dùng được.** Xác suất các mark đều nằm 0.2–0.5, không tách được mark nào có mặt.
5. **Lỗi có hệ thống ở `dot_below`.** Crop của nó là 1 pixel đơn — không đủ thông tin để
   phân biệt với bất kỳ mark nào khác. 12/12 miss ở cấu hình tốt nhất là `dot_below`.

## Cấu hình tốt nhất (80%)

```python
# crop glyph xuống đúng các hàng mà tone mark chiếm
crop = các hàng của glyph phủ bbox của mark
# vocabulary: mark render ở vị trí tự nhiên, lưới đầy đủ
state = {"tones": {tên: lưới_đầy_đủ}, "glyphs": [{"crop": crop}]}
# câu hỏi: Choice trên 5 mark + none
"`glyphs[i].crop` is the mark region cropped from a Vietnamese letter. Which tone mark from `tones` is it?"
```

Ổn định: 48/60 qua 3 lần chạy, confidence 0.75–0.79.

**Trên toàn bộ 120 glyph có thanh điệu** (gồm cả chữ HOA và nhóm 2-mark), con số thật là
**62%** — thấp hơn hẳn mẫu 60 glyph. Chữ HOA khó hơn hẳn (23% ở thí nghiệm tone-only).
Đây mới là con số phải dùng khi nói về độ tin cậy của Jev.

## Hệ quả cho dự án

1. **Jev không được làm cổng verify.** 80% nghĩa là ~20% glyph đúng bị đánh dấu oan.
   Cổng phải là **kiểm tra tất định** — coverage, giữ contour, phát hiện va chạm — những cái
   này chính xác tuyệt đối và đã bắt được lỗi thật (flatten, va chạm HOA).
2. **Jev chỉ là tín hiệu tham khảo.** Dùng để *xếp hạng* glyph cho người xem trước, không
   để chặn.
3. **Phase 3 (Jev chọn candidate) phải thiết kế lại.** Nếu Jev không đọc nổi glyph thì nó
   cũng không chọn được candidate nào tốt hơn. Cần cách khác: chấm điểm bằng code, hoặc
   để Jev phán trên *mô tả* thay vì trên lưới pixel.
4. **Người duyệt là chốt cuối.** Proof sheet (Phase 4) trở thành bước verify thật sự,
   không còn là "duyệt ca khó".

## Điều chưa thử

- **Jev phán trên mô tả thay vì lưới.** Ví dụ code mô tả mark bằng lời ("nét chéo 2 pixel
  từ (2,4) xuống (3,3)") rồi hỏi Jev. Chưa test — nhưng khi đó Jev chỉ đang đọc lại output
  của code, giá trị verify thấp.
- **Font có lưới lớn hơn** (16×32+). Thử với Arial 16×32 cho 3% nhưng **vocabulary bị lỗi**
  (mark bị kéo giãn theo bbox riêng), nên chưa kết luận được. Cần test lại tử tế nếu muốn
  theo hướng outline font.
- **Model khác.** Jev là model quyết định nhanh, không phải model thị giác. Một LLM thị giác
  thật (nhìn ảnh render) có thể làm được — nhưng đó là kiến trúc khác, không phải "jev + agent".
