-- name: GetAdminByEmail :one
SELECT * FROM admin_users WHERE email = $1 LIMIT 1;

-- name: GetAdminByID :one
SELECT * FROM admin_users WHERE id = $1 LIMIT 1;

-- name: CreateAdmin :one
INSERT INTO admin_users (email, password_hash, role)
VALUES ($1, $2, $3)
RETURNING *;

-- name: UpdateAdminLastLogin :exec
UPDATE admin_users SET last_login_at = now() WHERE id = $1;
