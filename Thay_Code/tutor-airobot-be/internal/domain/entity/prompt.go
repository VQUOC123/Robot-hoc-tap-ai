package entity

import (
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Stage identifies the AI pipeline stage a prompt belongs to.
type Stage int16

const (
	Stage1 Stage = 1 // Homework detection — does the image show a student doing homework?
	Stage2 Stage = 2 // Homework analysis — subject, grade, progress, hints.
)

// Prompt represents an AI prompt template for a given pipeline stage.
type Prompt struct {
	ID            uuid.UUID
	Name          string
	Stage         Stage
	Content       string
	SubjectFilter *string // nil means applies to all subjects
	GradeFilter   *string // nil means applies to all grades
	IsActive      bool
	Version       int
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// Validate performs basic domain-level validation on the prompt.
func (p *Prompt) Validate() error {
	if p.Name == "" {
		return fmt.Errorf("prompt name is required")
	}
	if len(p.Name) > 100 {
		return fmt.Errorf("prompt name must not exceed 100 characters")
	}
	if p.Stage != Stage1 && p.Stage != Stage2 {
		return fmt.Errorf("prompt stage must be 1 or 2")
	}
	if p.Content == "" {
		return fmt.Errorf("prompt content is required")
	}
	if p.SubjectFilter != nil && len(*p.SubjectFilter) > 50 {
		return fmt.Errorf("subject filter must not exceed 50 characters")
	}
	if p.GradeFilter != nil && len(*p.GradeFilter) > 10 {
		return fmt.Errorf("grade filter must not exceed 10 characters")
	}
	return nil
}
