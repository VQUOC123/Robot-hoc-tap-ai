package handler

import (
	"errors"

	"github.com/gofiber/fiber/v3"
	appDevice "github.com/nhanntv/tutor-airobot-be/internal/application/device"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/interfaces/http/dto/request"
	"github.com/nhanntv/tutor-airobot-be/pkg/httputil"
	"github.com/nhanntv/tutor-airobot-be/pkg/validator"
)

// DeviceCreateResponse wraps CreateDeviceOutput with an important note about the token.
type DeviceCreateResponse struct {
	appDevice.CreateDeviceOutput
	Note string `json:"note"`
}

// DeviceHandler handles device registration and management endpoints.
type DeviceHandler struct {
	createUC *appDevice.CreateDeviceUseCase
	revokeUC *appDevice.RevokeDeviceUseCase
	listUC   *appDevice.ListDevicesUseCase
}

// NewDeviceHandler creates a DeviceHandler.
func NewDeviceHandler(
	createUC *appDevice.CreateDeviceUseCase,
	revokeUC *appDevice.RevokeDeviceUseCase,
	listUC *appDevice.ListDevicesUseCase,
) *DeviceHandler {
	return &DeviceHandler{
		createUC: createUC,
		revokeUC: revokeUC,
		listUC:   listUC,
	}
}

// List returns all registered devices (tokens omitted).
func (h *DeviceHandler) List(c fiber.Ctx) error {
	devices, err := h.listUC.Execute(c.Context())
	if err != nil {
		return httputil.InternalError(c)
	}
	return httputil.OK(c, devices)
}

// Create registers a new device and returns the raw bearer token once.
// The caller must store the token securely — it cannot be retrieved after this response.
func (h *DeviceHandler) Create(c fiber.Ctx) error {
	var req request.CreateDeviceRequest
	if err := c.Bind().JSON(&req); err != nil {
		return httputil.BadRequest(c, "invalid request body")
	}
	if errs := validator.Validate(req); errs != nil {
		return httputil.BadRequest(c, errs[0].Message)
	}

	out, err := h.createUC.Execute(c.Context(), appDevice.CreateDeviceInput{Name: req.Name})
	if err != nil {
		return httputil.InternalError(c)
	}

	return httputil.Created(c, DeviceCreateResponse{
		CreateDeviceOutput: out,
		Note:               "Store the token securely — it will not be shown again.",
	})
}

// Revoke deactivates a device so it can no longer authenticate.
func (h *DeviceHandler) Revoke(c fiber.Ctx) error {
	id, err := parseUUID(c, "id")
	if err != nil {
		return httputil.BadRequest(c, "invalid device ID")
	}

	if err = h.revokeUC.Execute(c.Context(), id); err != nil {
		if errors.Is(err, apperror.ErrNotFound) {
			return httputil.NotFound(c, "device")
		}
		return httputil.InternalError(c)
	}
	return httputil.NoContent(c)
}
