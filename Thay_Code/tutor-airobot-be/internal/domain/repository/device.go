package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// DeviceRepository defines persistence operations for edge devices.
type DeviceRepository interface {
	// GetByTokenHash retrieves a device by the SHA-256 hex hash of its bearer token.
	// Returns ErrNotFound when the token does not exist or the device is inactive.
	GetByTokenHash(ctx context.Context, hash string) (*entity.Device, error)

	// List retrieves all devices ordered by created_at DESC.
	List(ctx context.Context) ([]*entity.Device, error)

	// Create persists a new device and returns the stored record.
	Create(ctx context.Context, d *entity.Device) (*entity.Device, error)

	// UpdateLastUsed records the timestamp and IP of the most recent authenticated request.
	UpdateLastUsed(ctx context.Context, id uuid.UUID, ip string) error

	// Revoke marks a device as inactive without deleting it.
	Revoke(ctx context.Context, id uuid.UUID) error

	// Delete removes a device permanently.
	Delete(ctx context.Context, id uuid.UUID) error
}
