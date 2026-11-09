package ai

import (
	"fmt"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/ai/openai_compat"
	"github.com/nhanntv/tutor-airobot-be/internal/infrastructure/crypto"
)

// AIClientFactory creates configured AI clients from provider entities.
type AIClientFactory interface {
	Create(provider *entity.Provider, masterKeyHex string) (service.AIClient, error)
}

// DefaultFactory creates OpenAI-compatible clients by decrypting the provider API key.
type DefaultFactory struct{}

// Ensure DefaultFactory implements AIClientFactory at compile time.
var _ AIClientFactory = (*DefaultFactory)(nil)

// NewDefaultFactory creates a DefaultFactory.
func NewDefaultFactory() *DefaultFactory {
	return &DefaultFactory{}
}

// Create decrypts the provider's API key and returns a ready-to-use AIClient.
func (f *DefaultFactory) Create(provider *entity.Provider, masterKeyHex string) (service.AIClient, error) {
	if provider == nil {
		return nil, fmt.Errorf("ai factory: provider is nil")
	}

	plainKey, err := crypto.Decrypt(provider.APIKeyEnc, masterKeyHex)
	if err != nil {
		return nil, fmt.Errorf("ai factory: decrypt api key for provider %s: %w", provider.ID, err)
	}

	client := openai_compat.NewClient(
		provider.BaseURL,
		string(plainKey),
		provider.Model,
		provider.TimeoutSec,
	)

	return client, nil
}
