package handler

import (
	"io"
	"mime/multipart"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
	appAnalysis "github.com/nhanntv/tutor-airobot-be/internal/application/analysis"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
)

// AnalysisHandler handles homework analysis requests from devices and history queries for admins.
type AnalysisHandler struct {
	analyzeUC *appAnalysis.AnalyzeUseCase
	listUC    *appAnalysis.ListAnalysesUseCase
}

// NewAnalysisHandler creates an AnalysisHandler.
func NewAnalysisHandler(
	analyzeUC *appAnalysis.AnalyzeUseCase,
	listUC *appAnalysis.ListAnalysesUseCase,
) *AnalysisHandler {
	return &AnalysisHandler{
		analyzeUC: analyzeUC,
		listUC:    listUC,
	}
}

// Analyze processes a homework image submitted by an authenticated device.
// Accepts multipart/form-data with fields: student_id, activity, focus_score, hw_visible, image.
func (h *AnalysisHandler) Analyze(c fiber.Ctx) error {
	device, ok := c.Locals("device").(*entity.Device)
	if !ok || device == nil {
		return httputil.Unauthorized(c)
	}

	// Parse multipart form
	form, err := c.MultipartForm()
	if err != nil {
		return httputil.BadRequest(c, "expected multipart/form-data")
	}

	// Read image file
	files := form.File["image"]
	if len(files) == 0 {
		return httputil.BadRequest(c, "image file is required")
	}
	f, err := files[0].Open()
	if err != nil {
		return httputil.BadRequest(c, "cannot read image file")
	}
	defer f.Close()

	imageRaw, err := io.ReadAll(f)
	if err != nil {
		return httputil.InternalError(c)
	}

	// Read form fields
	studentID := formValue(form, "student_id")
	activity := formValue(form, "activity")
	focusScore := formInt(form, "focus_score")
	hwVisible := formBool(form, "hw_visible")

	input := appAnalysis.AnalyzeInput{
		DeviceID:   device.ID,
		StudentID:  studentID,
		Activity:   activity,
		FocusScore: focusScore,
		HWVisible:  hwVisible,
		ImageRaw:   imageRaw,
	}

	out, err := h.analyzeUC.Execute(c.Context(), input)
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.OK(c, out)
}

// ListHistory returns paginated analysis records for admin review.
func (h *AnalysisHandler) ListHistory(c fiber.Ctx) error {
	input := appAnalysis.ListAnalysesInput{
		Cursor: c.Query("cursor"),
		Limit:  queryInt(c, "limit", 20),
	}

	if did := c.Query("device_id"); did != "" {
		id, err := uuid.Parse(did)
		if err == nil {
			input.DeviceID = &id
		}
	}
	if sub := c.Query("subject"); sub != "" {
		input.Subject = &sub
	}
	if hw := c.Query("doing_hw"); hw != "" {
		b := hw == "true"
		input.DoingHW = &b
	}
	if from := c.Query("from"); from != "" {
		input.From = &from
	}
	if to := c.Query("to"); to != "" {
		input.To = &to
	}

	out, err := h.listUC.Execute(c.Context(), input)
	if err != nil {
		return httputil.InternalError(c)
	}

	return httputil.OKWithMeta(c, out.Items, httputil.Meta{
		Cursor:  out.NextCursor,
		HasMore: out.HasMore,
	})
}

// ── multipart form helpers ────────────────────────────────────────────────────

func formValue(form *multipart.Form, key string) string {
	if vals := form.Value[key]; len(vals) > 0 {
		return vals[0]
	}
	return ""
}

func formInt(form *multipart.Form, key string) int {
	s := formValue(form, key)
	n := 0
	for _, ch := range s {
		if ch < '0' || ch > '9' {
			return 0
		}
		n = n*10 + int(ch-'0')
	}
	return n
}

func formBool(form *multipart.Form, key string) bool {
	v := formValue(form, key)
	return v == "true" || v == "1"
}

func queryInt(c fiber.Ctx, key string, defaultVal int) int {
	s := c.Query(key)
	if s == "" {
		return defaultVal
	}
	n := 0
	for _, ch := range s {
		if ch < '0' || ch > '9' {
			return defaultVal
		}
		n = n*10 + int(ch-'0')
	}
	return n
}
