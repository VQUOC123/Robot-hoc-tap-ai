package middleware

import (
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"
)

// RequestLogger returns a middleware that logs each HTTP request using zerolog.
// Fields logged: method, path, status, latency (ms), ip.
func RequestLogger() fiber.Handler {
	return func(c fiber.Ctx) error {
		start := time.Now()

		// Process request
		err := c.Next()

		latency := time.Since(start)
		status := c.Response().StatusCode()

		event := log.Info()
		if status >= 500 {
			event = log.Error()
		} else if status >= 400 {
			event = log.Warn()
		}

		event.
			Str("method", c.Method()).
			Str("path", c.Path()).
			Int("status", status).
			Int64("latency_ms", latency.Milliseconds()).
			Str("ip", c.IP()).
			Msg("http request")

		return err
	}
}
