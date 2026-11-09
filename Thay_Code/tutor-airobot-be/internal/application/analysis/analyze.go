package analysis

import (
	"context"
	"fmt"
	"time"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
	ai "github.com/nhanntv/tutor-airobot-be/internal/infrastructure/ai"
)

// AnalyzeUseCase orchestrates the two-stage AI homework analysis pipeline.
type AnalyzeUseCase struct {
	imageProc    service.ImageProcessor
	aiFactory    ai.AIClientFactory
	providerRepo repository.ProviderRepository
	analysisRepo repository.AnalysisRepository
	masterKeyHex string
}

// NewAnalyzeUseCase creates an AnalyzeUseCase with its dependencies.
func NewAnalyzeUseCase(
	imageProc service.ImageProcessor,
	aiFactory ai.AIClientFactory,
	providerRepo repository.ProviderRepository,
	analysisRepo repository.AnalysisRepository,
	masterKeyHex string,
) *AnalyzeUseCase {
	return &AnalyzeUseCase{
		imageProc:    imageProc,
		aiFactory:    aiFactory,
		providerRepo: providerRepo,
		analysisRepo: analysisRepo,
		masterKeyHex: masterKeyHex,
	}
}

// Execute runs the full analysis pipeline:
// 1. Process & resize the image
// 2. Load the default AI provider
// 3. Stage 1 — homework detection
// 4. If not doing HW, persist partial record and return early
// 5. Stage 2 — subject & progress analysis
// 6. Persist full record
// 7. Return structured output
func (uc *AnalyzeUseCase) Execute(ctx context.Context, input AnalyzeInput) (AnalyzeOutput, error) {
	// 1. Process image
	img, err := uc.imageProc.Process(ctx, input.ImageRaw, 1024, 768, 82)
	if err != nil {
		return AnalyzeOutput{}, fmt.Errorf("analyze: image processing: %w", err)
	}

	// 2. Get default provider and create AI client
	provider, err := uc.providerRepo.GetDefault(ctx)
	if err != nil {
		return AnalyzeOutput{}, fmt.Errorf("analyze: no default provider: %w", err)
	}

	client, err := uc.aiFactory.Create(provider, uc.masterKeyHex)
	if err != nil {
		return AnalyzeOutput{}, fmt.Errorf("analyze: create AI client: %w", err)
	}

	totalStart := time.Now()

	// 3. Stage 1 — Homework detection
	s1, err := client.DetectHomework(ctx, img.Data)
	if err != nil {
		return AnalyzeOutput{}, fmt.Errorf("analyze: stage 1: %w", err)
	}

	// Build partial analysis record
	providerID := provider.ID
	studentID := ptrString(input.StudentID)
	activity := ptrString(input.Activity)
	focusScore := int16(input.FocusScore)
	hwVisible := input.HWVisible
	s1DoingHW := s1.DoingHW

	a := &entity.Analysis{
		DeviceID:     input.DeviceID,
		StudentID:    studentID,
		Activity:     activity,
		FocusScore:   &focusScore,
		HWVisible:    &hwVisible,
		S1DoingHW:    &s1DoingHW,
		S1Confidence: &s1.Confidence,
		S1LatencyMs:  &s1.LatencyMs,
		ProviderID:   &providerID,
		ImageWidth:   ptrInt16(int16(img.Width)),
		ImageHeight:  ptrInt16(int16(img.Height)),
		ImageSizeKB:  ptrInt16(int16(img.SizeKB)),
	}

	// 4. Early exit when homework is not detected
	if !s1.DoingHW {
		_, _ = uc.analysisRepo.Create(ctx, a)

		return AnalyzeOutput{
			DoingHW:        false,
			Confidence:     s1.Confidence,
			LatencyTotalMs: s1.LatencyMs,
		}, nil
	}

	// 5. Stage 2 — Homework analysis
	s2, err := client.AnalyzeHomework(ctx, img.Data)
	if err != nil {
		return AnalyzeOutput{}, fmt.Errorf("analyze: stage 2: %w", err)
	}

	progress := int16(s2.Progress)
	a.S2Subject = ptrString(s2.Subject)
	a.S2Grade = ptrString(s2.Grade)
	a.S2HWType = ptrString(s2.HWType)
	a.S2Progress = &progress
	a.S2Hints = ptrString(s2.Hints)
	a.S2LatencyMs = &s2.LatencyMs

	// 6. Persist full record
	_, _ = uc.analysisRepo.Create(ctx, a)

	totalMs := int(time.Since(totalStart).Milliseconds())

	// 7. Return output
	return AnalyzeOutput{
		DoingHW:        true,
		Subject:        s2.Subject,
		Grade:          s2.Grade,
		HWType:         s2.HWType,
		Hints:          s2.Hints,
		Progress:       s2.Progress,
		Confidence:     s1.Confidence,
		LatencyTotalMs: totalMs,
	}, nil
}

// ── helpers ──────────────────────────────────────────────────────────────────

func ptrString(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

func ptrInt16(v int16) *int16 {
	return &v
}
