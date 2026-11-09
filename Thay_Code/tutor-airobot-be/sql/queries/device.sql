-- name: GetDeviceByTokenHash :one
SELECT * FROM devices WHERE token_hash = $1 AND is_active = true LIMIT 1;

-- name: ListDevices :many
SELECT * FROM devices ORDER BY created_at DESC;

-- name: CreateDevice :one
INSERT INTO devices (name, token_hash)
VALUES ($1, $2)
RETURNING *;

-- name: UpdateDeviceLastUsed :exec
UPDATE devices
SET last_used_at = now(), last_ip = $2
WHERE id = $1;

-- name: RevokeDevice :exec
UPDATE devices SET is_active = false WHERE id = $1;

-- name: DeleteDevice :exec
DELETE FROM devices WHERE id = $1;
