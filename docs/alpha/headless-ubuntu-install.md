# Headless Ubuntu Install

This guide installs Alice vNext from GitHub on a headless Ubuntu server, VPS, home lab box, or same-host agent machine. It assumes SSH access and no local GUI on the server.

Supported assumptions for this alpha:

- Ubuntu 22.04 LTS or 24.04 LTS
- Python 3.12-compatible system Python or newer venv support
- Node 20 through NodeSource or an existing Node 20 install
- local Postgres with `pgvector` on the same host, or an existing Postgres reached through `DATABASE_URL`
- services bound to `127.0.0.1` by default

This is the current headless install path for the Alice vNext public-preview line. The active preview release target is `v0.5.1-vnext-preview` on top of stable `v0.5.1`.

Historical note: `v0.6.0-alpha-rc.2` remains an older internal Ubuntu dogfood packaging milestone. Keep it for audit trail and rollback evidence, but do not treat it as the current public preview boundary.

## Recommended Secure Access

Use an SSH tunnel from your laptop:

```bash
ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@ubuntu-box
```

Then open this from your local browser:

```text
http://127.0.0.1:3000/vnext
```

Do not expose `/vnext`, the API, MCP, or browser clipper endpoint publicly by default. Keep services bound to localhost and add an authenticated reverse proxy only after the alpha path is working over SSH.

## Inspect-Before-Run Install

```bash
curl -fsSL https://raw.githubusercontent.com/samrusani/AliceBot/main/scripts/install-ubuntu.sh -o install-alice.sh
less install-alice.sh
bash install-alice.sh --branch main --install-dir ~/alicebot
```

For an immutable preview install after the preview tag is published, replace `--branch main` with `--tag v0.5.1-vnext-preview`.

Use `--non-interactive` only after you have chosen a safe install directory and know whether the host should install local Postgres.

## Installer Options

```bash
bash install-alice.sh --branch main
bash install-alice.sh --tag v0.5.1-vnext-preview
bash install-alice.sh --install-dir ~/alicebot
bash install-alice.sh --skip-postgres-install
bash install-alice.sh --install-systemd
bash install-alice.sh --non-interactive
bash install-alice.sh --dry-run
```

The installer is idempotent enough to rerun safely:

- existing git checkout is fetched and checked out to the requested tag or branch
- existing config is preserved
- repo `.env` is linked to the preserved config file when safe
- generated local database passwords are not printed
- blocking failures exit non-zero

## Local Configuration Layout

Default paths:

- repo: `~/alicebot`
- config: `~/.config/alicebot/.env`
- data: `~/.local/share/alicebot/`
- logs/state: `~/.local/state/alicebot/logs/`
- runtime pid/status files: `~/.alicebot/`
- local secret references: `~/.config/alicebot/secrets/`

The installer renders [packaging/ubuntu/alicebot.env.example](../../packaging/ubuntu/alicebot.env.example) into `~/.config/alicebot/.env` if the file does not already exist. Existing config is preserved.
For local Postgres installs, it detects the server major version, installs the matching `postgresql-<major>-pgvector` package, and creates the `vector` extension before migrations.

Important config keys:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql://alicebot_app:<redacted>@127.0.0.1:5432/alicebot
DATABASE_ADMIN_URL=postgresql://alicebot_admin:<redacted>@127.0.0.1:5432/alicebot
ALICE_API_HOST=127.0.0.1
ALICE_API_PORT=8000
ALICE_WEB_HOST=127.0.0.1
ALICE_WEB_PORT=3000
ALICE_SECRET_PROVIDER=encrypted_local
MODEL_PROVIDER=deterministic_local
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ALICEBOT_USER_ID=00000000-0000-0000-0000-000000000001
ALICE_MCP_COMMAND="~/alicebot/.venv/bin/python -m alicebot_api.mcp_server"
```

Secrets are referenced, not printed. Store real connector secrets through the configured secret-provider path, then configure connectors with `secret_ref` values such as `telegram.bot_token.default`.

## Manual Install Fallback

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git build-essential python3 python3-venv python3-pip libpq-dev postgresql postgresql-contrib postgresql-16-pgvector
git clone https://github.com/samrusani/AliceBot.git ~/alicebot
cd ~/alicebot
git checkout main
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
corepack enable
corepack prepare pnpm@10.23.0 --activate
cp .env.lite.example .env.lite
cp apps/web/.env.local.example apps/web/.env.local
pnpm --dir apps/web install
pnpm --dir apps/web build
cp packaging/ubuntu/alicebot.env.example ~/.config/alicebot/.env
less ~/.config/alicebot/.env
ln -sfn ~/.config/alicebot/.env .env
scripts/validate_env.sh ~/.config/alicebot/.env .env.lite apps/web/.env.local
# Create the alicebot database/roles to match ~/.config/alicebot/.env before this step.
sudo -u postgres psql -d alicebot -c 'CREATE EXTENSION IF NOT EXISTS vector;'
./.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
./.venv/bin/alicebot vnext doctor --fix-safe --ci
./.venv/bin/alicebot vnext alpha check --headless --skip-smokes
```

If you use existing Postgres, set `DATABASE_URL` and `DATABASE_ADMIN_URL` before migrations and confirm the database has `CREATE EXTENSION IF NOT EXISTS vector;` installed by a superuser. On Ubuntu 22.04, replace `postgresql-16-pgvector` with the package matching the installed server major version.

## Systemd Services

Templates live under [packaging/systemd](../../packaging/systemd):

- `alice-api.service`
- `alice-web.service`
- `alice-scheduler.service`

Install them through:

```bash
bash install-alice.sh --branch main --install-systemd
```

Then start:

```bash
sudo systemctl enable --now alice-api
sudo systemctl enable --now alice-web
sudo systemctl enable --now alice-scheduler
systemctl status alice-api
systemctl status alice-web
systemctl status alice-scheduler
journalctl -u alice-api -f
journalctl -u alice-web -f
journalctl -u alice-scheduler -f
```

Service behavior:

- runs as the installing non-root user
- loads `~/.config/alicebot/.env`
- restarts on failure
- API binds to `127.0.0.1:8000`
- web binds to `127.0.0.1:3000`
- scheduler uses the governed `alicebot vnext scheduler daemon start --foreground` path
- scheduler pid/status files live under the explicit installing-user path `~/.alicebot`, not systemd `%h`
- logs are visible through `journalctl`

## Headless Alpha Check

Before services:

```bash
~/alicebot/.venv/bin/alicebot vnext alpha check --headless --skip-smokes
~/alicebot/.venv/bin/alicebot vnext smoke headless-ubuntu
```

After services:

```bash
~/alicebot/.venv/bin/alicebot vnext alpha check --headless \
  --api-url http://127.0.0.1:8000/healthz \
  --web-url http://127.0.0.1:3000/vnext
```

Optional demo cycle:

```bash
~/alicebot/.venv/bin/alicebot vnext alpha check --headless --demo-cycle
```

No check requires a local browser on the Ubuntu host.

## Verify Runtime Posture

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -I http://127.0.0.1:3000/vnext
~/alicebot/.venv/bin/alicebot vnext doctor --fix-safe --ci
~/alicebot/.venv/bin/alicebot vnext smoke agent-integration-pack
~/alicebot/.venv/bin/alicebot vnext scheduler daemon status
~/alicebot/.venv/bin/alicebot vnext scheduler runs
```

CLI-only fallback if you cannot open `/vnext`:

```bash
~/alicebot/.venv/bin/alicebot vnext demo load --reset
~/alicebot/.venv/bin/alicebot context-pack --query "public preview launch checklist" --domain project --sensitivity-allowed private
~/alicebot/.venv/bin/alicebot daily-brief --domain project --sensitivity-allowed private
~/alicebot/.venv/bin/alicebot vnext artifacts list
~/alicebot/.venv/bin/alicebot vnext demo reset
```

## Connect Hermes

Use [hermes-dogfood-ubuntu.md](hermes-dogfood-ubuntu.md) for same-host Hermes setup. The short shape is:

- API URL: `http://127.0.0.1:8000`
- MCP command: `~/alicebot/.venv/bin/python -m alicebot_api.mcp_server`
- agent id: `hermes`
- agent type: `personal_assistant`
- permission profile: `trusted_local_agent`

## Firewall Note

Do not open ports `3000` or `8000` to the public internet. On a VPS, keep the host firewall closed for those ports and access through SSH tunnel first.

## Reset And Uninstall

Safe demo reset:

```bash
~/alicebot/.venv/bin/alicebot vnext demo reset
~/alicebot/.venv/bin/alicebot vnext doctor --fix-safe --ci
```

Stop services:

```bash
sudo systemctl disable --now alice-api alice-web alice-scheduler
```

Inspect the uninstall script before destructive cleanup:

```bash
less ~/alicebot/scripts/uninstall-ubuntu.sh
bash ~/alicebot/scripts/uninstall-ubuntu.sh
```

By default, uninstall only stops/removes services and preserves repo, config, secrets, local data, and database. Destructive cleanup requires explicit flags such as `--remove-repo`, `--remove-config`, `--remove-data`, or `--drop-database` and confirmation.

## Troubleshooting

Postgres unreachable:

```bash
systemctl status postgresql
sudo -u postgres psql -c 'SELECT 1'
```

Migration fails with `extension "vector" is not available`:

```bash
sudo apt-get update
sudo apt-get install -y postgresql-16-pgvector
sudo -u postgres psql -d alicebot -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

Use the pgvector package that matches your Postgres server major version.

Environment file rejected before startup:

```bash
~/alicebot/scripts/validate_env.sh ~/.config/alicebot/.env ~/alicebot/.env.lite
```

If a value contains spaces, quote it. For example:

```dotenv
ALICE_MCP_COMMAND="~/alicebot/.venv/bin/python -m alicebot_api.mcp_server"
```

Local compose password mismatch after changing `DATABASE_URL`:

```bash
docker compose down -v
make migrate
```

Only remove the compose volume if you are intentionally discarding the local dev database.

API not reachable:

```bash
journalctl -u alice-api -n 100 --no-pager
~/alicebot/.venv/bin/alicebot vnext doctor --fix-safe --ci
```

Web not reachable:

```bash
journalctl -u alice-web -n 100 --no-pager
pnpm --dir ~/alicebot/apps/web build
```

Scheduler not running:

```bash
journalctl -u alice-scheduler -n 100 --no-pager
~/alicebot/.venv/bin/alicebot vnext scheduler daemon status
~/alicebot/.venv/bin/alicebot vnext scheduler failures
```
