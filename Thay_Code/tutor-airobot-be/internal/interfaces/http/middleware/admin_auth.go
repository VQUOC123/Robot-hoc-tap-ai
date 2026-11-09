package middleware

import (
	"fmt"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/redis"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// AdminClaims mirrors the claims structure used in auth/login.go.
type AdminClaims struct {
	Email string `json:"email,omitempty"`
	Role  string `json:"role,omitempty"`
	jwt.RegisteredClaims
}

// AdminAuth returns a middleware that validates admin JWT access tokens.
// It rejects tokens whose JTI appears in the Redis blacklist (i.e. logged-out tokens).
func AdminAuth(jwtSecret string, blacklist *redis.JWTBlacklist) fiber.Handler {
	return func(c fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return httputil.Unauthorized(c)
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			return httputil.Unauthorized(c)
		}

		tokenStr := strings.TrimSpace(parts[1])

		claims := &AdminClaims{}
		token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
			}
			return []byte(jwtSecret), nil
		})
		if err != nil || !token.Valid {
			return httputil.Unauthorized(c)
		}

		// Check blacklist (token revoked via logout)
		if blacklist != nil {
			jti := claims.ID
			if jti != "" {
				blacklisted, blErr := blacklist.IsBlacklisted(c.Context(), jti)
				if blErr == nil && blacklisted {
					return httputil.Unauthorized(c)
				}
			}
		}

		c.Locals("claims", claims)
		return c.Next()
	}
}
