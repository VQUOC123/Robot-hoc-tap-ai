package entity

import (
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Device represents a Raspberry Pi or other edge device authorized to submit analyses.
// Authentication is done via a static bearer token whose SHA-256 hash is stored.
type Device struct {
	ID          uuid.UUID
	Name        string
	TokenHash   string // SHA-256 hex of the raw token
	LastUsedAt  *time.Time
	LastIP      *string
	IsActive    bool
	CreatedAt   time.Time
}

// Validate performs basic domain-level validation on the device.
func (d *Device) Validate() error {
	if d.Name == "" {
		return fmt.Errorf("device name is required")
	}
	if len(d.Name) > 100 {
		return fmt.Errorf("device name must not exceed 100 characters")
	}
	if d.TokenHash == "" {
		return fmt.Errorf("device token hash is required")
	}
	return nil
}
