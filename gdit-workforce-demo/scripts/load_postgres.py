#!/usr/bin/env python3
"""Load generated GDIT demo data into Supabase Postgres."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "out"
SECRET_DIR = Path.home() / "gdit" / ".secrets"
ROLES_FILE = SECRET_DIR / "supabase_roles.json"
SIGNING_KEY_FILE = SECRET_DIR / "app_signing_key"
PROJECT_REF = "hrirootesazdmuqwryzs"
DIRECT_HOST = f"db.{PROJECT_REF}.supabase.co"
DEFAULT_POOLER_HOST = "aws-0-us-east-1.pooler.supabase.com"
DB_NAME = "postgres"
SCHEMAS = ("workday", "salesforce", "oracle_lms", "security")


TABLES: dict[str, tuple[list[tuple[str, str]], list[str]]] = {
    "workday.workers": (
        [
            ("worker_id", "text PRIMARY KEY"),
            ("first_name", "text NOT NULL"),
            ("last_name", "text NOT NULL"),
            ("gender", "text NOT NULL"),
            ("birthdate", "date NOT NULL"),
            ("education_level", "text NOT NULL"),
            ("hire_date", "date NOT NULL"),
            ("term_date", "date"),
            ("term_type", "text"),
            ("division", "text NOT NULL"),
            ("business_unit", "text NOT NULL"),
            ("cost_center", "text NOT NULL"),
            ("location_state", "text NOT NULL"),
            ("location_city", "text NOT NULL"),
            ("remote_flag", "boolean NOT NULL"),
            ("job_family", "text NOT NULL"),
            ("job_title", "text NOT NULL"),
            ("job_level", "integer NOT NULL"),
            ("manager_id", "text REFERENCES workday.workers(worker_id) DEFERRABLE INITIALLY DEFERRED"),
            ("clearance_level", "text NOT NULL"),
            ("base_salary", "numeric(12,2) NOT NULL"),
            ("performance_rating", "integer NOT NULL"),
            ("last_updated", "timestamptz NOT NULL"),
        ],
        ["division", "hire_date", "term_date", "worker_id"],
    ),
    "workday.worker_events": (
        [
            ("event_id", "text PRIMARY KEY"),
            ("worker_id", "text NOT NULL REFERENCES workday.workers(worker_id)"),
            ("event_date", "date NOT NULL"),
            ("event_type", "text NOT NULL"),
            ("from_value", "text"),
            ("to_value", "text"),
        ],
        ["worker_id", "event_date"],
    ),
    "salesforce.opportunities": (
        [
            ("opp_id", "text PRIMARY KEY"),
            ("account_name", "text NOT NULL"),
            ("division", "text NOT NULL"),
            ("business_unit", "text NOT NULL"),
            ("stage", "text NOT NULL"),
            ("amount", "numeric(14,2) NOT NULL"),
            ("probability", "integer NOT NULL"),
            ("created_date", "date NOT NULL"),
            ("close_date", "date NOT NULL"),
            ("contract_vehicle", "text NOT NULL"),
            ("required_clearance", "text NOT NULL"),
        ],
        ["division", "created_date", "close_date"],
    ),
    "salesforce.staffing_requests": (
        [
            ("req_id", "text PRIMARY KEY"),
            ("opp_id", "text NOT NULL REFERENCES salesforce.opportunities(opp_id)"),
            ("division", "text NOT NULL"),
            ("job_family", "text NOT NULL"),
            ("clearance_required", "text NOT NULL"),
            ("headcount", "integer NOT NULL"),
            ("opened_date", "date NOT NULL"),
            ("needed_by", "date NOT NULL"),
            ("status", "text NOT NULL"),
            ("filled_date", "date"),
            ("filled_worker_id", "text REFERENCES workday.workers(worker_id)"),
        ],
        ["division", "needed_by", "opened_date"],
    ),
    "oracle_lms.courses": (
        [
            ("course_code", "text PRIMARY KEY"),
            ("course_name", "text NOT NULL"),
            ("category", "text NOT NULL"),
            ("required", "boolean NOT NULL"),
            ("recurrence_months", "integer"),
        ],
        ["category"],
    ),
    "oracle_lms.training_completions": (
        [
            ("completion_id", "text PRIMARY KEY"),
            ("worker_id", "text NOT NULL REFERENCES workday.workers(worker_id)"),
            ("course_code", "text NOT NULL REFERENCES oracle_lms.courses(course_code)"),
            ("assigned_date", "date NOT NULL"),
            ("due_date", "date NOT NULL"),
            ("completed_date", "date"),
            ("status", "text NOT NULL"),
            ("score", "integer"),
        ],
        ["worker_id", "assigned_date", "due_date"],
    ),
    "security.entitlements": (
        [
            ("user_email", "text NOT NULL"),
            ("division", "text NOT NULL"),
            ("PRIMARY KEY", "PRIMARY KEY (user_email, division)"),
        ],
        ["division"],
    ),
}


def read_secret(env_name: str, filename: str) -> str:
    value = os.environ.get(env_name)
    if value:
        return value.strip()
    path = SECRET_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing credential file: {path}")
    return path.read_text(encoding="utf-8").strip()


def read_role_passwords() -> dict[str, str]:
    if not ROLES_FILE.is_file():
        raise FileNotFoundError(
            f"{ROLES_FILE} is missing; run load_postgres.py --target supabase first"
        )
    payload = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
    return payload["passwords"]


def read_signing_key(connection: psycopg.Connection, rotate: bool) -> bytes:
    if rotate:
        return secrets.token_bytes(32)
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('security.app_signing_key')")
        table_exists = cursor.fetchone()[0] is not None
        if table_exists:
            cursor.execute(
                "SELECT secret_key FROM security.app_signing_key WHERE singleton"
            )
            row = cursor.fetchone()
            if row is not None:
                key = bytes(row[0])
                if len(key) != 32:
                    raise RuntimeError("Supabase signing key must be exactly 32 bytes")
                return key
    try:
        key = bytes.fromhex(SIGNING_KEY_FILE.read_text(encoding="ascii").strip())
    except FileNotFoundError:
        return secrets.token_bytes(32)
    except ValueError as exc:
        raise RuntimeError(f"Invalid cached signing key: {SIGNING_KEY_FILE}") from exc
    if len(key) != 32:
        raise RuntimeError("Cached signing key must be exactly 32 bytes")
    return key


def write_secret_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
        path.chmod(0o600)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def pooler_host_from_api() -> str | None:
    token_path = SECRET_DIR / "supabase_access_token"
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token and token_path.is_file():
        token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        return None
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/database/pooler",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    candidates: list[str] = []

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key).lower())
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and ("host" in key or key in {"address", "hostname"}):
            if value and "." in value:
                candidates.append(value)

    visit(payload)
    for candidate in candidates:
        if "pooler" in candidate or "pool" in candidate:
            return candidate
    return candidates[0] if candidates else None


def _connection_candidates(role: str) -> list[dict[str, Any]]:
    password = (
        read_secret("SUPABASE_DB_PASSWORD", "supabase_db_password")
        if role == "postgres"
        else read_role_passwords()[role]
    )
    direct_host = os.environ.get("SUPABASE_DB_HOST", DIRECT_HOST)
    database = os.environ.get("SUPABASE_DB_NAME", DB_NAME)
    port = int(os.environ.get("SUPABASE_DB_PORT", "5432"))
    candidates = [
        {
            "host": direct_host,
            "port": port,
            "user": role,
            "password": password,
            "dbname": database,
            "sslmode": "require",
            "connect_timeout": 10,
        }
    ]
    pooler_hosts = [os.environ.get("SUPABASE_POOLER_HOST", DEFAULT_POOLER_HOST)]
    for host in pooler_hosts:
        if host:
            candidates.append(
                {
                    "host": host,
                    "port": 5432,
                    "user": f"{role}.{PROJECT_REF}",
                    "password": password,
                    "dbname": database,
                    "sslmode": "require",
                    "connect_timeout": 10,
                }
            )
    return candidates


def connect_supabase(role: str = "postgres") -> psycopg.Connection:
    candidates = _connection_candidates(role)
    failures: list[str] = []
    for candidate in candidates:
        try:
            return psycopg.connect(**candidate)
        except psycopg.OperationalError as error:
            failures.append(f"{candidate['host']}: {error}")
    api_host = pooler_host_from_api()
    if api_host and all(candidate["host"] != api_host for candidate in candidates):
        try:
            return psycopg.connect(
                host=api_host,
                port=5432,
                user=f"{role}.{PROJECT_REF}",
                password=(
                    read_secret("SUPABASE_DB_PASSWORD", "supabase_db_password")
                    if role == "postgres"
                    else read_role_passwords()[role]
                ),
                dbname=os.environ.get("SUPABASE_DB_NAME", DB_NAME),
                sslmode="require",
                connect_timeout=10,
            )
        except psycopg.OperationalError as error:
            failures.append(f"{api_host}: {error}")
    raise psycopg.OperationalError(
        f"Could not connect to Supabase as {role}: " + " | ".join(failures)
    )


def create_roles(
    connection: psycopg.Connection, rotate_passwords: bool = False
) -> dict[str, str]:
    roles = ("tableau_reader", "app_reader", "feed_writer")
    if ROLES_FILE.is_file() and not rotate_passwords:
        saved_passwords = read_role_passwords()
        missing_roles = set(roles) - saved_passwords.keys()
        if missing_roles:
            raise ValueError(f"Saved role-password file is missing roles: {sorted(missing_roles)}")
        passwords = {role: saved_passwords[role] for role in roles}
    else:
        passwords = {role: secrets.token_urlsafe(36) for role in roles}
    with connection.cursor() as cursor:
        for role, password in passwords.items():
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE ROLE {}").format(sql.Identifier(role)))
            role_options = "LOGIN BYPASSRLS" if role == "tableau_reader" else "LOGIN NOBYPASSRLS"
            cursor.execute(
                sql.SQL("ALTER ROLE {} WITH " + role_options + " PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )

        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("app_data_view_owner",))
        if cursor.fetchone() is None:
            cursor.execute("CREATE ROLE app_data_view_owner NOLOGIN NOBYPASSRLS")
        cursor.execute(
            "ALTER ROLE app_data_view_owner WITH NOLOGIN NOBYPASSRLS"
        )
        cursor.execute(
            """
            SELECT granted_role.rolname
            FROM pg_auth_members AS membership
            JOIN pg_roles AS granted_role ON granted_role.oid = membership.roleid
            WHERE membership.member = (
                SELECT oid FROM pg_roles WHERE rolname = 'app_data_view_owner'
            )
            """
        )
        for (granted_role,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("REVOKE {} FROM app_data_view_owner").format(
                    sql.Identifier(granted_role)
                )
            )
        cursor.execute(
            """
            SELECT member_role.rolname
            FROM pg_auth_members AS membership
            JOIN pg_roles AS member_role ON member_role.oid = membership.member
            WHERE membership.roleid = (
                SELECT oid FROM pg_roles WHERE rolname = 'app_data_view_owner'
            )
            """
        )
        for (member_role,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("REVOKE app_data_view_owner FROM {}").format(
                    sql.Identifier(member_role)
                )
            )
    return passwords


def drop_and_create_schemas(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        for schema in SCHEMAS:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
            )
        for schema in SCHEMAS:
            cursor.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )


def create_tables(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        for qualified_name, (columns, indexes) in TABLES.items():
            schema, table = qualified_name.split(".", 1)
            ordinary_columns = [(name, definition) for name, definition in columns if name != "PRIMARY KEY"]
            declarations = [
                sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(definition))
                for name, definition in ordinary_columns
            ]
            if qualified_name == "security.entitlements":
                declarations.append(sql.SQL("PRIMARY KEY (user_email, division)"))
            cursor.execute(
                sql.SQL("CREATE TABLE {}.{} ({})").format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                    sql.SQL(", ").join(declarations),
                )
            )
            for column in indexes:
                cursor.execute(
                    sql.SQL("CREATE INDEX {} ON {}.{} ({})").format(
                        sql.Identifier(f"{table}_{column}_idx"),
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(column),
                    )
                )


def copy_table(connection: psycopg.Connection, qualified_name: str) -> None:
    path = DATA_DIR / f"{qualified_name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Generated data missing: {path}; run data/generate.py first")
    schema, table = qualified_name.split(".", 1)
    columns = [name for name, _definition in TABLES[qualified_name][0] if name != "PRIMARY KEY"]
    copy_query = sql.SQL("COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
    )
    with connection.cursor() as cursor, path.open("rb") as source:
        with cursor.copy(copy_query) as copy:
            while chunk := source.read(1024 * 1024):
                copy.write(chunk)


def configure_security(
    connection: psycopg.Connection, passwords: dict[str, str], signing_key: bytes
) -> None:
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions")
        cursor.execute(
            "CREATE TABLE security.app_signing_key "
            "(singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton), secret_key bytea NOT NULL)"
        )
        cursor.execute(
            "INSERT INTO security.app_signing_key (singleton, secret_key) VALUES (true, %s)",
            (psycopg.Binary(signing_key),),
        )
        cursor.execute(
            "REVOKE ALL ON security.app_signing_key FROM PUBLIC, tableau_reader, app_reader, feed_writer, app_data_view_owner"
        )
        cursor.execute(
            "CREATE TABLE security.app_audit ("
            "ts timestamptz NOT NULL DEFAULT statement_timestamp(), "
            "user_email text NOT NULL, route text NOT NULL, "
            "params jsonb NOT NULL DEFAULT '{}'::jsonb, row_count integer NOT NULL)"
        )
        cursor.execute("ALTER TABLE security.app_audit ENABLE ROW LEVEL SECURITY")
    statements = [
        "CREATE OR REPLACE FUNCTION security.current_user_email() "
        "RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, security, extensions AS $$ "
        "DECLARE token text := current_setting('app.user_token', true); "
        "parts text[]; email text; signing_key bytea; expected text; "
        "BEGIN "
        "IF token IS NULL THEN RETURN NULL; END IF; "
        "parts := string_to_array(token, '|'); "
        "IF parts IS NULL OR array_length(parts, 1) <> 3 OR parts[1] IS NULL OR parts[2] IS NULL OR parts[3] IS NULL "
        "OR parts[2] !~ '^[0-9]{1,12}$' THEN RETURN NULL; END IF; "
        "IF parts[2]::bigint <= extract(epoch FROM statement_timestamp())::bigint THEN RETURN NULL; END IF; "
        "email := parts[1]; "
        "SELECT secret_key INTO signing_key FROM security.app_signing_key WHERE singleton; "
        "IF signing_key IS NULL THEN RETURN NULL; END IF; "
        "expected := encode(extensions.hmac(convert_to(email || '|' || parts[2], 'UTF8'), signing_key, 'sha256'), 'hex'); "
        "IF lower(parts[3]) <> expected THEN RETURN NULL; END IF; "
        "IF NOT EXISTS (SELECT 1 FROM security.entitlements WHERE user_email = email) THEN RETURN NULL; END IF; "
        "RETURN email; END $$",
        "REVOKE ALL ON FUNCTION security.current_user_email() FROM PUBLIC",
        "GRANT EXECUTE ON FUNCTION security.current_user_email() TO app_reader",
        "CREATE OR REPLACE FUNCTION security.log_query(question_template text, params jsonb, row_count int) "
        "RETURNS void LANGUAGE plpgsql SECURITY DEFINER "
        "SET search_path = pg_catalog, security AS $$ "
        "DECLARE verified_email text := security.current_user_email(); "
        "BEGIN IF verified_email IS NULL THEN "
        "RAISE EXCEPTION USING ERRCODE = '28000', MESSAGE = 'verified identity required'; END IF; "
        "INSERT INTO security.app_audit(user_email, route, params, row_count) "
        "VALUES (verified_email, question_template, coalesce(params, '{}'::jsonb), row_count); "
        "END $$",
        "REVOKE ALL ON FUNCTION security.log_query(text, jsonb, integer) FROM PUBLIC",
        "GRANT EXECUTE ON FUNCTION security.log_query(text, jsonb, integer) TO app_reader",
        "GRANT SELECT ON security.app_audit TO app_reader",
        "CREATE POLICY app_audit_owner_read ON security.app_audit "
        "FOR SELECT TO app_reader USING (user_email = security.current_user_email())",
        "CREATE OR REPLACE FUNCTION security.allowed_divisions() "
        "RETURNS text[] LANGUAGE plpgsql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, security, extensions AS $$ "
        "DECLARE token text := current_setting('app.user_token', true); "
        "parts text[]; email text; signing_key bytea; expected text; "
        "BEGIN "
        "IF token IS NULL THEN RETURN ARRAY[]::text[]; END IF; "
        "parts := string_to_array(token, '|'); "
        "IF parts IS NULL OR array_length(parts, 1) <> 3 OR parts[1] IS NULL OR parts[2] IS NULL OR parts[3] IS NULL "
        "OR parts[2] !~ '^[0-9]{1,12}$' THEN RETURN ARRAY[]::text[]; END IF; "
        "IF parts[2]::bigint <= extract(epoch FROM statement_timestamp())::bigint THEN RETURN ARRAY[]::text[]; END IF; "
        "email := parts[1]; "
        "SELECT secret_key INTO signing_key FROM security.app_signing_key WHERE singleton; "
        "IF signing_key IS NULL THEN RETURN ARRAY[]::text[]; END IF; "
        "expected := encode(extensions.hmac(convert_to(email || '|' || parts[2], 'UTF8'), signing_key, 'sha256'), 'hex'); "
        "IF lower(parts[3]) <> expected THEN RETURN ARRAY[]::text[]; END IF; "
        "RETURN (SELECT CASE WHEN bool_or(division = '*') "
        "THEN ARRAY['Defense','Intelligence','Civilian','Health']::text[] "
        "ELSE coalesce(array_agg(division), ARRAY[]::text[]) END "
        "FROM security.entitlements WHERE security.entitlements.user_email = email); "
        "END $$",
        "REVOKE ALL ON FUNCTION security.allowed_divisions() FROM PUBLIC",
        "GRANT EXECUTE ON FUNCTION security.allowed_divisions() TO app_reader, app_data_view_owner",
        "GRANT USAGE ON SCHEMA workday, salesforce, oracle_lms, security "
        "TO tableau_reader, app_reader, feed_writer, app_data_view_owner",
        "GRANT SELECT ON ALL TABLES IN SCHEMA workday, salesforce, oracle_lms, security TO tableau_reader",
        "GRANT SELECT ON ALL TABLES IN SCHEMA workday, salesforce, oracle_lms TO app_data_view_owner",
        "GRANT SELECT, INSERT, UPDATE ON workday.workers, workday.worker_events, "
        "salesforce.staffing_requests TO feed_writer",
        "GRANT CREATE ON SCHEMA workday, salesforce, oracle_lms TO app_data_view_owner",
    ]
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
        cursor.execute(
            "REVOKE ALL ON security.app_signing_key FROM PUBLIC, tableau_reader, app_reader, feed_writer, app_data_view_owner"
        )
        for qualified_name in TABLES:
            schema, table = qualified_name.split(".", 1)
            cursor.execute(
                sql.SQL("ALTER TABLE {}.{} ENABLE ROW LEVEL SECURITY").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
            cursor.execute(
                sql.SQL("ALTER TABLE {}.{} FORCE ROW LEVEL SECURITY").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
        policies = {
            "workday.workers": (
                "division = ANY(security.allowed_divisions())",
                "division = ANY(security.allowed_divisions())",
            ),
            "workday.worker_events": (
                "EXISTS (SELECT 1 FROM workday.workers w WHERE w.worker_id = worker_events.worker_id "
                "AND w.division = ANY(security.allowed_divisions()))",
                "EXISTS (SELECT 1 FROM workday.workers w WHERE w.worker_id = worker_events.worker_id "
                "AND w.division = ANY(security.allowed_divisions()))",
            ),
            "salesforce.opportunities": (
                "division = ANY(security.allowed_divisions())",
                "division = ANY(security.allowed_divisions())",
            ),
            "salesforce.staffing_requests": (
                "division = ANY(security.allowed_divisions())",
                "division = ANY(security.allowed_divisions())",
            ),
            "oracle_lms.courses": ("true", "true"),
            "oracle_lms.training_completions": (
                "EXISTS (SELECT 1 FROM workday.workers w WHERE w.worker_id = training_completions.worker_id "
                "AND w.division = ANY(security.allowed_divisions()))",
                "EXISTS (SELECT 1 FROM workday.workers w WHERE w.worker_id = training_completions.worker_id "
                "AND w.division = ANY(security.allowed_divisions()))",
            ),
        }
        for qualified_name, (using, check) in policies.items():
            schema, table = qualified_name.split(".", 1)
            policy_name = f"{table}_division_policy"
            cursor.execute(
                sql.SQL("DROP POLICY IF EXISTS {} ON {}.{}").format(
                    sql.Identifier(policy_name), sql.Identifier(schema), sql.Identifier(table)
                )
            )
            cursor.execute(
                sql.SQL("CREATE POLICY {} ON {}.{} FOR ALL TO PUBLIC USING ({}) WITH CHECK ({})").format(
                    sql.Identifier(policy_name),
                    sql.Identifier(schema),
                    sql.Identifier(table),
                    sql.SQL(using),
                    sql.SQL(check),
                )
            )
        for qualified_name in (
            "workday.workers",
            "workday.worker_events",
            "salesforce.staffing_requests",
        ):
            schema, table = qualified_name.split(".", 1)
            policy_name = f"{table}_feed_writer_policy"
            cursor.execute(
                sql.SQL("CREATE POLICY {} ON {}.{} FOR ALL TO feed_writer USING (true) WITH CHECK (true)").format(
                    sql.Identifier(policy_name), sql.Identifier(schema), sql.Identifier(table)
                )
            )

        views = {
            "workday.workers_v": "SELECT * FROM workday.workers",
            "workday.worker_events_v": "SELECT * FROM workday.worker_events",
            "salesforce.opportunities_v": "SELECT * FROM salesforce.opportunities",
            "salesforce.staffing_requests_v": "SELECT * FROM salesforce.staffing_requests",
            "oracle_lms.courses_v": "SELECT * FROM oracle_lms.courses",
            "oracle_lms.training_completions_v": "SELECT * FROM oracle_lms.training_completions",
        }
        cursor.execute("GRANT app_data_view_owner TO postgres")
        cursor.execute("SET ROLE app_data_view_owner")
        for qualified_view, select_query in views.items():
            schema, view = qualified_view.split(".", 1)
            cursor.execute(
                sql.SQL("CREATE VIEW {}.{} AS " + select_query).format(
                    sql.Identifier(schema), sql.Identifier(view)
                )
            )
        cursor.execute("RESET ROLE")
        cursor.execute("REVOKE CREATE ON SCHEMA workday, salesforce, oracle_lms FROM app_data_view_owner")
        cursor.execute("REVOKE ALL ON ALL TABLES IN SCHEMA workday, salesforce, oracle_lms FROM app_reader")
        cursor.execute("SET ROLE app_data_view_owner")
        for qualified_view in views:
            schema, view = qualified_view.split(".", 1)
            cursor.execute(
                sql.SQL("GRANT SELECT ON {}.{} TO app_reader").format(
                    sql.Identifier(schema), sql.Identifier(view)
                )
            )
        cursor.execute("RESET ROLE")
        cursor.execute("REVOKE app_data_view_owner FROM postgres")
        cursor.execute("GRANT SELECT ON security.entitlements TO tableau_reader")
        cursor.execute(
            """
            CREATE VIEW security.v_entitlement_expanded AS
            SELECT entitlements.user_email, divisions.division
            FROM security.entitlements AS entitlements
            CROSS JOIN (
                VALUES ('Defense'), ('Intelligence'), ('Civilian'), ('Health')
            ) AS divisions(division)
            WHERE entitlements.division = '*'
            UNION ALL
            SELECT user_email, division
            FROM security.entitlements
            WHERE division <> '*'
            """
        )
        cursor.execute(
            "GRANT SELECT ON security.v_entitlement_expanded TO tableau_reader"
        )


def load_supabase(rotate_passwords: bool = False) -> None:
    connection = connect_supabase("postgres")
    passwords: dict[str, str] = {}
    signing_key: bytes
    try:
        connection.autocommit = False
        signing_key = read_signing_key(connection, rotate=rotate_passwords)
        drop_and_create_schemas(connection)
        create_tables(connection)
        passwords = create_roles(connection, rotate_passwords=rotate_passwords)
        configure_security(connection, passwords, signing_key)
        for qualified_name in TABLES:
            copy_table(connection, qualified_name)
            print(f"Loaded {qualified_name}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    write_secret_file(
        ROLES_FILE,
        json.dumps({"project_ref": PROJECT_REF, "passwords": passwords}, indent=2) + "\n",
    )
    write_secret_file(SIGNING_KEY_FILE, signing_key.hex() + "\n")
    print("Supabase load complete; role passwords and signing-key cache saved with mode 0600.")


def load_databricks() -> None:
    raise NotImplementedError("Databricks loading is intentionally not implemented yet.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("supabase", "databricks"), default="supabase")
    parser.add_argument(
        "--rotate-passwords",
        action="store_true",
        help="rotate role passwords and the app signing key",
    )
    args = parser.parse_args()
    if args.target == "supabase":
        load_supabase(rotate_passwords=args.rotate_passwords)
    else:
        load_databricks()


if __name__ == "__main__":
    main()
