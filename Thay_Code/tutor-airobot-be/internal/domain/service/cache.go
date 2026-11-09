package service

import (
	"context"
	"time"
)

// Cache abstracts Redis operations used by rate limiting and JWT blacklisting.
type Cache interface {
	// IncrAndExpire atomically increments a counter and sets its TTL on first creation.
	// Returns the new counter value.
	IncrAndExpire(ctx context.Context, key string, ttl time.Duration) (int64, error)

	// SetBlacklist adds a JWT ID (jti) to the blacklist with the given TTL.
	SetBlacklist(ctx context.Context, jti string, ttl time.Duration) error

	// IsBlacklisted reports whether a JWT ID is in the blacklist.
	IsBlacklisted(ctx context.Context, jti string) (bool, error)

	// IncrCounter increments a named counter, setting a 24-hour TTL on first creation.
	IncrCounter(ctx context.Context, key string) error

	// GetCounter returns the current value of a named counter.
	// Returns 0 without error when the key does not exist.
	GetCounter(ctx context.Context, key string) (int64, error)
}
