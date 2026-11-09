package request

// CreateDeviceRequest carries fields for POST /api/v1/devices.
type CreateDeviceRequest struct {
	Name string `json:"name" validate:"required,min=1,max=100"`
}
