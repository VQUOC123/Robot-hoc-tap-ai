package request

// CreatePromptRequest carries fields for POST /api/v1/prompts.
type CreatePromptRequest struct {
	Name          string  `json:"name"           validate:"required,min=1,max=100"`
	Stage         int16   `json:"stage"          validate:"required,oneof=1 2"`
	Content       string  `json:"content"        validate:"required"`
	SubjectFilter *string `json:"subject_filter"`
	GradeFilter   *string `json:"grade_filter"`
	IsActive      bool    `json:"is_active"`
}

// UpdatePromptRequest carries fields for PUT /api/v1/prompts/:id.
type UpdatePromptRequest struct {
	Name          string  `json:"name"           validate:"required,min=1,max=100"`
	Stage         int16   `json:"stage"          validate:"required,oneof=1 2"`
	Content       string  `json:"content"        validate:"required"`
	SubjectFilter *string `json:"subject_filter"`
	GradeFilter   *string `json:"grade_filter"`
	IsActive      bool    `json:"is_active"`
}
