package repo

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/pkg/timeutil"
)

// AnalysisRepo implements repository.AnalysisRepository using pgxpool.
type AnalysisRepo struct {
	pool *pgxpool.Pool
}

func NewAnalysisRepo(pool *pgxpool.Pool) *AnalysisRepo {
	return &AnalysisRepo{pool: pool}
}

var _ repository.AnalysisRepository = (*AnalysisRepo)(nil)

func (r *AnalysisRepo) Create(ctx context.Context, a *entity.Analysis) (*entity.Analysis, error) {
	const q = `
		INSERT INTO analyses (
			device_id, student_id, activity, focus_score, hw_visible,
			s1_doing_hw, s1_confidence, s1_latency_ms,
			s2_subject, s2_grade, s2_hw_type, s2_progress, s2_hints, s2_latency_ms,
			provider_id, image_path, image_width, image_height, image_size_kb
		) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
		RETURNING id, device_id, student_id, activity, focus_score, hw_visible,
			s1_doing_hw, s1_confidence, s1_latency_ms,
			s2_subject, s2_grade, s2_hw_type, s2_progress, s2_hints, s2_latency_ms,
			provider_id, image_path, image_width, image_height, image_size_kb, created_at`

	row := r.pool.QueryRow(ctx, q,
		a.DeviceID, a.StudentID, a.Activity, a.FocusScore, a.HWVisible,
		a.S1DoingHW, a.S1Confidence, a.S1LatencyMs,
		a.S2Subject, a.S2Grade, a.S2HWType, a.S2Progress, a.S2Hints, a.S2LatencyMs,
		a.ProviderID, a.ImagePath, a.ImageWidth, a.ImageHeight, a.ImageSizeKB,
	)
	created, err := scanAnalysis(row)
	if err != nil {
		return nil, fmt.Errorf("analysis.Create: %w", err)
	}
	return created, nil
}

func (r *AnalysisRepo) GetByID(ctx context.Context, id uuid.UUID) (*entity.Analysis, error) {
	const q = `
		SELECT id, device_id, student_id, activity, focus_score, hw_visible,
			s1_doing_hw, s1_confidence, s1_latency_ms,
			s2_subject, s2_grade, s2_hw_type, s2_progress, s2_hints, s2_latency_ms,
			provider_id, image_path, image_width, image_height, image_size_kb, created_at
		FROM analyses WHERE id = $1`

	row := r.pool.QueryRow(ctx, q, id)
	a, err := scanAnalysis(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("analysis")
		}
		return nil, fmt.Errorf("analysis.GetByID: %w", err)
	}
	return a, nil
}

func (r *AnalysisRepo) List(ctx context.Context, filter repository.AnalysisFilter) ([]*entity.Analysis, error) {
	q := `
		SELECT id, device_id, student_id, activity, focus_score, hw_visible,
			s1_doing_hw, s1_confidence, s1_latency_ms,
			s2_subject, s2_grade, s2_hw_type, s2_progress, s2_hints, s2_latency_ms,
			provider_id, image_path, image_width, image_height, image_size_kb, created_at
		FROM analyses WHERE 1=1`

	args := []any{}
	n := 1

	if filter.DeviceID != nil {
		q += fmt.Sprintf(" AND device_id = $%d", n)
		args = append(args, *filter.DeviceID)
		n++
	}
	if filter.Subject != nil {
		q += fmt.Sprintf(" AND s2_subject = $%d", n)
		args = append(args, *filter.Subject)
		n++
	}
	if filter.DoingHW != nil {
		q += fmt.Sprintf(" AND s1_doing_hw = $%d", n)
		args = append(args, *filter.DoingHW)
		n++
	}
	if filter.From != nil {
		q += fmt.Sprintf(" AND created_at >= $%d", n)
		args = append(args, *filter.From)
		n++
	}
	if filter.To != nil {
		q += fmt.Sprintf(" AND created_at <= $%d", n)
		args = append(args, *filter.To)
		n++
	}
	if filter.Cursor != nil {
		q += fmt.Sprintf(" AND created_at < $%d", n)
		args = append(args, *filter.Cursor)
		n++
	}

	limit := filter.Limit
	if limit <= 0 {
		limit = 20
	}
	q += fmt.Sprintf(" ORDER BY created_at DESC LIMIT $%d", n)
	args = append(args, limit)

	rows, err := r.pool.Query(ctx, q, args...)
	if err != nil {
		return nil, fmt.Errorf("analysis.List: %w", err)
	}
	defer rows.Close()

	var analyses []*entity.Analysis
	for rows.Next() {
		a, err := scanAnalysis(rows)
		if err != nil {
			return nil, fmt.Errorf("analysis.List scan: %w", err)
		}
		analyses = append(analyses, a)
	}
	return analyses, rows.Err()
}

func (r *AnalysisRepo) CountToday(ctx context.Context) (total int64, homework int64, err error) {
	today := timeutil.StartOfDay(time.Now())

	const qtotal = `SELECT COUNT(*) FROM analyses WHERE created_at >= $1`
	if err = r.pool.QueryRow(ctx, qtotal, today).Scan(&total); err != nil {
		return 0, 0, fmt.Errorf("analysis.CountToday total: %w", err)
	}

	const qhw = `SELECT COUNT(*) FROM analyses WHERE created_at >= $1 AND s1_doing_hw = true`
	if err = r.pool.QueryRow(ctx, qhw, today).Scan(&homework); err != nil {
		return 0, 0, fmt.Errorf("analysis.CountToday homework: %w", err)
	}

	return total, homework, nil
}

func (r *AnalysisRepo) CountBySubject(ctx context.Context, from, to time.Time) ([]repository.SubjectCount, error) {
	const q = `
		SELECT s2_subject, COUNT(*) AS cnt
		FROM analyses
		WHERE created_at >= $1 AND created_at < $2 AND s2_subject IS NOT NULL
		GROUP BY s2_subject
		ORDER BY cnt DESC`

	rows, err := r.pool.Query(ctx, q, from, to)
	if err != nil {
		return nil, fmt.Errorf("analysis.CountBySubject: %w", err)
	}
	defer rows.Close()

	var counts []repository.SubjectCount
	for rows.Next() {
		var sc repository.SubjectCount
		if err := rows.Scan(&sc.Subject, &sc.Count); err != nil {
			return nil, fmt.Errorf("analysis.CountBySubject scan: %w", err)
		}
		counts = append(counts, sc)
	}
	return counts, rows.Err()
}

func (r *AnalysisRepo) AvgLatencyByProvider(ctx context.Context, from time.Time) ([]repository.ProviderLatency, error) {
	const q = `
		SELECT provider_id,
		       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY s1_latency_ms + COALESCE(s2_latency_ms, 0)) AS p50,
		       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s1_latency_ms + COALESCE(s2_latency_ms, 0)) AS p95,
		       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY s1_latency_ms + COALESCE(s2_latency_ms, 0)) AS p99
		FROM analyses
		WHERE created_at >= $1 AND provider_id IS NOT NULL AND s1_latency_ms IS NOT NULL
		GROUP BY provider_id`

	rows, err := r.pool.Query(ctx, q, from)
	if err != nil {
		return nil, fmt.Errorf("analysis.AvgLatencyByProvider: %w", err)
	}
	defer rows.Close()

	var results []repository.ProviderLatency
	for rows.Next() {
		var pl repository.ProviderLatency
		if err := rows.Scan(&pl.ProviderID, &pl.P50Ms, &pl.P95Ms, &pl.P99Ms); err != nil {
			return nil, fmt.Errorf("analysis.AvgLatencyByProvider scan: %w", err)
		}
		results = append(results, pl)
	}
	return results, rows.Err()
}

func (r *AnalysisRepo) CountAll(ctx context.Context) (int64, error) {
	const q = `SELECT COUNT(*) FROM analyses`
	var total int64
	if err := r.pool.QueryRow(ctx, q).Scan(&total); err != nil {
		return 0, fmt.Errorf("analysis.CountAll: %w", err)
	}
	return total, nil
}

func (r *AnalysisRepo) AvgLatencyLast24h(ctx context.Context) (float64, error) {
	const q = `
		SELECT COALESCE(AVG(s1_latency_ms + COALESCE(s2_latency_ms, 0)), 0)
		FROM analyses
		WHERE created_at >= NOW() - INTERVAL '24 hours'
		  AND s1_latency_ms IS NOT NULL`
	var avg float64
	if err := r.pool.QueryRow(ctx, q).Scan(&avg); err != nil {
		return 0, fmt.Errorf("analysis.AvgLatencyLast24h: %w", err)
	}
	return avg, nil
}

func (r *AnalysisRepo) LatencyByHour(ctx context.Context, from time.Time) ([]repository.LatencyHourly, error) {
	const q = `
		SELECT date_trunc('hour', created_at) AS hour,
		       AVG(s1_latency_ms + COALESCE(s2_latency_ms, 0)) AS avg_ms,
		       COUNT(*) AS cnt
		FROM analyses
		WHERE created_at >= $1
		  AND s1_latency_ms IS NOT NULL
		GROUP BY hour
		ORDER BY hour ASC`

	rows, err := r.pool.Query(ctx, q, from)
	if err != nil {
		return nil, fmt.Errorf("analysis.LatencyByHour: %w", err)
	}
	defer rows.Close()

	var results []repository.LatencyHourly
	for rows.Next() {
		var lh repository.LatencyHourly
		if err := rows.Scan(&lh.Hour, &lh.AvgMs, &lh.Count); err != nil {
			return nil, fmt.Errorf("analysis.LatencyByHour scan: %w", err)
		}
		results = append(results, lh)
	}
	return results, rows.Err()
}

func scanAnalysis(row scannable) (*entity.Analysis, error) {
	var a entity.Analysis
	err := row.Scan(
		&a.ID, &a.DeviceID, &a.StudentID, &a.Activity, &a.FocusScore, &a.HWVisible,
		&a.S1DoingHW, &a.S1Confidence, &a.S1LatencyMs,
		&a.S2Subject, &a.S2Grade, &a.S2HWType, &a.S2Progress, &a.S2Hints, &a.S2LatencyMs,
		&a.ProviderID, &a.ImagePath, &a.ImageWidth, &a.ImageHeight, &a.ImageSizeKB,
		&a.CreatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &a, nil
}
