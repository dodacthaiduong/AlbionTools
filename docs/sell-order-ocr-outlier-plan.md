# Sell Order OCR Full-Region + Outlier Filter Plan

**Created:** 2026-05-22 (Asia/Saigon)  
**Status:** Planning / handoff for next coding session

---

## 1) Mục tiêu

Nâng cấp logic lấy `lowest sell price` để tránh bị kéo giá bởi 1-2 lệnh phá giá số lượng thấp.

### Hiện trạng
- Bot đang đọc **1 vùng giá** (`lowest_sell_order_price`) => chỉ có 1 số.
- Nếu có 1 lệnh bất thường (ví dụ 50,000) bot có thể hạ theo mức đó.

### Mục tiêu mới
- OCR **toàn bộ vùng danh sách sell order** (nhiều dòng).
- Parse theo dòng để lấy cặp **(price, quantity)**.
- Tính `effective_lowest_price` bằng rule lọc outlier theo số lượng + độ chênh.

---

## 2) Phạm vi thay đổi (proposed)

## A. Calibration / data model

### A1) Thêm region mới
- `sell_orders_table` (Rect): vùng chứa toàn bộ bảng sell orders.

### A2) File dự kiến sửa
- `bot/albion_bot/calibration/models.py`
  - thêm field `sell_orders_table: Optional[Rect] = None`
- `bot/albion_bot/gui/calibration_tab.py`
  - thêm key vào `_REGION_KEYS` để user select trên GUI
- `backend/internal/models/models.go`
  - thêm field trong `CalibrationRegions` để backend trả đúng schema

### A3) Backward compatibility
- Nếu calibration cũ chưa có `sell_orders_table`:
  - fallback về logic cũ (`lowest_sell_order_price`) để không crash.

---

## B. OCR parser cho order book

### B1) Tạo model nội bộ
Thêm dataclass/pydantic đơn giản trong `selling/price.py` hoặc module mới:

```python
class MarketOrderLevel(TypedDict):
    price: int
    quantity: int
```

### B2) API đọc full-region OCR
Đề xuất thêm trong `bot/albion_bot/ocr/reader.py`:

```python
def read_text_boxes(region: Rect) -> list[dict]:
    # return [{"text": str, "box": [[x,y],...], "score": float}, ...]
```

> Lưu ý: cần giữ tọa độ box để group theo hàng (Y-axis).

### B3) Parse theo dòng
Pipeline đề xuất:
1. OCR all boxes trong `sell_orders_table`
2. Chuẩn hóa text (remove spaces, commas OCR noise)
3. Group box theo trục Y thành từng dòng
4. Theo vị trí X (cột), tách trường `price` và `quantity`
5. Validate: `price > 0`, `quantity > 0`

### B4) Regex gợi ý
- Price: chuỗi số lớn, thường có `,` hoặc `.` phân tách
- Quantity: số nguyên dương, thường nhỏ hơn giá

Ví dụ helper:
```python
def parse_int_loose(s: str) -> int | None:
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None
```

---

## C. Thuật toán outlier filtering

## C1) Ý tưởng
Không dùng `min(price)` trực tiếp. Dùng `effective_lowest_price`:
- Nếu lệnh thấp nhất có `quantity` rất nhỏ **và** lệch quá xa so với mức kế tiếp => bỏ qua.
- Nếu mức thấp có lượng lớn (hoặc nhiều dòng gần mức đó) => chấp nhận hạ theo.

## C2) Config đề xuất (trong `bot_config`)
- `outlier_min_qty_to_trust` (int, default: `3`)
- `outlier_max_gap_pct` (float, default: `20.0`)
- `outlier_min_total_qty_nearby` (int, default: `5`)
- `outlier_nearby_band_pct` (float, default: `2.0`)

> Chưa cần UI ngay. Có thể đọc từ DB với default cứng, giống `is_premium` hiện tại.

## C3) Rule v1 (dễ code, dễ debug)
Giả sử danh sách đã sort tăng dần theo giá:
- `best = levels[0]`, `next = levels[1]` (nếu có)
- `gap_pct = (next.price - best.price) / next.price * 100`
- Nếu:
  - `best.quantity < outlier_min_qty_to_trust`
  - và `gap_pct > outlier_max_gap_pct`
  => xem `best` là outlier, chọn `next.price`
- Ngược lại dùng `best.price`

### C4) Rule v1.1 (nâng cấp nhẹ)
Nếu quanh `best.price` có tổng qty trong dải ±`outlier_nearby_band_pct` đủ lớn (`>= outlier_min_total_qty_nearby`) thì vẫn trust `best`.

---

## D. Integration vào pricing workflow

### D1) Hàm mới đề xuất
Trong `bot/albion_bot/selling/price.py`:
- `get_sell_order_levels_ocr(region) -> list[MarketOrderLevel]`
- `pick_effective_lowest_price(levels, settings) -> Optional[int]`
- `get_effective_lowest_sell_price(slot, market_city, regions, settings) -> Optional[int]`

### D2) Flow đề xuất
1. Nếu có `sell_orders_table`:
   - OCR full table -> parse levels -> pick effective lowest
2. Nếu fail hoặc levels rỗng:
   - fallback `lowest_sell_order_price` OCR cũ
3. Nếu vẫn fail:
   - fallback API như hiện tại

---

## E. Logging / observability

Thêm log để debug nhanh khi giá bị skip:
- Số levels parse được
- top 3 levels (`price@qty`)
- Lý do bỏ outlier (`qty thấp`, `gap cao`)
- Giá cuối cùng được chọn (`effective_lowest`)

Ví dụ:
```text
pricing levels: 50000@1, 98000@12, 99000@8
outlier detected: 50000@1 (gap=48.98% > 20%) -> using 98000
```

---

## 3) Checklist implementation (để code ngày mai)

- [ ] Add calibration region `sell_orders_table` (models + GUI + backend model)
- [ ] Add OCR box-level reader (`read_text_boxes`) in `ocr/reader.py`
- [ ] Implement row-grouping + parse `(price, quantity)`
- [ ] Implement outlier filter rule v1
- [ ] Add sell settings defaults + loader for outlier params
- [ ] Integrate effective price into `place_sell_order` flow
- [ ] Add fallback chain: full-table OCR -> old OCR -> API
- [ ] Add detailed debug logs
- [ ] Smoke test in real market UI with 3 scenarios (normal / one fake low / real downtrend)

---

## 4) Acceptance criteria

1. Nếu có 1 lệnh phá giá qty thấp (vd `50000 x 1`) nhưng mức kế tiếp gần market bình thường:
   - Bot **không** lấy 50,000 làm lowest hiệu lực.
2. Nếu mức giá thấp có qty lớn (hoặc nhiều level gần đó tổng qty lớn):
   - Bot chấp nhận hạ theo market mới.
3. Nếu OCR full-table fail:
   - Bot vẫn chạy bằng fallback cũ, không crash.
4. Không phá compatibility calibration cũ.

---

## 5) Test scenarios gợi ý

## S1: Normal market
- Levels: `99000x5`, `99500x6`, `100000x10`
- Kỳ vọng: dùng `99000`

## S2: Single fake low
- Levels: `50000x1`, `98000x10`, `98500x7`
- Kỳ vọng: bỏ `50000`, dùng `98000`

## S3: Real market dump
- Levels: `70000x25`, `70500x20`, `71000x18`
- Kỳ vọng: dùng `70000`

## S4: OCR noisy
- Parse ra 0-1 level hợp lệ
- Kỳ vọng: fallback old OCR/API

---

## 6) Ghi chú thiết kế

- Không cố định `scan_rows`: ưu tiên OCR toàn bộ vùng user chọn.
- `scan_rows` (nếu thêm) chỉ là guard hiệu năng optional, không phải bắt buộc.
- Nên parse bằng OCR boxes (tọa độ), tránh ghép text thô cả khối vì dễ lệch cột.

---

## 7) File map tham chiếu nhanh

- `bot/albion_bot/calibration/models.py`
- `bot/albion_bot/gui/calibration_tab.py`
- `backend/internal/models/models.go`
- `bot/albion_bot/ocr/reader.py`
- `bot/albion_bot/selling/price.py`
- `bot/albion_bot/selling/config.py`
- `bot/albion_bot/selling/market.py`

---

## 8) Mức ưu tiên

- **P0 (bắt buộc):** A + B + C(v1) + D + fallback + logging
- **P1 (nên có):** Rule v1.1 (nearby qty band)
- **P2 (để sau):** UI chỉnh outlier params trong Config tab
