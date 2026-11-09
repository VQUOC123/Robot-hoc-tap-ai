package middleware

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"

	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// DeviceAuth returns a middleware that authenticates edge devices via bearer token.
// It computes SHA-256(token) → looks up in device repo → injects device into locals.
// Last-used timestamp and IP are updated in the background on each successful request.
func DeviceAuth(deviceRepo repository.DeviceRepository) fiber.Handler {
	return func(c fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return httputil.Unauthorized(c)
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			return httputil.Unauthorized(c)
		}

		rawToken := strings.TrimSpace(parts[1])
		if rawToken == "" {
			return httputil.Unauthorized(c)
		}

		// SHA-256 hash to look up in the database
		sum := sha256.Sum256([]byte(rawToken))
		tokenHash := hex.EncodeToString(sum[:])

		device, err := deviceRepo.GetByTokenHash(c.Context(), tokenHash)
		if err != nil {
			return httputil.Unauthorized(c)
		}

		// Inject device into locals for downstream handlers
		c.Locals("device", device)

		// Update last_used_at and IP in background to avoid blocking response
		deviceID := device.ID
		ip := c.IP()
		go func() {
			_ = deviceRepo.UpdateLastUsed(c.Context(), deviceID, ip)
		}()

		return c.Next()
	}
}
