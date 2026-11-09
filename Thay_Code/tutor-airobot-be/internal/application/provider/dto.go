package provider

import (
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// CreateProviderInput carries fields required to register a new AI provider.
type CreateProviderInput struct {
	Name       string
	BaseURL    string
	APIKey     string
	Model      string
	TimeoutSec int
	IsDefault  bool
}

// UpdateProviderInput carries fields that can be changed on an existing provider.
type UpdateProviderInput struct {
	Name       string
	BaseURL    string
	APIKey     string // empty string means "do not change the existing key"
	Model      string
	TimeoutSec int
	IsDefault  bool
	IsActive   bool
}

// ProviderOutput is the public representation of a provider.
// The API key is never returned in plaintext — a masked placeholder is used instead.
type ProviderOutput struct {
	ID            uuid.UUID  `json:"id"`
	Name          string     `json:"name"`
	BaseURL       string     `json:"base_url"`
	APIKeyMasked  string     `json:"api_key"`
	Model         string     `json:"model"`
	TimeoutSec    int        `json:"timeout_sec"`
	IsDefault     bool       `json:"is_default"`
	IsActive      bool       `json:"is_active"`
	LastTestedAt  *time.Time `json:"last_tested_at"`
	LastLatencyMs *int       `json:"last_latency_ms"`
	CreatedAt     time.Time  `json:"created_at"`
	UpdatedAt     time.Time  `json:"updated_at"`
}

// TestConnectionOutput is returned after pinging a provider.
type TestConnectionOutput struct {
	LatencyMs int    `json:"latency_ms"`
	Success   bool   `json:"success"`
	Error     string `json:"error,omitempty"`
}

// toOutput converts a Provider entity to a ProviderOutput, masking the API key.
func toOutput(p *entity.Provider) *ProviderOutput {
	return &ProviderOutput{
		ID:            p.ID,
		Name:          p.Name,
		BaseURL:       p.BaseURL,
		APIKeyMasked:  "••••••",
		Model:         p.Model,
		TimeoutSec:    p.TimeoutSec,
		IsDefault:     p.IsDefault,
		IsActive:      p.IsActive,
		LastTestedAt:  p.LastTestedAt,
		LastLatencyMs: p.LastLatencyMs,
		CreatedAt:     p.CreatedAt,
		UpdatedAt:     p.UpdatedAt,
	}
}
