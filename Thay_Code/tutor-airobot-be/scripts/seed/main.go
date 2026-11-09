package main

import (
	"context"
	"fmt"
	"os"

	"github.com/joho/godotenv"
	"github.com/rs/zerolog/log"
	"golang.org/x/crypto/bcrypt"

	"github.com/nhanntv/tutor-airobot-be/configs"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/crypto"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/postgres"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/postgres/repo"
	"github.com/nhanntv/tutor-airobot-be/pkg/logger"
)

const (
	adminEmail    = "admin@tutor.local"
	adminPassword = "admin123"
)

func main() {
	_ = godotenv.Load()

	cfg, err := configs.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "config error: %v\n", err)
		os.Exit(1)
	}

	logger.Init(cfg.LogLevel, true)
	ctx := context.Background()

	// Connect to database
	pool, err := postgres.NewPool(ctx, cfg.DatabaseURL, 5, 1)
	if err != nil {
		log.Fatal().Err(err).Msg("database connection failed")
	}
	defer pool.Close()

	adminRepo := repo.NewAdminRepo(pool)
	providerRepo := repo.NewProviderRepo(pool)
	promptRepo := repo.NewPromptRepo(pool)

	// ── 1. Seed admin user ─────────────────────────────────────────────────────
	existing, _ := adminRepo.GetByEmail(ctx, adminEmail)
	if existing != nil {
		log.Info().Str("email", adminEmail).Msg("admin user already exists, skipping")
	} else {
		hash, bcryptErr := bcrypt.GenerateFromPassword([]byte(adminPassword), bcrypt.DefaultCost)
		if bcryptErr != nil {
			log.Fatal().Err(bcryptErr).Msg("bcrypt failed")
		}
		admin := &entity.AdminUser{
			Email:        adminEmail,
			PasswordHash: string(hash),
			Role:         entity.RoleAdmin,
		}
		if _, createErr := adminRepo.Create(ctx, admin); createErr != nil {
			log.Fatal().Err(createErr).Msg("failed to create admin user")
		}
		log.Info().Str("email", adminEmail).Msg("admin user created")
	}

	// ── 2. Seed demo provider ──────────────────────────────────────────────────
	existingProviders, _ := providerRepo.List(ctx)
	if len(existingProviders) > 0 {
		log.Info().Msg("providers already exist, skipping provider seed")
	} else {
		placeholderKey := "sk-placeholder-replace-with-real-key"
		encKey, encErr := crypto.Encrypt([]byte(placeholderKey), cfg.AESMasterKey)
		if encErr != nil {
			log.Fatal().Err(encErr).Msg("failed to encrypt demo API key")
		}

		provider := &entity.Provider{
			Name:       "LiteLLM Proxy (Demo)",
			BaseURL:    "http://localhost:4000",
			APIKeyEnc:  encKey,
			Model:      "gpt-4o-mini",
			TimeoutSec: 30,
			IsDefault:  true,
			IsActive:   true,
		}
		if _, createErr := providerRepo.Create(ctx, provider); createErr != nil {
			log.Fatal().Err(createErr).Msg("failed to create demo provider")
		}
		log.Info().Str("name", provider.Name).Msg("demo provider created")
	}

	// ── 3. Seed default Stage 1 prompt ────────────────────────────────────────
	stage1Filter := repository.PromptFilter{Stage: 1}
	existingPrompts, _ := promptRepo.List(ctx, stage1Filter)
	if len(existingPrompts) > 0 {
		log.Info().Msg("stage 1 prompt already exists, skipping")
	} else {
		stage1Content := `Analyze this student workspace image. Reply with JSON only (no markdown):
{"doing_hw":<true|false>,"conf":<0.0-1.0>}
doing_hw=true ONLY if the student is clearly doing school homework (books, notebooks, writing).`

		prompt1 := &entity.Prompt{
			Name:     "Default Stage 1 - Homework Detection",
			Stage:    entity.Stage1,
			Content:  stage1Content,
			IsActive: true,
			Version:  1,
		}
		if _, createErr := promptRepo.Create(ctx, prompt1); createErr != nil {
			log.Fatal().Err(createErr).Msg("failed to create stage 1 prompt")
		}
		log.Info().Str("name", prompt1.Name).Msg("stage 1 prompt created")
	}

	// ── 4. Seed default Stage 2 prompt ────────────────────────────────────────
	stage2Filter := repository.PromptFilter{Stage: 2}
	stage2Prompts, _ := promptRepo.List(ctx, stage2Filter)
	if len(stage2Prompts) > 0 {
		log.Info().Msg("stage 2 prompt already exists, skipping")
	} else {
		stage2Content := `The student in this image is doing homework. Analyze and reply with JSON only (no markdown):
{"subject":"<Toán/Văn/Tiếng Anh/Lý/Hóa/Sinh/Sử/Địa/Tin/other>","grade":"<1-12 or null>","hw_type":"<bài tập/luận văn/đọc hiểu/lý thuyết/other>","progress":<0-100>,"hints":"<1-2 sentences Vietnamese hint to help the student>"}
Be concise and helpful. Hints should be encouraging and specific to the subject.`

		prompt2 := &entity.Prompt{
			Name:     "Default Stage 2 - Homework Analysis",
			Stage:    entity.Stage2,
			Content:  stage2Content,
			IsActive: true,
			Version:  1,
		}
		if _, createErr := promptRepo.Create(ctx, prompt2); createErr != nil {
			log.Fatal().Err(createErr).Msg("failed to create stage 2 prompt")
		}
		log.Info().Str("name", prompt2.Name).Msg("stage 2 prompt created")
	}

	fmt.Println()
	fmt.Println("Seeding complete!")
	fmt.Println()
	fmt.Println("Admin credentials:")
	fmt.Printf("  Email:    %s\n", adminEmail)
	fmt.Printf("  Password: %s\n", adminPassword)
	fmt.Println()
	fmt.Println("Next steps:")
	fmt.Println("  1. Replace the demo provider's placeholder API key via the admin UI")
	fmt.Println("  2. Register a device: POST /api/v1/devices  (AdminAuth required)")
	fmt.Println("  3. Use the returned token as:  Authorization: Bearer <token>")
	fmt.Println("  4. Submit images: POST /api/v1/device/analyze  (DeviceAuth)")
	fmt.Println()
}
