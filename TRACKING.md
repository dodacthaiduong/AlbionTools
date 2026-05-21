# TRACKING.md — Sell Order Refactor Log

## 2026-05-21

### Scope
Refactor bot từ quicksell (Sell Now) sang sell-order workflow, theo yêu cầu:
- OCR ưu tiên, fallback API để lấy giá sell thấp nhất
- Giá đặt theo bước 1000:
  - 191900 -> 191000
  - 191000 -> 190000
- Không đặt order nếu net revenue sau phí < cost_price
- Poll My Orders để nhận diện order đã khớp

### Implemented

#### 1) Data / config
- Đổi `min_sell_price` -> `cost_price` trong bot + backend + frontend API interface.
- Thêm global config trong Mongo collection `bot_config`:
  - `_id: "global"`
  - `is_premium: bool`
- Bot đọc setting bằng module mới:
  - `bot/albion_bot/selling/config.py`

#### 2) Calibration regions
- Xóa phụ thuộc `sell_now_button` khỏi flow mới.
- Đổi `buy_order_price` -> `lowest_sell_order_price`.
- Thêm regions mới cho sell-order:
  - `sell_order_price_input`
  - `sell_order_confirm_button`
  - `my_orders_tab`
  - `my_orders_list`
- Cập nhật calibration GUI list key ở:
  - `bot/albion_bot/gui/calibration_tab.py`
- Có compatibility alias để đọc calibration cũ:
  - `buy_order_price` -> `lowest_sell_order_price`

#### 3) Sell-order pricing engine
- Thêm module mới:
  - `bot/albion_bot/selling/price.py`
- Chức năng chính:
  - OCR giá thấp nhất
  - fallback API (albion-online-data)
  - tính giá đặt theo rule 1000
  - tính phí:
    - listing fee 2.5%
    - transaction fee 4% (premium) / 8% (non-premium)
  - chỉ cho phép đặt nếu `net_revenue >= cost_price`

#### 4) Market workflow
- Refactor toàn bộ:
  - `bot/albion_bot/selling/market.py`
- Thêm flow:
  - đặt sell order (`place_sell_order`)
  - kiểm tra open order đã khớp (`reconcile_filled_orders`)
- Lưu open orders vào collection `sell_orders`.
- Khi order khớp -> tạo transaction `filled`.

#### 5) Main loop
- Refactor:
  - `bot/albion_bot/selling/loop.py`
- Chu kỳ mới:
  1. Reconcile My Orders
  2. Scan inventory
  3. Đặt sell orders theo cost_price/is_premium
  4. Sort + stack
- Session stats mở rộng:
  - `orders_placed`
  - `orders_filled`

#### 6) Input backend
- Mở rộng InputBackend:
  - `type_text`
  - `hotkey`
- Implement cho Linux và Windows.

#### 7) Backend / frontend DTO
- Backend Go:
  - `UpdateMinSellPrice` -> `UpdateCostPrice`
  - payload PATCH đổi sang `cost_price`
  - model `ItemConfig` đổi field `cost_price`
  - update calibration region struct tương ứng
- Frontend TS interface:
  - `ItemConfig.min_sell_price` -> `cost_price`

### Validation
- Python compile:
  - `uv run --project ./bot python -m compileall ./bot/albion_bot` ✅
- Go build:
  - `go build ./...` (cwd `backend`) ✅
- Frontend build:
  - `npm run build` (cwd `frontend`) ✅
  - Có warning budget bundle (không phải lỗi compile)

### Notes / follow-up
- Theo phương án B: **chưa thêm UI cho `is_premium`**. Cấu hình qua DB (`bot_config`).
- Cần **recalibrate** các vùng mới trước khi chạy sell loop.
- Tài liệu chi tiết cũ (`docs/albion-auto-seller-plan.md`) chưa refactor toàn bộ nội dung legacy quicksell.

---

## 2026-05-22 (Next coding session handoff)

### Mục tiêu phiên kế tiếp
- Nâng cấp pricing từ đọc 1 giá sang OCR full-region order book.
- Lọc outlier theo quantity để tránh bị kéo giá bởi lệnh phá giá số lượng thấp.

### Tài liệu kế hoạch chính
- `docs/sell-order-ocr-outlier-plan.md`

### Checklist triển khai (P0 trước)
- [ ] Thêm calibration region `sell_orders_table`:
  - `bot/albion_bot/calibration/models.py`
  - `bot/albion_bot/gui/calibration_tab.py`
  - `backend/internal/models/models.go`
- [ ] Thêm OCR box-level reader (giữ tọa độ text box):
  - `bot/albion_bot/ocr/reader.py`
- [ ] Parse full table thành danh sách `(price, quantity)` theo từng dòng:
  - `bot/albion_bot/selling/price.py` (hoặc module phụ)
- [ ] Implement outlier rule v1:
  - bỏ giá thấp nhất nếu `qty` thấp + `gap` quá lớn với mức kế tiếp
- [ ] Mở rộng settings với default an toàn (DB `bot_config`):
  - `outlier_min_qty_to_trust=3`
  - `outlier_max_gap_pct=20.0`
- [ ] Integrate vào flow đặt giá:
  - ưu tiên `sell_orders_table` -> fallback `lowest_sell_order_price` -> fallback API
- [ ] Thêm debug logs giải thích quyết định giá (levels + lý do skip outlier)

### Acceptance test nhanh cần chạy
- [ ] S1 normal market: dùng mức thấp nhất hợp lệ.
- [ ] S2 1 lệnh phá giá qty thấp: bỏ outlier.
- [ ] S3 market dump thật (qty lớn): chấp nhận hạ theo.
- [ ] S4 OCR nhiễu/không parse đủ dữ liệu: fallback chain chạy bình thường.

### Ghi chú để đỡ quên khi code
- Không cố định `scan_rows`; ưu tiên OCR toàn vùng người dùng chọn.
- Nếu calibration cũ chưa có `sell_orders_table`, bot vẫn phải chạy được bằng logic cũ.
- Ưu tiên parser dựa trên OCR boxes + tọa độ (tránh join text thô toàn khối).
