# Installation Guide

## Prerequisites

### MongoDB 7+ Community

**Ubuntu / Debian:**
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

**Windows:**
Download and install from https://www.mongodb.com/try/download/community
Enable "Install MongoDB as a Service" during setup.

Verify: `mongosh --eval "db.runCommand({ connectionStatus: 1 })"`

---

### Python 3.11+ with uv

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # or ~/.bashrc
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### Go 1.22+

**Linux:**
```bash
# Download from https://go.dev/dl/ and follow official instructions
wget https://go.dev/dl/go1.22.4.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.4.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.zshrc
source ~/.zshrc
```

**Windows:** Download installer from https://go.dev/dl/

---

### Node.js 20+ and Angular CLI

```bash
# Install Node.js via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install 20
npm install -g @angular/cli@18
```

---

## Running the Project

### Bot
```bash
cd bot
uv sync
uv run python -m albion_bot --help
```

### Backend
```bash
cd backend
go run ./cmd/server
```

### Frontend
```bash
cd frontend
npm install
ng serve
```
