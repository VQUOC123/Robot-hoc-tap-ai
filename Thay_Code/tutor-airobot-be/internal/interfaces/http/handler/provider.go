package handler

import (
	"errors"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
	appProvider "github.com/nhanntv/tutor-airobot-be/internal/application/provider"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/dto/request"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
	"github.com/nhanntv/tutor-airobot-be/pkg/validator"
)

// ProviderHandler handles CRUD + test operations for AI providers.
type ProviderHandler struct {
	createUC *appProvider.CreateProviderUseCase
	updateUC *appProvider.UpdateProviderUseCase
	deleteUC *appProvider.DeleteProviderUseCase
	listUC   *appProvider.ListProvidersUseCase
	getUC    *appProvider.GetProviderUseCase
	testUC   *appProvider.TestConnectionUseCase
}

// NewProviderHandler creates a ProviderHandler.
func NewProviderHandler(
	createUC *appProvider.CreateProviderUseCase,
	updateUC *appProvider.UpdateProviderUseCase,
	deleteUC *appProvider.DeleteProviderUseCase,
	listUC *appProvider.ListProvidersUseCase,
	getUC *appProvider.GetProviderUseCase,
	testUC *appProvider.TestConnectionUseCase,
) *ProviderHandler {
	return &ProviderHandler{
		createUC: createUC,
		updateUC: updateUC,
		deleteUC: deleteUC,
		listUC:   listUC,
		getUC:    getUC,
		testUC:   testUC,
	}
}

// List returns all AI providers.
func (h *ProviderHandler) List(c fiber.Ctx) error {
	providers, err := h.listUC.Execute(c.Context())
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.OK(c, providers)
}

// Get returns a single provider by ID.
func (h *ProviderHandler) Get(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid provider ID")
	}

	p, err := h.getUC.Execute(c.Context(), id)
	if err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "provider")
		}
		return httputil.InternalError(c)
	}
	return httputil.OK(c, p)
}

// Create registers a new AI provider.
func (h *ProviderHandler) Create(c fiber.Ctx) error {
	var req request.CreateProviderRequest
	if err := c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	p, err := h.createUC.Execute(c.Context(), appProvider.CreateProviderInput{
		Name:       req.Name,
		BaseURL:    req.BaseURL,
		APIKey:     req.APIKey,
		Model:      req.Model,
		TimeoutSec: req.TimeoutSec,
		IsDefault:  req.IsDefault,
	})
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.Created(c, p)
}

// Update modifies an existing provider.
func (h *ProviderHandler) Update(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid provider ID")
	}

	var req request.UpdateProviderRequest
	if err = c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	p, err := h.updateUC.Execute(c.Context(), id, appProvider.UpdateProviderInput{
		Name:       req.Name,
		BaseURL:    req.BaseURL,
		APIKey:     req.APIKey,
		Model:      req.Model,
		TimeoutSec: req.TimeoutSec,
		IsDefault:  req.IsDefault,
		IsActive:   req.IsActive,
	})
	if err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "provider")
		}
		return httputil.InternalError(c)
	}
	return httputil.OK(c, p)
}

// Delete removes a provider permanently.
func (h *ProviderHandler) Delete(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid provider ID")
	}

	if err = h.deleteUC.Execute(c.Context(), id); err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "provider")
		}
		return httputil.InternalError(c)
	}
	return httputil.NoContent(c)
}

// Test pings the provider and records latency.
func (h *ProviderHandler) Test(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid provider ID")
	}

	result, err := h.testUC.Execute(c.Context(), id)
	if err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "provider")
		}
		return httputil.InternalError(c)
	}
	return httputil.OK(c, result)
}

// parseUUID extracts and parses a UUID path parameter.
func parseUUID(c fiber.Ctx, param string) (uuid.UUID, error) {
	return uuid.Parse(c.Params(param))
}
