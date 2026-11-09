-- +goose Up
CREATE TABLE prompts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    stage           SMALLINT NOT NULL CHECK (stage IN (1, 2)),
    content         TEXT NOT NULL,
    subject_filter  VARCHAR(50),
    grade_filter    VARCHAR(10),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prompts_stage_active ON prompts (stage, is_active);

-- +goose Down
DROP INDEX IF EXISTS idx_prompts_stage_active;
DROP TABLE IF EXISTS prompts;
