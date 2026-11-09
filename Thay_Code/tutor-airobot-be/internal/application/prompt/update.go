package prompt

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// UpdatePromptUseCase modifies an existing prompt template.
type UpdatePromptUseCase struct {
	promptRepo repository.PromptRepository
}

// NewUpdatePromptUseCase creates an UpdatePromptUseCase.
func NewUpdatePromptUseCase(promptRepo repository.PromptRepository) *UpdatePromptUseCase {
	return &UpdatePromptUseCase{promptRepo: promptRepo}
}

// Execute applies the input changes to the prompt identified by id.
func (uc *UpdatePromptUseCase) Execute(ctx context.Context, id uuid.UUID, input UpdatePromptInput) (*PromptOutput, error) {
	existing, err := uc.promptRepo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}

	if input.Name != "" {
		existing.Name = input.Name
	}
	if input.Content != "" {
		existing.Content = input.Content
	}
	if input.Stage != 0 {
		existing.Stage = entity.Stage(input.Stage)
	}
	existing.SubjectFilter = input.SubjectFilter
	existing.GradeFilter = input.GradeFilter
	existing.IsActive = input.IsActive

	if err = existing.Validate(); err != nil {
		return nil, fmt.Errorf("update prompt: %w", err)
	}

	updated, err := uc.promptRepo.Update(ctx, existing)
	if err != nil {
		return nil, fmt.Errorf("update prompt: persist: %w", err)
	}

	return toOutput(updated), nil
}
