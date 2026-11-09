package prompt

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// DeletePromptUseCase permanently removes a prompt template.
type DeletePromptUseCase struct {
	promptRepo repository.PromptRepository
}

// NewDeletePromptUseCase creates a DeletePromptUseCase.
func NewDeletePromptUseCase(promptRepo repository.PromptRepository) *DeletePromptUseCase {
	return &DeletePromptUseCase{promptRepo: promptRepo}
}

// Execute deletes the prompt identified by id.
func (uc *DeletePromptUseCase) Execute(ctx context.Context, id uuid.UUID) error {
	return uc.promptRepo.Delete(ctx, id)
}
