package redis

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

const blacklistPrefix = "jwt:blacklist:"

// JWTBlacklist stores invalidated JWT IDs in Redis until they expire naturally.
// Tokens are keyed by their jti claim.
type JWTBlacklist struct {
	client *redis.Client
}

// NewJWTBlacklist creates a JWTBlacklist using the given Redis client.
func NewJWTBlacklist(client *redis.Client) *JWTBlacklist {
	return &JWTBlacklist{client: client}
}

// Add registers a JWT ID as blacklisted for the given TTL.
// The TTL should match the remaining lifetime of the token.
func (b *JWTBlacklist) Add(ctx context.Context, jti string, ttl time.Duration) error {
	key := blacklistPrefix + jti
	if err := b.client.Set(ctx, key, "1", ttl).Err(); err != nil {
		return fmt.Errorf("jwt_blacklist: add %s: %w", jti, err)
	}
	return nil
}

// IsBlacklisted reports whether the given JWT ID has been revoked.
func (b *JWTBlacklist) IsBlacklisted(ctx context.Context, jti string) (bool, error) {
	key := blacklistPrefix + jti
	err := b.client.Get(ctx, key).Err()
	if err == redis.Nil {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("jwt_blacklist: check %s: %w", jti, err)
	}
	return true, nil
}
