#!/usr/bin/env python3
"""Check the planted GDIT workforce stories and Postgres access controls."""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import psycopg

from load_postgres import ROOT, connect_supabase
from sign_identity import sign_identity


DEFAULT_OUTPUT = Path.home() / "gdit" / "evidence" / "verify_stories.txt"


def quarter_bounds(today: date) -> tuple[date, str, str]:
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_start_month, 1)
    quarter_end = quarter_start - timedelta(days=1)
    quarter_number = (quarter_end.month - 1) // 3 + 1
    return quarter_end, f"FY{quarter_end.year % 100:02d}", f"Q{quarter_number}"


def query_all(connection: psycopg.Connection, query: str, params: tuple = ()) -> list[tuple]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def story_output() -> str:
    lines = ["GDIT Workforce & Pipeline planted-story verification", f"Run date: {date.today().isoformat()}"]
    connection = connect_supabase("postgres")
    try:
        owner_capabilities = query_all(
            connection,
            "SELECT rolcanlogin, rolsuper, rolbypassrls FROM pg_roles "
            "WHERE rolname = 'app_data_view_owner'",
        )
        if owner_capabilities != [(False, False, False)]:
            raise AssertionError(
                f"app_data_view_owner capabilities are unsafe: {owner_capabilities}"
            )
        owner_memberships = query_all(
            connection,
            """
            WITH RECURSIVE role_closure(oid) AS (
              SELECT oid FROM pg_roles WHERE rolname = 'app_data_view_owner'
              UNION
              SELECT membership.roleid
              FROM pg_auth_members AS membership
              JOIN role_closure AS parent_role
                ON membership.member = parent_role.oid
            )
            SELECT role_info.rolname, role_info.rolsuper, role_info.rolbypassrls,
                   EXISTS (
                     SELECT 1
                     FROM pg_class AS base_relation
                     JOIN pg_namespace AS base_schema
                       ON base_schema.oid = base_relation.relnamespace
                     WHERE base_relation.relowner = role_info.oid
                       AND base_relation.relkind IN ('r', 'p')
                       AND base_schema.nspname IN
                           ('workday', 'salesforce', 'oracle_lms', 'security')
                   ) AS owns_base_table
            FROM role_closure
            JOIN pg_roles AS role_info ON role_info.oid = role_closure.oid
            ORDER BY role_info.rolname
            """,
        )
        if not owner_memberships or any(
            superuser or bypass_rls or owns_base_table
            for _, superuser, bypass_rls, owns_base_table in owner_memberships
        ):
            raise AssertionError(
                f"app_data_view_owner has unsafe recursive memberships: {owner_memberships}"
            )
        lines.append(
            "0) app_data_view_owner is NOLOGIN NOSUPERUSER NOBYPASSRLS; "
            f"recursive roles checked={len(owner_memberships)}"
        )

        force_rls_tables = [
            "workday.workers",
            "workday.worker_events",
            "salesforce.opportunities",
            "salesforce.staffing_requests",
            "oracle_lms.courses",
            "oracle_lms.training_completions",
        ]
        forced_rows = query_all(
            connection,
            """
            SELECT base_schema.nspname || '.' || base_relation.relname,
                   base_relation.relrowsecurity, base_relation.relforcerowsecurity
            FROM pg_class AS base_relation
            JOIN pg_namespace AS base_schema
              ON base_schema.oid = base_relation.relnamespace
            WHERE base_schema.nspname || '.' || base_relation.relname = ANY(%s)
            """,
            (force_rls_tables,),
        )
        forced_states = {
            table_name: (row_security, force_row_security)
            for table_name, row_security, force_row_security in forced_rows
        }
        if forced_states != {table: (True, True) for table in force_rls_tables}:
            raise AssertionError(f"RLS tables are not forced: {forced_states}")
        tableau_bypass = query_all(
            connection,
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'tableau_reader'",
        )
        if tableau_bypass != [(True,)]:
            raise AssertionError("tableau_reader must retain BYPASSRLS")
        lines.append(
            f"FORCE RLS enabled on {len(forced_states)} base tables; "
            "tableau_reader retains BYPASSRLS"
        )

        attrition = query_all(
            connection,
            """
            WITH bounds AS (
              SELECT date_trunc('month', current_date)::date AS month_start,
                     (date_trunc('month', current_date) - interval '3 months')::date AS latest_start,
                     (date_trunc('month', current_date) - interval '6 months')::date AS prior_start
            )
            SELECT CASE WHEN w.term_date >= b.latest_start THEN 'latest 3 full months'
                        ELSE 'prior 3 full months' END AS period,
                   count(*) AS voluntary_terms,
                   count(*) FILTER (WHERE w.job_family IN ('Software Engineering', 'Cyber')) AS target_families,
                   count(*) FILTER (
                     WHERE w.job_family IN ('Software Engineering', 'Cyber')
                       AND w.job_level IN (2, 3) AND w.clearance_level = 'TS/SCI'
                       AND w.location_state IN ('VA', 'MD')
                   ) AS target_profile
            FROM workday.workers w CROSS JOIN bounds b
            WHERE w.division = 'Defense' AND w.term_type = 'Voluntary'
              AND ((w.term_date >= b.latest_start AND w.term_date < b.month_start)
                OR (w.term_date >= b.prior_start AND w.term_date < b.latest_start))
            GROUP BY period ORDER BY min(w.term_date)
            """,
        )
        counts = {row[0]: row[1:] for row in attrition}
        latest = counts.get("latest 3 full months", (0, 0, 0))
        prior = counts.get("prior 3 full months", (0, 0, 0))
        ratio = latest[0] / prior[0] if prior[0] else float("inf")
        lines.extend(
            [
                "",
                "1) Defense voluntary attrition, last 3 full months vs prior 3",
                f"   latest={latest[0]} prior={prior[0]} ratio={ratio:.2f}x",
                f"   target-family exits (latest/prior)={latest[1]}/{prior[1]}",
                f"   TS/SCI Software/Cyber level 2-3 in VA/MD (latest/prior)={latest[2]}/{prior[2]}",
            ]
        )

        request_rows = query_all(
            connection,
            """
            WITH eligible AS (
              SELECT o.opp_id, o.amount, r.req_id, r.job_family, r.clearance_required,
                     r.headcount, r.status, r.needed_by
              FROM salesforce.opportunities o
              JOIN salesforce.staffing_requests r USING (opp_id)
              WHERE o.stage = 'Won' AND o.account_name IN ('Army', 'Navy')
            )
            SELECT job_family, clearance_required, count(*),
                   sum(headcount) FILTER (WHERE status = 'Open' AND needed_by < current_date)
            FROM eligible
            GROUP BY job_family, clearance_required
            ORDER BY sum(headcount) FILTER (WHERE status = 'Open' AND needed_by < current_date) DESC NULLS LAST,
                     count(*) DESC
            LIMIT 8
            """,
        )
        risk = query_all(
            connection,
            """
            WITH per_opp AS (
              SELECT o.opp_id, o.amount,
                     sum(r.headcount) AS requested_headcount,
                     sum(r.headcount) FILTER (
                       WHERE r.status = 'Open' AND r.needed_by < current_date
                     ) AS past_due_open_headcount
              FROM salesforce.opportunities o
              JOIN salesforce.staffing_requests r USING (opp_id)
              WHERE o.stage = 'Won' AND o.account_name IN ('Army', 'Navy')
              GROUP BY o.opp_id, o.amount
            )
            SELECT count(*) FILTER (WHERE past_due_open_headcount > 0),
                   coalesce(sum(amount * past_due_open_headcount / nullif(requested_headcount, 0)), 0),
                   coalesce(sum(past_due_open_headcount), 0)
            FROM per_opp
            """,
        )[0]
        lines.extend(
            [
                "",
                "2) Open past-due staffing requests on Won Army/Navy opportunities",
                f"   affected opportunities={risk[0]} unfilled headcount={risk[2]} revenue at risk=${risk[1]:,.2f}",
                "   top job families / clearance:",
            ]
        )
        for family, clearance, request_count, overdue_headcount in request_rows:
            lines.append(
                f"     {family} / {clearance}: requests={request_count}, past-due open headcount={overdue_headcount or 0}"
            )

        training = query_all(
            connection,
            """
            SELECT w.business_unit,
                   count(*) FILTER (WHERE t.status = 'Overdue') AS overdue,
                   count(*) FILTER (WHERE t.status IN ('Completed', 'Overdue')) AS due,
                   round(
                     count(*) FILTER (WHERE t.status = 'Overdue')::numeric
                     / nullif(count(*) FILTER (WHERE t.status IN ('Completed', 'Overdue')), 0), 4
                   ) AS overdue_rate
            FROM oracle_lms.training_completions t
            JOIN workday.workers w USING (worker_id)
            JOIN oracle_lms.courses c USING (course_code)
            WHERE w.division = 'Intelligence' AND c.category = 'Security'
            GROUP BY w.business_unit ORDER BY overdue_rate DESC
            """,
        )
        target_rate = next((row[3] for row in training if row[0] == "Intelligence Programs"), 0)
        baseline_values = [float(row[3]) for row in training if row[0] != "Intelligence Programs" and row[3] is not None]
        baseline = sum(baseline_values) / len(baseline_values) if baseline_values else 0
        lines.extend(
            [
                "",
                "3) Intelligence Security training overdue rate by business unit",
                f"   Intelligence Programs={float(target_rate or 0):.1%} baseline(other Intelligence BUs)={baseline:.1%} ratio={float(target_rate or 0) / baseline if baseline else 0:.2f}x",
            ]
        )
        for business_unit, overdue, due, rate in training:
            lines.append(
                f"     {business_unit}: overdue={overdue}/{due}, rate={float(rate or 0):.1%}"
            )

        quarter_end, fiscal_year, fiscal_quarter = quarter_bounds(date.today())
        actual_rows = query_all(
            connection,
            """
            SELECT division, count(*)
            FROM workday.workers
            WHERE hire_date <= %s AND (term_date IS NULL OR term_date > %s)
            GROUP BY division ORDER BY division
            """,
            (quarter_end, quarter_end),
        )
        budget_path = ROOT / "data" / "finance" / "fy_headcount_budget.xlsx"
        budget = pd.read_excel(budget_path)
        selected_budget = budget.loc[
            budget["fiscal_year"].eq(fiscal_year)
            & budget["fiscal_quarter"].eq(fiscal_quarter)
        ].groupby("division")["headcount_budget"].sum()
        actual_by_division = dict(actual_rows)
        lines.extend(
            [
                "",
                f"4) Headcount vs budget at latest full quarter ({fiscal_year} {fiscal_quarter}, through {quarter_end})",
            ]
        )
        for division in ["Defense", "Intelligence", "Civilian", "Health"]:
            actual = actual_by_division.get(division, 0)
            planned = float(selected_budget.get(division, 0))
            variance = (actual / planned - 1) if planned else 0
            lines.append(
                f"   {division}: actual={actual:,} budget={planned:,.2f} variance={variance:+.1%}"
            )

        live_rows = query_all(
            connection,
            """
            SELECT e.event_id, e.worker_id, e.event_type, w.division, w.job_family, w.clearance_level
            FROM workday.worker_events e
            JOIN workday.workers w USING (worker_id)
            WHERE left(e.event_id, 5) = 'LIVE-' AND e.event_date = current_date
            ORDER BY e.event_id DESC
            """,
        )
        lines.extend(["", "5) Live feed rows visible to Postgres"])
        lines.append(f"   today's LIVE events={len(live_rows)}")
        for event_id, worker_id, event_type, division, family, clearance in live_rows[:5]:
            lines.append(
                f"   {event_id}: {event_type} {worker_id} ({division}, {clearance} {family})"
            )
    finally:
        connection.close()

    lines.extend(["", "6) RLS and read-only role checks"])
    app_connection = connect_supabase("app_reader")
    try:
        with app_connection.cursor() as cursor:
            division_counts = {}
            for email, expected_divisions in [
                ("defense.lead@gdit-demo.example", {"Defense"}),
                ("intel.lead@gdit-demo.example", {"Intelligence"}),
                ("exec@gdit-demo.example", {"Defense", "Intelligence", "Civilian", "Health"}),
            ]:
                token = sign_identity(email)
                cursor.execute("SELECT set_config('app.user_token', %s, false)", (token,))
                cursor.execute(
                    "SELECT division, count(*) FROM workday.workers_v GROUP BY division ORDER BY division"
                )
                visible = {division: count for division, count in cursor.fetchall()}
                if set(visible) != expected_divisions:
                    raise AssertionError(
                        f"RLS mismatch for {email}: expected {sorted(expected_divisions)}, got {sorted(visible)}"
                    )
                division_counts[email] = visible
                lines.append(
                    f"   app_reader {email}: "
                    + ", ".join(f"{division}={visible[division]:,}" for division in sorted(visible))
                )
            defense_count = division_counts["defense.lead@gdit-demo.example"]["Defense"]
            intel_count = division_counts["intel.lead@gdit-demo.example"]["Intelligence"]
            if defense_count == intel_count:
                raise AssertionError(
                    "Defense and Intelligence view counts unexpectedly match"
                )
            lines.append(
                f"   Defense and Intelligence view counts differ: "
                f"{defense_count:,} vs {intel_count:,}"
            )
            for role in ("app_reader", "tableau_reader", "feed_writer"):
                cursor.execute(
                    "SELECT has_table_privilege(%s, 'security.app_signing_key', 'SELECT')",
                    (role,),
                )
                if cursor.fetchone()[0]:
                    raise AssertionError(f"{role} unexpectedly has signing-key SELECT privilege")
            lines.append("   login roles cannot SELECT security.app_signing_key")
            view_privileges = {
                "workday.workers_v": "workday.workers",
                "workday.worker_events_v": "workday.worker_events",
                "salesforce.opportunities_v": "salesforce.opportunities",
                "salesforce.staffing_requests_v": "salesforce.staffing_requests",
                "oracle_lms.courses_v": "oracle_lms.courses",
                "oracle_lms.training_completions_v": "oracle_lms.training_completions",
            }
            for view, base_table in view_privileges.items():
                cursor.execute(
                    "SELECT has_table_privilege('app_reader', %s, 'SELECT'), "
                    "has_table_privilege('app_reader', %s, 'SELECT')",
                    (view, base_table),
                )
                view_select, base_select = cursor.fetchone()
                if not view_select or base_select:
                    raise AssertionError(
                        f"app_reader privilege mismatch for {view}: "
                        f"view SELECT={view_select}, base SELECT={base_select}"
                    )
                lines.append(f"   app_reader SELECT {view}; base-table SELECT denied")
            defense_token = sign_identity("defense.lead@gdit-demo.example")
            forged_token = defense_token[:-1] + (
                "0" if defense_token[-1] != "0" else "1"
            )
            cursor.execute("SELECT set_config('app.user_token', %s, false)", (forged_token,))
            cursor.execute("SELECT count(*) FROM workday.workers_v")
            if cursor.fetchone()[0] != 0:
                raise AssertionError("Forged identity token unexpectedly returned rows")
            lines.append("   forged app.user_token: 0 rows")

            expired_token = sign_identity("defense.lead@gdit-demo.example", ttl=1)
            time.sleep(2)
            cursor.execute("SELECT set_config('app.user_token', %s, false)", (expired_token,))
            cursor.execute("SELECT count(*) FROM workday.workers_v")
            if cursor.fetchone()[0] != 0:
                raise AssertionError("Expired identity token unexpectedly returned rows")
            lines.append("   expired app.user_token: 0 rows")

            cursor.execute("SELECT set_config('app.user_token', '', false)")
            cursor.execute(
                "SELECT set_config('app.user_email', 'exec@gdit-demo.example', false)"
            )
            cursor.execute("SELECT count(*) FROM workday.workers_v")
            if cursor.fetchone()[0] != 0:
                raise AssertionError("Unsigned app.user_email unexpectedly returned rows")
            lines.append("   unsigned app.user_email: 0 rows")
    finally:
        app_connection.close()

    tableau_connection = connect_supabase("tableau_reader")
    try:
        with tableau_connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM workday.workers")
            tableau_count = cursor.fetchone()[0]
            lines.append(f"   tableau_reader SELECT workday.workers: {tableau_count:,} rows")
            try:
                cursor.execute("INSERT INTO workday.workers (worker_id) VALUES ('RLS-VERIFY-INSERT')")
            except psycopg.errors.InsufficientPrivilege:
                tableau_connection.rollback()
                lines.append("   tableau_reader INSERT: denied as expected")
            else:
                tableau_connection.rollback()
                raise AssertionError("tableau_reader unexpectedly had INSERT permission")
    finally:
        tableau_connection.close()

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = story_output()
    print(output, end="")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"Evidence written to {args.output}")


if __name__ == "__main__":
    main()
