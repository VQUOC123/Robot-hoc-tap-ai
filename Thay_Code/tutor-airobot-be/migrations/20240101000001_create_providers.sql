-- +goose Up
CREATE TABLE providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    base_url        TEXT NOT NULL,
    api_key_enc     BYTEA NOT NULL,
    model           VARCHAR(100) NOT NULL,
    timeout_sec     INTEGER NOT NULL DEFAULT 30,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_tested_at  TIMESTAMPTZ,
    last_latency_ms INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT providers_name_key UNIQUE (name)
);

-- +goose Down
DROP TABLE IF EXISTS providers;
