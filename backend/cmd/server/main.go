package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"path/filepath"
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

	// Resolve frontend dist path relative to project root (one level up from backend/)
	exe, _ := os.Executable()
	// When using `go run`, exe is in a temp dir; fall back to source-relative path
	projectRoot := filepath.Join(filepath.Dir(exe), "..")
	frontendDist := filepath.Join(projectRoot, "frontend", "dist", "albion-dashboard", "browser")
	// Check if that path exists; if not, try relative to cwd (for `go run` from project root)
	if _, err := os.Stat(frontendDist); err != nil {
		cwd, _ := os.Getwd()
		frontendDist = filepath.Join(cwd, "..", "frontend", "dist", "albion-dashboard", "browser")
		if _, err := os.Stat(frontendDist); err != nil {
			// Last resort: relative to cwd (running from project root)
			frontendDist = filepath.Join(cwd, "frontend", "dist", "albion-dashboard", "browser")
		}
	}
	log.Printf("serving frontend from: %s", frontendDist)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(options.Client().ApplyURI(viper.GetString("mongo_uri")))
	if err != nil {
		log.Fatalf("mongo connect: %v", err)
	}
	if err := client.Ping(ctx, nil); err != nil {
		log.Fatalf("mongo ping: %v", err)
	}
	log.Println("connected to MongoDB")

	repo := db.NewRepository(client, viper.GetString("mongo_db"))
	handler := api.NewHandler(repo)
	hub := ws.NewHub()

	r := gin.Default()

	// CORS for local Angular dev server
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
		apiv1.PATCH("/item-configs/:id", handler.UpdateItemConfig)
		apiv1.GET("/bot/status", handler.BotStatus)
		apiv1.GET("/inventory", handler.GetInventory)

		// Calibration GUI
		apiv1.GET("/calibration/profiles", handler.ListCalibrationProfiles)
		apiv1.POST("/calibration/save", handler.SaveCalibration)
		apiv1.POST("/calibration/capture-click", handler.StartCaptureClick)
		apiv1.GET("/calibration/capture-click/:id", handler.PollCaptureClick)
		apiv1.GET("/calibration/screenshot", handler.Screenshot)
	}

	// Serve Angular static files
	r.Static("/assets", filepath.Join(frontendDist, "assets"))
	r.StaticFile("/favicon.ico", filepath.Join(frontendDist, "favicon.ico"))
	r.NoRoute(func(c *gin.Context) {
		c.File(filepath.Join(frontendDist, "index.html"))
	})

	addr := "localhost:" + viper.GetString("port")
	if viper.GetBool("lan") {
		addr = "0.0.0.0:" + viper.GetString("port")
	}
	log.Printf("backend listening on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("server: %v", err)
	}
}
