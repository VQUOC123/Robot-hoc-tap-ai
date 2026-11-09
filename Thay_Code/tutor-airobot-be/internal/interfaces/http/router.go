package http

import (
	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/configs"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/handler"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/middleware"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/redis"
)

// Handlers groups all HTTP handlers for dependency injection.
type Handlers struct {
	Health   *handler.HealthHandler
	Auth     *handler.AuthHandler
	Provider *handler.ProviderHandler
	Prompt   *handler.PromptHandler
	Device   *handler.DeviceHandler
	Analysis *handler.AnalysisHandler
	Stats    *handler.StatsHandler
}

// MiddlewareDeps groups dependencies needed to construct middleware.
type MiddlewareDeps struct {
	Config     *configs.Config
	DeviceRepo repository.DeviceRepository
	Blacklist  *redis.JWTBlacklist
	RateLimiter *redis.RateLimiter
}

// SetupRoutes registers all application routes on the Fiber app.
//
// Route summary:
//
//	GET  /health                              — no auth
//	POST /api/v1/device/analyze               — DeviceAuth + device rate limit
//	POST /api/v1/auth/login                   — IP rate limit
//	POST /api/v1/auth/refresh                 — no auth
//	POST /api/v1/auth/logout                  — AdminAuth
//	GET  /api/v1/providers                    — AdminAuth
//	POST /api/v1/providers                    — AdminAuth
//	GET  /api/v1/providers/:id               — AdminAuth
//	PUT  /api/v1/providers/:id               — AdminAuth
//	DELETE /api/v1/providers/:id             — AdminAuth
//	POST /api/v1/providers/:id/test          — AdminAuth
//	GET  /api/v1/prompts                      — AdminAuth
//	POST /api/v1/prompts                      — AdminAuth
//	PUT  /api/v1/prompts/:id                  — AdminAuth
//	DELETE /api/v1/prompts/:id               — AdminAuth
//	GET  /api/v1/devices                      — AdminAuth
//	POST /api/v1/devices                      — AdminAuth
//	POST /api/v1/devices/:id/revoke          — AdminAuth
//	GET  /api/v1/analyses                     — AdminAuth
//	GET  /api/v1/stats/overview              — AdminAuth
//	GET  /api/v1/stats/latency               — AdminAuth
//	GET  /api/v1/stats/subjects              — AdminAuth
func SetupRoutes(app *fiber.App, h *Handlers, deps MiddlewareDeps) {
	cfg := deps.Config

	// Global middleware
	app.Use(middleware.Recover())
	app.Use(middleware.RequestLogger())
	app.Use(middleware.CORS(cfg.AdminFrontendURL))

	// Health check — unauthenticated
	app.Get("/health", h.Health.Handle)

	// ── Device-facing endpoint ────────────────────────────────────────────────
	deviceGroup := app.Group("/api/v1/device",
		middleware.DeviceAuth(deps.DeviceRepo),
		middleware.RateLimitDevice(deps.RateLimiter, cfg.RateLimitDeviceRPM),
	)
	deviceGroup.Post("/analyze", h.Analysis.Analyze)

	// ── Auth endpoints ────────────────────────────────────────────────────────
	authGroup := app.Group("/api/v1/auth")
	authGroup.Post("/login",
		middleware.RateLimitIP(deps.RateLimiter, cfg.RateLimitAuthRPM),
		h.Auth.Login,
	)
	authGroup.Post("/refresh", h.Auth.Refresh)
	authGroup.Post("/logout",
		middleware.AdminAuth(cfg.JWTSecret, deps.Blacklist),
		h.Auth.Logout,
	)

	// ── Admin-only endpoints ──────────────────────────────────────────────────
	adminAuth := middleware.AdminAuth(cfg.JWTSecret, deps.Blacklist)
	adminRateLimit := middleware.RateLimitAdmin(deps.RateLimiter, cfg.RateLimitAdminRPM)

	admin := app.Group("/api/v1", adminAuth, adminRateLimit)

	// Providers
	admin.Get("/providers", h.Provider.List)
	admin.Post("/providers", h.Provider.Create)
	admin.Get("/providers/:id", h.Provider.Get)
	admin.Put("/providers/:id", h.Provider.Update)
	admin.Delete("/providers/:id", h.Provider.Delete)
	admin.Post("/providers/:id/test", h.Provider.Test)

	// Prompts
	admin.Get("/prompts", h.Prompt.List)
	admin.Post("/prompts", h.Prompt.Create)
	admin.Put("/prompts/:id", h.Prompt.Update)
	admin.Delete("/prompts/:id", h.Prompt.Delete)

	// Devices (admin management)
	admin.Get("/devices", h.Device.List)
	admin.Post("/devices", h.Device.Create)
	admin.Post("/devices/:id/revoke", h.Device.Revoke)

	// Analyses history
	admin.Get("/analyses", h.Analysis.ListHistory)

	// Statistics
	admin.Get("/stats/overview", h.Stats.Overview)
	admin.Get("/stats/latency", h.Stats.Latency)
	admin.Get("/stats/subjects", h.Stats.Subjects)
}
