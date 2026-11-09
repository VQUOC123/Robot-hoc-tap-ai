package provider

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/crypto"
)

// UpdateProviderUseCase modifies an existing AI provider.
type UpdateProviderUseCase struct {
	providerRepo repository.ProviderRepository
	masterKeyHex string
}

// NewUpdateProviderUseCase creates an UpdateProviderUseCase.
func NewUpdateProviderUseCase(
	providerRepo repository.ProviderRepository,
	masterKeyHex string,
) *UpdateProviderUseCase {
	return &UpdateProviderUseCase{
		providerRepo: providerRepo,
		masterKeyHex: masterKeyHex,
	}
}

// Execute updates the provider identified by id with the supplied input.
// An empty APIKey in the input means the existing encrypted key is preserved.
func (uc *UpdateProviderUseCase) Execute(ctx context.Context, id uuid.UUID, input UpdateProviderInput) (*ProviderOutput, error) {
	existing, err := uc.providerRepo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}

	if input.Name != "" {
		existing.Name = input.Name
	}
	if input.BaseURL != "" {
		existing.BaseURL = input.BaseURL
	}
	if input.Model != "" {
		existing.Model = input.Model
	}
	if input.TimeoutSec > 0 {
		existing.TimeoutSec = input.TimeoutSec
	}
	existing.IsDefault = input.IsDefault
	existing.IsActive = input.IsActive

	// Re-encrypt only when a new key is provided
	if input.APIKey != "" {
		encKey, err := crypto.Encrypt([]byte(input.APIKey), uc.masterKeyHex)
		if err != nil {
			return nil, fmt.Errorf("update provider: encrypt key: %w", err)
		}
		existing.APIKeyEnc = encKey
	}

	if err = existing.Validate(); err != nil {
		return nil, fmt.Errorf("update provider: %w", err)
	}

	if input.IsDefault {
		if err = uc.providerRepo.ClearDefault(ctx); err != nil {
			return nil, fmt.Errorf("update provider: clear existing default: %w", err)
		}
	}

	updated, err := uc.providerRepo.Update(ctx, existing)
	if err != nil {
		return nil, fmt.Errorf("update provider: persist: %w", err)
	}

	return toOutput(updated), nil
}
