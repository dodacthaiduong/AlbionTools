## User

Please read [@albion-auto-seller-plan.md](file:///home/durond/ProjectCode/albion-auto-seller-plan.md)  and give your opinion on what additional information is still needed to start the project.

## Assistant

Let me read the full plan file.

**Tool Call: Read albion-auto-seller-plan.md**
Status: Completed

```
1	# Albion Auto Seller — Kế Hoạch Dự Án
2	
3	---
4	
5	## 📋 1. Requirements Summary
6	
7	### Thông tin project
8	
9	| Trường | Giá trị |
10	|---|---|
11	| **Tên dự kiến** | Albion Auto Seller *(có thể đổi)* |
12	| **Mục đích** | Tự động bán vật phẩm trên market Albion Online qua giả lập chuột/phím |
13	| **User** | Cá nhân + bạn bè (mỗi user 1 máy độc lập) |
14	| **Platform** | Linux (X11) + Windows |
15	
16	---
17	
18	### Functional Requirements
19	
20	#### FR-1: Calibration (CLI wizard trong bot)
21	- User kéo chọn region cho: 2 ô inventory đầu-cuối, nút Sell Now, vùng giá buy order, vùng tên item, icon disconnect, popup close button, nút Sort, nút Stack
22	- User nhập grid layout inventory (rows × cols, mặc định 8×6)
23	- Lưu calibration vào MongoDB + file backup JSON
24	
25	#### FR-2: Auto-scan Inventory (tool riêng)
26	- Bot click qua từng ô có item, OCR tooltip
27	- Extract: tên, tier, enchant, quality, giá EST (từ game)
28	- Lưu vào collection `item_configs` với `min_sell_price = null`
29	- User điền `min_sell_price` sau qua web dashboard
30	
31	#### FR-3: Bot Selling Loop
32	- Scan 48 ô inventory, skip ô trống (detect bằng pixel color)
33	- Mỗi ô có item: click tooltip → OCR → lookup config
34	- Nếu có `min_sell_price`: click Sell Now → OCR giá buy order → bán nếu giá ≥ min
35	- Bấm Sort + Stack sau mỗi vòng
36	- **Quality logic**: bot chỉ bán khi `item_quality ≥ buy_order_quality` (đã chốt trước đó)
37	- Random mouse jitter khi di chuyển
38	- Random offset ±3–5 pixel cho mỗi click
39	
40	#### FR-4: Error Handling
41	- **Disconnect**: detect icon → pause → poll check icon biến mất → auto resume
42	- **Sell fail popup**: click close → skip item → tiếp tục
43	- **Market lag**: đợi 5s → retry, không giới hạn số lần
44	- **Errors khác**: pause + log, chờ user
45	
46	#### FR-5: Bot Control
47	- Start/Stop từ CLI của bot
48	- *(Phase 2)* Start/Stop từ web dashboard
49	
50	#### FR-6: Web Dashboard
51	- Dark mode
52	- Đa ngôn ngữ VI/EN (switcher ở header, lưu localStorage)
53	- Không cần login (localhost only by default, `--lan` flag để LAN access)
54	- **Trang**: Dashboard (tổng quan), Transactions (lịch sử + export CSV), Inventory (snapshot hiện tại), Config (danh sách item + min_sell_price), Bot Status
55	
56	#### FR-7: Logging
57	- Chỉ log giao dịch thành công
58	- Log vĩnh viễn
59	- Export CSV
60	
61	---
62	
63	### Non-Functional Requirements
64	
65	| Loại | Yêu cầu |
66	|---|---|
67	| Hiệu năng | 1 cycle 48 ô: 30–60s (giới hạn OCR) |
68	| Bảo mật | Không login, localhost-first |
69	| Khả dụng | Bot chạy on-demand (không tự start) |
70	| Cross-platform | Linux X11 + Windows |
71	| RAM | < 1GB tổng hệ thống |
72	| Lưu trữ | MongoDB local, ~1GB cho vài năm log |
73	
74	---
75	
76	### Out of Scope (Phase 2+)
77	
78	- Notification (Telegram/Discord)
79	- Multi-account
80	- Điều khiển bot từ web
81	- Advanced anti-detection (lịch ngủ, pause dài)
82	- macOS support
83	- Wayland support
84	
85	---
86	
87	## 🏗️ 2. Architecture
88	
89	```
90	┌────────────────────────────────────────────────┐
91	│  Máy User (Linux X11 / Windows)                │
92	│                                                │
93	│  ┌────────────────┐                            │
94	│  │ Albion Online  │◄─── input (xdotool/        │
95	│  │ Game Client    │      pyautogui)             │
96	│  └───────┬────────┘                            │
97	│          │ screen capture (mss)                │
98	│          ▼                                     │
99	│  ┌──────────────────────┐                      │
100	│  │ Bot Agent (Python)   │                      │
101	│  │ ┌──────────────────┐ │                      │
102	│  │ │ Platform Layer   │ │  ← abstraction       │
103	│  │ │ (linux/windows)  │ │                      │
104	│  │ └──────────────────┘ │                      │
105	│  │ ┌──────────────────┐ │                      │
106	│  │ │ OCR Engine       │ │  ← PaddleOCR         │
107	│  │ │ (image + text)   │ │                      │
108	│  │ └──────────────────┘ │                      │
109	│  │ ┌──────────────────┐ │                      │
110	│  │ │ Selling Logic    │ │                      │
111	│  │ └──────────────────┘ │                      │
112	│  │ ┌──────────────────┐ │                      │
113	│  │ │ Calibration CLI  │ │                      │
114	│  │ └──────────────────┘ │                      │
115	│  └──────────┬───────────┘                      │
116	│             │ pymongo                           │
117	│             ▼                                   │
118	│  ┌──────────────────────┐                      │
119	│  │ MongoDB (local)      │                      │
120	│  │ :27017               │                      │
121	│  └──────────┬───────────┘                      │
122	│             │ mongo-driver                      │
123	│             ▼                                   │
124	│  ┌──────────────────────┐                      │
125	│  │ Backend (Go + Gin)   │  :8080               │
126	│  │ - REST API           │                      │
127	│  │ - WebSocket (live)   │                      │
128	│  │ - Serve static FE    │                      │
129	│  └──────────┬───────────┘                      │
130	│             │ HTTP                              │
131	│             ▼                                   │
132	│  ┌──────────────────────┐                      │
133	│  │ Angular Dashboard    │                      │
134	│  │ (static files)       │                      │
135	│  └──────────────────────┘                      │
136	│                                                │
137	│  Browser: http://localhost:8080                │
138	└────────────────────────────────────────────────┘
139	```
140	
141	### Tech Stack
142	
143	#### Bot (Python 3.11+)
144	
145	| Package | Mục đích |
146	|---|---|
147	| `mss` | Screen capture (cross-platform, fast) |
148	| `opencv-python` | Image processing, template matching |
149	| `paddleocr` | OCR engine (tiếng Anh) |
150	| `pyautogui` + `pynput` | Input simulation (fallback) |
151	| `python-xlib` / `pydirectinput` | Native input (Linux / Windows) |
152	| `pymongo` | MongoDB client |
153	| `click` | CLI framework |
154	| `pydantic` | Data validation |
155	
156	#### Backend (Go 1.22+)
157	
158	| Package | Mục đích |
159	|---|---|
160	| `gin-gonic/gin` | HTTP framework |
161	| `go.mongodb.org/mongo-driver` | MongoDB |
162	| `gorilla/websocket` | WebSocket |
163	| `spf13/viper` | Config |
164	
165	#### Frontend (Angular 17+)
166	
167	| Package | Mục đích |
168	|---|---|
169	| Angular Material / PrimeNG | UI components (dark theme) |
170	| `ngx-translate` | i18n VI/EN |
171	| `chart.js` + `ng2-charts` | Biểu đồ |
172	| `rxjs` | WebSocket stream |
173	
174	#### Database
175	
176	**MongoDB 7+ (Community Edition)**
177	
178	---
179	
180	## 🗄️ 3. Database Schema (MongoDB)
181	
182	### Collection: `calibrations`
183	
184	```javascript
185	{
186	  _id: ObjectId,
187	  profile_name: "default",
188	  platform: "linux-x11" | "windows",
189	  screen: { width: 1920, height: 1080 },
190	  inventory: {
191	    rows: 8,
192	    cols: 6,
193	    first_cell: { x: 820, y: 650, w: 60, h: 60 },
194	    last_cell:  { x: 1180, y: 1070, w: 60, h: 60 },
195	    cells: [{ index: 0, x: 850, y: 680 }, ...]  // computed: array 48 cells
196	  },
197	  regions: {
198	    sell_now_button:    { x, y, w, h },
199	    buy_order_price:    { x, y, w, h },
200	    tooltip_item_name:  { x, y, w, h },
201	    tooltip_est_price:  { x, y, w, h },
202	    disconnect_icon:    { x, y, w, h },
203	    popup_close:        { x, y, w, h },
204	    sort_button:        { x, y, w, h },
205	    stack_button:       { x, y, w, h }
206	  },
207	  created_at: ISODate,
208	  updated_at: ISODate
209	}
210	```
211	
212	### Collection: `item_configs`
213	
214	```javascript
215	{
216	  _id: ObjectId,
217	  base_name:        "Adept's Leather Bag",  // tên không có tier/enchant
218	  full_name:        "Adept's Leather Bag",  // tên đầy đủ OCR được
219	  tier:             4,                       // 1–8
220	  enchant:          0,                       // 0–4
221	  quality:          null,                    // null = bán mọi quality
222	  estimated_price:  15000,                   // từ game OCR
223	  min_sell_price:   null,                    // user nhập sau
224	  enabled:          true,
225	  last_scanned_at:  ISODate,
226	  created_at:       ISODate,
227	  updated_at:       ISODate
228	}
229	// Index: { base_name: 1, tier: 1, enchant: 1 } unique
230	```
231	
232	### Collection: `transactions`
233	
234	```javascript
235	{
236	  _id: ObjectId,
237	  timestamp:  ISODate,
238	  session_id: ObjectId,
239	  item: {
240	    config_id: ObjectId,
241	    full_name: "Adept's Leather Bag",
242	    tier:      4,
243	    enchant:   0,
244	    quality:   3
245	  },
246	  quantity:    5,
247	  unit_price:  16500,
248	  total_price: 82500,
249	  market_city: "Caerleon",
250	  status:      "success"   // chỉ log success theo yêu cầu
251	}
252	// Index: { timestamp: -1 }, { session_id: 1 }
253	```
254	
255	### Collection: `inventory_snapshots`
256	
257	```javascript
258	{
259	  _id: ObjectId,
260	  timestamp:  ISODate,
261	  session_id: ObjectId,
262	  items: [
263	    {
264	      slot:      0,
265	      config_id: ObjectId,
266	      full_name: "Adept's Leather Bag",
267	      tier:      4,
268	      enchant:   0,
269	      quality:   3,
270	      quantity:  247
271	    }
272	  ],
273	  empty_slots:            12,
274	  total_estimated_value:  1250000
275	}
276	// Index: { timestamp: -1 }
277	// Strategy: snapshot sau mỗi vòng để track inventory over time
278	```
279	
280	### Collection: `bot_sessions`
281	
282	```javascript
283	{
284	  _id:        ObjectId,
285	  started_at: ISODate,
286	  ended_at:   ISODate,
287	  status:     "running" | "paused" | "stopped" | "error",
288	  stop_reason: "user_requested" | "disconnect" | "error",
289	  stats: {
290	    cycles_completed: 42,
291	    items_sold:       156,
292	    total_revenue:    2500000,
293	    errors_count:     3
294	  },
295	  calibration_id: ObjectId
296	}
297	```
298	
299	### Collection: `error_logs` *(tùy chọn, để debug)*
300	
301	```javascript
302	{
303	  _id:        ObjectId,
304	  timestamp:  ISODate,
305	  session_id: ObjectId,
306	  level:      "warning" | "error",
307	  event:      "disconnect_detected" | "ocr_failed" | "market_lag",
308	  details:    { /* any */ },
309	  screenshot_path: "/path/to/screenshot.png"
310	}
311	```
312	
313	---
314	
315	## 🗓️ 4. Roadmap / Milestones
316	
317	### Milestone 0: Project Setup *(1–2 ngày)*
318	- Khởi tạo repo, cấu trúc thư mục
319	- Setup Python venv, Go mod, Angular project
320	- Docker Compose cho MongoDB dev
321	- Install scripts cho Linux + Windows
322	- README + contributing guide
323	
324	### Milestone 1: Core Bot Infrastructure *(3–5 ngày)*
325	- Platform abstraction layer (Linux X11 + Windows)
326	- Screen capture module (mss)
327	- Input simulation module với mouse jitter + random offset
328	- OCR module (PaddleOCR wrapper)
329	- Calibration CLI wizard
330	- MongoDB connection + models
331	- Test manual trên 2 OS
332	
333	### Milestone 2: Backend API + Database *(2–3 ngày)*
334	- Go server với Gin
335	- MongoDB models + repositories
336	- REST API cho: calibrations, item_configs (CRUD), transactions (read), snapshots (read), sessions
337	- WebSocket cho live status
338	- Serve static Angular
339	
340	### Milestone 3: Web Dashboard *(4–5 ngày)*
341	- Angular project với Material + dark theme
342	- i18n setup VI/EN
343	- Trang Dashboard (charts + stats)
344	- Trang Transactions (table + filter + export CSV)
345	- Trang Inventory (snapshot view)
346	- Trang Config (item list + edit min_sell_price)
347	- Trang Bot Status (live via WebSocket)
348	
349	### Milestone 4: Selling Logic *(5–7 ngày)* — **Phần khó nhất**
350	- Scan inventory: detect ô trống, detect item
351	- Tooltip parsing: OCR tên, tier, enchant, quality, EST price
352	- Auto-scan tool: quét và lưu vào `item_configs`
353	- Selling loop: click Sell Now, OCR giá, so sánh, bán/skip
354	- Quality logic đầy đủ
355	- Error handling cơ bản (disconnect, popup, lag)
356	- Session management + transaction logging
357	- Inventory snapshot sau mỗi vòng
358	
359	### Milestone 5: Integration + Testing *(3–4 ngày)*
360	- Test end-to-end trên Linux X11
361	- Test end-to-end trên Windows
362	- Fine-tune delay, jitter, retry
363	- Bug fixing
364	- User docs (hướng dẫn cài đặt, calibrate, config)
365	
366	### Milestone 6: Polish *(2–3 ngày)*
367	- Install script hoàn thiện
368	- Error messages rõ ràng
369	- Dashboard UX polish
370	- Performance optimization
371	- Release v1.0
372	
373	> **Tổng ước tính: ~3–4 tuần full-time cho 1 developer**
374	
375	---
376	
377	## ⚠️ 5. Risk Register
378	
379	| # | Rủi ro | Khả năng | Tác động | Mitigation |
380	|---|---|---|---|---|
381	| R1 | Account bị ban bởi EAC/Sandbox | **Cao** | **Nghiêm trọng** | Account phụ, mouse jitter, random offset; document rủi ro cho user |
382	| R2 | OCR đọc sai giá → bán lỗ | Trung bình | Cao | Double-read (OCR 2 lần), validation regex, min_sell_price làm safety net |
383	| R3 | Calibration lệch khi game update UI | Trung bình | Trung bình | CLI recalibrate nhanh, versioning calibration |
384	| R4 | Windows + EAC detect input injection | Cao | Cao | Dùng `pydirectinput` (ít bị detect hơn pyautogui); cảnh báo user Windows rủi ro cao hơn |
385	| R5 | Game disconnect mất thao tác dở | Trung bình | Thấp | Detect icon disconnect, state machine pause/resume |
386	| R6 | MongoDB crash mất data | Thấp | Trung bình | Backup định kỳ (script), MongoDB journal |
387	| R7 | Tooltip OCR không ổn định (chữ animation/transparent) | Trung bình | Cao | Retry OCR, chụp nhiều frame lấy consensus |
388	| R8 | User config sai min_sell_price → bán lỗ lớn | Thấp | Cao | Validation: min_sell_price ≥ 50% estimated_price (warning) |
389	| R9 | Cross-platform bugs (Windows vs Linux) | Cao | Trung bình | Platform abstraction layer, CI test cả 2 OS |
390	| R10 | Performance chậm (cycle > 60s) | Trung bình | Thấp | Profile + optimize, skip empty cells by pixel |
391	
392	---
393	
394	## 📁 6. Project Structure
395	
396	```
397	albion-auto-seller/
398	├── README.md
399	├── LICENSE
400	├── docker-compose.yml           # MongoDB for dev
401	├── install.sh                   # Linux installer
402	├── install.ps1                  # Windows installer
403	│
404	├── bot/                         # Python bot
405	│   ├── pyproject.toml
406	│   ├── requirements.txt
407	│   └── albion_bot/
408	│       ├── __init__.py
409	│       ├── cli.py               # entry point
410	│       ├── config.py
411	│       ├── platform/
412	│       │   ├── base.py
413	│       │   ├── linux_x11.py
414	│       │   └── windows.py
415	│       ├── capture/
416	│       │   └── screen.py
417	│       ├── input/
418	│       │   ├── mouse.py
419	│       │   └── keyboard.py
420	│       ├── ocr/
421	│       │   └── engine.py
422	│       ├── calibration/
423	│       │   └── wizard.py
424	│       ├── scanner/
425	│       │   └── inventory.py
426	│       ├── seller/
427	│       │   ├── loop.py
428	│       │   └── logic.py
429	│       ├── db/
430	│       │   ├── client.py
431	│       │   └── models.py
432	│       └── utils/
433	│
434	├── backend/                     # Go API
435	│   ├── go.mod
436	│   ├── go.sum
437	│   ├── cmd/server/main.go
438	│   └── internal/
439	│       ├── api/
440	│       ├── models/
441	│       ├── repository/
442	│       ├── service/
443	│       ├── websocket/
444	│       └── config/
445	│
446	├── frontend/                    # Angular
447	│   ├── package.json
448	│   ├── angular.json
449	│   └── src/
450	│       ├── app/
451	│       │   ├── pages/
452	│       │   │   ├── dashboard/
453	│       │   │   ├── transactions/
454	│       │   │   ├── inventory/
455	│       │   │   ├── config/
456	│       │   │   └── status/
457	│       │   ├── services/
458	│       │   ├── models/
459	│       │   └── shared/
460	│       ├── assets/i18n/
461	│       │   ├── en.json
462	│       │   └── vi.json
463	│       └── styles/
464	│
465	└── docs/
466	    ├── installation.md
467	    ├── calibration-guide.md
468	    ├── user-manual.md
469	    └── troubleshooting.md
470	```
471	
```

## Assistant

The plan is well-structured, but here are the gaps that need to be filled before starting:

**Critical — needed before writing any code:**

1. **Screen resolution & game UI specifics** — What resolution does the target machine run at? Does the game run in fullscreen or windowed? This directly affects calibration defaults and OCR region sizing.

2. **OCR language/font** — Albion Online's item names are in English, but are there any non-ASCII characters in item names or prices? PaddleOCR needs to be configured with the right model (en vs multilingual).

3. **Sell flow UI details** — The plan mentions "click Sell Now → OCR giá buy order" but doesn't clarify: does the sell dialog open as a separate popup, or inline? How many clicks does the full sell flow take? This is the core loop and needs a step-by-step UI walkthrough.

4. **Quality detection** — FR-3 mentions `item_quality ≥ buy_order_quality` but the schema has `quality: null` meaning "sell any quality." How does the bot read the buy order's quality requirement from the UI? Is it visible in the sell dialog?

5. **Quantity per sell** — Does the bot sell all stacked items at once, or one at a time? The `transactions` schema has `quantity` but the selling loop doesn't describe how quantity is determined or entered.

**Important — needed before Milestone 4:**

6. **Empty slot detection pixel color** — What color/pixel signature indicates an empty inventory slot? This needs to be documented or discovered via testing before the scan loop can be written.

7. **Market city field** — `transactions.market_city` is in the schema but there's no mention of how the bot detects which city the player is in. Is this user-configured at startup, or OCR'd from the UI?

8. **Tooltip trigger mechanism** — Does hovering over an item show the tooltip, or does it require a click? If hover, `pyautogui`/`xdotool` hover timing needs to be specified.

9. **Bot ↔ Backend communication** — The bot writes directly to MongoDB, and the backend reads from it. Is there any case where the backend needs to signal the bot (e.g., config changes taking effect mid-session)? If yes, a polling interval or IPC mechanism needs to be defined.

**Nice to have before starting:**

10. **Angular version decision** — Angular 17+ is listed but Angular 18/19 are available now (May 2026). Worth pinning the exact version to avoid mid-project breaking changes.

11. **Install script scope** — Do the install scripts handle MongoDB installation, or assume it's already present? This affects the Milestone 0 estimate significantly.

The most blocking gap is **#3 (sell flow UI details)** — without a clear step-by-step of what the bot needs to do inside the sell dialog, Milestone 4 can't be accurately scoped or implemented.

## User

1. The game's resolution is chosen by the player, and the game runs in windowed mode.

2. I'm not sure — how should I provide that information?

3. I still don't understand this one either — how should I provide that information?

4. I haven't grasped your point — could you explain it more clearly?

5. Quantity per sell = the maximum quantity the market can purchase at that price.

6. The color can be determined by the player through OCR or another, better method.

7. We can OCR from the UI to identify which city we're selling in.

8. A click is required.

9. Communication happens directly.

10. I don't know — I've never used Angular before.

11. I'm not sure — could you explain that more clearly?

## Assistant

Good answers. Let me go through each one:

**2. OCR language/font**
You need to play the game and check: do any item names contain accented characters, symbols, or non-Latin letters? For example "Adept's Leather Bag" is pure ASCII — that's fine. If all item names and prices are standard English + numbers + punctuation, PaddleOCR's English model works perfectly. You don't need to do anything special right now — just keep this in mind during Milestone 1 testing. If OCR misreads names, we'll know to switch models then.

**3. Sell flow UI details**
This is the most important unknown. Before coding the sell loop, someone needs to manually walk through the exact sequence of clicks in the game UI:
- Click item in inventory → what happens? (tooltip appears? dialog opens?)
- Click "Sell Now" → what appears on screen?
- How many fields/buttons are in the sell dialog?
- How do you confirm the sale?

The best way to document this: take screenshots of each step and annotate them. You don't need to do this now, but it must be done before Milestone 4.

**4. Quality logic clarification**
When you open the sell dialog for an item, the market shows existing buy orders. Each buy order may specify a minimum quality (e.g., "Normal", "Good", "Outstanding"). The question is: does the game UI display the buy order's quality requirement visibly in the sell dialog? If yes, the bot can OCR it and compare against the item's quality. If the UI doesn't show it, the quality check can't be automated. This needs to be verified in-game.

**5. Quantity** — Clear, no issue. The bot reads the max quantity from the sell dialog and uses that value.

**6. Empty slot detection** — Agreed, pixel color sampling during calibration is the right approach. The calibration wizard should include a step where the user points to an empty slot so the bot can record its color signature.

**10. Angular version** — Since you're new to Angular, I'd recommend pinning to **Angular 18** (stable, well-documented, long-term support). Angular 19 introduced some breaking changes that make tutorials harder to follow. We can decide this at Milestone 0.

**11. Install script scope**
The install scripts (`install.sh` / `install.ps1`) could do two very different things:
- **Minimal**: just install Python deps + Go binary + Angular build. Assumes MongoDB is already running.
- **Full**: also install and start MongoDB as a service.

The "full" version is much more work and varies a lot between Linux distros and Windows versions. Recommend starting with **minimal** — document MongoDB installation separately in `docs/installation.md`, and the script only sets up the app itself. Clarify this before Milestone 0.

---

**Summary of remaining blockers:**
- Item name character set (verify during M1 testing — not blocking now)
- Sell flow UI screenshots (must have before M4)
- Buy order quality visibility in sell dialog (must verify in-game before M4)
- Install script scope decision (decide before M0)

## User

2. The language uses pure ASCII characters only.
3. `Image` `Image` 
Clicking an item in the inventory displays its information
Clicking "Sell" at the final step executes the sale immediately
The image depicts the final step with the sell button
No confirmation dialog appears — clicking the red "Sell" button at the final step sells immediately

4. `Image` In the final sell dialog, you can select a quality tier on the left side, while the right side displays the buy orders and sell orders for that specific quality tier only.

11. I still don't quite grasp what you mean.

## Assistant

Looking at the screenshots, I can now better explain the quality logic question.

**What I was asking about (question 4):**

In the sell dialog, there's a quality selector on the left side. When you select a quality tier (e.g., "Normal," "Good," "Outstanding"), the right panel updates to show **only the buy orders and sell orders for that specific quality**.

**The question was:** When the bot reads the buy order price from the sell dialog, does it also see the quality requirement of that buy order? Or does it just see a price?

**From the screenshot, it appears:**
- The quality is selected by the player/bot on the left
- The right side shows orders filtered to that quality
- There is no separate "quality requirement" field visible — the quality is implicit based on which tab/tier is selected

**So the quality logic is simpler than I thought:**
- The bot selects a quality tier to sell at
- It reads the best buy order price shown for that tier
- It compares that price against `min_sell_price`
- No separate quality-matching logic is needed — the UI handles filtering by quality automatically

**Remaining question:** Does the bot always sell at the same quality tier the item was scanned at, or does it try multiple quality tiers? This would determine whether the bot needs to iterate through quality options or just use the item's natural quality.

## User

`Image`
 `Image` 

This is the market interface when selling. You can sort by price—of course, we’ll choose highest to lowest—and at this point, we just need to select the correct item name and filter by type, tier, enchant, and quality. The best available price will then appear at the top.

Orders that can be sold will have a red sell button.
Orders with a black sell button mean the item in our inventory does not meet the buying order’s conditions (wrong type, wrong tier, wrong enchant, or our item’s quality is higher than what the buyer is accepting).
In this case, we will compare salable orders with our inventory to determine which items can be sold.
