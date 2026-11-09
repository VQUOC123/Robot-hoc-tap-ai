-- +goose Up
CREATE TABLE analyses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id     UUID NOT NULL REFERENCES devices(id),
    student_id    VARCHAR(100),
    -- context
    activity      VARCHAR(50),
    focus_score   SMALLINT,
    hw_visible    BOOLEAN,
    -- stage 1
    s1_doing_hw   BOOLEAN,
    s1_confidence NUMERIC(4,3),
    s1_latency_ms INTEGER,
    -- stage 2 (null when s1_doing_hw = false)
    s2_subject    VARCHAR(50),
    s2_grade      VARCHAR(10),
    s2_hw_type    VARCHAR(50),
    s2_progress   SMALLINT,
    s2_hints      TEXT,
    s2_latency_ms INTEGER,
    -- provider
    provider_id   UUID REFERENCES providers(id),
    -- image metadata
    image_path    TEXT,
    image_width   SMALLINT,
    image_height  SMALLINT,
    image_size_kb SMALLINT,
    -- timing
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_analyses_created_at ON analyses (created_at DESC);
CREATE INDEX idx_analyses_device_id  ON analyses (device_id, created_at DESC);
CREATE INDEX idx_analyses_s2_subject ON analyses (s2_subject) WHERE s2_subject IS NOT NULL;
CREATE INDEX idx_analyses_s1_doing_hw ON analyses (s1_doing_hw, created_at DESC);

-- +goose Down
DROP INDEX IF EXISTS idx_analyses_s1_doing_hw;
DROP INDEX IF EXISTS idx_analyses_s2_subject;
DROP INDEX IF EXISTS idx_analyses_device_id;
DROP INDEX IF EXISTS idx_analyses_created_at;
DROP TABLE IF EXISTS analyses;
