package httputil

import "github.com/gofiber/fiber/v3"

// Response is the standard JSON envelope for all API responses.
type Response[T any] struct {
	Data  T     `json:"data,omitempty"`
	Error *Err  `json:"error,omitempty"`
	Meta  *Meta `json:"meta,omitempty"`
}

// Err represents a structured API error.
type Err struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

// Meta carries pagination and other response metadata.
type Meta struct {
	Cursor  *string `json:"cursor,omitempty"`
	HasMore bool    `json:"has_more"`
	Total   *int64  `json:"total,omitempty"`
}

// OK sends a 200 response with data.
func OK[T any](c fiber.Ctx, data T) error {
	return c.Status(fiber.StatusOK).JSON(Response[T]{Data: data})
}

// OKWithMeta sends a 200 response with data and pagination meta.
func OKWithMeta[T any](c fiber.Ctx, data T, meta Meta) error {
	return c.Status(fiber.StatusOK).JSON(Response[T]{Data: data, Meta: &meta})
}

// Created sends a 201 response with data.
func Created[T any](c fiber.Ctx, data T) error {
	return c.Status(fiber.StatusCreated).JSON(Response[T]{Data: data})
}

// NoContent sends a 204 response.
func NoContent(c fiber.Ctx) error {
	return c.SendStatus(fiber.StatusNoContent)
}

// Fail sends an error response with the given HTTP status.
func Fail(c fiber.Ctx, status int, code, message string) error {
	return c.Status(status).JSON(Response[any]{
		Error: &Err{Code: code, Message: message},
	})
}

// BadRequest sends a 400 response.
func BadRequest(c fiber.Ctx, message string) error {
	return Fail(c, fiber.StatusBadRequest, "BAD_REQUEST", message)
}

// Unauthorized sends a 401 response.
func Unauthorized(c fiber.Ctx) error {
	return Fail(c, fiber.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
}

// Forbidden sends a 403 response.
func Forbidden(c fiber.Ctx) error {
	return Fail(c, fiber.StatusForbidden, "FORBIDDEN", "Insufficient permissions")
}

// NotFound sends a 404 response.
func NotFound(c fiber.Ctx, resource string) error {
	return Fail(c, fiber.StatusNotFound, "NOT_FOUND", resource+" not found")
}

// Conflict sends a 409 response.
func Conflict(c fiber.Ctx, message string) error {
	return Fail(c, fiber.StatusConflict, "CONFLICT", message)
}

// InternalError sends a 500 response.
func InternalError(c fiber.Ctx) error {
	return Fail(c, fiber.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}
