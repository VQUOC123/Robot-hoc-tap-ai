package provider

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// GetProviderUseCase retrieves a single AI provider by ID.
type GetProviderUseCase struct {
	providerRepo repository.ProviderRepository
}

// NewGetProviderUseCase creates a GetProviderUseCase.
func NewGetProviderUseCase(providerRepo repository.ProviderRepository) *GetProviderUseCase {
	return &GetProviderUseCase{providerRepo: providerRepo}
}

// Execute returns the provider output for the given id.
func (uc *GetProviderUseCase) Execute(ctx context.Context, id uuid.UUID) (*ProviderOutput, error) {
	p, err := uc.providerRepo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	return toOutput(p), nil
}
