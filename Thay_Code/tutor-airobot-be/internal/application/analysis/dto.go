package analysis

import (
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// AnalyzeInput carries the context and raw image submitted by a device.
type AnalyzeInput struct {
	DeviceID   uuid.UUID
	StudentID  string
	Activity   string
	FocusScore int
	HWVisible  bool
	ImageRaw   []byte // raw JPEG or PNG bytes from the device camera
}

// AnalyzeOutput is the result returned to the device after processing.
type AnalyzeOutput struct {
	DoingHW        bool    `json:"doing_hw"`
	Subject        string  `json:"subject,omitempty"`
	Grade          string  `json:"grade,omitempty"`
	HWType         string  `json:"hw_type,omitempty"`
	Hints          string  `json:"hints,omitempty"`
	Progress       int     `json:"progress,omitempty"`
	Confidence     float64 `json:"confidence"`
	LatencyTotalMs int     `json:"latency_total_ms"`
}

// ListAnalysesInput carries pagination and filter parameters.
type ListAnalysesInput struct {
	DeviceID *uuid.UUID
	Subject  *string
	DoingHW  *bool
	From     *string // ISO-8601 date "2006-01-02", inclusive lower bound
	To       *string // ISO-8601 date "2006-01-02", inclusive upper bound
	Cursor   string  // base64-encoded cursor from previous page
	Limit    int
}

// ListAnalysesOutput is the paginated list response.
type ListAnalysesOutput struct {
	Items      []*AnalysisOutput `json:"items"`
	NextCursor *string           `json:"next_cursor,omitempty"`
	HasMore    bool              `json:"has_more"`
}

// AnalysisOutput is the public representation of a stored analysis record.
type AnalysisOutput struct {
	ID           uuid.UUID  `json:"id"`
	DeviceID     uuid.UUID  `json:"device_id"`
	DeviceName   string     `json:"device_name"`
	StudentID    *string    `json:"student_id,omitempty"`
	Activity     *string    `json:"activity,omitempty"`
	FocusScore   *int16     `json:"focus_score,omitempty"`
	HWVisible    *bool      `json:"hw_visible,omitempty"`
	DoingHW      *bool      `json:"doing_hw,omitempty"`
	Confidence   *float64   `json:"confidence,omitempty"`
	Subject      *string    `json:"subject,omitempty"`
	Grade        *string    `json:"grade,omitempty"`
	HWType       *string    `json:"hw_type,omitempty"`
	Progress     *int16     `json:"progress,omitempty"`
	Hints        *string    `json:"hints,omitempty"`
	ProviderID   *uuid.UUID `json:"provider_id,omitempty"`
	ProviderName *string    `json:"provider_name,omitempty"`
	LatencyMs    *int       `json:"latency_ms,omitempty"`
	ImageWidth   *int16     `json:"image_width,omitempty"`
	ImageHeight  *int16     `json:"image_height,omitempty"`
	ImageSizeKB  *int16     `json:"image_size_kb,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
}

// entityToOutput converts an Analysis entity to the public AnalysisOutput.
// deviceName and providerName are resolved by the use case layer via batch lookup.
func entityToOutput(a *entity.Analysis, deviceName string, providerName *string) *AnalysisOutput {
	out := &AnalysisOutput{
		ID:           a.ID,
		DeviceID:     a.DeviceID,
		DeviceName:   deviceName,
		StudentID:    a.StudentID,
		Activity:     a.Activity,
		FocusScore:   a.FocusScore,
		HWVisible:    a.HWVisible,
		DoingHW:      a.S1DoingHW,
		Confidence:   a.S1Confidence,
		Subject:      a.S2Subject,
		Grade:        a.S2Grade,
		HWType:       a.S2HWType,
		Progress:     a.S2Progress,
		Hints:        a.S2Hints,
		ProviderID:   a.ProviderID,
		ProviderName: providerName,
		ImageWidth:   a.ImageWidth,
		ImageHeight:  a.ImageHeight,
		ImageSizeKB:  a.ImageSizeKB,
		CreatedAt:    a.CreatedAt,
	}

	// Compute combined latency from both AI stages.
	total := 0
	if a.S1LatencyMs != nil {
		total += *a.S1LatencyMs
	}
	if a.S2LatencyMs != nil {
		total += *a.S2LatencyMs
	}
	if total > 0 {
		out.LatencyMs = &total
	}

	return out
}
