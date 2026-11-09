-- name: GetPrompt :one
SELECT * FROM prompts WHERE id = $1 LIMIT 1;

-- name: GetActivePromptByStage :one
SELECT * FROM prompts
WHERE stage = $1 AND is_active = true
  AND (subject_filter IS NULL OR subject_filter = $2)
ORDER BY subject_filter NULLS LAST
LIMIT 1;

-- name: ListPrompts :many
SELECT * FROM prompts
WHERE ($1::smallint = 0 OR stage = $1)
  AND ($2::boolean IS NULL OR is_active = $2)
ORDER BY stage, created_at DESC;

-- name: CreatePrompt :one
INSERT INTO prompts (name, stage, content, subject_filter, grade_filter, is_active)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;

-- name: UpdatePrompt :one
UPDATE prompts
SET name = $2, content = $3, subject_filter = $4,
    grade_filter = $5, is_active = $6,
    version = version + 1, updated_at = now()
WHERE id = $1
RETURNING *;

-- name: DeletePrompt :exec
DELETE FROM prompts WHERE id = $1;
