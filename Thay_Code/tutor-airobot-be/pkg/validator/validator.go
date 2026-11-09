package validator

import (
	"strings"

	"github.com/go-playground/validator/v10"
)

var instance = validator.New()

// ValidationError represents a field-level validation failure.
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// Validate validates a struct and returns a slice of field errors.
// Returns nil when valid.
func Validate(s any) []ValidationError {
	err := instance.Struct(s)
	if err == nil {
		return nil
	}

	var errs []ValidationError
	for _, e := range err.(validator.ValidationErrors) {
		errs = append(errs, ValidationError{
			Field:   toSnakeCase(e.Field()),
			Message: humanize(e),
		})
	}
	return errs
}

func toSnakeCase(s string) string {
	var result strings.Builder
	for i, r := range s {
		if i > 0 && r >= 'A' && r <= 'Z' {
			result.WriteRune('_')
		}
		result.WriteRune(r)
	}
	return strings.ToLower(result.String())
}

func humanize(e validator.FieldError) string {
	switch e.Tag() {
	case "required":
		return "this field is required"
	case "min":
		return "value is too short (min " + e.Param() + ")"
	case "max":
		return "value is too long (max " + e.Param() + ")"
	case "email":
		return "invalid email address"
	case "url":
		return "invalid URL"
	case "oneof":
		return "must be one of: " + e.Param()
	default:
		return "invalid value"
	}
}
