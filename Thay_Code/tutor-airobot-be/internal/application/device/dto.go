package device

import (
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// CreateDeviceInput carries the registration data for a new device.
type CreateDeviceInput struct {
	Name string
}

// CreateDeviceOutput includes the raw token which is shown only once at creation.
type CreateDeviceOutput struct {
	ID         uuid.UUID  `json:"id"`
	Name       string     `json:"name"`
	RawToken   string     `json:"token"` // shown once — store securely
	IsActive   bool       `json:"is_active"`
	CreatedAt  time.Time  `json:"created_at"`
}

// DeviceOutput is the safe public representation (no token).
type DeviceOutput struct {
	ID          uuid.UUID  `json:"id"`
	Name        string     `json:"name"`
	LastUsedAt  *time.Time `json:"last_used_at"`
	LastIP      *string    `json:"last_ip"`
	IsActive    bool       `json:"is_active"`
	CreatedAt   time.Time  `json:"created_at"`
}

// toOutput converts a Device entity to DeviceOutput (omits token).
func toOutput(d *entity.Device) *DeviceOutput {
	return &DeviceOutput{
		ID:         d.ID,
		Name:       d.Name,
		LastUsedAt: d.LastUsedAt,
		LastIP:     d.LastIP,
		IsActive:   d.IsActive,
		CreatedAt:  d.CreatedAt,
	}
}
