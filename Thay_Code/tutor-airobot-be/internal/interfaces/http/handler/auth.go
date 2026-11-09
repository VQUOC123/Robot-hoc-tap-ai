package handler

import (
	"errors"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/internal/application/auth"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/dto/request"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/middleware"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
	"github.com/nhanntv/tutor-airobot-be/pkg/validator"
)

const refreshCookieName = "refresh_token"

// AuthHandler handles admin authentication endpoints.
type AuthHandler struct {
	loginUC   *auth.LoginUseCase
	refreshUC *auth.RefreshUseCase
	logoutUC  *auth.LogoutUseCase
	refreshExpiryDays int
}

// NewAuthHandler creates an AuthHandler.
func NewAuthHandler(
	loginUC *auth.LoginUseCase,
	refreshUC *auth.RefreshUseCase,
	logoutUC *auth.LogoutUseCase,
	refreshExpiryDays int,
) *AuthHandler {
	return &AuthHandler{
		loginUC:           loginUC,
		refreshUC:         refreshUC,
		logoutUC:          logoutUC,
		refreshExpiryDays: refreshExpiryDays,
	}
}

// Login authenticates the admin, sets a refresh-token HttpOnly cookie, and returns the access token.
func (h *AuthHandler) Login(c fiber.Ctx) error {
	var req request.LoginRequest
	if err := c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	output, refreshToken, err := h.loginUC.Execute(c.Context(), auth.LoginInput{
		Email:    req.Email,
		Password: req.Password,
	})
	if err != nil {
		if errors.Is(err, apperror.ErrUnauthorized) {
			return httputil.Unauthorized(c)
		}
		return httputil.InternalError(c)
	}

	// Set refresh token as HttpOnly cookie
	c.Cookie(&fiber.Cookie{
		Name:     refreshCookieName,
		Value:    refreshToken,
		HTTPOnly: true,
		Secure:   true,
		SameSite: "Strict",
		MaxAge:   h.refreshExpiryDays * 24 * 60 * 60,
		Path:     "/",
	})

	return httputil.OK(c, output)
}

// Refresh reads the refresh-token cookie and returns a new access token.
func (h *AuthHandler) Refresh(c fiber.Ctx) error {
	refreshToken := c.Cookies(refreshCookieName)
	if refreshToken == "" {
		return httputil.Unauthorized(c)
	}

	output, err := h.refreshUC.Execute(c.Context(), refreshToken)
	if err != nil {
		return httputil.Unauthorized(c)
	}

	return httputil.OK(c, output)
}

// Logout blacklists the current access token JTI and clears the refresh cookie.
func (h *AuthHandler) Logout(c fiber.Ctx) error {
	claims, ok := c.Locals("claims").(*middleware.AdminClaims)
	if !ok || claims == nil {
		return httputil.Unauthorized(c)
	}

	// Calculate remaining TTL from token expiry
	var ttl time.Duration
	if exp := claims.ExpiresAt; exp != nil {
		ttl = time.Until(exp.Time)
	}

	if err := h.logoutUC.Execute(c.Context(), claims.ID, ttl); err != nil {
		return httputil.InternalError(c)
	}

	// Clear the refresh cookie
	c.Cookie(&fiber.Cookie{
		Name:    refreshCookieName,
		Value:   "",
		MaxAge:  -1,
		Path:    "/",
	})

	return httputil.NoContent(c)
}
