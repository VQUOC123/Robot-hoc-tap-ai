package provider

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// DeleteProviderUseCase permanently removes an AI provider.
type DeleteProviderUseCase struct {
	providerRepo repository.ProviderRepository
}

// NewDeleteProviderUseCase creates a DeleteProviderUseCase.
func NewDeleteProviderUseCase(providerRepo repository.ProviderRepository) *DeleteProviderUseCase {
	return &DeleteProviderUseCase{providerRepo: providerRepo}
}

// Execute deletes the provider identified by id.
func (uc *DeleteProviderUseCase) Execute(ctx context.Context, id uuid.UUID) error {
	return uc.providerRepo.Delete(ctx, id)
}
