package handler

import (
	"github.com/gofiber/fiber/v3"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// HealthResponse is the payload returned by GET /health.
type HealthResponse struct {
	Status  string `json:"status"`
	DB      string `json:"db"`
	Redis   string `json:"redis"`
	Version string `json:"version"`
}

// HealthHandler checks connectivity to dependencies and returns overall service health.
type HealthHandler struct {
	db      *pgxpool.Pool
	redis   *redis.Client
	version string
}

// NewHealthHandler creates a HealthHandler.
func NewHealthHandler(db *pgxpool.Pool, redisClient *redis.Client, version string) *HealthHandler {
	return &HealthHandler{db: db, redis: redisClient, version: version}
}

// Handle responds with the health status of the service and its dependencies.
func (h *HealthHandler) Handle(c fiber.Ctx) error {
	dbStatus := "ok"
	if err := h.db.Ping(c.Context()); err != nil {
		dbStatus = "error: " + err.Error()
	}

	redisStatus := "ok"
	if err := h.redis.Ping(c.Context()).Err(); err != nil {
		redisStatus = "error: " + err.Error()
	}

	overallStatus := "ok"
	if dbStatus != "ok" || redisStatus != "ok" {
		overallStatus = "degraded"
	}

	return httputil.OK(c, HealthResponse{
		Status:  overallStatus,
		DB:      dbStatus,
		Redis:   redisStatus,
		Version: h.version,
	})
}
