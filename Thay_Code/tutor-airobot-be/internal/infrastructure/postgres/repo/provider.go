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
)

// ProviderRepo implements repository.ProviderRepository using pgxpool.
type ProviderRepo struct {
	pool *pgxpool.Pool
}

// NewProviderRepo creates a ProviderRepo backed by the given pool.
func NewProviderRepo(pool *pgxpool.Pool) *ProviderRepo {
	return &ProviderRepo{pool: pool}
}

// Ensure interface compliance at compile time.
var _ repository.ProviderRepository = (*ProviderRepo)(nil)

func (r *ProviderRepo) GetByID(ctx context.Context, id uuid.UUID) (*entity.Provider, error) {
	const q = `
		SELECT id, name, base_url, api_key_enc, model, timeout_sec,
		       is_default, is_active, last_tested_at, last_latency_ms,
		       created_at, updated_at
		FROM providers WHERE id = $1`

	row := r.pool.QueryRow(ctx, q, id)
	p, err := scanProvider(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("provider")
		}
		return nil, fmt.Errorf("provider.GetByID: %w", err)
	}
	return p, nil
}

func (r *ProviderRepo) GetDefault(ctx context.Context) (*entity.Provider, error) {
	const q = `
		SELECT id, name, base_url, api_key_enc, model, timeout_sec,
		       is_default, is_active, last_tested_at, last_latency_ms,
		       created_at, updated_at
		FROM providers WHERE is_default = true AND is_active = true
		LIMIT 1`

	row := r.pool.QueryRow(ctx, q)
	p, err := scanProvider(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("default provider")
		}
		return nil, fmt.Errorf("provider.GetDefault: %w", err)
	}
	return p, nil
}

func (r *ProviderRepo) List(ctx context.Context) ([]*entity.Provider, error) {
	const q = `
		SELECT id, name, base_url, api_key_enc, model, timeout_sec,
		       is_default, is_active, last_tested_at, last_latency_ms,
		       created_at, updated_at
		FROM providers ORDER BY created_at DESC`

	rows, err := r.pool.Query(ctx, q)
	if err != nil {
		return nil, fmt.Errorf("provider.List: %w", err)
	}
	defer rows.Close()

	var providers []*entity.Provider
	for rows.Next() {
		p, err := scanProvider(rows)
		if err != nil {
			return nil, fmt.Errorf("provider.List scan: %w", err)
		}
		providers = append(providers, p)
	}
	return providers, rows.Err()
}

func (r *ProviderRepo) Create(ctx context.Context, p *entity.Provider) (*entity.Provider, error) {
	const q = `
		INSERT INTO providers (name, base_url, api_key_enc, model, timeout_sec, is_default, is_active)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, name, base_url, api_key_enc, model, timeout_sec,
		          is_default, is_active, last_tested_at, last_latency_ms,
		          created_at, updated_at`

	row := r.pool.QueryRow(ctx, q,
		p.Name, p.BaseURL, p.APIKeyEnc, p.Model, p.TimeoutSec, p.IsDefault, p.IsActive,
	)
	created, err := scanProvider(row)
	if err != nil {
		return nil, fmt.Errorf("provider.Create: %w", err)
	}
	return created, nil
}

func (r *ProviderRepo) Update(ctx context.Context, p *entity.Provider) (*entity.Provider, error) {
	const q = `
		UPDATE providers
		SET name = $2, base_url = $3, api_key_enc = $4, model = $5,
		    timeout_sec = $6, is_default = $7, is_active = $8,
		    updated_at = now()
		WHERE id = $1
		RETURNING id, name, base_url, api_key_enc, model, timeout_sec,
		          is_default, is_active, last_tested_at, last_latency_ms,
		          created_at, updated_at`

	row := r.pool.QueryRow(ctx, q,
		p.ID, p.Name, p.BaseURL, p.APIKeyEnc, p.Model,
		p.TimeoutSec, p.IsDefault, p.IsActive,
	)
	updated, err := scanProvider(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("provider")
		}
		return nil, fmt.Errorf("provider.Update: %w", err)
	}
	return updated, nil
}

func (r *ProviderRepo) UpdateTestResult(ctx context.Context, id uuid.UUID, latencyMs int) error {
	const q = `
		UPDATE providers
		SET last_tested_at = $2, last_latency_ms = $3, updated_at = now()
		WHERE id = $1`

	now := time.Now().UTC()
	_, err := r.pool.Exec(ctx, q, id, now, latencyMs)
	if err != nil {
		return fmt.Errorf("provider.UpdateTestResult: %w", err)
	}
	return nil
}

func (r *ProviderRepo) ClearDefault(ctx context.Context) error {
	const q = `UPDATE providers SET is_default = false, updated_at = now() WHERE is_default = true`
	if _, err := r.pool.Exec(ctx, q); err != nil {
		return fmt.Errorf("provider.ClearDefault: %w", err)
	}
	return nil
}

func (r *ProviderRepo) Delete(ctx context.Context, id uuid.UUID) error {
	const q = `DELETE FROM providers WHERE id = $1`
	tag, err := r.pool.Exec(ctx, q, id)
	if err != nil {
		return fmt.Errorf("provider.Delete: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return apperror.NotFound("provider")
	}
	return nil
}

// scanProvider scans a provider row from any pgx row scanner.
type scannable interface {
	Scan(dest ...any) error
}

func scanProvider(row scannable) (*entity.Provider, error) {
	var p entity.Provider
	err := row.Scan(
		&p.ID, &p.Name, &p.BaseURL, &p.APIKeyEnc, &p.Model, &p.TimeoutSec,
		&p.IsDefault, &p.IsActive, &p.LastTestedAt, &p.LastLatencyMs,
		&p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &p, nil
}
