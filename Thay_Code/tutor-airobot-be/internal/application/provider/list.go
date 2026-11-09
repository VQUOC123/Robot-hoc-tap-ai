package provider

import (
	"context"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// ListProvidersUseCase retrieves all AI providers.
type ListProvidersUseCase struct {
	providerRepo repository.ProviderRepository
}

// NewListProvidersUseCase creates a ListProvidersUseCase.
func NewListProvidersUseCase(providerRepo repository.ProviderRepository) *ListProvidersUseCase {
	return &ListProvidersUseCase{providerRepo: providerRepo}
}

// Execute returns all providers ordered by creation date descending.
func (uc *ListProvidersUseCase) Execute(ctx context.Context) ([]*ProviderOutput, error) {
	providers, err := uc.providerRepo.List(ctx)
	if err != nil {
		return nil, err
	}

	out := make([]*ProviderOutput, len(providers))
	for i, p := range providers {
		out[i] = toOutput(p)
	}
	return out, nil
}
