// Package migrations embeds all goose SQL migration files for inclusion in the server binary.
package migrations

import "embed"

// FS holds all *.sql migration files in this directory.
//
//go:embed *.sql
var FS embed.FS
