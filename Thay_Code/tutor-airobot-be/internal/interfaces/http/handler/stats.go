package handler

import (
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
	"github.com/nhanntv/tutor-airobot-be/pkg/timeutil"
)

// OverviewResponse is the payload for GET /api/v1/stats/overview.
type OverviewResponse struct {
	TotalAnalyses   int64   `json:"total_analyses"`
	TodayTotal      int64   `json:"today_total"`
	TodayHomework   int64   `json:"today_homework"`
	HomeworkRate    float64 `json:"homework_rate"`
	AvgLatencyMs    float64 `json:"avg_latency_ms"`
	ActiveProviders int     `json:"active_providers"`
	ActiveDevices   int     `json:"active_devices"`
	TopSubject      string  `json:"top_subject,omitempty"`
}

// LatencyHourlyResponse is one data point for GET /api/v1/stats/latency.
type LatencyHourlyResponse struct {
	Hour  string  `json:"hour"`   // RFC3339 UTC hour timestamp
	AvgMs float64 `json:"avg_ms"` // average total latency (s1 + s2) in ms
	Count int64   `json:"count"`  // number of analyses in this hour
}

// SubjectStatResponse is one data point for GET /api/v1/stats/subjects.
type SubjectStatResponse struct {
	Subject string `json:"subject"`
	Count   int64  `json:"count"`
}

// StatsHandler serves analytics and latency dashboards.
type StatsHandler struct {
	analysisRepo repository.AnalysisRepository
	deviceRepo   repository.DeviceRepository
	providerRepo repository.ProviderRepository
}

// NewStatsHandler creates a StatsHandler.
func NewStatsHandler(
	analysisRepo repository.AnalysisRepository,
	deviceRepo repository.DeviceRepository,
	providerRepo repository.ProviderRepository,
) *StatsHandler {
	return &StatsHandler{
		analysisRepo: analysisRepo,
		deviceRepo:   deviceRepo,
		providerRepo: providerRepo,
	}
}

// Overview returns key system metrics for the admin dashboard.
func (h *StatsHandler) Overview(c fiber.Ctx) error {
	ctx := c.Context()

	totalAll, err := h.analysisRepo.CountAll(ctx)
	if err != nil {
		return httputil.InternalError(c)
	}

	todayTotal, todayHomework, err := h.analysisRepo.CountToday(ctx)
	if err != nil {
		return httputil.InternalError(c)
	}

	avgLatency, err := h.analysisRepo.AvgLatencyLast24h(ctx)
	if err != nil {
		return httputil.InternalError(c)
	}

	var hwRate float64
	if todayTotal > 0 {
		hwRate = float64(todayHomework) / float64(todayTotal)
	}

	// Top subject from the last 7 days.
	from7d := timeutil.StartOfDay(time.Now().AddDate(0, 0, -7))
	subjects, _ := h.analysisRepo.CountBySubject(ctx, from7d, time.Now().UTC())
	topSubject := ""
	if len(subjects) > 0 {
		topSubject = subjects[0].Subject
	}

	// Count active devices and providers via in-memory filter on List results.
	activeDevices := 0
	if devices, err := h.deviceRepo.List(ctx); err == nil {
		for _, d := range devices {
			if d.IsActive {
				activeDevices++
			}
		}
	}

	activeProviders := 0
	if providers, err := h.providerRepo.List(ctx); err == nil {
		for _, p := range providers {
			if p.IsActive {
				activeProviders++
			}
		}
	}

	return httputil.OK(c, OverviewResponse{
		TotalAnalyses:   totalAll,
		TodayTotal:      todayTotal,
		TodayHomework:   todayHomework,
		HomeworkRate:    hwRate,
		AvgLatencyMs:    avgLatency,
		ActiveProviders: activeProviders,
		ActiveDevices:   activeDevices,
		TopSubject:      topSubject,
	})
}

// Latency returns average AI latency grouped by UTC hour for the last 24 hours.
func (h *StatsHandler) Latency(c fiber.Ctx) error {
	from := time.Now().UTC().Add(-24 * time.Hour)
	hourly, err := h.analysisRepo.LatencyByHour(c.Context(), from)
	if err != nil {
		return httputil.InternalError(c)
	}

	result := make([]LatencyHourlyResponse, 0, len(hourly))
	for _, lh := range hourly {
		result = append(result, LatencyHourlyResponse{
			Hour:  lh.Hour.UTC().Format(time.RFC3339),
			AvgMs: lh.AvgMs,
			Count: lh.Count,
		})
	}

	return httputil.OK(c, result)
}

// Subjects returns per-subject analysis counts for the last 30 days.
func (h *StatsHandler) Subjects(c fiber.Ctx) error {
	from := timeutil.StartOfDay(time.Now().AddDate(0, 0, -30))
	to := time.Now().UTC()

	counts, err := h.analysisRepo.CountBySubject(c.Context(), from, to)
	if err != nil {
		return httputil.InternalError(c)
	}

	result := make([]SubjectStatResponse, 0, len(counts))
	for _, sc := range counts {
		result = append(result, SubjectStatResponse{
			Subject: sc.Subject,
			Count:   sc.Count,
		})
	}

	return httputil.OK(c, result)
}
