package prompt

import (
	"context"
	"fmt"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// CreatePromptUseCase persists a new AI prompt template.
type CreatePromptUseCase struct {
	promptRepo repository.PromptRepository
}

// NewCreatePromptUseCase creates a CreatePromptUseCase.
func NewCreatePromptUseCase(promptRepo repository.PromptRepository) *CreatePromptUseCase {
	return &CreatePromptUseCase{promptRepo: promptRepo}
}

// Execute validates and persists the new prompt.
func (uc *CreatePromptUseCase) Execute(ctx context.Context, input CreatePromptInput) (*PromptOutput, error) {
	p := &entity.Prompt{
		Name:          input.Name,
		Stage:         entity.Stage(input.Stage),
		Content:       input.Content,
		SubjectFilter: input.SubjectFilter,
		GradeFilter:   input.GradeFilter,
		IsActive:      input.IsActive,
		Version:       1,
	}

	if err := p.Validate(); err != nil {
		return nil, fmt.Errorf("create prompt: %w", err)
	}

	created, err := uc.promptRepo.Create(ctx, p)
	if err != nil {
		return nil, fmt.Errorf("create prompt: persist: %w", err)
	}

	return toOutput(created), nil
}
