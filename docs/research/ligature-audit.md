# Ligature: đo bản cộng đồng, và cái bẫy script `latn`

Ngày: 2026-09-20 · Trạng thái: **chưa dùng được** — cơ chế đã xong, glyph chưa đạt

## Vấn đề

Font chính `DepartureMonoViet-Regular.otf` không có ligature lập trình. Bản dựng tay
`DepartureMonoLigaZ-Regular.otf` có, nhưng do pipeline `legacy/` làm và **mất 19/20 feature**
của font gốc (chỉ còn `liga`).

Nguồn duy nhất có sẵn là bản cộng đồng của [@danicaj3w](https://github.com/danicaj3w/departure-mono),
nhắc ở [departure-mono#12](https://github.com/rektdeckard/departure-mono/issues/12).

## Maintainer đã cảnh báo trước

Ở issue #12, @minoraxis trả lời bản cộng đồng:

> There are a few things I'd address to stay in the spirit of Departure Mono: **snapping each
> character to the pixel grid (7x14)**, **maintaining the fixed pitch (monospace)**, and
> reviewing some inconsistency/legibility questions.

Đo lại thì **đúng cả hai điểm**.

## Đo bản cộng đồng — 26 glyph

| tiêu chí | kết quả |
|---|---|
| điểm contour lệch lưới (không phải bội số 50) | **24/26 glyph** |
| advance khác `350 × số ký tự` | **25/26 glyph** |
| advance đúng bằng 350 (tức 1 ô, sai cho ligature nhiều ký tự) | 2 glyph |

Advance nguồn trải từ 350 (`exclam_equal`) tới 1100 (`less_exclam_hyphen_hyphen`) — không
theo quy luật nào.

## Hai glyph hỏng hẳn

`greater_equal` (`>=`) và `less_equal` (`<=`) **thiếu hẳn thành phần `=`**:

```
>=  bản cộng đồng        >=  ghép từ glyph gốc
   ..#...........           ..#...........
   ...#..........           ...#..........
   ....#.........           ....#...#####.
   .....#........           .....#........
   ....#.........           ....#...#####.
   ...#..........           ...#..........
   ..#...........           ..#...........
   ..####........
```

Mực chỉ chiếm x 100..300 trong khi advance cần 700. Hai glyph này vẽ như glyph **một ô**,
không phải ligature hai ký tự.

## Cái bẫy: `mergeFeature` gắn `liga` thiếu script `latn`

Sinh feature file từ pack rồi gọi `fontforge.mergeFeature()`. Bản đầu chỉ khai:

```
languagesystem DFLT dflt;
```

Kết quả: `liga` **có** trong bảng GSUB, 26 substitution **có**, `hb-shape` mặc định **ra ligature** —
nhưng trình duyệt **không** áp dụng. Đo bằng `hb-shape` mới lộ:

```
hb-shape            ==  ->  [equal_equal=0+700]        ← DFLT, có ligature
hb-shape --script=latn  ==  ->  [equal=0+350|equal=1+350]  ← latn, KHÔNG
```

`==` là ký tự Common nên shaper mặc định rơi về `DFLT`; còn văn bản Latin trong trình duyệt
resolve về `latn`. Thiếu một dòng `languagesystem latn dflt;` là ligature chết trong thực tế
mà mọi phép kiểm "có lookup trong bảng" đều báo đạt.

**Sửa**: khai cả hai `languagesystem`. Sau đó `hb-shape --script=latn` ra `[equal_equal=0+700]`.

## Snap thôi là chưa đủ — contour teo thành điểm

Làm tròn mọi đỉnh về bội số 50 **không** bảo toàn hình. Hai đỉnh kề nhau có thể rơi vào
cùng một ô, để lại contour **diện tích 0** — fontforge vẽ ra hư không, mà ảnh raster lại
che mất vì ô đó vẫn có mực từ contour khác.

Đo trên chính 26 glyph này: **9 contour teo trên 2 glyph**. Nếu chỉ snap mà không dọn,
font ra vẫn "trông đúng" trong proof sheet nhưng mang contour rác.

Nên `snap()` làm ba việc, không phải một:

1. kéo mọi đỉnh về bội số của `pitch`;
2. gộp đỉnh trùng **kề nhau** (và đỉnh cuối trùng đỉnh đầu của contour khép kín);
3. bỏ contour còn dưới 3 đỉnh — báo lại số lượng trong `LigatureReport.dropped`.

## Cổng verify phải kiểm cả ba tầng

`_ligatures()` trong `verify.py` kiểm theo thứ tự:

1. **GSUB thay thế đúng** — dãy glyph nguồn phải trỏ tới đúng glyph đích, và feature phải
   được bật cho **default LangSys của từng script bắt buộc** (`DFLT`, `latn`).
2. **Trên lưới** — mọi điểm là bội số của `pitch`.
3. **Đúng nhịp** — `advance == pitch × cols × số ký tự`.

Tầng 1 có hai ca false-pass đã gặp thật, cả hai đều đã dựng font để thử:

| ca | `hb-shape` mặc định | `hb-shape --script=latn` | cổng cũ | cổng mới |
|---|---|---|---|---|
| `liga` chỉ đăng ký dưới `DFLT` | có ligature | **không** | ĐẠT (sai) | KHÔNG ĐẠT |
| `liga` chỉ bật cho `latn/TRK`, không bật `latn` default | có ligature | **không** | ĐẠT (sai) | KHÔNG ĐẠT |

Cả hai đều qua được phép kiểm "lookup có nằm trong bảng GSUB". Phải đọc **`DefaultLangSys`
của từng script riêng biệt** — gộp `DefaultLangSys` với mọi `LangSysRecord` là bỏ lọt ca
thứ hai.

Bản cộng đồng fail tầng 2 và 3; bản `mergeFeature` thiếu `latn` fail tầng 1.

## Cơ chế đã xong

`src/vietfont/ligatures.py` + `--ligatures <pack.json>` cho cả `add` và `verify`:

- `LigaturePack` đọc `fonts/departure-mono-viet/ligatures.json` (26 quy tắc, sinh từ `legacy/ligatures.fea`);
- `add_ligatures()` copy glyph từ font nguồn, **snap mọi điểm về lưới**, đặt advance theo số ô,
  rồi gắn `liga` bằng `mergeFeature` — cách này **giữ nguyên 19 feature** còn lại, khác bản `legacy/`.

Đo trên bản dựng thử: 818 điểm được snap trên 24 glyph, 26 advance được sửa, và
`hb-shape --script=latn` ra ligature cho `== != ... ++ && **`.

## Vì sao chưa bật trong bản phát hành

Snap và sửa advance chỉ chữa **hình học**. Chúng không chữa câu thứ ba của maintainer —
*legibility inconsistencies*. Còn nguyên:

- `>=` và `<=` thiếu thành phần `=` (hỏng hẳn, không phải chuyện thẩm mỹ);
- `==`, `--`, `...` không đối xứng và không lấp đầy bề ngang advance;
- `**`, `***`, `****` nhìn rối ở cỡ nhỏ.

Nên `DepartureMonoViet-Regular.otf` **vẫn không có ligature**. Muốn bật thì phải vẽ lại
26 glyph cho đúng lưới và đúng nhịp, rồi duyệt bằng proof sheet — không phải chuyện snap.

## Cách bật khi glyph đã đạt

```bash
vietfont add <gốc> -o <ra> --marks marks.json --ligatures ligatures.json
vietfont verify <ra> --source <gốc> --marks marks.json --ligatures ligatures.json
```
