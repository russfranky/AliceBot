#!/usr/bin/env bash
set -euo pipefail

app_user="${ALICEBOT_APP_USER:-alicebot_app}"
app_password="${ALICEBOT_APP_PASSWORD:-alicebot_app}"

sql_escape() {
  printf "%s" "$1" | sed "s/'/''/g"
}

app_user_sql="$(sql_escape "${app_user}")"
app_password_sql="$(sql_escape "${app_password}")"

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<SQL
DO \$\$
DECLARE
  app_user text := '${app_user_sql}';
  app_password text := '${app_password_sql}';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_user) THEN
    EXECUTE format(
      'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
      app_user,
      app_password
    );
  ELSE
    EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', app_user, app_password);
  END IF;

  EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), app_user);
END
\$\$;
SQL
