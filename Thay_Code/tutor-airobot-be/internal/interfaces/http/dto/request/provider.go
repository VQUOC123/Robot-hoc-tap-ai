package request

// CreateProviderRequest carries fields for POST /api/v1/providers.
type CreateProviderRequest struct {
	Name       string `json:"name"        validate:"required,min=1,max=100"`
	BaseURL    string `json:"base_url"    validate:"required,url"`
	APIKey     string `json:"api_key"     validate:"required,min=10"`
	Model      string `json:"model"       validate:"required"`
	TimeoutSec int    `json:"timeout_sec" validate:"min=5,max=120"`
	IsDefault  bool   `json:"is_default"`
}

// UpdateProviderRequest carries fields for PUT /api/v1/providers/:id.
type UpdateProviderRequest struct {
	Name       string `json:"name"        validate:"required,min=1,max=100"`
	BaseURL    string `json:"base_url"    validate:"required,url"`
	APIKey     string `json:"api_key"`    // empty = keep existing
	Model      string `json:"model"       validate:"required"`
	TimeoutSec int    `json:"timeout_sec" validate:"min=5,max=120"`
	IsDefault  bool   `json:"is_default"`
	IsActive   bool   `json:"is_active"`
}
