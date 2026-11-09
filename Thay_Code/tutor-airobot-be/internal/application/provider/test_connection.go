package provider

import (
	"bytes"
	"context"
	"image"
	"image/color"
	"image/jpeg"
	"time"

	"github.com/google/uuid"
	ai "github.com/nhanntv/tutor-airobot-be/internal/infrastructure/ai"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// TestConnectionUseCase pings an AI provider with a minimal test image.
type TestConnectionUseCase struct {
	providerRepo repository.ProviderRepository
	aiFactory    ai.AIClientFactory
	masterKeyHex string
}

// NewTestConnectionUseCase creates a TestConnectionUseCase.
func NewTestConnectionUseCase(
	providerRepo repository.ProviderRepository,
	aiFactory ai.AIClientFactory,
	masterKeyHex string,
) *TestConnectionUseCase {
	return &TestConnectionUseCase{
		providerRepo: providerRepo,
		aiFactory:    aiFactory,
		masterKeyHex: masterKeyHex,
	}
}

// Execute tests connectivity to the given provider and records the result.
func (uc *TestConnectionUseCase) Execute(ctx context.Context, id uuid.UUID) (TestConnectionOutput, error) {
	p, err := uc.providerRepo.GetByID(ctx, id)
	if err != nil {
		return TestConnectionOutput{}, err
	}

	client, err := uc.aiFactory.Create(p, uc.masterKeyHex)
	if err != nil {
		return TestConnectionOutput{Success: false, Error: err.Error()}, nil
	}

	// Build a minimal 1×1 white JPEG for the test call
	testImage := make1x1JPEG()

	start := time.Now()
	_, callErr := client.DetectHomework(ctx, testImage)
	latency := int(time.Since(start).Milliseconds())

	if callErr != nil {
		return TestConnectionOutput{
			LatencyMs: latency,
			Success:   false,
			Error:     callErr.Error(),
		}, nil
	}

	// Persist the test result — ignore errors (non-critical)
	_ = uc.providerRepo.UpdateTestResult(ctx, id, latency)

	return TestConnectionOutput{
		LatencyMs: latency,
		Success:   true,
	}, nil
}

// make1x1JPEG creates a 1×1 white JPEG image as bytes for provider ping tests.
func make1x1JPEG() []byte {
	img := image.NewRGBA(image.Rect(0, 0, 1, 1))
	img.SetRGBA(0, 0, color.RGBA{R: 255, G: 255, B: 255, A: 255})

	var buf bytes.Buffer
	_ = jpeg.Encode(&buf, img, &jpeg.Options{Quality: 50})
	return buf.Bytes()
}
