package entity

import (
	"time"

	"github.com/google/uuid"
)

// Analysis stores the result of a single homework analysis request
// from a device, including both Stage 1 (detection) and Stage 2 (subject analysis).
type Analysis struct {
	ID        uuid.UUID
	DeviceID  uuid.UUID
	StudentID *string

	// Context sent by the device
	Activity   *string
	FocusScore *int16
	HWVisible  *bool

	// Stage 1: Homework detection
	S1DoingHW    *bool
	S1Confidence *float64
	S1LatencyMs  *int

	// Stage 2: Homework analysis (populated only when S1DoingHW = true)
	S2Subject    *string
	S2Grade      *string
	S2HWType     *string
	S2Progress   *int16
	S2Hints      *string
	S2LatencyMs  *int

	// Provider that processed the request
	ProviderID *uuid.UUID

	// Captured image metadata
	ImagePath    *string
	ImageWidth   *int16
	ImageHeight  *int16
	ImageSizeKB  *int16

	CreatedAt time.Time
}
