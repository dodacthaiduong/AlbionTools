# Albion Auto Seller

Bot tự động bán đồ trên chợ Albion Online bằng cách mô phỏng chuột/bàn phím, kèm dashboard web để theo dõi giao dịch và cấu hình giá.

---

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Bot | Python 3.11+, mss, PaddleOCR, pymongo, click, pydantic |
| Input (Linux) | python-xlib |
| Input (Windows) | pydirectinput |
| Backend | Go 1.22+, gin-gonic, viper |
| Frontend | Angular 18, Angular Material, chart.js |
| Database | MongoDB 7+ (local, port 27017) |

---

## Yêu cầu cài đặt

### MongoDB 7+

**Ubuntu / Debian:**
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

**Windows:** Tải tại https://www.mongodb.com/try/download/community, bật "Install MongoDB as a Service".

### Python 3.11+ với uv

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # hoặc ~/.bashrc
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Go 1.22+

```bash
wget https://go.dev/dl/go1.22.4.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.4.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.zshrc
source ~/.zshrc
```

**Windows:** Tải installer tại https://go.dev/dl/

### Node.js 20+ và Angular CLI

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install 20
npm install -g @angular/cli@18
```

---

## Cài đặt nhanh

```bash
git clone https://github.com/dodacthaiduong/AlbionTools.git
cd AlbionTools

# Chạy toàn bộ stack (dev mode)
make dev
```

Hoặc chạy từng phần riêng:

```bash
make frontend-dev    # Angular dev server tại http://localhost:4200
make backend-run     # Go backend tại http://localhost:8080
```

---

## Cách dùng bot

**Bước 1 — Calibration** (chỉ cần làm 1 lần):
```bash
make bot-gui
```
Mở giao diện đồ họa để khoanh vùng các khu vực trên màn hình (nút bán, ô giá, kho đồ...).

**Bước 2 — Đặt giá tối thiểu:**

Mở dashboard tại `http://localhost:8080` → vào trang **Config** → đặt giá tối thiểu cho từng vật phẩm.

**Bước 3 — Chạy bot:**
```bash
make bot-sell
```
Bot sẽ tự động quét kho, tìm lệnh mua phù hợp và bán. Nhấn `Ctrl+C` để dừng.

---

## Các lệnh make

| Lệnh | Mô tả |
|---|---|
| `make dev` | Chạy toàn bộ stack ở dev mode |
| `make prod` | Build frontend rồi chạy backend |
| `make bot-gui` | Mở giao diện calibration |
| `make bot-sell` | Bắt đầu vòng lặp bán hàng |
| `make bot-calibrate` | Chạy wizard calibration (CLI) |
| `make bot-status` | Kiểm tra kết nối MongoDB |
| `make logs` | Xem log realtime |
| `make clean` | Xóa build artifacts và logs |

---

## Debug Mode

Bật log chi tiết bằng cách đặt biến môi trường `DEBUG=true`:

```bash
DEBUG=true make bot-sell
```

Log sẽ được ghi ra file `debug.log` trong thư mục hiện tại. Khi có lỗi, bot tự động tạo báo cáo lỗi đầy đủ để dễ dàng báo cáo.

---

## Cấu trúc thư mục

```
AlbionTools/
├── bot/          # Python bot (OCR, input simulation, selling logic)
├── backend/      # Go API server
├── frontend/     # Angular dashboard
├── docs/         # Tài liệu cài đặt và ảnh tham khảo
├── Makefile      # Lệnh tắt
└── start.sh      # Script khởi động stack
```

---

## Tài liệu thêm

- [Hướng dẫn cài đặt chi tiết](docs/installation.md)
