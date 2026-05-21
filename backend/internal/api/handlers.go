package api

import (
	"encoding/csv"
	"log"
	"net/http"
	"os/exec"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/v2/bson"

	"github.com/durond/albion-auto-seller/internal/db"
	"github.com/durond/albion-auto-seller/internal/models"
)

type Handler struct {
	repo *db.Repository
}

func NewHandler(repo *db.Repository) *Handler {
	return &Handler{repo: repo}
}

// GET /api/transactions?limit=50&offset=0
func (h *Handler) ListTransactions(c *gin.Context) {
	limit, _ := strconv.ParseInt(c.DefaultQuery("limit", "50"), 10, 64)
	offset, _ := strconv.ParseInt(c.DefaultQuery("offset", "0"), 10, 64)
	log.Printf("[API] Lấy danh sách giao dịch: limit=%d, offset=%d", limit, offset)

	txs, err := h.repo.ListTransactions(c.Request.Context(), limit, offset)
	if err != nil {
		log.Printf("[LỖI] Không lấy được danh sách giao dịch: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	total, _ := h.repo.CountTransactions(c.Request.Context())
	log.Printf("[API OK] Trả về %d/%d giao dịch", len(txs), total)
	c.JSON(http.StatusOK, gin.H{"data": txs, "total": total})
}

// GET /api/transactions/export
func (h *Handler) ExportTransactionsCSV(c *gin.Context) {
	log.Println("[API] Xuất toàn bộ giao dịch ra file CSV...")
	txs, err := h.repo.ListTransactions(c.Request.Context(), 100000, 0)
	if err != nil {
		log.Printf("[LỖI] Không xuất được CSV: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Header("Content-Disposition", "attachment; filename=transactions.csv")
	c.Header("Content-Type", "text/csv")

	w := csv.NewWriter(c.Writer)
	_ = w.Write([]string{"timestamp", "item", "tier", "enchant", "quantity", "unit_price", "total_price", "market_city", "status"})
	for _, tx := range txs {
		_ = w.Write([]string{
			tx.Timestamp.Format(time.RFC3339),
			tx.Item.FullName,
			strconv.Itoa(tx.Item.Tier),
			strconv.Itoa(tx.Item.Enchant),
			strconv.Itoa(tx.Quantity),
			strconv.Itoa(tx.UnitPrice),
			strconv.Itoa(tx.TotalPrice),
			tx.MarketCity,
			tx.Status,
		})
	}
	w.Flush()
	log.Printf("[API OK] Đã xuất %d giao dịch ra CSV.", len(txs))
}

// GET /api/item-configs
func (h *Handler) ListItemConfigs(c *gin.Context) {
	log.Println("[API] Lấy danh sách cấu hình vật phẩm...")
	items, err := h.repo.ListItemConfigs(c.Request.Context())
	if err != nil {
		log.Printf("[LỖI] Không lấy được cấu hình vật phẩm: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	log.Printf("[API OK] Trả về %d cấu hình vật phẩm.", len(items))
	c.JSON(http.StatusOK, gin.H{"data": items})
}

// PATCH /api/item-configs/:id
func (h *Handler) UpdateItemConfig(c *gin.Context) {
	idStr := c.Param("id")
	log.Printf("[API] Cập nhật cấu hình vật phẩm ID: %s", idStr)
	oid, err := bson.ObjectIDFromHex(idStr)
	if err != nil {
		log.Printf("[LỖI] ID vật phẩm không hợp lệ: %s", idStr)
		c.JSON(http.StatusBadRequest, gin.H{"error": "id không hợp lệ"})
		return
	}

	var body struct {
		CostPrice *int `json:"cost_price"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		log.Printf("[LỖI] Dữ liệu gửi lên không đúng định dạng: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.repo.UpdateCostPrice(c.Request.Context(), oid, body.CostPrice); err != nil {
		log.Printf("[LỖI] Không cập nhật được giá vốn: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	log.Printf("[API OK] Đã cập nhật giá vốn cho vật phẩm %s.", idStr)
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

// GET /api/bot/status
func (h *Handler) BotStatus(c *gin.Context) {
	log.Println("[API] Lấy trạng thái bot...")
	session, err := h.repo.GetLatestSession(c.Request.Context())
	if err != nil {
		log.Printf("[LỖI] Không lấy được trạng thái bot: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if session == nil {
		log.Println("[API OK] Bot đang ở trạng thái: rảnh (chưa có phiên nào)")
		c.JSON(http.StatusOK, gin.H{"status": "idle"})
		return
	}
	log.Printf("[API OK] Trạng thái bot: %s", session.Status)
	c.JSON(http.StatusOK, session)
}

// GET /api/calibration/profiles
func (h *Handler) ListCalibrationProfiles(c *gin.Context) {
	log.Println("[API] Lấy danh sách profile calibration...")
	profiles, err := h.repo.ListCalibrationProfiles(c.Request.Context())
	if err != nil {
		log.Printf("[LỖI] Không lấy được danh sách profile: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	log.Printf("[API OK] Tìm thấy %d profile calibration.", len(profiles))
	c.JSON(http.StatusOK, gin.H{"data": profiles})
}

// POST /api/calibration/save
func (h *Handler) SaveCalibration(c *gin.Context) {
	log.Println("[API] Đang lưu calibration mới...")
	var doc models.CalibrationDoc
	if err := c.ShouldBindJSON(&doc); err != nil {
		log.Printf("[LỖI] Dữ liệu calibration không đúng định dạng: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	id, err := h.repo.SaveCalibration(c.Request.Context(), doc)
	if err != nil {
		log.Printf("[LỖI] Không lưu được calibration: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	log.Printf("[API OK] Đã lưu calibration profile '%s' (ID: %s).", doc.ProfileName, id)
	c.JSON(http.StatusOK, gin.H{"id": id})
}

// POST /api/calibration/capture-click
func (h *Handler) StartCaptureClick(c *gin.Context) {
	log.Println("[API] Bắt đầu lệnh chụp tọa độ click...")
	id, err := h.repo.CreateCaptureCommand(c.Request.Context())
	if err != nil {
		log.Printf("[LỖI] Không tạo được lệnh chụp click: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	log.Printf("[API OK] Đã tạo lệnh chụp click, ID: %s", id)
	c.JSON(http.StatusOK, gin.H{"id": id})
}

// GET /api/calibration/capture-click/:id
func (h *Handler) PollCaptureClick(c *gin.Context) {
	id := c.Param("id")
	x, y, done, err := h.repo.PollCaptureCommand(c.Request.Context(), id)
	if err != nil {
		log.Printf("[LỖI] Không kiểm tra được lệnh chụp click %s: %v", id, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !done {
		c.JSON(http.StatusOK, gin.H{"done": false})
		return
	}
	log.Printf("[API OK] Đã chụp được tọa độ click: x=%d, y=%d", x, y)
	c.JSON(http.StatusOK, gin.H{"done": true, "x": x, "y": y})
}

// GET /api/calibration/screenshot?x=&y=&w=&h=
func (h *Handler) Screenshot(c *gin.Context) {
	x := c.DefaultQuery("x", "0")
	y := c.DefaultQuery("y", "0")
	w := c.DefaultQuery("w", "200")
	hh := c.DefaultQuery("h", "100")
	log.Printf("[API] Chụp màn hình vùng: x=%s, y=%s, w=%s, h=%s", x, y, w, hh)

	cmd := exec.Command("uv", "run", "--project", "./bot", "python",
		"./bot/albion_bot/calibration/screenshot_helper.py", x, y, w, hh)
	out, err := cmd.Output()
	if err != nil {
		log.Printf("[LỖI] Không chụp được màn hình: %v\nNguyên nhân có thể: lệnh `uv` chưa cài, hoặc script Python bị lỗi.", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "chụp màn hình thất bại: " + err.Error()})
		return
	}
	log.Printf("[API OK] Đã chụp màn hình thành công (%d bytes).", len(out))
	c.Data(http.StatusOK, "image/png", out)
}

// GET /api/inventory
func (h *Handler) GetInventory(c *gin.Context) {
	log.Println("[API] Lấy ảnh chụp kho đồ mới nhất...")
	snap, err := h.repo.GetLatestSnapshot(c.Request.Context())
	if err != nil {
		log.Printf("[LỖI] Không lấy được kho đồ: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if snap == nil {
		log.Println("[API OK] Chưa có dữ liệu kho đồ nào.")
		c.JSON(http.StatusOK, gin.H{"data": nil})
		return
	}
	log.Printf("[API OK] Trả về kho đồ có %d vật phẩm.", len(snap.Items))
	c.JSON(http.StatusOK, gin.H{"data": snap})
}
