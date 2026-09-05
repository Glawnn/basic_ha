# basic_ha — template dev HA + Mosquitto
# Inspiré de pc-ha/Makefile, sans Rust
COMPOSE := docker compose -f docker/compose.yaml

.PHONY: help env-up env-down restart logs logs-ha logs-mqtt env-clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env-up: ## Start HA + Mosquitto (clean test env)
	$(COMPOSE) up -d

env-down: ## Stop all services (keep volumes)
	$(COMPOSE) down

restart: env-down env-up ## Restart all services

logs: ## Follow all logs
	$(COMPOSE) logs -f

logs-ha: ## Follow Home Assistant logs
	$(COMPOSE) logs -f homeassistant

logs-mqtt: ## Follow Mosquitto logs
	$(COMPOSE) logs -f mosquitto

env-clean: ## Stop all + drop HA volume (fresh onboarding)
	$(COMPOSE) down -v
