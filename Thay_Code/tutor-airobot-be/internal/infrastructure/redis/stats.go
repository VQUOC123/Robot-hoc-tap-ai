package redis

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
)

// Ensure Stats implements service.Cache at compile time.
var _ service.Cache = (*Stats)(nil)

const (
	blacklistKeyPrefix = "jwt:bl:"
	counterTTL         = 25 * time.Hour // slightly longer than a day for safety
)

// Stats implements the Cache interface's counter and blacklist operations.
// It is designed to be embedded or composed into a combined cache adapter.
type Stats struct {
	client *redis.Client
}

// NewStats creates a Stats instance backed by the given Redis client.
func NewStats(client *redis.Client) *Stats {
	return &Stats{client: client}
}

// IncrAndExpire atomically increments key and sets its TTL on first creation.
func (s *Stats) IncrAndExpire(ctx context.Context, key string, ttl time.Duration) (int64, error) {
	pipe := s.client.Pipeline()
	incrCmd := pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, ttl)
	if _, err := pipe.Exec(ctx); err != nil {
		return 0, fmt.Errorf("stats.IncrAndExpire %s: %w", key, err)
	}
	return incrCmd.Val(), nil
}

// SetBlacklist adds jti to the JWT blacklist with the given TTL.
func (s *Stats) SetBlacklist(ctx context.Context, jti string, ttl time.Duration) error {
	key := blacklistKeyPrefix + jti
	if err := s.client.Set(ctx, key, "1", ttl).Err(); err != nil {
		return fmt.Errorf("stats.SetBlacklist: %w", err)
	}
	return nil
}

// IsBlacklisted reports whether jti is in the blacklist.
func (s *Stats) IsBlacklisted(ctx context.Context, jti string) (bool, error) {
	key := blacklistKeyPrefix + jti
	err := s.client.Get(ctx, key).Err()
	if err == redis.Nil {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("stats.IsBlacklisted: %w", err)
	}
	return true, nil
}

// IncrCounter increments a named counter. Sets a 25-hour TTL on first creation.
func (s *Stats) IncrCounter(ctx context.Context, key string) error {
	pipe := s.client.Pipeline()
	pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, counterTTL)
	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("stats.IncrCounter %s: %w", key, err)
	}
	return nil
}

// GetCounter returns the current value of a named counter. Returns 0 when missing.
func (s *Stats) GetCounter(ctx context.Context, key string) (int64, error) {
	val, err := s.client.Get(ctx, key).Int64()
	if err == redis.Nil {
		return 0, nil
	}
	if err != nil {
		return 0, fmt.Errorf("stats.GetCounter %s: %w", key, err)
	}
	return val, nil
}
