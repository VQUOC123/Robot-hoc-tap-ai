package middleware

import (
	"fmt"
	"runtime/debug"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// Recover returns a middleware that catches panics, logs the stack trace,
// and responds with a 500 Internal Server Error.
func Recover() fiber.Handler {
	return func(c fiber.Ctx) (err error) {
		defer func() {
			if r := recover(); r != nil {
				stack := debug.Stack()
				log.Error().
					Str("panic", fmt.Sprintf("%v", r)).
					Bytes("stack", stack).
					Str("method", c.Method()).
					Str("path", c.Path()).
					Msg("recovered from panic")

				err = httputil.InternalError(c)
			}
		}()
		return c.Next()
	}
}
