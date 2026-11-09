package device

import (
	"context"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// RevokeDeviceUseCase deactivates an edge device without deleting it.
type RevokeDeviceUseCase struct {
	deviceRepo repository.DeviceRepository
}

// NewRevokeDeviceUseCase creates a RevokeDeviceUseCase.
func NewRevokeDeviceUseCase(deviceRepo repository.DeviceRepository) *RevokeDeviceUseCase {
	return &RevokeDeviceUseCase{deviceRepo: deviceRepo}
}

// Execute marks the device as inactive so it can no longer authenticate.
func (uc *RevokeDeviceUseCase) Execute(ctx context.Context, id uuid.UUID) error {
	return uc.deviceRepo.Revoke(ctx, id)
}
