 Installation issues to fix (reproducible):

 Resolution: fixed for `v0.6.0-alpha-rc.2`. The installer/setup path now pins pnpm, creates `.env.lite`, validates env files before sourcing, quotes values with spaces, defaults the local Ubuntu template to development mode, requires the repo venv, and aligns Docker Compose Postgres credentials with the active Alice env.

  1. make setup can fail on pnpm v11 with:
      - ERR_PNPM_IGNORED_BUILDS ... Run "pnpm approve-builds"
      - Result: setup exits non-zero, install looks broken/incomplete.
      - Fix: make setup non-interactive for pnpm build approvals (or pin pnpm
        behavior/version, or preconfigure allowed build deps in repo config).
  2. Generated .env contains invalid shell syntax:
      - ALICE_MCP_COMMAND=/path/to/python -m alicebot_api.mcp_server
      - Startup scripts source .env, so this executes -m as a command (-m:
        command not found).
      - Fix: always quote values with spaces when writing .env (or stop source-
        parsing and use dotenv parsing in scripts).
  3. Installer/runtime mode mismatch:
      - .env was generated with APP_ENV=production for local install.
      - Current app validation requires stricter production-only hardening
        values and rejects defaults.
      - Fix: default local install to APP_ENV=development, or production
        installer must populate all required production-safe vars.
  4. DB credential mismatch with docker compose defaults:
      - .env had custom DB passwords, but docker-compose.yml starts Postgres
        with default creds.
      - make migrate then fails with repeated password authentication failed for
        user "alicebot_admin" and timeout.
      - Fix: either align .env credentials with compose defaults for local mode,
        or make compose use env-provided credentials consistently.
  5. Missing .env.lite in install flow:
      - Lite scripts/docs expect it, but it may not be created by installer.
      - Fix: create .env.lite automatically (from .env.lite.example) during
        setup.

  Suggested guardrails so this doesn't repeat:

  - Add a preflight script that validates .env syntax and required keys before
    any startup.
  - Add CI/local smoke test: fresh clone -> make setup && make migrate && make
    doctor must pass non-interactively.
  - Add a check that sourced env lines with spaces are properly quoted.
  - Add a startup check that DB auth matches compose profile before running
    migrations.


---
Here the errors we got in the terminal:

 1. Your repo .env is a symlink to an external file, not a local file: .env:1
     -> /home/sam/.config/alicebot/.env.
  2. That external env has a Bash-breaking assignment at /home/sam/.config/
     alicebot/.env:50: ALICE_MCP_COMMAND=... -m ... is unquoted with spaces.
     Since startup scripts source .env (scripts/dev_up.sh:7, scripts/
     api_dev.sh:7, scripts/alice_lite_up.sh:7), this can fail immediately with
     -m: command not found.
  3. .venv is missing (.venv/bin/python does not exist), so scripts fall back to
     system python3 (scripts/dev_up.sh:13). But required modules are not
     installed there (psycopg, alembic, fastapi, sqlalchemy, uvicorn missing),
     and python3 -m alembic --version fails.
  4. Active env is in production mode: /home/sam/.config/alicebot/.env:4 has
     APP_ENV=production. In this repo, production mode enforces stricter
     settings (apps/api/src/alicebot_api/config.py:648); with your current key
     set, validation fails (for example missing required hardening vars).
  5. Config drift: active env differs from current template heavily (many
     missing current keys; extra legacy keys). Also .env.lite is missing, while
     quickstart expects it (README.md:55, README.md:267).

  Repo state itself is clean but detached (## HEAD (no branch)), so this is
  primarily an environment/install issue, not code corruption.
--
