# Albion Auto Seller

## Context & Objectives
Automate selling items on Albion Online market via mouse/keyboard simulation. Single-user per machine (personal + friends). Linux X11 + Windows. Web dashboard for config and monitoring.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot | Python 3.11+ |
| Screen capture | `mss` |
| Image processing | `opencv-python` |
| OCR | PaddleOCR (English model, pure ASCII input) |
| Input simulation | `python-xlib` (Linux) / `pydirectinput` (Windows) |
| DB client | `pymongo` |
| CLI | `click` |
| Validation | `pydantic` |
| Backend | Go 1.22+ with `gin-gonic/gin` |
| WebSocket | `gorilla/websocket` |
| Config | `spf13/viper` |
| Frontend | Angular 18 (pinned), Angular Material, dark theme |
| i18n | `ngx-translate` (VI/EN, stored in localStorage) |
| Charts | `chart.js` + `ng2-charts` |
| Database | MongoDB 7+ Community, local, port 27017 |

---

## Functional Requirements

- **FR-1 Calibration (CLI wizard)**
  - User selects regions for: first/last inventory cell, sell button, buy order price area, item name area, disconnect icon, popup close button, sort button, stack button
  - User inputs grid layout (rows × cols, default 8×6 = 48 slots)
  - Saved to MongoDB `calibrations` collection + JSON backup

- **FR-2 Inventory Scan**
  - Bot clicks each slot → item detail panel appears (auto-switches on each click, no dismiss needed)
  - OCR reads from panel: name, tier, enchant, quality, quantity, estimated price
  - Empty slots detected by pixel color (calibrated during FR-1)
  - Data saved to `item_configs` with `min_sell_price = null`
  - User fills `min_sell_price` via web dashboard

- **FR-3 Selling Loop**
  - **Phase 1 — Scan all 48 slots**, collect item data (skip empty slots)
  - **Phase 2 — For each item collected:**
    1. Open market sell interface
    2. Apply filters: name, type, tier, enchant (quality handled automatically by game)
    3. Sort by price descending
    4. Find first order with **red sell button** (= item meets order conditions)
    5. Read price via OCR
    6. If price ≥ `min_sell_price` → click sell → log transaction (quantity, unit price, total)
    7. If price < `min_sell_price` → close sell interface → next item
  - **Phase 3:** Click Sort + Stack buttons
  - **Repeat from Phase 1**
  - Random mouse jitter on movement; random ±3–5px offset per click
  - Quantity sold = maximum the market will buy at that price

- **FR-4 Quality Logic**
  - Bot does NOT select quality — the game auto-selects it when a red sell button is available
  - Red button = item meets buyer's conditions; black button = does not meet conditions
  - Bot only interacts with red-button orders

- **FR-5 Error Handling**
  - Disconnect icon detected → pause → poll until icon disappears → auto-resume
  - Sell fail popup → click close → skip item → continue
  - Market lag → wait 5s → retry (unlimited retries)
  - Other errors → pause + log → wait for user

- **FR-6 Bot Control**
  - Start/Stop from CLI
  - *(Phase 2)* Start/Stop from web dashboard

- **FR-7 Web Dashboard**
  - Dark mode, VI/EN switcher in header
  - No login required (localhost by default; `--lan` flag for LAN access)
  - Pages: Dashboard (overview), Transactions (history + CSV export), Inventory (snapshot), Config (item list + min_sell_price editor), Bot Status (live via WebSocket)

- **FR-8 Logging**
  - Log successful transactions only
  - Permanent storage
  - CSV export

---

## Non-Functional Requirements

| Type | Requirement |
|---|---|
| Performance | 1 cycle (48 slots): 30–60s |
| Security | No login, localhost-first |
| Availability | On-demand only (no auto-start) |
| Platform | Linux X11 + Windows |
| RAM | < 1GB total |
| Storage | MongoDB local, ~1GB for years of logs |
| OCR input | Pure ASCII (English item names and prices only) |

---

## Business Rules & Logic

- `min_sell_price` is set per item config by the user; null = item not configured = skip
- Bot only sells if `current_best_price ≥ min_sell_price`
- Quality selection is fully automatic by the game; bot ignores quality selector
- Red sell button = sellable; black sell button = skip that order, check next
- Quantity = max the market will buy at that price (read from sell dialog)
- Market city is detected via OCR from the UI at sell time
- Sort + Stack is performed after every full sell cycle (not per item)
- Inventory scan always precedes sell phase in each cycle

---

## Architecture

- **Bot (Python):** Platform abstraction layer → screen capture → OCR → selling logic → calibration CLI → writes directly to MongoDB
- **Backend (Go):** REST API + WebSocket server → reads MongoDB → serves static Angular frontend on port 8080
- **Frontend (Angular):** Dashboard UI → communicates with Go backend via HTTP + WebSocket
- **MongoDB (local):** Single source of truth; bot writes, backend reads
- **Bot ↔ Backend communication:** Bot writes to MongoDB; backend reads. Config changes take effect at next cycle (no IPC needed)
- **Install script scope:** Minimal — installs app dependencies only. MongoDB installation documented separately in `docs/installation.md`

---

## Database Schema

```javascript
// calibrations
{
  _id: ObjectId,
  profile_name: "default",
  platform: "linux-x11" | "windows",
  screen: { width: 1920, height: 1080 },
  inventory: {
    rows: 8, cols: 6,
    first_cell: { x, y, w, h },
    last_cell: { x, y, w, h },
    cells: [{ index: 0, x, y }]  // 48 computed cells
  },
  regions: {
    sell_now_button: { x, y, w, h },
    buy_order_price: { x, y, w, h },
    tooltip_item_name: { x, y, w, h },
    tooltip_est_price: { x, y, w, h },
    disconnect_icon: { x, y, w, h },
    popup_close: { x, y, w, h },
    sort_button: { x, y, w, h },
    stack_button: { x, y, w, h },
    empty_slot_sample: { x, y, w, h }  // pixel color reference for empty detection
  },
  created_at: ISODate,
  updated_at: ISODate
}

// item_configs
// Index: { base_name: 1, tier: 1, enchant: 1 } unique
{
  _id: ObjectId,
  base_name: "Adept's Leather Bag",
  full_name: "Adept's Leather Bag",
  tier: 4,           // 1–8
  enchant: 0,        // 0–4
  estimated_price: 15000,
  min_sell_price: null,  // null = not configured = skip
  enabled: true,
  last_scanned_at: ISODate,
  created_at: ISODate,
  updated_at: ISODate
}

// transactions
// Index: { timestamp: -1 }, { session_id: 1 }
{
  _id: ObjectId,
  timestamp: ISODate,
  session_id: ObjectId,
  item: {
    config_id: ObjectId,
    full_name: "Adept's Leather Bag",
    tier: 4,
    enchant: 0
  },
  quantity: 5,
  unit_price: 16500,
  total_price: 82500,
  market_city: "Caerleon",  // OCR'd from UI
  status: "success"
}

// inventory_snapshots
// Index: { timestamp: -1 }
// Taken after each full cycle
{
  _id: ObjectId,
  timestamp: ISODate,
  session_id: ObjectId,
  items: [{
    slot: 0,
    config_id: ObjectId,
    full_name: "Adept's Leather Bag",
    tier: 4,
    enchant: 0,
    quantity: 247
  }],
  empty_slots: 12,
  total_estimated_value: 1250000
}

// bot_sessions
{
  _id: ObjectId,
  started_at: ISODate,
  ended_at: ISODate,
  status: "running" | "paused" | "stopped" | "error",
  stop_reason: "user_requested" | "disconnect" | "error",
  stats: {
    cycles_completed: 42,
    items_sold: 156,
    total_revenue: 2500000,
    errors_count: 3
  },
  calibration_id: ObjectId
}

// error_logs (optional, for debug)
{
  _id: ObjectId,
  timestamp: ISODate,
  session_id: ObjectId,
  level: "warning" | "error",
  event: "disconnect_detected" | "ocr_failed" | "market_lag",
  details: {},
  screenshot_path: "/path/to/screenshot.png"
}
```

---

## Key Decisions & Rationale

| Decision | Reason |
|---|---|
| Python for bot | Best ecosystem for screen capture + OCR + input simulation |
| Go for backend | Fast, lightweight HTTP server; good MongoDB driver |
| Angular 18 (pinned) | Stable LTS; Angular 19 has breaking changes |
| PaddleOCR English model | All item names/prices are pure ASCII |
| MongoDB local | Simple, no network dependency, sufficient for single-user |
| No login on dashboard | Localhost-only by default; LAN flag available |
| Bot writes directly to MongoDB | No IPC needed; config changes take effect next cycle |
| Minimal install script | MongoDB setup varies too much per OS; documented separately |
| Quality ignored by bot | Game auto-selects quality when red sell button is available |
| Red/black button detection | Pixel color check (faster and more reliable than OCR for color) |
| Scan-then-sell two-phase loop | Cleaner separation; avoids re-opening detail panel during sell phase |
| `pydirectinput` on Windows | Less detectable than `pyautogui` by EAC |

---

## Constraints & Out of Scope

**Constraints:**
- Game runs in windowed mode (resolution chosen by player)
- Calibration must be re-run if game UI changes
- Bot is single-account, single-machine

**Out of Scope (Phase 2+):**
- Notifications (Telegram/Discord)
- Multi-account support
- Bot control from web dashboard
- Advanced anti-detection (sleep schedules, long pauses)
- macOS support
- Wayland support

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Account banned by EAC/anti-cheat | High | Critical | Use secondary account; mouse jitter + random offsets; document risk for user |
| OCR misreads price → sells at loss | Medium | High | Double-read OCR; regex validation; `min_sell_price` as safety net |
| Calibration drifts after game UI update | Medium | Medium | Fast recalibrate CLI; versioned calibration profiles |
| Windows EAC detects input injection | High | High | Use `pydirectinput`; warn user Windows is higher risk |
| Disconnect mid-operation | Medium | Low | Detect disconnect icon; pause/resume state machine |
| MongoDB crash loses data | Low | Medium | Periodic backup script; MongoDB journaling |
| Tooltip OCR unstable (animation/transparency) | Medium | High | Retry OCR; multi-frame consensus |
| User sets wrong `min_sell_price` → sells at loss | Low | High | Warn if `min_sell_price` < 50% of `estimated_price` |
| Cross-platform bugs | High | Medium | Platform abstraction layer; test both OS |
| Cycle > 60s (performance) | Medium | Low | Profile + optimize; skip empty slots by pixel color |

---

## Open Questions

None. All design questions resolved. Sell flow UI screenshots partially provided (item detail panel confirmed). Full market sell interface screenshots available from earlier discussion.

**Ready to begin Milestone 0 (project setup).**
