package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"golang.org/x/crypto/bcrypt"
)

// AdminClaims are the JWT claims stored in both access and refresh tokens.
type AdminClaims struct {
	Email string `json:"email,omitempty"`
	Role  string `json:"role,omitempty"`
	jwt.RegisteredClaims
}

// LoginUseCase authenticates an admin user and issues a JWT pair.
type LoginUseCase struct {
	adminRepo          repository.AdminRepository
	jwtSecret          string
	accessExpiryMin    int
	refreshExpiryDays  int
}

// NewLoginUseCase creates a LoginUseCase with the given dependencies.
func NewLoginUseCase(
	adminRepo repository.AdminRepository,
	jwtSecret string,
	accessExpiryMin, refreshExpiryDays int,
) *LoginUseCase {
	return &LoginUseCase{
		adminRepo:         adminRepo,
		jwtSecret:         jwtSecret,
		accessExpiryMin:   accessExpiryMin,
		refreshExpiryDays: refreshExpiryDays,
	}
}

// Execute verifies the credentials and returns an access token, refresh token, and user info.
func (uc *LoginUseCase) Execute(ctx context.Context, input LoginInput) (LoginOutput, string, error) {
	admin, err := uc.adminRepo.GetByEmail(ctx, input.Email)
	if err != nil {
		// Return generic error to avoid email enumeration
		return LoginOutput{}, "", apperror.Unauthorized("invalid email or password")
	}

	if err = bcrypt.CompareHashAndPassword([]byte(admin.PasswordHash), []byte(input.Password)); err != nil {
		return LoginOutput{}, "", apperror.Unauthorized("invalid email or password")
	}

	now := time.Now()

	// Access token — short-lived
	accessJTI := uuid.New().String()
	accessClaims := AdminClaims{
		Email: admin.Email,
		Role:  string(admin.Role),
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   admin.ID.String(),
			ID:        accessJTI,
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Duration(uc.accessExpiryMin) * time.Minute)),
			IssuedAt:  jwt.NewNumericDate(now),
		},
	}
	accessToken, err := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims).
		SignedString([]byte(uc.jwtSecret))
	if err != nil {
		return LoginOutput{}, "", fmt.Errorf("login: sign access token: %w", err)
	}

	// Refresh token — long-lived, no email/role to minimise payload
	refreshJTI := uuid.New().String()
	refreshClaims := AdminClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   admin.ID.String(),
			ID:        refreshJTI,
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Duration(uc.refreshExpiryDays) * 24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(now),
		},
	}
	refreshToken, err := jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims).
		SignedString([]byte(uc.jwtSecret))
	if err != nil {
		return LoginOutput{}, "", fmt.Errorf("login: sign refresh token: %w", err)
	}

	_ = uc.adminRepo.UpdateLastLogin(ctx, admin.ID)

	output := LoginOutput{
		AccessToken: accessToken,
		User: UserInfo{
			ID:    admin.ID,
			Email: admin.Email,
			Role:  string(admin.Role),
		},
	}

	return output, refreshToken, nil
}
