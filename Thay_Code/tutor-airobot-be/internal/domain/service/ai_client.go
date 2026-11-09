package service

import "context"

// Stage1Result holds the output of the homework detection stage.
type Stage1Result struct {
	DoingHW    bool    // true when the student is clearly doing school homework
	Confidence float64 // 0.0–1.0
	LatencyMs  int     // round-trip time including provider latency
}

// Stage2Result holds the output of the homework analysis stage.
type Stage2Result struct {
	Subject   string // e.g. "Toán", "Văn", "Tiếng Anh"
	Grade     string // e.g. "10", "11" or empty when unknown
	HWType    string // e.g. "bài tập", "luận văn"
	Progress  int    // estimated completion 0–100
	Hints     string // 1-2 sentence Vietnamese hint for the student
	LatencyMs int
}

// AIClient abstracts the two-stage AI homework analysis pipeline.
// Implementations delegate to a specific provider (OpenAI-compatible, etc.).
type AIClient interface {
	// DetectHomework performs Stage 1: classify whether the image shows homework.
	DetectHomework(ctx context.Context, imageJPEG []byte) (Stage1Result, error)

	// AnalyzeHomework performs Stage 2: extract subject, grade, progress, and hints.
	// Should only be called when Stage 1 returned DoingHW = true.
	AnalyzeHomework(ctx context.Context, imageJPEG []byte) (Stage2Result, error)
}
