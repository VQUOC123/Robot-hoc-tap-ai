package analysis

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/pkg/pagination"
)

// ListAnalysesUseCase retrieves a page of analysis records enriched with device/provider names.
type ListAnalysesUseCase struct {
	analysisRepo repository.AnalysisRepository
	deviceRepo   repository.DeviceRepository
	providerRepo repository.ProviderRepository
}

// NewListAnalysesUseCase creates a ListAnalysesUseCase.
func NewListAnalysesUseCase(
	analysisRepo repository.AnalysisRepository,
	deviceRepo repository.DeviceRepository,
	providerRepo repository.ProviderRepository,
) *ListAnalysesUseCase {
	return &ListAnalysesUseCase{
		analysisRepo: analysisRepo,
		deviceRepo:   deviceRepo,
		providerRepo: providerRepo,
	}
}

// Execute decodes the cursor, queries the repository, enriches results with names, and encodes the next cursor.
func (uc *ListAnalysesUseCase) Execute(ctx context.Context, input ListAnalysesInput) (ListAnalysesOutput, error) {
	cursorTime, err := pagination.DecodeCursor(input.Cursor)
	if err != nil {
		return ListAnalysesOutput{}, fmt.Errorf("list analyses: invalid cursor: %w", err)
	}

	limit := pagination.NormalizeLimit(input.Limit)

	filter := repository.AnalysisFilter{
		DeviceID: input.DeviceID,
		Subject:  input.Subject,
		DoingHW:  input.DoingHW,
		Limit:    limit + 1, // fetch one extra to determine HasMore
	}
	if !cursorTime.IsZero() {
		filter.Cursor = &cursorTime
	}
	if input.From != nil {
		t, err := time.Parse("2006-01-02", *input.From)
		if err == nil {
			filter.From = &t
		}
	}
	if input.To != nil {
		t, err := time.Parse("2006-01-02", *input.To)
		if err == nil {
			// End of day — include the full "to" date.
			endOfDay := t.Add(24*time.Hour - time.Second)
			filter.To = &endOfDay
		}
	}

	records, err := uc.analysisRepo.List(ctx, filter)
	if err != nil {
		return ListAnalysesOutput{}, fmt.Errorf("list analyses: query: %w", err)
	}

	hasMore := len(records) > limit
	if hasMore {
		records = records[:limit]
	}

	// Batch-load device names and provider names to avoid N+1 queries.
	deviceNames := uc.buildDeviceNameMap(ctx)
	providerNames := uc.buildProviderNameMap(ctx)

	items := make([]*AnalysisOutput, len(records))
	for i, a := range records {
		dName := deviceNames[a.DeviceID]
		var pName *string
		if a.ProviderID != nil {
			if name, ok := providerNames[*a.ProviderID]; ok {
				pName = &name
			}
		}
		items[i] = entityToOutput(a, dName, pName)
	}

	var nextCursor *string
	if hasMore && len(records) > 0 {
		encoded := pagination.EncodeCursor(records[len(records)-1].CreatedAt)
		nextCursor = &encoded
	}

	return ListAnalysesOutput{
		Items:      items,
		NextCursor: nextCursor,
		HasMore:    hasMore,
	}, nil
}

// buildDeviceNameMap loads all devices and returns a map of ID → name.
// On error it returns an empty map so analyses still render without names.
func (uc *ListAnalysesUseCase) buildDeviceNameMap(ctx context.Context) map[uuid.UUID]string {
	m := make(map[uuid.UUID]string)
	devices, err := uc.deviceRepo.List(ctx)
	if err != nil {
		return m
	}
	for _, d := range devices {
		m[d.ID] = d.Name
	}
	return m
}

// buildProviderNameMap loads all providers and returns a map of ID → name.
func (uc *ListAnalysesUseCase) buildProviderNameMap(ctx context.Context) map[uuid.UUID]string {
	m := make(map[uuid.UUID]string)
	providers, err := uc.providerRepo.List(ctx)
	if err != nil {
		return m
	}
	for _, p := range providers {
		m[p.ID] = p.Name
	}
	return m
}
