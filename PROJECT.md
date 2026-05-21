# PROJECT.md — Albion Auto Seller

**Last updated:** 2026-05-21

---

## Project Purpose

Bot tự động bán đồ trên chợ Albion Online bằng cách mô phỏng chuột/bàn phím.
Hiện tại workflow chính là **sell order** (không còn quicksell Sell Now): bot đọc giá sell thấp nhất (OCR ưu tiên, fallback API), tính giá đặt theo rule bước 1000, và chỉ đặt order khi net revenue sau phí không thấp hơn `cost_price`.
Kèm theo dashboard web để xem lịch sử giao dịch và cấu hình `cost_price` cho từng vật phẩm.
Chạy trên Linux X11 (và Windows), dữ liệu lưu vào MongoDB local.

---

## Folder Structure

```
ProjectCode/
├── bot/                        # Python bot — logic chính
│   ├── main.py                 # Entry point của bot (CLI)
│   └── albion_bot/
│       ├── calibration/        # Wizard calibration, chụp màn hình, lưu vùng
│       ├── db/                 # Kết nối MongoDB
│       ├── gui/                # Giao diện đồ họa (tkinter)
│       ├── inventory/          # Quét kho đồ, model vật phẩm
│       ├── ocr/                # Đọc chữ/giá từ màn hình (PaddleOCR)
│       ├── platform/           # Điều khiển chuột (Linux X11 / Windows)
│       ├── selling/            # Vòng lặp bán hàng, logic thị trường
│       ├── debug_logger.py     # Module debug/logging trung tâm
│       └── logging_config.py   # Cấu hình logging (file + console)
├── backend/                    # Go API server
│   ├── cmd/server/main.go      # Entry point backend
│   └── internal/
│       ├── api/handlers.go     # Các route API REST
│       ├── db/repository.go    # Truy vấn MongoDB
│       ├── models/models.go    # Struct dữ liệu
│       └── websocket/hub.go    # WebSocket hub
├── frontend/                   # Angular 18 dashboard
│   └── src/                    # Source code Angular
├── docs/                       # Tài liệu, ảnh tham khảo
│   ├── installation.md         # Hướng dẫn cài đặt chi tiết
│   └── albion-auto-seller-plan.md  # Kế hoạch và yêu cầu chức năng
├── logs/                       # Log runtime (tự tạo, không commit)
├── Makefile                    # Lệnh tắt để chạy project
├── start.sh                    # Script khởi động toàn bộ stack
├── README.md                   # Hướng dẫn sử dụng
└── .gitignore
```

---

## Key Files

| File | Mô tả |
|---|---|
| `bot/main.py` | CLI entry point — các lệnh: `sell`, `gui`, `calibrate`, `status` |
| `bot/albion_bot/selling/loop.py` | Vòng lặp sell-order chính |
| `bot/albion_bot/selling/market.py` | Logic đặt sell order + reconcile order đã khớp |
| `bot/albion_bot/selling/price.py` | Logic lấy giá thấp nhất (OCR/API), tính giá đặt và phí |
| `bot/albion_bot/selling/config.py` | Đọc global config (`is_premium`) từ MongoDB |
| `bot/albion_bot/inventory/scanner.py` | Quét từng ô kho đồ bằng OCR |
| `bot/albion_bot/ocr/reader.py` | Đọc chữ và giá từ màn hình |
| `bot/albion_bot/calibration/wizard.py` | Lưu calibration vào MongoDB |
| `bot/albion_bot/debug_logger.py` | Hệ thống debug/logging trung tâm |
| `backend/cmd/server/main.go` | Khởi động Go server, kết nối MongoDB, đăng ký routes |
| `backend/internal/api/handlers.go` | Xử lý các API request |
| `backend/internal/db/repository.go` | Truy vấn MongoDB |
| `Makefile` | Tất cả lệnh chạy project |

---

## Entry Points

| Thành phần | Lệnh khởi động |
|---|---|
| Bot | `cd bot && uv run python main.py sell` hoặc `make bot-sell` |
| Backend | `cd backend && go run ./cmd/server` hoặc `make backend-run` |
| Frontend | `cd frontend && npm start` hoặc `make frontend-dev` |
| Toàn bộ stack | `make dev` |

---

## Config Files

| File | Mô tả |
|---|---|
| `Makefile` | Biến `PORT` (mặc định 8080), `LAN=true` để mở LAN |
| Biến môi trường | `DEBUG=true/false` — bật/tắt debug logging |
| `backend/cmd/server/main.go` | `MONGO_URI`, `MONGO_DB`, `PORT`, `LAN` qua env vars |

Không có file `.env` — cấu hình qua biến môi trường trực tiếp.

---

## Dependencies

**Python (bot):**
- `paddleocr` — OCR đọc chữ từ màn hình
- `mss` — chụp màn hình
- `pymongo` — kết nối MongoDB
- `pydantic` — validation dữ liệu
- `click` — CLI
- `python-xlib` — điều khiển chuột Linux
- `pydirectinput` — điều khiển chuột Windows

**Go (backend):**
- `gin-gonic/gin` — HTTP framework
- `spf13/viper` — đọc config từ env
- `go.mongodb.org/mongo-driver/v2` — MongoDB driver

**Frontend:**
- `Angular 18` + Angular Material
- `chart.js` + `ng2-charts`

---

## Ignore List (không bao giờ đọc)

- `bot/.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/.angular/`
- `bot/albion_bot/**/__pycache__/`
- `logs/`
- `.git/`
