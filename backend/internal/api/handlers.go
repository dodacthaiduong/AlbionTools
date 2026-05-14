package api

import (
	"encoding/csv"
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

	txs, err := h.repo.ListTransactions(c.Request.Context(), limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	total, _ := h.repo.CountTransactions(c.Request.Context())
	c.JSON(http.StatusOK, gin.H{"data": txs, "total": total})
}

// GET /api/transactions/export
func (h *Handler) ExportTransactionsCSV(c *gin.Context) {
	txs, err := h.repo.ListTransactions(c.Request.Context(), 100000, 0)
	if err != nil {
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
}

// GET /api/item-configs
func (h *Handler) ListItemConfigs(c *gin.Context) {
	items, err := h.repo.ListItemConfigs(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": items})
}

// PATCH /api/item-configs/:id
func (h *Handler) UpdateItemConfig(c *gin.Context) {
	idStr := c.Param("id")
	oid, err := bson.ObjectIDFromHex(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var body struct {
		MinSellPrice *int `json:"min_sell_price"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.repo.UpdateMinSellPrice(c.Request.Context(), oid, body.MinSellPrice); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

// GET /api/bot/status
func (h *Handler) BotStatus(c *gin.Context) {
	session, err := h.repo.GetLatestSession(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if session == nil {
		c.JSON(http.StatusOK, gin.H{"status": "idle"})
		return
	}
	c.JSON(http.StatusOK, session)
}

// GET /api/calibration/profiles
func (h *Handler) ListCalibrationProfiles(c *gin.Context) {
	profiles, err := h.repo.ListCalibrationProfiles(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": profiles})
}

// POST /api/calibration/save
func (h *Handler) SaveCalibration(c *gin.Context) {
	var doc models.CalibrationDoc
	if err := c.ShouldBindJSON(&doc); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	id, err := h.repo.SaveCalibration(c.Request.Context(), doc)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": id})
}

// POST /api/calibration/capture-click
// Returns a command ID; frontend polls GET /api/calibration/capture-click/:id
func (h *Handler) StartCaptureClick(c *gin.Context) {
	id, err := h.repo.CreateCaptureCommand(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": id})
}

// GET /api/calibration/capture-click/:id
func (h *Handler) PollCaptureClick(c *gin.Context) {
	id := c.Param("id")
	x, y, done, err := h.repo.PollCaptureCommand(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !done {
		c.JSON(http.StatusOK, gin.H{"done": false})
		return
	}
	c.JSON(http.StatusOK, gin.H{"done": true, "x": x, "y": y})
}

// GET /api/calibration/screenshot?x=&y=&w=&h=
func (h *Handler) Screenshot(c *gin.Context) {
	x := c.DefaultQuery("x", "0")
	y := c.DefaultQuery("y", "0")
	w := c.DefaultQuery("w", "200")
	hh := c.DefaultQuery("h", "100")

	// Call Python screenshot helper as subprocess
	cmd := exec.Command("uv", "run", "--project", "./bot", "python",
		"./bot/albion_bot/calibration/screenshot_helper.py", x, y, w, hh)
	out, err := cmd.Output()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "screenshot failed: " + err.Error()})
		return
	}
	c.Data(http.StatusOK, "image/png", out)
}

// GET /api/inventory
func (h *Handler) GetInventory(c *gin.Context) {
	snap, err := h.repo.GetLatestSnapshot(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if snap == nil {
		c.JSON(http.StatusOK, gin.H{"data": nil})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": snap})
}
