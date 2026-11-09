package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// PromptFilter specifies optional constraints when listing prompts.
type PromptFilter struct {
	Stage    int16
	IsActive *bool // nil means no filter
}

// PromptRepository defines persistence operations for AI prompt templates.
type PromptRepository interface {
	// GetByID retrieves a prompt by its primary key.
	GetByID(ctx context.Context, id uuid.UUID) (*entity.Prompt, error)

	// GetActiveByStage retrieves the best matching active prompt for the given
	// stage and optional subject. Subject-specific prompts take priority over
	// generic ones. Returns ErrNotFound when none exists.
	GetActiveByStage(ctx context.Context, stage int16, subject string) (*entity.Prompt, error)

	// List retrieves prompts matching the filter, ordered by created_at DESC.
	List(ctx context.Context, filter PromptFilter) ([]*entity.Prompt, error)

	// Create persists a new prompt and returns the stored record.
	Create(ctx context.Context, p *entity.Prompt) (*entity.Prompt, error)

	// Update persists changes to an existing prompt.
	Update(ctx context.Context, p *entity.Prompt) (*entity.Prompt, error)

	// Delete removes a prompt permanently.
	Delete(ctx context.Context, id uuid.UUID) error
}
