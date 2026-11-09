package timeutil

import "time"

// NowUTC returns the current time in UTC.
func NowUTC() time.Time {
	return time.Now().UTC()
}

// StartOfDay returns 00:00:00 UTC for the given time.
func StartOfDay(t time.Time) time.Time {
	y, m, d := t.UTC().Date()
	return time.Date(y, m, d, 0, 0, 0, 0, time.UTC)
}

// DurationFromDays converts days to time.Duration.
func DurationFromDays(days int) time.Duration {
	return time.Duration(days) * 24 * time.Hour
}
