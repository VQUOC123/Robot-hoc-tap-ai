package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// ProviderRepository defines persistence operations for AI providers.
type ProviderRepository interface {
	// GetByID retrieves a provider by its primary key.
	GetByID(ctx context.Context, id uuid.UUID) (*entity.Provider, error)

	// GetDefault retrieves the provider marked as default.
	// Returns ErrNotFound when no default provider exists.
	GetDefault(ctx context.Context) (*entity.Provider, error)

	// List retrieves all providers ordered by created_at DESC.
	List(ctx context.Context) ([]*entity.Provider, error)

	// Create persists a new provider and returns the stored record.
	Create(ctx context.Context, p *entity.Provider) (*entity.Provider, error)

	// Update persists changes to an existing provider.
	Update(ctx context.Context, p *entity.Provider) (*entity.Provider, error)

	// UpdateTestResult records the outcome of a connectivity test.
	UpdateTestResult(ctx context.Context, id uuid.UUID, latencyMs int) error

	// ClearDefault removes the is_default flag from all providers.
	// Call before setting a new default.
	ClearDefault(ctx context.Context) error

	// Delete removes a provider permanently.
	Delete(ctx context.Context, id uuid.UUID) error
}
