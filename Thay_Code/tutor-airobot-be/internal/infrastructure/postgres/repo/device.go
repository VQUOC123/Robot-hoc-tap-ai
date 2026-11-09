package repo

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/entity"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/repository"
)

// DeviceRepo implements repository.DeviceRepository using pgxpool.
type DeviceRepo struct {
	pool *pgxpool.Pool
}

func NewDeviceRepo(pool *pgxpool.Pool) *DeviceRepo {
	return &DeviceRepo{pool: pool}
}

var _ repository.DeviceRepository = (*DeviceRepo)(nil)

func (r *DeviceRepo) GetByTokenHash(ctx context.Context, hash string) (*entity.Device, error) {
	const q = `
		SELECT id, name, token_hash, last_used_at, last_ip, is_active, created_at
		FROM devices WHERE token_hash = $1 AND is_active = true`

	row := r.pool.QueryRow(ctx, q, hash)
	d, err := scanDevice(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, apperror.NotFound("device")
		}
		return nil, fmt.Errorf("device.GetByTokenHash: %w", err)
	}
	return d, nil
}

func (r *DeviceRepo) List(ctx context.Context) ([]*entity.Device, error) {
	const q = `
		SELECT id, name, token_hash, last_used_at, last_ip, is_active, created_at
		FROM devices ORDER BY created_at DESC`

	rows, err := r.pool.Query(ctx, q)
	if err != nil {
		return nil, fmt.Errorf("device.List: %w", err)
	}
	defer rows.Close()

	var devices []*entity.Device
	for rows.Next() {
		d, err := scanDevice(rows)
		if err != nil {
			return nil, fmt.Errorf("device.List scan: %w", err)
		}
		devices = append(devices, d)
	}
	return devices, rows.Err()
}

func (r *DeviceRepo) Create(ctx context.Context, d *entity.Device) (*entity.Device, error) {
	const q = `
		INSERT INTO devices (name, token_hash, is_active)
		VALUES ($1, $2, $3)
		RETURNING id, name, token_hash, last_used_at, last_ip, is_active, created_at`

	row := r.pool.QueryRow(ctx, q, d.Name, d.TokenHash, d.IsActive)
	created, err := scanDevice(row)
	if err != nil {
		return nil, fmt.Errorf("device.Create: %w", err)
	}
	return created, nil
}

func (r *DeviceRepo) UpdateLastUsed(ctx context.Context, id uuid.UUID, ip string) error {
	const q = `
		UPDATE devices SET last_used_at = $2, last_ip = $3::inet
		WHERE id = $1`

	now := time.Now().UTC()
	if _, err := r.pool.Exec(ctx, q, id, now, ip); err != nil {
		return fmt.Errorf("device.UpdateLastUsed: %w", err)
	}
	return nil
}

func (r *DeviceRepo) Revoke(ctx context.Context, id uuid.UUID) error {
	const q = `UPDATE devices SET is_active = false WHERE id = $1`
	tag, err := r.pool.Exec(ctx, q, id)
	if err != nil {
		return fmt.Errorf("device.Revoke: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return apperror.NotFound("device")
	}
	return nil
}

func (r *DeviceRepo) Delete(ctx context.Context, id uuid.UUID) error {
	const q = `DELETE FROM devices WHERE id = $1`
	tag, err := r.pool.Exec(ctx, q, id)
	if err != nil {
		return fmt.Errorf("device.Delete: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return apperror.NotFound("device")
	}
	return nil
}

func scanDevice(row scannable) (*entity.Device, error) {
	var d entity.Device
	var lastIP *string
	err := row.Scan(
		&d.ID, &d.Name, &d.TokenHash, &d.LastUsedAt, &lastIP, &d.IsActive, &d.CreatedAt,
	)
	if err != nil {
		return nil, err
	}
	d.LastIP = lastIP
	return &d, nil
}
