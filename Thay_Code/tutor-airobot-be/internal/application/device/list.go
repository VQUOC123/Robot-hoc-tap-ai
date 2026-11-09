package device

import (
	"context"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// ListDevicesUseCase retrieves all registered devices.
type ListDevicesUseCase struct {
	deviceRepo repository.DeviceRepository
}

// NewListDevicesUseCase creates a ListDevicesUseCase.
func NewListDevicesUseCase(deviceRepo repository.DeviceRepository) *ListDevicesUseCase {
	return &ListDevicesUseCase{deviceRepo: deviceRepo}
}

// Execute returns all devices ordered by creation date descending.
func (uc *ListDevicesUseCase) Execute(ctx context.Context) ([]*DeviceOutput, error) {
	devices, err := uc.deviceRepo.List(ctx)
	if err != nil {
		return nil, err
	}

	out := make([]*DeviceOutput, len(devices))
	for i, d := range devices {
		out[i] = toOutput(d)
	}
	return out, nil
}
