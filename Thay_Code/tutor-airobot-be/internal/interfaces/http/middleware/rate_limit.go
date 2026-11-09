package middleware

import (
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/redis"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// RateLimitDevice returns a per-device sliding-window rate limiter.
// The bucket key is "rate:device:<device_id>".
func RateLimitDevice(limiter *redis.RateLimiter, rpm int) fiber.Handler {
	return func(c fiber.Ctx) error {
		device, ok := c.Locals("device").(*entity.Device)
		if !ok || device == nil {
			return httputil.Unauthorized(c)
		}

		key := "rate:device:" + device.ID.String()
		allowed, err := limiter.Allow(c.Context(), key, rpm, time.Minute)
		if err != nil {
			// Fail open on Redis errors to avoid blocking legitimate traffic
			return c.Next()
		}
		if !allowed {
			return httputil.Fail(c, fiber.StatusTooManyRequests, "RATE_LIMITED", "too many requests, please slow down")
		}
		return c.Next()
	}
}

// RateLimitIP returns a per-IP sliding-window rate limiter.
// The bucket key is "rate:ip:<ip>".
func RateLimitIP(limiter *redis.RateLimiter, rpm int) fiber.Handler {
	return func(c fiber.Ctx) error {
		key := "rate:ip:" + c.IP()
		allowed, err := limiter.Allow(c.Context(), key, rpm, time.Minute)
		if err != nil {
			return c.Next()
		}
		if !allowed {
			return httputil.Fail(c, fiber.StatusTooManyRequests, "RATE_LIMITED", "too many requests, please slow down")
		}
		return c.Next()
	}
}

// RateLimitAdmin returns a per-IP rate limiter suited for admin API endpoints.
func RateLimitAdmin(limiter *redis.RateLimiter, rpm int) fiber.Handler {
	return RateLimitIP(limiter, rpm)
}
