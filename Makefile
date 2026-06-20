PYTHON ?= ./.venv/bin/python
ALICEBOT ?= ./.venv/bin/alicebot
PNPM ?= pnpm
WEB_DIR ?= apps/web
ALICE_WEB_HOST ?= 127.0.0.1
ALICE_WEB_PORT ?= 3000

.PHONY: setup migrate api dev runtime web-build doctor vnext scheduler alpha-check test-web test-python

setup:
	@test -f .env || cp .env.example .env
	@test -f .env.lite || cp .env.lite.example .env.lite
	@test -f $(WEB_DIR)/.env.local || cp $(WEB_DIR)/.env.local.example $(WEB_DIR)/.env.local
	./scripts/validate_env.sh .env .env.lite $(WEB_DIR)/.env.local
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]'
	PNPM="$(PNPM)" WEB_DIR="$(WEB_DIR)" ./scripts/pnpm_web_install.sh
	@echo "Setup complete. Next: make migrate && make doctor"

migrate:
	./scripts/dev_up.sh

api:
	APP_RELOAD=false ./scripts/api_dev.sh

doctor:
	$(ALICEBOT) vnext doctor --fix-safe --ci

dev:
	./scripts/dev_up.sh
	APP_RELOAD=false ./scripts/api_dev.sh & \
	api_pid=$$!; \
	$(PNPM) --dir $(WEB_DIR) dev & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$api_pid $$web_pid

runtime:
	./scripts/dev_up.sh
	$(PNPM) --dir $(WEB_DIR) build
	APP_RELOAD=false ./scripts/api_dev.sh & \
	api_pid=$$!; \
	$(PNPM) --dir $(WEB_DIR) start --hostname $(ALICE_WEB_HOST) --port $(ALICE_WEB_PORT) & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$api_pid $$web_pid

web-build:
	$(PNPM) --dir $(WEB_DIR) build

vnext:
	@echo "Start the low-CPU local runtime with: make runtime"
	@echo "Use make dev only when editing the web UI."
	@echo "Then open: http://localhost:$(ALICE_WEB_PORT)/vnext"

scheduler:
	$(ALICEBOT) vnext scheduler daemon start --foreground

alpha-check:
	$(ALICEBOT) vnext alpha check

test-python:
	$(PYTHON) -m pytest tests/unit -q
	$(PYTHON) -m pytest tests/integration -q

test-web:
	$(PNPM) --dir $(WEB_DIR) test
	$(PNPM) --dir $(WEB_DIR) lint
	$(PNPM) --dir $(WEB_DIR) build
