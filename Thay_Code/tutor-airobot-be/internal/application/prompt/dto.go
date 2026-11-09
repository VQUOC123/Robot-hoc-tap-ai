package prompt

import (
	"time"

	"github.com/google/uuid"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
)

// CreatePromptInput carries fields required to create a new prompt template.
type CreatePromptInput struct {
	Name          string
	Content       string
	Stage         int16
	SubjectFilter *string
	GradeFilter   *string
	IsActive      bool
}

// UpdatePromptInput carries fields that can be changed on an existing prompt.
type UpdatePromptInput struct {
	Name          string
	Content       string
	Stage         int16
	SubjectFilter *string
	GradeFilter   *string
	IsActive      bool
}

// PromptOutput is the public representation of a prompt template.
type PromptOutput struct {
	ID            uuid.UUID `json:"id"`
	Name          string    `json:"name"`
	Stage         int16     `json:"stage"`
	Content       string    `json:"content"`
	SubjectFilter *string   `json:"subject_filter"`
	GradeFilter   *string   `json:"grade_filter"`
	IsActive      bool      `json:"is_active"`
	Version       int       `json:"version"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// toOutput converts a Prompt entity to a PromptOutput.
func toOutput(p *entity.Prompt) *PromptOutput {
	return &PromptOutput{
		ID:            p.ID,
		Name:          p.Name,
		Stage:         int16(p.Stage),
		Content:       p.Content,
		SubjectFilter: p.SubjectFilter,
		GradeFilter:   p.GradeFilter,
		IsActive:      p.IsActive,
		Version:       p.Version,
		CreatedAt:     p.CreatedAt,
		UpdatedAt:     p.UpdatedAt,
	}
}
