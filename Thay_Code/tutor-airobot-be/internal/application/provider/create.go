package provider

import (
	"context"
	"fmt"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/crypto"
)

// CreateProviderUseCase creates a new AI provider, optionally setting it as default.
type CreateProviderUseCase struct {
	providerRepo repository.ProviderRepository
	masterKeyHex string
}

// NewCreateProviderUseCase creates a CreateProviderUseCase.
func NewCreateProviderUseCase(
	providerRepo repository.ProviderRepository,
	masterKeyHex string,
) *CreateProviderUseCase {
	return &CreateProviderUseCase{
		providerRepo: providerRepo,
		masterKeyHex: masterKeyHex,
	}
}

// Execute encrypts the API key and persists the new provider.
// When IsDefault is true, all other providers have their is_default flag cleared first.
func (uc *CreateProviderUseCase) Execute(ctx context.Context, input CreateProviderInput) (*ProviderOutput, error) {
	encKey, err := crypto.Encrypt([]byte(input.APIKey), uc.masterKeyHex)
	if err != nil {
		return nil, fmt.Errorf("create provider: encrypt key: %w", err)
	}

	timeoutSec := input.TimeoutSec
	if timeoutSec == 0 {
		timeoutSec = 30
	}

	p := &entity.Provider{
		Name:       input.Name,
		BaseURL:    input.BaseURL,
		APIKeyEnc:  encKey,
		Model:      input.Model,
		TimeoutSec: timeoutSec,
		IsDefault:  input.IsDefault,
		IsActive:   true,
	}

	if err = p.Validate(); err != nil {
		return nil, fmt.Errorf("create provider: %w", err)
	}

	if input.IsDefault {
		if err = uc.providerRepo.ClearDefault(ctx); err != nil {
			return nil, fmt.Errorf("create provider: clear existing default: %w", err)
		}
	}

	created, err := uc.providerRepo.Create(ctx, p)
	if err != nil {
		return nil, fmt.Errorf("create provider: persist: %w", err)
	}

	return toOutput(created), nil
}
