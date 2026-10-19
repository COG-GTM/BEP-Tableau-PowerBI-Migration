#!/usr/bin/env python3
"""Query Supabase equivalents of the Tableau workbook's headline calculations."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
from psycopg.rows import dict_row


DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parent
sys.path.insert(0, str(DEMO_ROOT))

from scripts.load_postgres import connect_supabase  # noqa: E402


IDENTITIES = (
    "exec@gdit-demo.example",
    "defense.lead@gdit-demo.example",
    "intel.lead@gdit-demo.example",
)
EXPECTED = {
    "defense_latest_exits": 156,
    "defense_prior_exits": 78,
    "army_navy_revenue_at_risk_usd": Decimal("236023502.67"),
    "intelligence_programs_security_overdue_percent": Decimal("29.4"),
    "civilian_budget_variance_percent": Decimal("-5.9"),
}


def rows(connection, query: str, params=()):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def divisions_for(connection, view_as: str):
    result = rows(
        connection,
        """
        SELECT division
        FROM security.v_entitlement_expanded
        WHERE user_email = %s
        ORDER BY division
        """,
        (view_as,),
    )
    return [row["division"] for row in result]


def kpis_by_division(connection, view_as: str):
    return rows(
        connection,
        """
        WITH bounds AS (
          SELECT date_trunc('month', current_date)::date AS month_start,
                 (date_trunc('month', current_date) - interval '3 months')::date AS latest_start,
                 (date_trunc('month', current_date) - interval '6 months')::date AS prior_start
        ),
        visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        )
        SELECT w.division,
               count(*) FILTER (
                 WHERE w.hire_date <= current_date
                   AND (w.term_date IS NULL OR w.term_date > current_date)
               ) AS headcount,
               count(*) FILTER (
                 WHERE w.term_type = 'Voluntary'
                   AND w.term_date >= b.latest_start
                   AND w.term_date < b.month_start
               ) AS vol_exits_latest,
               count(*) FILTER (
                 WHERE w.term_type = 'Voluntary'
                   AND w.term_date >= b.prior_start
                   AND w.term_date < b.latest_start
               ) AS vol_exits_prior
        FROM visible v
        JOIN workday.workers w USING (division)
        CROSS JOIN bounds b
        GROUP BY w.division
        ORDER BY w.division
        """,
        (view_as,),
    )


def monthly_exits_trend(connection, view_as: str):
    return rows(
        connection,
        """
        WITH visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        ),
        months AS (
          SELECT generate_series(
            date_trunc('month', current_date) - interval '36 months',
            date_trunc('month', current_date) - interval '1 month',
            interval '1 month'
          )::date AS month
        )
        SELECT v.division,
               m.month,
               count(w.worker_id) AS voluntary_exits
        FROM visible v
        CROSS JOIN months m
        LEFT JOIN workday.workers w
          ON w.division = v.division
         AND w.term_type = 'Voluntary'
         AND date_trunc('month', w.term_date)::date = m.month
        GROUP BY v.division, m.month
        ORDER BY v.division, m.month
        """,
        (view_as,),
    )


def top_titles(connection, view_as: str):
    return rows(
        connection,
        """
        WITH bounds AS (
          SELECT date_trunc('month', current_date)::date AS month_start,
                 (date_trunc('month', current_date) - interval '3 months')::date AS latest_start
        ),
        visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        )
        SELECT w.job_title, count(*) AS voluntary_exits
        FROM visible v
        JOIN workday.workers w USING (division)
        CROSS JOIN bounds b
        WHERE w.term_type = 'Voluntary'
          AND w.term_date >= b.latest_start
          AND w.term_date < b.month_start
        GROUP BY w.job_title
        ORDER BY voluntary_exits DESC, w.job_title
        LIMIT 10
        """,
        (view_as,),
    )


def revenue_at_risk_by_account(connection, view_as: str):
    return rows(
        connection,
        """
        WITH visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        ),
        per_opportunity AS (
          SELECT o.opp_id,
                 o.account_name,
                 o.amount,
                 sum(r.headcount) AS requested_headcount,
                 sum(r.headcount) FILTER (
                   WHERE r.status = 'Open' AND r.needed_by < current_date
                 ) AS past_due_open_headcount
          FROM visible v
          JOIN salesforce.opportunities o USING (division)
          JOIN salesforce.staffing_requests r USING (opp_id)
          WHERE o.stage = 'Won'
          GROUP BY o.opp_id, o.account_name, o.amount
        )
        SELECT account_name,
               count(*) FILTER (WHERE past_due_open_headcount > 0) AS affected_opportunities,
               coalesce(sum(
                 amount * past_due_open_headcount / nullif(requested_headcount, 0)
               ), 0) AS revenue_at_risk_usd,
               coalesce(sum(past_due_open_headcount), 0) AS past_due_open_headcount
        FROM per_opportunity
        GROUP BY account_name
        ORDER BY account_name
        """,
        (view_as,),
    )


def overdue_rate_by_business_unit(connection, view_as: str):
    return rows(
        connection,
        """
        WITH visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        )
        SELECT w.division,
               w.business_unit,
               count(*) FILTER (WHERE t.status = 'Overdue') AS overdue,
               count(*) FILTER (WHERE t.status IN ('Completed', 'Overdue')) AS due,
               round(
                 count(*) FILTER (WHERE t.status = 'Overdue')::numeric
                 / nullif(count(*) FILTER (WHERE t.status IN ('Completed', 'Overdue')), 0),
                 4
               ) AS overdue_rate
        FROM visible v
        JOIN workday.workers w USING (division)
        JOIN oracle_lms.training_completions t USING (worker_id)
        JOIN oracle_lms.courses c USING (course_code)
        WHERE c.category = 'Security'
        GROUP BY w.division, w.business_unit
        ORDER BY w.division, overdue_rate DESC, w.business_unit
        """,
        (view_as,),
    )


def quarter_end_for(today: date):
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_start_month, 1)
    quarter_end = quarter_start - timedelta(days=1)
    quarter_number = (quarter_end.month - 1) // 3 + 1
    return quarter_end, f"FY{quarter_end.year % 100:02d}", f"Q{quarter_number}"


def headcount_vs_budget(connection, view_as: str, quarter_end: date, budget_frame: pd.DataFrame, fiscal_year: str, fiscal_quarter: str):
    selected_budget = (
        budget_frame.loc[
            budget_frame["fiscal_year"].eq(fiscal_year)
            & budget_frame["fiscal_quarter"].eq(fiscal_quarter)
        ]
        .groupby("division", as_index=False)["headcount_budget"]
        .sum()
    )
    budget_values = [
        (row.division, int(row.headcount_budget))
        for row in selected_budget.itertuples(index=False)
    ]
    if not budget_values:
        return []
    placeholders = ", ".join(["(%s, %s)"] * len(budget_values))
    budget_params = [item for budget_row in budget_values for item in budget_row]
    query = f"""
        WITH visible AS (
          SELECT division
          FROM security.v_entitlement_expanded
          WHERE user_email = %s
        ),
        budget AS (
          SELECT *
          FROM (VALUES {placeholders}) AS b(division, headcount_budget)
        )
        SELECT w.division,
               count(*) AS actual_headcount,
               b.headcount_budget,
               round((count(*)::numeric / nullif(b.headcount_budget, 0) - 1) * 100, 1)
                 AS variance_percent
        FROM visible v
        JOIN workday.workers w USING (division)
        JOIN budget b USING (division)
        WHERE w.hire_date <= %s
          AND (w.term_date IS NULL OR w.term_date > %s)
        GROUP BY w.division, b.headcount_budget
        ORDER BY w.division
    """
    return rows(connection, query, [view_as, *budget_params, quarter_end, quarter_end])


def evaluate():
    connection = connect_supabase("tableau_reader")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_date")
            today = cursor.fetchone()[0]
        quarter_end, fiscal_year, fiscal_quarter = quarter_end_for(today)
        budget_frame = pd.read_excel(
            DEMO_ROOT / "data/finance/fy_headcount_budget.xlsx"
        )
        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "database_date": today.isoformat(),
            "window_months": 3,
            "as_of_quarter_end": quarter_end.isoformat(),
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "view_as": {},
        }
        for identity in IDENTITIES:
            report["view_as"][identity] = {
                "visible_divisions": divisions_for(connection, identity),
                "kpis_by_division": kpis_by_division(connection, identity),
                "monthly_exits_trend_last_36_months": monthly_exits_trend(connection, identity),
                "top_10_titles_latest_window": top_titles(connection, identity),
                "revenue_at_risk_by_account": revenue_at_risk_by_account(connection, identity),
                "overdue_rate_by_business_unit": overdue_rate_by_business_unit(connection, identity),
                "headcount_vs_budget_at_quarter_end": headcount_vs_budget(
                    connection,
                    identity,
                    quarter_end,
                    budget_frame,
                    fiscal_year,
                    fiscal_quarter,
                ),
            }
        return json_safe(report)
    finally:
        connection.close()


def check_targets(report):
    executive = report["view_as"]["exec@gdit-demo.example"]
    defense = next(row for row in executive["kpis_by_division"] if row["division"] == "Defense")
    intelligence_rate = next(
        row
        for row in executive["overdue_rate_by_business_unit"]
        if row["division"] == "Intelligence" and row["business_unit"] == "Intelligence Programs"
    )
    civilian_budget = next(
        row
        for row in executive["headcount_vs_budget_at_quarter_end"]
        if row["division"] == "Civilian"
    )
    revenue_total = sum(
        Decimal(str(row["revenue_at_risk_usd"]))
        for row in executive["revenue_at_risk_by_account"]
    )
    army_navy_total = sum(
        Decimal(str(row["revenue_at_risk_usd"]))
        for row in executive["revenue_at_risk_by_account"]
        if row["account_name"] in {"Army", "Navy"}
    )
    observed = {
        "defense_latest_exits": defense["vol_exits_latest"],
        "defense_prior_exits": defense["vol_exits_prior"],
        "revenue_at_risk_won_usd": revenue_total.quantize(Decimal("0.01")),
        "army_navy_revenue_at_risk_usd": army_navy_total.quantize(Decimal("0.01")),
        "intelligence_programs_security_overdue_percent": (
            Decimal(str(intelligence_rate["overdue_rate"])) * 100
        ).quantize(Decimal("0.1")),
        "civilian_budget_variance_percent": Decimal(str(civilian_budget["variance_percent"])),
    }
    comparisons = {key: observed[key] == expected for key, expected in EXPECTED.items()}
    return {
        "observed": json_safe(observed),
        "expected": json_safe(EXPECTED),
        "passed": comparisons,
        "all_passed": all(comparisons.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assert-seed",
        action="store_true",
        help="fail when the fresh seeded-data story targets do not match",
    )
    args = parser.parse_args()
    report = evaluate()
    targets = check_targets(report)
    report["target_checks"] = targets
    report["revenue_at_risk_won_usd"] = targets["observed"]["revenue_at_risk_won_usd"]
    report["army_navy_revenue_at_risk_usd"] = targets["observed"][
        "army_navy_revenue_at_risk_usd"
    ]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    expected_dir = DEMO_ROOT / "tableau/expected"
    expected_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = Path.home() / "gdit/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (expected_dir / f"{stamp}.json").write_text(output, encoding="utf-8")
    latest_path = evidence_dir / "expected_values_latest.json"
    latest_path.write_text(output, encoding="utf-8")
    print(output, end="")
    print(f"Timestamped output: {expected_dir / f'{stamp}.json'}")
    print(f"Evidence copy: {latest_path}")
    if args.assert_seed and not targets["all_passed"]:
        raise SystemExit("Expected-value target mismatch; see observed values above.")


if __name__ == "__main__":
    main()
