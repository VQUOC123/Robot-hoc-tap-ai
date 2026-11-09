package configs

import (
	"fmt"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config holds all application configuration loaded from environment variables.
// Values are read once at startup — no runtime reloading.
type Config struct {
	// Server
	AppPort string
	AppEnv  string

	// Database
	DatabaseURL string
	DBMaxConns  int
	DBMinConns  int

	// Redis
	RedisURL string

	// Security
	JWTSecret    string
	AESMasterKey string

	// CORS
	AdminFrontendURL string

	// Logging
	LogLevel string

	// Rate Limiting
	RateLimitDeviceRPM int
	RateLimitAuthRPM   int
	RateLimitAdminRPM  int

	// AI
	DefaultAITimeoutSec int
	MaxImageSizeMB      int

	// JWT Expiry
	JWTAccessExpiryMin   int
	JWTRefreshExpiryDays int
}

// Load reads .env (if present) then environment variables.
// Returns error if any required variable is missing.
func Load() (*Config, error) {
	// Load .env file — ignore error if file does not exist (production uses real env vars)
	_ = godotenv.Load()

	cfg := &Config{
		AppPort: getEnv("APP_PORT", "8080"),
		AppEnv:  getEnv("APP_ENV", "development"),

		DatabaseURL: getEnv("DATABASE_URL", ""),
		DBMaxConns:  getEnvInt("DB_MAX_CONNS", 20),
		DBMinConns:  getEnvInt("DB_MIN_CONNS", 5),

		RedisURL: getEnv("REDIS_URL", "redis://localhost:6379/0"),

		JWTSecret:    getEnv("JWT_SECRET", ""),
		AESMasterKey: getEnv("AES_MASTER_KEY", ""),

		AdminFrontendURL: getEnv("ADMIN_FRONTEND_URL", "http://localhost:5173"),

		LogLevel: getEnv("LOG_LEVEL", "info"),

		RateLimitDeviceRPM: getEnvInt("RATE_LIMIT_DEVICE_RPM", 20),
		RateLimitAuthRPM:   getEnvInt("RATE_LIMIT_AUTH_RPM", 5),
		RateLimitAdminRPM:  getEnvInt("RATE_LIMIT_ADMIN_RPM", 300),

		DefaultAITimeoutSec: getEnvInt("DEFAULT_AI_TIMEOUT_SEC", 30),
		MaxImageSizeMB:      getEnvInt("MAX_IMAGE_SIZE_MB", 5),

		JWTAccessExpiryMin:   getEnvInt("JWT_ACCESS_EXPIRY_MIN", 15),
		JWTRefreshExpiryDays: getEnvInt("JWT_REFRESH_EXPIRY_DAYS", 7),
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

func (c *Config) validate() error {
	required := map[string]string{
		"DATABASE_URL":  c.DatabaseURL,
		"JWT_SECRET":    c.JWTSecret,
		"AES_MASTER_KEY": c.AESMasterKey,
	}
	for key, val := range required {
		if val == "" {
			return fmt.Errorf("required env var %s is not set", key)
		}
	}
	if len(c.JWTSecret) < 32 {
		return fmt.Errorf("JWT_SECRET must be at least 32 characters")
	}
	return nil
}

func (c *Config) IsDevelopment() bool {
	return c.AppEnv == "development"
}

// ── helpers ──────────────────────────────────────────────────────────────────

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

func getEnvInt(key string, defaultVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return defaultVal
	}
	return n
}
