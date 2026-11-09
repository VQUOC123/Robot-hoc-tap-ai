package http

import (
	"context"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/configs"
)

// Server wraps a Fiber application with graceful shutdown support.
type Server struct {
	app *fiber.App
}

// New creates a configured Fiber application with sensible production defaults.
func New(cfg *configs.Config) *Server {
	app := fiber.New(fiber.Config{
		// Body size limit: MaxImageSizeMB + 1 MB for form fields
		BodyLimit: (cfg.MaxImageSizeMB + 1) * 1024 * 1024,

		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,

		// Disable default error handler — our Recover middleware handles panics
		ErrorHandler: func(c fiber.Ctx, err error) error {
			code := fiber.StatusInternalServerError
			if e, ok := err.(*fiber.Error); ok {
				code = e.Code
			}
			return c.Status(code).JSON(fiber.Map{
				"error": fiber.Map{
					"code":    fmt.Sprintf("%d", code),
					"message": err.Error(),
				},
			})
		},
	})

	return &Server{app: app}
}

// RegisterRoutes wires all HTTP routes to the Fiber application.
func (s *Server) RegisterRoutes(h *Handlers, deps MiddlewareDeps) {
	SetupRoutes(s.app, h, deps)
}

// Start begins listening on the given address (e.g. ":8080").
func (s *Server) Start(addr string) error {
	return s.app.Listen(addr)
}

// Shutdown gracefully stops the server, waiting for in-flight requests up to the deadline.
func (s *Server) Shutdown(ctx context.Context) error {
	return s.app.ShutdownWithContext(ctx)
}
