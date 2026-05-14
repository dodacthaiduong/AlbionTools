package models

import (
	"time"

	"go.mongodb.org/mongo-driver/v2/bson"
)

type Rect struct {
	X int `bson:"x" json:"x"`
	Y int `bson:"y" json:"y"`
	W int `bson:"w" json:"w"`
	H int `bson:"h" json:"h"`
}

type ItemConfig struct {
	ID             bson.ObjectID `bson:"_id,omitempty" json:"id"`
	BaseName       string        `bson:"base_name" json:"base_name"`
	FullName       string        `bson:"full_name" json:"full_name"`
	Tier           int           `bson:"tier" json:"tier"`
	Enchant        int           `bson:"enchant" json:"enchant"`
	EstimatedPrice *int          `bson:"estimated_price" json:"estimated_price"`
	MinSellPrice   *int          `bson:"min_sell_price" json:"min_sell_price"`
	Enabled        bool          `bson:"enabled" json:"enabled"`
	LastScannedAt  time.Time     `bson:"last_scanned_at" json:"last_scanned_at"`
	CreatedAt      time.Time     `bson:"created_at" json:"created_at"`
	UpdatedAt      time.Time     `bson:"updated_at" json:"updated_at"`
}

type TransactionItem struct {
	ConfigID string `bson:"config_id,omitempty" json:"config_id,omitempty"`
	FullName string `bson:"full_name" json:"full_name"`
	Tier     int    `bson:"tier" json:"tier"`
	Enchant  int    `bson:"enchant" json:"enchant"`
}

type Transaction struct {
	ID          bson.ObjectID   `bson:"_id,omitempty" json:"id"`
	Timestamp   time.Time       `bson:"timestamp" json:"timestamp"`
	SessionID   string          `bson:"session_id" json:"session_id"`
	Item        TransactionItem `bson:"item" json:"item"`
	Quantity    int             `bson:"quantity" json:"quantity"`
	UnitPrice   int             `bson:"unit_price" json:"unit_price"`
	TotalPrice  int             `bson:"total_price" json:"total_price"`
	MarketCity  string          `bson:"market_city" json:"market_city"`
	Status      string          `bson:"status" json:"status"`
}

type SessionStats struct {
	CyclesCompleted int `bson:"cycles_completed" json:"cycles_completed"`
	ItemsSold       int `bson:"items_sold" json:"items_sold"`
	TotalRevenue    int `bson:"total_revenue" json:"total_revenue"`
	ErrorsCount     int `bson:"errors_count" json:"errors_count"`
}

type BotSession struct {
	ID             bson.ObjectID  `bson:"_id,omitempty" json:"id"`
	StartedAt      time.Time      `bson:"started_at" json:"started_at"`
	EndedAt        *time.Time     `bson:"ended_at,omitempty" json:"ended_at,omitempty"`
	Status         string         `bson:"status" json:"status"`
	StopReason     *string        `bson:"stop_reason,omitempty" json:"stop_reason,omitempty"`
	Stats          SessionStats   `bson:"stats" json:"stats"`
	CalibrationID  *string        `bson:"calibration_id,omitempty" json:"calibration_id,omitempty"`
}

type InventorySnapshotItem struct {
	Slot       int    `bson:"slot" json:"slot"`
	ConfigID   string `bson:"config_id" json:"config_id"`
	FullName   string `bson:"full_name" json:"full_name"`
	Tier       int    `bson:"tier" json:"tier"`
	Enchant    int    `bson:"enchant" json:"enchant"`
	Quantity   int    `bson:"quantity" json:"quantity"`
}

type InventorySnapshot struct {
	ID                  bson.ObjectID           `bson:"_id,omitempty" json:"id"`
	Timestamp           time.Time               `bson:"timestamp" json:"timestamp"`
	SessionID           string                  `bson:"session_id" json:"session_id"`
	Items               []InventorySnapshotItem `bson:"items" json:"items"`
	EmptySlots          int                     `bson:"empty_slots" json:"empty_slots"`
	TotalEstimatedValue int                     `bson:"total_estimated_value" json:"total_estimated_value"`
}
