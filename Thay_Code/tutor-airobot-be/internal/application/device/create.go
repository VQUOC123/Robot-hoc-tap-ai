package device

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// CreateDeviceUseCase registers a new edge device and returns a one-time raw token.
type CreateDeviceUseCase struct {
	deviceRepo repository.DeviceRepository
}

// NewCreateDeviceUseCase creates a CreateDeviceUseCase.
func NewCreateDeviceUseCase(deviceRepo repository.DeviceRepository) *CreateDeviceUseCase {
	return &CreateDeviceUseCase{deviceRepo: deviceRepo}
}

// Execute generates a 32-byte random bearer token, stores its SHA-256 hash,
// and returns the raw token once. The caller must store it securely — it cannot be retrieved later.
func (uc *CreateDeviceUseCase) Execute(ctx context.Context, input CreateDeviceInput) (CreateDeviceOutput, error) {
	if input.Name == "" {
		return CreateDeviceOutput{}, fmt.Errorf("create device: name is required")
	}

	// Generate 32 random bytes → hex-encode → 64-char raw token
	rawBytes := make([]byte, 32)
	if _, err := rand.Read(rawBytes); err != nil {
		return CreateDeviceOutput{}, fmt.Errorf("create device: generate token: %w", err)
	}
	rawToken := hex.EncodeToString(rawBytes)

	// SHA-256 hash for storage (64 hex chars)
	sum := sha256.Sum256([]byte(rawToken))
	tokenHash := hex.EncodeToString(sum[:])

	d := &entity.Device{
		Name:      input.Name,
		TokenHash: tokenHash,
		IsActive:  true,
	}

	created, err := uc.deviceRepo.Create(ctx, d)
	if err != nil {
		return CreateDeviceOutput{}, fmt.Errorf("create device: persist: %w", err)
	}

	return CreateDeviceOutput{
		ID:        created.ID,
		Name:      created.Name,
		RawToken:  rawToken,
		IsActive:  created.IsActive,
		CreatedAt: created.CreatedAt,
	}, nil
}
