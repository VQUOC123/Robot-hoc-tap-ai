package request

// AnalyzeFormRequest carries the multipart form fields for POST /api/v1/device/analyze.
// The actual image bytes are read separately from the multipart file part.
type AnalyzeFormRequest struct {
	StudentID  string `form:"student_id"`
	Activity   string `form:"activity"`
	FocusScore int    `form:"focus_score"`
	HWVisible  bool   `form:"hw_visible"`
}
