-- name: GetProvider :one
SELECT * FROM providers WHERE id = $1 LIMIT 1;

-- name: GetDefaultProvider :one
SELECT * FROM providers WHERE is_default = true AND is_active = true LIMIT 1;

-- name: ListProviders :many
SELECT * FROM providers ORDER BY is_default DESC, created_at DESC;

-- name: CreateProvider :one
INSERT INTO providers (name, base_url, api_key_enc, model, timeout_sec, is_default)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;

-- name: UpdateProvider :one
UPDATE providers
SET name = $2, base_url = $3, api_key_enc = $4, model = $5,
    timeout_sec = $6, is_default = $7, is_active = $8, updated_at = now()
WHERE id = $1
RETURNING *;

-- name: UpdateProviderTestResult :exec
UPDATE providers
SET last_tested_at = now(), last_latency_ms = $2, updated_at = now()
WHERE id = $1;

-- name: ClearDefaultProvider :exec
UPDATE providers SET is_default = false, updated_at = now()
WHERE is_default = true;

-- name: DeleteProvider :exec
DELETE FROM providers WHERE id = $1;
