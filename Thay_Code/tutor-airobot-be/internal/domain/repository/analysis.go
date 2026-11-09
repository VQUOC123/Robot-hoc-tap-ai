package repository

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// AnalysisFilter specifies constraints for paginated analysis queries.
type AnalysisFilter struct {
	DeviceID *uuid.UUID
	Subject  *string
	DoingHW  *bool
	From     *time.Time // created_at >= from
	To       *time.Time // created_at <= to
	Cursor   *time.Time // created_at < cursor (exclusive, for keyset pagination)
	Limit    int
}

// SubjectCount aggregates analysis counts per homework subject.
type SubjectCount struct {
	Subject string
	Count   int64
}

// ProviderLatency holds percentile latency statistics for a provider.
type ProviderLatency struct {
	ProviderID uuid.UUID
	P50Ms      float64
	P95Ms      float64
	P99Ms      float64
}

// LatencyHourly holds average total latency aggregated by UTC hour.
type LatencyHourly struct {
	Hour  time.Time
	AvgMs float64
	Count int64
}

// AnalysisRepository defines persistence operations for analysis records.
type AnalysisRepository interface {
	// Create persists a new analysis record and returns the stored record.
	Create(ctx context.Context, a *entity.Analysis) (*entity.Analysis, error)

	// GetByID retrieves an analysis by its primary key.
	GetByID(ctx context.Context, id uuid.UUID) (*entity.Analysis, error)

	// List retrieves analyses matching the filter using keyset pagination.
	List(ctx context.Context, filter AnalysisFilter) ([]*entity.Analysis, error)

	// CountToday returns total analyses and homework analyses for today (UTC).
	CountToday(ctx context.Context) (total int64, homework int64, err error)

	// CountAll returns the total number of analysis records ever stored.
	CountAll(ctx context.Context) (int64, error)

	// CountBySubject returns per-subject counts within the given time range.
	CountBySubject(ctx context.Context, from, to time.Time) ([]SubjectCount, error)

	// AvgLatencyByProvider returns latency percentiles per provider since from.
	AvgLatencyByProvider(ctx context.Context, from time.Time) ([]ProviderLatency, error)

	// LatencyByHour returns average total latency grouped by UTC hour since from.
	LatencyByHour(ctx context.Context, from time.Time) ([]LatencyHourly, error)

	// AvgLatencyLast24h returns the overall average total latency for the last 24 hours.
	AvgLatencyLast24h(ctx context.Context) (float64, error)
}
