package auth

import "github.com/google/uuid"

// LoginInput carries credentials submitted by an admin user.
type LoginInput struct {
	Email    string
	Password string
}

// UserInfo is a minimal admin user representation embedded in tokens.
type UserInfo struct {
	ID    uuid.UUID `json:"id"`
	Email string    `json:"email"`
	Role  string    `json:"role"`
}

// LoginOutput is returned on successful login.
type LoginOutput struct {
	AccessToken string   `json:"access_token"`
	User        UserInfo `json:"user"`
}

// RefreshOutput is returned when a refresh token is exchanged for a new access token.
type RefreshOutput struct {
	AccessToken string `json:"access_token"`
}
