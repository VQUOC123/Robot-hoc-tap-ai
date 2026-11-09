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

// AdminRepo implements repository.AdminRepository using pgxpool.
type AdminRepo struct {
	pool *pgxpool.Pool
}

func NewAdminRepo(pool *pgxpool.Pool) *AdminRepo {
	return &AdminRepo{pool: pool}
}

var _ repository.AdminRepository = (*AdminRepo)(nil)

func (r *AdminRepo) GetByEmail(ctx context.Context, email string) (*entity.AdminUser, error) {
	const q = `
		SELECT id, email, password_hash, role, last_login_at, created_at
		FROM admin_users WHERE email = $1`

	row := r.pool.QueryRow(ctx, q, email)
	a, err := scanAdmin(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("admin user")
		}
		return nil, fmt.Errorf("admin.GetByEmail: %w", err)
	}
	return a, nil
}

func (r *AdminRepo) GetByID(ctx context.Context, id uuid.UUID) (*entity.AdminUser, error) {
	const q = `
		SELECT id, email, password_hash, role, last_login_at, created_at
		FROM admin_users WHERE id = $1`

	row := r.pool.QueryRow(ctx, q, id)
	a, err := scanAdmin(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("admin user")
		}
		return nil, fmt.Errorf("admin.GetByID: %w", err)
	}
	return a, nil
}

func (r *AdminRepo) Create(ctx context.Context, a *entity.AdminUser) (*entity.AdminUser, error) {
	const q = `
		INSERT INTO admin_users (email, password_hash, role)
		VALUES ($1, $2, $3)
		RETURNING id, email, password_hash, role, last_login_at, created_at`

	row := r.pool.QueryRow(ctx, q, a.Email, a.PasswordHash, string(a.Role))
	created, err := scanAdmin(row)
	if err != nil {
		return nil, fmt.Errorf("admin.Create: %w", err)
	}
	return created, nil
}

func (r *AdminRepo) UpdateLastLogin(ctx context.Context, id uuid.UUID) error {
	const q = `UPDATE admin_users SET last_login_at = now() WHERE id = $1`
	if _, err := r.pool.Exec(ctx, q, id); err != nil {
		return fmt.Errorf("admin.UpdateLastLogin: %w", err)
	}
	return nil
}

func scanAdmin(row scannable) (*entity.AdminUser, error) {
	var a entity.AdminUser
	var role string
	err := row.Scan(&a.ID, &a.Email, &a.PasswordHash, &role, &a.LastLoginAt, &a.CreatedAt)
	if err != nil {
		return nil, err
	}
	a.Role = entity.Role(role)
	return &a, nil
}
