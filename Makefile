# Makefile — Albion auto-seller project
# Run `make help` to see all available targets.

SHELL := /bin/bash
ROOT  := $(shell pwd)

# ── colours ──────────────────────────────────────────────────────────────────
CYAN  := \033[0;36m
NC    := \033[0m

.PHONY: help dev prod \
        frontend-install frontend-build frontend-dev \
        backend-run backend-build \
        bot-status bot-calibrate bot-gui bot-sell \
        logs clean

# ── default target ───────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  $(CYAN)Albion Auto-Seller$(NC) — available targets"
	@echo ""
	@echo "  Launch"
	@echo "    make dev          Start full stack in dev mode (ng serve + go run)"
	@echo "    make prod         Build frontend then start backend"
	@echo ""
	@echo "  Frontend"
	@echo "    make frontend-install   npm install"
	@echo "    make frontend-build     ng build (production)"
	@echo "    make frontend-dev       ng serve (port 4200)"
	@echo ""
	@echo "  Backend"
	@echo "    make backend-run        go run ./cmd/server"
	@echo "    make backend-build      go build -o server ./cmd/server"
	@echo ""
	@echo "  Bot"
	@echo "    make bot-status              Check MongoDB connection"
	@echo "    make bot-calibrate           Run calibration wizard"
	@echo "    make bot-gui                  Launch the desktop GUI"
	@echo "    make bot-sell                Start the selling loop"
	@echo ""
	@echo "  Misc"
	@echo "    make logs         Tail all log files"
	@echo "    make clean        Remove build artifacts and logs"
	@echo ""

# ── full stack ───────────────────────────────────────────────────────────────
dev:
	@chmod +x start.sh && ./start.sh --dev

prod:
	@chmod +x start.sh && ./start.sh

# ── frontend ─────────────────────────────────────────────────────────────────
frontend-install:
	cd frontend && npm install

frontend-build: frontend-install
	cd frontend && npm run build

frontend-dev: frontend-install
	cd frontend && npm start

# ── backend ──────────────────────────────────────────────────────────────────
backend-run:
	cd backend && go run ./cmd/server

backend-build:
	cd backend && go build -o server ./cmd/server

# ── bot ──────────────────────────────────────────────────────────────────────
bot-status:
	cd bot && uv run python main.py status

bot-calibrate:
	cd bot && uv run python main.py calibrate

bot-gui:
	cd bot && uv run python main.py gui

bot-sell:
	cd bot && uv run python main.py sell

# ── misc ─────────────────────────────────────────────────────────────────────
logs:
	@mkdir -p logs
	@tail -f logs/*.log 2>/dev/null || echo "No log files found yet. Start the stack first."

clean:
	rm -rf frontend/dist
	rm -rf backend/server
	rm -rf logs
	@echo "Clean complete."
