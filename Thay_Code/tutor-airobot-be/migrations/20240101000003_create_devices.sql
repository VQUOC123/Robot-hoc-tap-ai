-- +goose Up
CREATE TABLE devices (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(100) NOT NULL,
    token_hash   CHAR(64) NOT NULL UNIQUE,
    last_used_at TIMESTAMPTZ,
    last_ip      INET,
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- +goose Down
DROP TABLE IF EXISTS devices;
