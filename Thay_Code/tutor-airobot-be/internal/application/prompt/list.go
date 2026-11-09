package prompt

import (
	"context"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// ListPromptsUseCase retrieves prompt templates with optional filtering.
type ListPromptsUseCase struct {
	promptRepo repository.PromptRepository
}

// NewListPromptsUseCase creates a ListPromptsUseCase.
func NewListPromptsUseCase(promptRepo repository.PromptRepository) *ListPromptsUseCase {
	return &ListPromptsUseCase{promptRepo: promptRepo}
}

// Execute returns all prompts matching the filter, ordered by creation date descending.
func (uc *ListPromptsUseCase) Execute(ctx context.Context, filter repository.PromptFilter) ([]*PromptOutput, error) {
	prompts, err := uc.promptRepo.List(ctx, filter)
	if err != nil {
		return nil, err
	}

	out := make([]*PromptOutput, len(prompts))
	for i, p := range prompts {
		out[i] = toOutput(p)
	}
	return out, nil
}
