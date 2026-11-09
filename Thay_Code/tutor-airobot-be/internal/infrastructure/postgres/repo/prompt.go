package repo

import (
	"context"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// PromptRepo implements repository.PromptRepository using pgxpool.
type PromptRepo struct {
	pool *pgxpool.Pool
}

// NewPromptRepo creates a PromptRepo backed by the given pool.
func NewPromptRepo(pool *pgxpool.Pool) *PromptRepo {
	return &PromptRepo{pool: pool}
}

var _ repository.PromptRepository = (*PromptRepo)(nil)

func (r *PromptRepo) GetByID(ctx context.Context, id uuid.UUID) (*entity.Prompt, error) {
	const q = `
		SELECT id, name, stage, content, subject_filter, grade_filter,
		       is_active, version, created_at, updated_at
		FROM prompts WHERE id = $1`

	row := r.pool.QueryRow(ctx, q, id)
	p, err := scanPrompt(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("prompt")
		}
		return nil, fmt.Errorf("prompt.GetByID: %w", err)
	}
	return p, nil
}

// GetActiveByStage returns the best active prompt for the stage.
// Subject-specific prompts take priority over generic ones (subject_filter IS NULL).
func (r *PromptRepo) GetActiveByStage(ctx context.Context, stage int16, subject string) (*entity.Prompt, error) {
	const q = `
		SELECT id, name, stage, content, subject_filter, grade_filter,
		       is_active, version, created_at, updated_at
		FROM prompts
		WHERE stage = $1 AND is_active = true
		  AND (subject_filter = $2 OR subject_filter IS NULL)
		ORDER BY
		  CASE WHEN subject_filter = $2 THEN 0 ELSE 1 END,
		  created_at DESC
		LIMIT 1`

	row := r.pool.QueryRow(ctx, q, stage, subject)
	p, err := scanPrompt(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("active prompt")
		}
		return nil, fmt.Errorf("prompt.GetActiveByStage: %w", err)
	}
	return p, nil
}

func (r *PromptRepo) List(ctx context.Context, filter repository.PromptFilter) ([]*entity.Prompt, error) {
	q := `
		SELECT id, name, stage, content, subject_filter, grade_filter,
		       is_active, version, created_at, updated_at
		FROM prompts WHERE 1=1`

	args := []any{}
	argN := 1

	if filter.Stage != 0 {
		q += fmt.Sprintf(" AND stage = $%d", argN)
		args = append(args, filter.Stage)
		argN++
	}
	if filter.IsActive != nil {
		q += fmt.Sprintf(" AND is_active = $%d", argN)
		args = append(args, *filter.IsActive)
		argN++
	}
	_ = argN
	q += " ORDER BY created_at DESC"

	rows, err := r.pool.Query(ctx, q, args...)
	if err != nil {
		return nil, fmt.Errorf("prompt.List: %w", err)
	}
	defer rows.Close()

	var prompts []*entity.Prompt
	for rows.Next() {
		p, err := scanPrompt(rows)
		if err != nil {
			return nil, fmt.Errorf("prompt.List scan: %w", err)
		}
		prompts = append(prompts, p)
	}
	return prompts, rows.Err()
}

func (r *PromptRepo) Create(ctx context.Context, p *entity.Prompt) (*entity.Prompt, error) {
	const q = `
		INSERT INTO prompts (name, stage, content, subject_filter, grade_filter, is_active, version)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, name, stage, content, subject_filter, grade_filter,
		          is_active, version, created_at, updated_at`

	row := r.pool.QueryRow(ctx, q,
		p.Name, int16(p.Stage), p.Content, p.SubjectFilter, p.GradeFilter, p.IsActive, p.Version,
	)
	created, err := scanPrompt(row)
	if err != nil {
		return nil, fmt.Errorf("prompt.Create: %w", err)
	}
	return created, nil
}

func (r *PromptRepo) Update(ctx context.Context, p *entity.Prompt) (*entity.Prompt, error) {
	const q = `
		UPDATE prompts
		SET name = $2, stage = $3, content = $4, subject_filter = $5,
		    grade_filter = $6, is_active = $7, version = version + 1,
		    updated_at = now()
		WHERE id = $1
		RETURNING id, name, stage, content, subject_filter, grade_filter,
		          is_active, version, created_at, updated_at`

	row := r.pool.QueryRow(ctx, q,
		p.ID, p.Name, int16(p.Stage), p.Content, p.SubjectFilter, p.GradeFilter, p.IsActive,
	)
	updated, err := scanPrompt(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("prompt")
		}
		return nil, fmt.Errorf("prompt.Update: %w", err)
	}
	return updated, nil
}

func (r *PromptRepo) Delete(ctx context.Context, id uuid.UUID) error {
	const q = `DELETE FROM prompts WHERE id = $1`
	tag, err := r.pool.Exec(ctx, q, id)
	if err != nil {
		return fmt.Errorf("prompt.Delete: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return apperror.NotFound("prompt")
	}
	return nil
}

func scanPrompt(row scannable) (*entity.Prompt, error) {
	var p entity.Prompt
	var stage int16
	err := row.Scan(
		&p.ID, &p.Name, &stage, &p.Content, &p.SubjectFilter, &p.GradeFilter,
		&p.IsActive, &p.Version, &p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	p.Stage = entity.Stage(stage)
	return &p, nil
}
