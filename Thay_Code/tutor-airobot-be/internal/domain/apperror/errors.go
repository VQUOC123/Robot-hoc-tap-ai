package apperror

import (
	"errors"
	"fmt"
)

// Sentinel errors — use errors.Is() for matching.
var (
	ErrNotFound      = errors.New("not found")
	ErrUnauthorized  = errors.New("unauthorized")
	ErrForbidden     = errors.New("forbidden")
	ErrConflict      = errors.New("conflict")
	ErrInvalidInput  = errors.New("invalid input")
	ErrInternalError = errors.New("internal error")
)

// AppError carries a machine-readable code and a human-readable message
// alongside a wrapped sentinel for errors.Is compatibility.
type AppError struct {
	Code    string
	Message string
	Err     error
}

func (e *AppError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %s", e.Code, e.Message)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *AppError) Unwrap() error {
	return e.Err
}

// New creates an AppError wrapping the given sentinel.
func New(sentinel error, code, message string) *AppError {
	return &AppError{
		Code:    code,
		Message: message,
		Err:     fmt.Errorf("%w", sentinel),
	}
}

// NotFound returns an AppError wrapping ErrNotFound.
func NotFound(resource string) *AppError {
	return New(ErrNotFound, "NOT_FOUND", resource+" not found")
}

// Unauthorized returns an AppError wrapping ErrUnauthorized.
func Unauthorized(message string) *AppError {
	if message == "" {
		message = "authentication required"
	}
	return New(ErrUnauthorized, "UNAUTHORIZED", message)
}

// Forbidden returns an AppError wrapping ErrForbidden.
func Forbidden(message string) *AppError {
	if message == "" {
		message = "insufficient permissions"
	}
	return New(ErrForbidden, "FORBIDDEN", message)
}

// Conflict returns an AppError wrapping ErrConflict.
func Conflict(message string) *AppError {
	return New(ErrConflict, "CONFLICT", message)
}

// InvalidInput returns an AppError wrapping ErrInvalidInput.
func InvalidInput(message string) *AppError {
	return New(ErrInvalidInput, "INVALID_INPUT", message)
}

// Internal returns an AppError wrapping ErrInternalError.
func Internal(message string) *AppError {
	if message == "" {
		message = "an unexpected error occurred"
	}
	return New(ErrInternalError, "INTERNAL_ERROR", message)
}
