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

func (r *Repository) UpdateCostPrice(ctx context.Context, id bson.ObjectID, price *int) error {
	_, err := r.db.Collection("item_configs").UpdateOne(
		ctx,
		bson.D{{Key: "_id", Value: id}},
		bson.D{{Key: "$set", Value: bson.D{
			{Key: "cost_price", Value: price},
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

// --- Calibration ---

func (r *Repository) SaveCalibration(ctx context.Context, doc models.CalibrationDoc) (string, error) {
	existing := r.db.Collection("calibrations").FindOne(ctx, bson.D{{Key: "profile_name", Value: doc.ProfileName}})
	var old bson.M
	if err := existing.Decode(&old); err == nil {
		id := old["_id"].(bson.ObjectID)
		doc.UpdatedAt = time.Now().UTC()
		_, err := r.db.Collection("calibrations").ReplaceOne(ctx, bson.D{{Key: "_id", Value: id}}, doc)
		return id.Hex(), err
	}
	doc.CreatedAt = time.Now().UTC()
	doc.UpdatedAt = doc.CreatedAt
	result, err := r.db.Collection("calibrations").InsertOne(ctx, doc)
	if err != nil {
		return "", err
	}
	return result.InsertedID.(bson.ObjectID).Hex(), nil
}

func (r *Repository) ListCalibrationProfiles(ctx context.Context) ([]string, error) {
	cur, err := r.db.Collection("calibrations").Find(ctx, bson.D{})
	if err != nil {
		return nil, err
	}
	var docs []bson.M
	if err := cur.All(ctx, &docs); err != nil {
		return nil, err
	}
	profiles := make([]string, 0, len(docs))
	for _, d := range docs {
		if name, ok := d["profile_name"].(string); ok {
			profiles = append(profiles, name)
		}
	}
	return profiles, nil
}

// --- Calibration commands (click capture IPC) ---

func (r *Repository) CreateCaptureCommand(ctx context.Context) (string, error) {
	doc := bson.M{
		"type":       "capture_click",
		"status":     "pending",
		"created_at": time.Now().UTC(),
	}
	result, err := r.db.Collection("calibration_commands").InsertOne(ctx, doc)
	if err != nil {
		return "", err
	}
	return result.InsertedID.(bson.ObjectID).Hex(), nil
}

func (r *Repository) PollCaptureCommand(ctx context.Context, id string) (int, int, bool, error) {
	oid, err := bson.ObjectIDFromHex(id)
	if err != nil {
		return 0, 0, false, err
	}
	var doc bson.M
	err = r.db.Collection("calibration_commands").FindOne(ctx, bson.D{{Key: "_id", Value: oid}}).Decode(&doc)
	if err != nil {
		return 0, 0, false, err
	}
	if doc["status"] != "done" {
		return 0, 0, false, nil
	}
	x := int(doc["x"].(int32))
	y := int(doc["y"].(int32))
	return x, y, true, nil
}

func (r *Repository) GetLatestSnapshot(ctx context.Context) (*models.InventorySnapshot, error) {
	opts := options.FindOne().SetSort(bson.D{{Key: "timestamp", Value: -1}})
	var snap models.InventorySnapshot
	err := r.db.Collection("inventory_snapshots").FindOne(ctx, bson.D{}, opts).Decode(&snap)
	if err == mongo.ErrNoDocuments {
		return nil, nil
	}
	return &snap, err
}
