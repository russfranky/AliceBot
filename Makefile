PYTHON ?= ./.venv/bin/python
ALICEBOT ?= ./.venv/bin/alicebot
PNPM ?= pnpm
WEB_DIR ?= apps/web

.PHONY: setup migrate dev doctor vnext scheduler alpha-check test-web test-python

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]'
	$(PNPM) --dir $(WEB_DIR) install
	@echo "Setup complete. Next: make migrate && make doctor"

migrate:
	./scripts/dev_up.sh

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

vnext:
	@echo "Start the local runtime with: make dev"
	@echo "Then open: http://localhost:3000/vnext"

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
