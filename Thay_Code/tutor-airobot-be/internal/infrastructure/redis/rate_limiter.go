package redis

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// RateLimiter implements a sliding-window rate limiter backed by Redis sorted sets.
// Each request is recorded as a ZADD member with score = unix nanosecond timestamp.
// Expired members (older than window) are pruned before counting.
type RateLimiter struct {
	client *redis.Client
}

// NewRateLimiter creates a RateLimiter using the given Redis client.
func NewRateLimiter(client *redis.Client) *RateLimiter {
	return &RateLimiter{client: client}
}

// Allow returns true when the caller is within the rate limit.
// key identifies the rate-limit bucket (e.g. "rate:device:<id>").
// limit is the maximum number of requests allowed within window.
func (r *RateLimiter) Allow(ctx context.Context, key string, limit int, window time.Duration) (bool, error) {
	now := time.Now()
	windowStart := float64(now.Add(-window).UnixNano())
	nowStr := strconv.FormatInt(now.UnixNano(), 10)

	pipe := r.client.Pipeline()

	// Remove entries older than the window
	pipe.ZRemRangeByScore(ctx, key, "-inf", fmt.Sprintf("%f", windowStart))
	// Add current request
	pipe.ZAdd(ctx, key, redis.Z{Score: float64(now.UnixNano()), Member: nowStr})
	// Count entries in window
	countCmd := pipe.ZCard(ctx, key)
	// Set key expiry to avoid orphaned keys
	pipe.Expire(ctx, key, window+time.Second)

	if _, err := pipe.Exec(ctx); err != nil {
		return false, fmt.Errorf("rate_limiter: pipeline exec: %w", err)
	}

	count := countCmd.Val()
	return count <= int64(limit), nil
}
