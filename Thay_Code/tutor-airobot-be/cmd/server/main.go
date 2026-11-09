package main

import (
	"context"
	"database/sql"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib" // pgx stdlib driver for database/sql
	"github.com/pressly/goose/v3"
	"github.com/rs/zerolog/log"

	"github.com/nhanntv/tutor-airobot-be/configs"
	appAnalysis "github.com/nhanntv/tutor-airobot-be/internal/application/analysis"
	appAuth "github.com/nhanntv/tutor-airobot-be/internal/application/auth"
	appDevice "github.com/nhanntv/tutor-airobot-be/internal/application/device"
	appPrompt "github.com/nhanntv/tutor-airobot-be/internal/application/prompt"
	appProvider "github.com/nhanntv/tutor-airobot-be/internal/application/provider"
	aiInfra "github.com/nhanntv/tutor-airobot-be/internal/infrastructure/ai"
	imageInfra "github.com/nhanntv/tutor-airobot-be/internal/infrastructure/image"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/postgres"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/postgres/repo"
	redisInfra "github.com/nhanntv/tutor-airobot-be/internal/infrastructure/redis"
	httpServer "github.com/nhanntv/tutor-airobot-be/internal/interfaces/http"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/handler"
	dbmigrations "github.com/nhanntv/tutor-airobot-be/migrations"
	"github.com/nhanntv/tutor-airobot-be/pkg/logger"
)

const version = "1.0.0"

func main() {
	// ── 1. Load configuration ─────────────────────────────────────────────────
	cfg, err := configs.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("failed to load configuration")
	}

	// ── 2. Initialise logger ──────────────────────────────────────────────────
	logger.Init(cfg.LogLevel, cfg.IsDevelopment())

	log.Info().
		Str("version", version).
		Str("env", cfg.AppEnv).
		Msg("starting tutor-airobot-be")

	ctx := context.Background()

	// ── 3. Connect to Postgres (pgxpool for the app) ──────────────────────────
	pool, err := postgres.NewPool(ctx, cfg.DatabaseURL, cfg.DBMaxConns, cfg.DBMinConns)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to postgres")
	}
	defer pool.Close()

	// ── 4. Connect to Redis ───────────────────────────────────────────────────
	redisClient, err := redisInfra.NewClient(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to redis")
	}
	defer redisClient.Close()

	// ── 5. Run database migrations (goose requires database/sql) ──────────────
	sqlDB, err := sql.Open("pgx", cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to open sql.DB for migrations")
	}
	defer sqlDB.Close()

	goose.SetBaseFS(dbmigrations.FS)
	if err = goose.SetDialect("postgres"); err != nil {
		log.Fatal().Err(err).Msg("failed to set goose dialect")
	}
	if err = goose.Up(sqlDB, "."); err != nil {
		log.Fatal().Err(err).Msg("failed to run migrations")
	}
	log.Info().Msg("migrations applied successfully")

	// ── 6. Create repositories ────────────────────────────────────────────────
	providerRepo := repo.NewProviderRepo(pool)
	promptRepo := repo.NewPromptRepo(pool)
	analysisRepo := repo.NewAnalysisRepo(pool)
	deviceRepo := repo.NewDeviceRepo(pool)
	adminRepo := repo.NewAdminRepo(pool)

	// ── 7. Create infrastructure services ────────────────────────────────────
	imageProc := imageInfra.NewProcessor(cfg.MaxImageSizeMB)
	aiFactory := aiInfra.NewDefaultFactory()
	blacklist := redisInfra.NewJWTBlacklist(redisClient)
	rateLimiter := redisInfra.NewRateLimiter(redisClient)
	statsCache := redisInfra.NewStats(redisClient)

	// ── 8. Create use cases ───────────────────────────────────────────────────

	// Auth
	loginUC := appAuth.NewLoginUseCase(adminRepo, cfg.JWTSecret, cfg.JWTAccessExpiryMin, cfg.JWTRefreshExpiryDays)
	refreshUC := appAuth.NewRefreshUseCase(adminRepo, cfg.JWTSecret, cfg.JWTAccessExpiryMin)
	logoutUC := appAuth.NewLogoutUseCase(statsCache)

	// Provider
	createProviderUC := appProvider.NewCreateProviderUseCase(providerRepo, cfg.AESMasterKey)
	updateProviderUC := appProvider.NewUpdateProviderUseCase(providerRepo, cfg.AESMasterKey)
	deleteProviderUC := appProvider.NewDeleteProviderUseCase(providerRepo)
	listProviderUC := appProvider.NewListProvidersUseCase(providerRepo)
	getProviderUC := appProvider.NewGetProviderUseCase(providerRepo)
	testProviderUC := appProvider.NewTestConnectionUseCase(providerRepo, aiFactory, cfg.AESMasterKey)

	// Prompt
	createPromptUC := appPrompt.NewCreatePromptUseCase(promptRepo)
	updatePromptUC := appPrompt.NewUpdatePromptUseCase(promptRepo)
	deletePromptUC := appPrompt.NewDeletePromptUseCase(promptRepo)
	listPromptUC := appPrompt.NewListPromptsUseCase(promptRepo)

	// Device
	createDeviceUC := appDevice.NewCreateDeviceUseCase(deviceRepo)
	revokeDeviceUC := appDevice.NewRevokeDeviceUseCase(deviceRepo)
	listDeviceUC := appDevice.NewListDevicesUseCase(deviceRepo)

	// Analysis
	analyzeUC := appAnalysis.NewAnalyzeUseCase(imageProc, aiFactory, providerRepo, analysisRepo, cfg.AESMasterKey)
	listAnalysesUC := appAnalysis.NewListAnalysesUseCase(analysisRepo, deviceRepo, providerRepo)

	// ── 9. Create HTTP handlers ───────────────────────────────────────────────
	handlers := &httpServer.Handlers{
		Health: handler.NewHealthHandler(pool, redisClient, version),
		Auth:   handler.NewAuthHandler(loginUC, refreshUC, logoutUC, cfg.JWTRefreshExpiryDays),
		Provider: handler.NewProviderHandler(
			createProviderUC, updateProviderUC, deleteProviderUC,
			listProviderUC, getProviderUC, testProviderUC,
		),
		Prompt: handler.NewPromptHandler(
			createPromptUC, updatePromptUC, deletePromptUC, listPromptUC,
		),
		Device:   handler.NewDeviceHandler(createDeviceUC, revokeDeviceUC, listDeviceUC),
		Analysis: handler.NewAnalysisHandler(analyzeUC, listAnalysesUC),
		Stats:    handler.NewStatsHandler(analysisRepo, deviceRepo, providerRepo),
	}

	// ── 10. Create HTTP server and register routes ────────────────────────────
	srv := httpServer.New(cfg)
	srv.RegisterRoutes(handlers, httpServer.MiddlewareDeps{
		Config:      cfg,
		DeviceRepo:  deviceRepo,
		Blacklist:   blacklist,
		RateLimiter: rateLimiter,
	})

	// ── 11. Start server with graceful shutdown ───────────────────────────────
	addr := ":" + cfg.AppPort
	log.Info().Str("addr", addr).Msg("HTTP server starting")

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	go func() {
		if startErr := srv.Start(addr); startErr != nil {
			log.Error().Err(startErr).Msg("server stopped")
		}
	}()

	<-quit
	log.Info().Msg("shutdown signal received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if shutdownErr := srv.Shutdown(shutdownCtx); shutdownErr != nil {
		log.Error().Err(shutdownErr).Msg("graceful shutdown failed")
	} else {
		log.Info().Msg("server shut down cleanly")
	}
}
