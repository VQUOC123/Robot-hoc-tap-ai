-- +goose Up
CREATE TABLE settings (
    key        VARCHAR(100) PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Default system settings
INSERT INTO settings (key, value) VALUES
    ('capture_interval_sec', '10'),
    ('image_quality',        '82'),
    ('cooldown_hw_sec',      '30'),
    ('cooldown_no_hw_sec',   '10'),
    ('max_image_width',      '1024'),
    ('max_image_height',     '768');

-- +goose Down
DROP TABLE IF EXISTS settings;
