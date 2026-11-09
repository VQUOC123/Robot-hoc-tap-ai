package entity

import (
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Role represents the permission level of an admin user.
type Role string

const (
	RoleViewer Role = "viewer" // Read-only access
	RoleEditor Role = "editor" // Can modify providers and prompts
	RoleAdmin  Role = "admin"  // Full access including user management
)

// AdminUser represents a human administrator who manages the backend via the dashboard.
type AdminUser struct {
	ID           uuid.UUID
	Email        string
	PasswordHash string
	Role         Role
	LastLoginAt  *time.Time
	CreatedAt    time.Time
}

// Validate performs basic domain-level validation on the admin user.
func (a *AdminUser) Validate() error {
	if a.Email == "" {
		return fmt.Errorf("admin email is required")
	}
	if a.PasswordHash == "" {
		return fmt.Errorf("admin password hash is required")
	}
	switch a.Role {
	case RoleViewer, RoleEditor, RoleAdmin:
		// valid
	default:
		return fmt.Errorf("admin role must be one of: viewer, editor, admin")
	}
	return nil
}

// IsAtLeast returns true when the user's role is at least as privileged as the given role.
func (a *AdminUser) IsAtLeast(role Role) bool {
	order := map[Role]int{
		RoleViewer: 1,
		RoleEditor: 2,
		RoleAdmin:  3,
	}
	return order[a.Role] >= order[role]
}
