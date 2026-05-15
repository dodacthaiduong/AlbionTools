package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"

	"github.com/durond/albion-auto-seller/internal/api"
	"github.com/durond/albion-auto-seller/internal/db"
	ws "github.com/durond/albion-auto-seller/internal/websocket"
)

func main() {
	viper.SetDefault("mongo_uri", "mongodb://localhost:27017")
	viper.SetDefault("mongo_db", "albion_bot")
	viper.SetDefault("port", "8080")
	viper.SetDefault("lan", false)
	viper.AutomaticEnv()

	log.Println("[KHỞI ĐỘNG] Albion Bot Backend đang khởi động...")

	// Xác định thư mục frontend
	log.Println("[BƯỚC 1] Đang tìm thư mục frontend đã build...")
	exe, _ := os.Executable()
	projectRoot := filepath.Join(filepath.Dir(exe), "..")
	frontendDist := filepath.Join(projectRoot, "frontend", "dist", "albion-dashboard", "browser")
	if _, err := os.Stat(frontendDist); err != nil {
		cwd, _ := os.Getwd()
		frontendDist = filepath.Join(cwd, "..", "frontend", "dist", "albion-dashboard", "browser")
		if _, err := os.Stat(frontendDist); err != nil {
			frontendDist = filepath.Join(cwd, "frontend", "dist", "albion-dashboard", "browser")
		}
	}
	if _, err := os.Stat(frontendDist); err != nil {
		log.Printf("[CẢNH BÁO] Không tìm thấy thư mục frontend tại: %s", frontendDist)
		log.Println("[CẢNH BÁO] Nguyên nhân có thể: chưa chạy `npm run build` trong thư mục frontend/")
	} else {
		log.Printf("[BƯỚC 1 OK] Thư mục frontend: %s", frontendDist)
	}

	// Kết nối MongoDB
	log.Printf("[BƯỚC 2] Đang kết nối MongoDB tại: %s ...", viper.GetString("mongo_uri"))
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(options.Client().ApplyURI(viper.GetString("mongo_uri")))
	if err != nil {
		log.Fatalf("[LỖI] Không thể kết nối MongoDB: %v\nNguyên nhân có thể: MongoDB chưa chạy hoặc sai địa chỉ URI.", err)
	}
	if err := client.Ping(ctx, nil); err != nil {
		log.Fatalf("[LỖI] Không ping được MongoDB: %v\nNguyên nhân có thể: MongoDB đang khởi động hoặc firewall chặn cổng 27017.", err)
	}
	log.Printf("[BƯỚC 2 OK] Đã kết nối MongoDB. Database: '%s'", viper.GetString("mongo_db"))

	// Khởi tạo các thành phần
	log.Println("[BƯỚC 3] Đang khởi tạo repository, handler và WebSocket hub...")
	repo := db.NewRepository(client, viper.GetString("mongo_db"))
	handler := api.NewHandler(repo)
	hub := ws.NewHub()
	log.Println("[BƯỚC 3 OK] Đã khởi tạo xong.")

	// Cấu hình router
	log.Println("[BƯỚC 4] Đang cấu hình các route API...")
	r := gin.Default()

	// CORS cho Angular dev server
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type")
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	})

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	r.GET("/ws", hub.HandleWS)

	apiv1 := r.Group("/api")
	{
		apiv1.GET("/transactions", handler.ListTransactions)
		apiv1.GET("/transactions/export", handler.ExportTransactionsCSV)
		apiv1.GET("/item-configs", handler.ListItemConfigs)
		apiv1.GET("/bot/status", handler.BotStatus)
		apiv1.GET("/inventory", handler.GetInventory)
	}
	log.Println("[BƯỚC 4 OK] Các route API đã được đăng ký.")

	// Phục vụ file tĩnh Angular
	r.StaticFS("/assets", http.Dir(filepath.Join(frontendDist, "assets")))
	r.StaticFile("/favicon.ico", filepath.Join(frontendDist, "favicon.ico"))
	r.NoRoute(func(c *gin.Context) {
		urlPath := strings.TrimPrefix(c.Request.URL.Path, "/")
		reqPath := filepath.Join(frontendDist, urlPath)
		if info, err := os.Stat(reqPath); err == nil && !info.IsDir() {
			c.File(reqPath)
			return
		}
		c.File(filepath.Join(frontendDist, "index.html"))
	})

	addr := "localhost:" + viper.GetString("port")
	if viper.GetBool("lan") {
		addr = "0.0.0.0:" + viper.GetString("port")
	}
	log.Printf("[KHỞI ĐỘNG XONG] Backend đang lắng nghe tại: http://%s", addr)
	log.Println("[THÔNG TIN] Nhấn Ctrl+C để dừng server.")
	if err := r.Run(addr); err != nil {
		log.Fatalf("[LỖI] Server dừng bất ngờ: %v", err)
	}
}
