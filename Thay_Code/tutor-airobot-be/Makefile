.PHONY: dev build test test-int migrate migrate-down generate seed lint docker-build

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Start local dev server (docker infra + hot reload)
	docker-compose up -d postgres redis
	@echo "Waiting for postgres..."
	@until docker-compose exec postgres pg_isready -U tutor > /dev/null 2>&1; do sleep 1; done
	@$(MAKE) migrate
	air -c .air.toml

infra-up: ## Start only postgres + redis
	docker-compose up -d postgres redis

infra-down: ## Stop postgres + redis
	docker-compose down

# ── Build ─────────────────────────────────────────────────────────────────────

build: ## Build production binary
	CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bin/server ./cmd/server

build-local: ## Build for current OS (dev/testing)
	go build -o bin/server ./cmd/server

# ── Testing ───────────────────────────────────────────────────────────────────

test: ## Run unit tests
	go test ./... -race -cover -short

test-int: ## Run integration tests (requires running DB + Redis)
	go test ./... -race -tags=integration

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Apply all pending migrations
	goose -dir migrations postgres "$(DATABASE_URL)" up

migrate-down: ## Rollback last migration
	goose -dir migrations postgres "$(DATABASE_URL)" down

migrate-status: ## Show migration status
	goose -dir migrations postgres "$(DATABASE_URL)" status

migrate-reset: ## Rollback all migrations
	goose -dir migrations postgres "$(DATABASE_URL)" reset

# ── Code Generation ───────────────────────────────────────────────────────────

generate: ## Generate type-safe SQL code with sqlc
	sqlc generate

# ── Seed ─────────────────────────────────────────────────────────────────────

seed: ## Seed default data (admin user + demo provider + default prompts)
	go run scripts/seed/main.go

# ── Code Quality ──────────────────────────────────────────────────────────────

lint: ## Run golangci-lint
	golangci-lint run ./...

fmt: ## Format code
	gofmt -s -w .
	goimports -w .

vet: ## Run go vet
	go vet ./...

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -t tutor-airobot-be:latest .

docker-run: ## Run with docker-compose (full stack)
	docker-compose --profile app up

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
