package entity

import (
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Provider represents an AI provider configuration (LiteLLM, OpenAI, etc.).
type Provider struct {
	ID            uuid.UUID
	Name          string
	BaseURL       string
	APIKeyEnc     []byte // AES-256-GCM encrypted API key
	Model         string
	TimeoutSec    int
	IsDefault     bool
	IsActive      bool
	LastTestedAt  *time.Time
	LastLatencyMs *int
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// Validate performs basic domain-level validation on the provider.
func (p *Provider) Validate() error {
	if p.Name == "" {
		return fmt.Errorf("provider name is required")
	}
	if len(p.Name) > 100 {
		return fmt.Errorf("provider name must not exceed 100 characters")
	}
	if p.BaseURL == "" {
		return fmt.Errorf("provider base URL is required")
	}
	if p.Model == "" {
		return fmt.Errorf("provider model is required")
	}
	if len(p.APIKeyEnc) == 0 {
		return fmt.Errorf("provider API key is required")
	}
	if p.TimeoutSec < 5 || p.TimeoutSec > 120 {
		return fmt.Errorf("provider timeout must be between 5 and 120 seconds")
	}
	return nil
}
