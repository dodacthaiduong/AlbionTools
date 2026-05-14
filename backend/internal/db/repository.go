package db

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"

	"github.com/durond/albion-auto-seller/internal/models"
)

type Repository struct {
	db *mongo.Database
}

func NewRepository(client *mongo.Client, dbName string) *Repository {
	return &Repository{db: client.Database(dbName)}
}

// --- Transactions ---

func (r *Repository) ListTransactions(ctx context.Context, limit int64, offset int64) ([]models.Transaction, error) {
	opts := options.Find().SetSort(bson.D{{Key: "timestamp", Value: -1}}).SetLimit(limit).SetSkip(offset)
	cur, err := r.db.Collection("transactions").Find(ctx, bson.D{}, opts)
	if err != nil {
		return nil, err
	}
	var results []models.Transaction
	return results, cur.All(ctx, &results)
}

func (r *Repository) CountTransactions(ctx context.Context) (int64, error) {
	return r.db.Collection("transactions").CountDocuments(ctx, bson.D{})
}

// --- Item configs ---

func (r *Repository) ListItemConfigs(ctx context.Context) ([]models.ItemConfig, error) {
	cur, err := r.db.Collection("item_configs").Find(ctx, bson.D{})
	if err != nil {
		return nil, err
	}
	var results []models.ItemConfig
	return results, cur.All(ctx, &results)
}

func (r *Repository) UpdateMinSellPrice(ctx context.Context, id bson.ObjectID, price *int) error {
	_, err := r.db.Collection("item_configs").UpdateOne(
		ctx,
		bson.D{{Key: "_id", Value: id}},
		bson.D{{Key: "$set", Value: bson.D{
			{Key: "min_sell_price", Value: price},
			{Key: "updated_at", Value: time.Now().UTC()},
		}}},
	)
	return err
}

// --- Bot sessions ---

func (r *Repository) GetLatestSession(ctx context.Context) (*models.BotSession, error) {
	opts := options.FindOne().SetSort(bson.D{{Key: "started_at", Value: -1}})
	var session models.BotSession
	err := r.db.Collection("bot_sessions").FindOne(ctx, bson.D{}, opts).Decode(&session)
	if err == mongo.ErrNoDocuments {
		return nil, nil
	}
	return &session, err
}

// --- Inventory snapshots ---

func (r *Repository) GetLatestSnapshot(ctx context.Context) (*models.InventorySnapshot, error) {
	opts := options.FindOne().SetSort(bson.D{{Key: "timestamp", Value: -1}})
	var snap models.InventorySnapshot
	err := r.db.Collection("inventory_snapshots").FindOne(ctx, bson.D{}, opts).Decode(&snap)
	if err == mongo.ErrNoDocuments {
		return nil, nil
	}
	return &snap, err
}
