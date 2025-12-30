.PHONY: help up down build logs test clean dev prod restart

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start all services in production mode
	docker-compose up -d

down: ## Stop all services
	docker-compose down

build: ## Build all Docker images
	docker-compose build

logs: ## View logs from all services
	docker-compose logs -f

test: ## Run backend tests
	cd backend && pytest -v

clean: ## Stop services and remove volumes
	docker-compose down -v

dev: ## Start all services in development mode with hot reload
	docker-compose -f docker-compose.dev.yml up

prod: ## Build and start all services in production mode
	docker-compose up --build -d

restart: ## Restart all services
	docker-compose restart

status: ## Show status of all services
	docker-compose ps

backend-logs: ## View backend logs
	docker-compose logs -f backend

frontend-logs: ## View frontend logs
	docker-compose logs -f frontend

redis-logs: ## View redis logs
	docker-compose logs -f redis

shell-backend: ## Open shell in backend container
	docker-compose exec backend sh

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

redis-cli: ## Connect to Redis CLI
	docker-compose exec redis redis-cli
