package handler

import (
	"errors"

	"github.com/gofiber/fiber/v3"
	appPrompt "github.com/nhanntv/tutor-airobot-be/internal/application/prompt"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/dto/request"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
	"github.com/nhanntv/tutor-airobot-be/pkg/validator"
)

// PromptHandler handles CRUD operations for AI prompt templates.
type PromptHandler struct {
	createUC *appPrompt.CreatePromptUseCase
	updateUC *appPrompt.UpdatePromptUseCase
	deleteUC *appPrompt.DeletePromptUseCase
	listUC   *appPrompt.ListPromptsUseCase
}

// NewPromptHandler creates a PromptHandler.
func NewPromptHandler(
	createUC *appPrompt.CreatePromptUseCase,
	updateUC *appPrompt.UpdatePromptUseCase,
	deleteUC *appPrompt.DeletePromptUseCase,
	listUC *appPrompt.ListPromptsUseCase,
) *PromptHandler {
	return &PromptHandler{
		createUC: createUC,
		updateUC: updateUC,
		deleteUC: deleteUC,
		listUC:   listUC,
	}
}

// List returns prompt templates with optional stage filter.
func (h *PromptHandler) List(c fiber.Ctx) error {
	filter := repository.PromptFilter{}

	if stageStr := c.Query("stage"); stageStr != "" {
		var stage int16
		if _, err := parseIntParam(stageStr, &stage); err == nil {
			filter.Stage = stage
		}
	}
	if activeStr := c.Query("is_active"); activeStr != "" {
		active := activeStr == "true"
		filter.IsActive = &active
	}

	prompts, err := h.listUC.Execute(c.Context(), filter)
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.OK(c, prompts)
}

// Create registers a new prompt template.
func (h *PromptHandler) Create(c fiber.Ctx) error {
	var req request.CreatePromptRequest
	if err := c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	p, err := h.createUC.Execute(c.Context(), appPrompt.CreatePromptInput{
		Name:          req.Name,
		Content:       req.Content,
		Stage:         req.Stage,
		SubjectFilter: req.SubjectFilter,
		GradeFilter:   req.GradeFilter,
		IsActive:      req.IsActive,
	})
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.Created(c, p)
}

// Update modifies an existing prompt template.
func (h *PromptHandler) Update(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid prompt ID")
	}

	var req request.UpdatePromptRequest
	if err = c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	p, err := h.updateUC.Execute(c.Context(), id, appPrompt.UpdatePromptInput{
		Name:          req.Name,
		Content:       req.Content,
		Stage:         req.Stage,
		SubjectFilter: req.SubjectFilter,
		GradeFilter:   req.GradeFilter,
		IsActive:      req.IsActive,
	})
	if err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "prompt")
		}
		return httputil.InternalError(c)
	}
	return httputil.OK(c, p)
}

// Delete removes a prompt permanently.
func (h *PromptHandler) Delete(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid prompt ID")
	}

	if err = h.deleteUC.Execute(c.Context(), id); err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "prompt")
		}
		return httputil.InternalError(c)
	}
	return httputil.NoContent(c)
}

// parseIntParam is a simple helper to parse a string into an *int16.
func parseIntParam(s string, dest *int16) (int16, error) {
	var v int
	_, err := readInt(s, &v)
	if err != nil {
		return 0, err
	}
	*dest = int16(v)
	return *dest, nil
}

func readInt(s string, v *int) (int, error) {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, errors.New("not a number")
		}
		n = n*10 + int(c-'0')
	}
	*v = n
	return n, nil
}
