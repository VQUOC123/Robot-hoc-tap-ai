package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// RefreshUseCase validates a refresh token and issues a new access token.
type RefreshUseCase struct {
	adminRepo         repository.AdminRepository
	jwtSecret         string
	accessExpiryMin   int
}

// NewRefreshUseCase creates a RefreshUseCase.
func NewRefreshUseCase(
	adminRepo repository.AdminRepository,
	jwtSecret string,
	accessExpiryMin int,
) *RefreshUseCase {
	return &RefreshUseCase{
		adminRepo:       adminRepo,
		jwtSecret:       jwtSecret,
		accessExpiryMin: accessExpiryMin,
	}
}

// Execute validates the refresh token and returns a new access token.
func (uc *RefreshUseCase) Execute(ctx context.Context, refreshToken string) (RefreshOutput, error) {
	token, err := jwt.ParseWithClaims(refreshToken, &AdminClaims{}, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return []byte(uc.jwtSecret), nil
	})
	if err != nil || !token.Valid {
		return RefreshOutput{}, apperror.Unauthorized("invalid or expired refresh token")
	}

	claims, ok := token.Claims.(*AdminClaims)
	if !ok {
		return RefreshOutput{}, apperror.Unauthorized("malformed refresh token claims")
	}

	adminID, err := uuid.Parse(claims.Subject)
	if err != nil {
		return RefreshOutput{}, apperror.Unauthorized("invalid subject in refresh token")
	}

	admin, err := uc.adminRepo.GetByID(ctx, adminID)
	if err != nil {
		return RefreshOutput{}, apperror.Unauthorized("admin user not found")
	}

	now := time.Now()
	newJTI := uuid.New().String()
	accessClaims := AdminClaims{
		Email: admin.Email,
		Role:  string(admin.Role),
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   admin.ID.String(),
			ID:        newJTI,
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Duration(uc.accessExpiryMin) * time.Minute)),
			IssuedAt:  jwt.NewNumericDate(now),
		},
	}

	accessToken, err := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims).
		SignedString([]byte(uc.jwtSecret))
	if err != nil {
		return RefreshOutput{}, fmt.Errorf("refresh: sign access token: %w", err)
	}

	return RefreshOutput{AccessToken: accessToken}, nil
}
