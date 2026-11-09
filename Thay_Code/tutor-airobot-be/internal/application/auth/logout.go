package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
)

// LogoutUseCase blacklists the current access token's JTI in the cache.
type LogoutUseCase struct {
	cache service.Cache
}

// NewLogoutUseCase creates a LogoutUseCase.
func NewLogoutUseCase(cache service.Cache) *LogoutUseCase {
	return &LogoutUseCase{cache: cache}
}

// Execute adds the JTI to the blacklist so the token cannot be reused after logout.
// ttl should be the remaining lifetime of the access token.
func (uc *LogoutUseCase) Execute(ctx context.Context, jti string, ttl time.Duration) error {
	if jti == "" {
		return fmt.Errorf("logout: jti is required")
	}
	if ttl <= 0 {
		// Token already expired — nothing to blacklist
		return nil
	}
	if err := uc.cache.SetBlacklist(ctx, jti, ttl); err != nil {
		return fmt.Errorf("logout: blacklist token: %w", err)
	}
	return nil
}
