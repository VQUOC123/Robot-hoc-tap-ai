package pagination

import (
	"encoding/base64"
	"fmt"
	"time"
)

const DefaultLimit = 20
const MaxLimit = 100

// DecodeCursor decodes a base64 cursor string into a time.Time value.
// Returns zero time and no error when cursor is empty (first page).
func DecodeCursor(cursor string) (time.Time, error) {
	if cursor == "" {
		return time.Time{}, nil
	}
	b, err := base64.StdEncoding.DecodeString(cursor)
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid cursor encoding")
	}
	t, err := time.Parse(time.RFC3339Nano, string(b))
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid cursor format")
	}
	return t, nil
}

// EncodeCursor encodes a time.Time into a base64 cursor string.
func EncodeCursor(t time.Time) string {
	return base64.StdEncoding.EncodeToString([]byte(t.Format(time.RFC3339Nano)))
}

// NormalizeLimit clamps limit to [1, MaxLimit].
// Returns DefaultLimit when limit <= 0.
func NormalizeLimit(limit int) int {
	if limit <= 0 {
		return DefaultLimit
	}
	if limit > MaxLimit {
		return MaxLimit
	}
	return limit
}
