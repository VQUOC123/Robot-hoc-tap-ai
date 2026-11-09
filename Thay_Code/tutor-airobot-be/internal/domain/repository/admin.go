package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// AdminRepository defines persistence operations for admin users.
type AdminRepository interface {
	// GetByEmail retrieves an admin user by email address.
	// Returns ErrNotFound when no match exists.
	GetByEmail(ctx context.Context, email string) (*entity.AdminUser, error)

	// GetByID retrieves an admin user by primary key.
	GetByID(ctx context.Context, id uuid.UUID) (*entity.AdminUser, error)

	// Create persists a new admin user and returns the stored record.
	Create(ctx context.Context, a *entity.AdminUser) (*entity.AdminUser, error)

	// UpdateLastLogin sets last_login_at to now() for the given admin.
	UpdateLastLogin(ctx context.Context, id uuid.UUID) error
}
