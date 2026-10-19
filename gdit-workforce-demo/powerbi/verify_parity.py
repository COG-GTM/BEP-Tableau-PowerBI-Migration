#!/usr/bin/env python3
"""Compare Power BI measure semantics with independent PostgreSQL aggregates."""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))

from scripts.load_postgres import connect_supabase  # noqa: E402


EXPECTED_PATH = Path.home() / "gdit/evidence/expected_values_latest.json"
EVIDENCE_PATH = Path.home() / "gdit/evidence/parity_latest.txt"
IDENTITIES = (
    "exec@gdit-demo.example",
    "defense.lead@gdit-demo.example",
    "intel.lead@gdit-demo.example",
)


def query(connection, sql: str, parameters: tuple = ()) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, parameters)
        names = [column.name for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def json_value(value):
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def normalize(rows: list[dict]) -> list[dict]:
    return [{key: json_value(value) for key, value in row.items()} for row in rows]


def compare(expected, actual, path: str = "value") -> None:
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            raise AssertionError(f"{path}: keys differ: {set(expected)} != {set(actual)}")
        for key in expected:
            compare(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            raise AssertionError(f"{path}: row counts differ: {len(expected)} != {len(actual)}")
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if isinstance(expected, int):
            matches = expected == actual
        elif "revenue_at_risk" in path or path.endswith("_usd"):
            matches = Decimal(str(expected)).quantize(Decimal("0.01")) == Decimal(
                str(actual)
            ).quantize(Decimal("0.01"))
        elif path.endswith("variance_percent"):
            matches = Decimal(str(expected)).quantize(Decimal("0.1")) == Decimal(
                str(actual)
            ).quantize(Decimal("0.1"))
        elif path.endswith("overdue_rate"):
            matches = (Decimal(str(expected)) * 100).quantize(
                Decimal("0.1")
            ) == (Decimal(str(actual)) * 100).quantize(Decimal("0.1"))
        else:
            matches = abs(float(expected) - float(actual)) < 1e-9
        if not matches:
            raise AssertionError(f"{path}: {expected} != {actual}")
    elif expected != actual:
        raise AssertionError(f"{path}: {expected!r} != {actual!r}")


def visible_divisions(connection, identity: str) -> list[str]:
    return [
        row["division"]
        for row in query(
            connection,
            "SELECT division FROM security.v_entitlement_expanded "
            "WHERE user_email = %s ORDER BY division",
            (identity,),
        )
    ]


def parity_rows(connection, identity: str, divisions: list[str], expected: dict) -> dict:
    kpis = query(
        connection,
        """
        SELECT division,
               (SELECT count(*) FROM workday.workers w
                 WHERE w.division = d.division AND w.hire_date <= current_date
                   AND (w.term_date IS NULL OR w.term_date > current_date)) AS headcount,
               (SELECT count(*) FROM workday.workers w
                 WHERE w.division = d.division AND w.term_type = 'Voluntary'
                   AND w.term_date >= date_trunc('month', current_date) - interval '3 months'
                   AND w.term_date < date_trunc('month', current_date)) AS vol_exits_latest,
               (SELECT count(*) FROM workday.workers w
                 WHERE w.division = d.division AND w.term_type = 'Voluntary'
                   AND w.term_date >= date_trunc('month', current_date) - interval '6 months'
                   AND w.term_date < date_trunc('month', current_date) - interval '3 months') AS vol_exits_prior
        FROM unnest(%s::text[]) AS d(division)
        ORDER BY division
        """,
        (divisions,),
    )
    monthly = query(
        connection,
        """
        SELECT d.division, m.month::date AS month, count(w.worker_id) AS voluntary_exits
        FROM unnest(%s::text[]) AS d(division)
        CROSS JOIN generate_series(
            date_trunc('month', current_date) - interval '36 months',
            date_trunc('month', current_date) - interval '1 month',
            interval '1 month'
        ) AS m(month)
        LEFT JOIN workday.workers w
          ON w.division = d.division
         AND w.term_type = 'Voluntary'
         AND date_trunc('month', w.term_date) = m.month
        GROUP BY d.division, m.month
        ORDER BY d.division, m.month
        """,
        (divisions,),
    )
    top_titles = query(
        connection,
        """
        SELECT job_title, count(*) AS voluntary_exits
        FROM workday.workers
        WHERE division = ANY(%s::text[])
          AND term_type = 'Voluntary'
          AND term_date >= date_trunc('month', current_date) - interval '3 months'
          AND term_date < date_trunc('month', current_date)
        GROUP BY job_title
        ORDER BY voluntary_exits DESC, job_title
        LIMIT 10
        """,
        (divisions,),
    )
    revenue = query(
        connection,
        """
        WITH request_totals AS (
            SELECT opp_id, sum(headcount) AS requested_hc
            FROM salesforce.staffing_requests
            GROUP BY opp_id
        ),
        overdue AS (
            SELECT opp_id, sum(headcount) AS past_due_hc
            FROM salesforce.staffing_requests
            WHERE status = 'Open' AND needed_by < current_date
            GROUP BY opp_id
        )
        SELECT o.account_name,
               count(*) FILTER (WHERE coalesce(p.past_due_hc, 0) > 0) AS affected_opportunities,
               coalesce(sum(p.past_due_hc), 0) AS past_due_open_headcount,
               coalesce(sum(o.amount * p.past_due_hc / nullif(t.requested_hc, 0))
                   FILTER (WHERE o.stage = 'Won'), 0) AS revenue_at_risk_usd
        FROM salesforce.opportunities o
        JOIN request_totals t USING (opp_id)
        LEFT JOIN overdue p USING (opp_id)
        WHERE o.division = ANY(%s::text[]) AND o.stage = 'Won'
        GROUP BY o.account_name
        ORDER BY o.account_name
        """,
        (divisions,),
    )
    overdue_rates = query(
        connection,
        """
        SELECT w.business_unit, w.division,
               sum((t.status = 'Overdue')::int) AS overdue,
               sum((t.status IN ('Completed', 'Overdue'))::int) AS due,
               round(
                   sum((t.status = 'Overdue')::int)::numeric
                   / nullif(sum((t.status IN ('Completed', 'Overdue'))::int), 0), 4
               ) AS overdue_rate
        FROM workday.workers w
        JOIN oracle_lms.training_completions t USING (worker_id)
        JOIN oracle_lms.courses c USING (course_code)
        WHERE w.division = ANY(%s::text[]) AND c.category = 'Security'
        GROUP BY w.division, w.business_unit
        ORDER BY w.division, overdue_rate DESC, w.business_unit
        """,
        (divisions,),
    )
    quarter_end = date.fromisoformat(expected["as_of_quarter_end"])
    budget_frame = pd.read_excel(DEMO_ROOT / "data/finance/fy_headcount_budget.xlsx")
    budget_values = [
        (division, int(headcount_budget))
        for division, headcount_budget in budget_frame.loc[
            budget_frame["fiscal_year"].eq(expected["fiscal_year"])
            & budget_frame["fiscal_quarter"].eq(expected["fiscal_quarter"])
        ].groupby("division")["headcount_budget"].sum().items()
    ]
    if not budget_values:
        raise AssertionError("The expected fiscal quarter is missing from the budget workbook")
    budget_placeholders = ", ".join(["(%s, %s)"] * len(budget_values))
    budget = query(
        connection,
        f"""
        WITH imported_budget(division, headcount_budget) AS (
            VALUES {budget_placeholders}
        )
        SELECT d.division,
               (SELECT count(*) FROM workday.workers w
                 WHERE w.division = d.division AND w.hire_date <= %s
                   AND (w.term_date IS NULL OR w.term_date > %s)) AS actual_headcount,
               b.headcount_budget
        FROM unnest(%s::text[]) AS d(division)
        LEFT JOIN imported_budget b ON b.division = d.division
        ORDER BY d.division
        """,
        (
            *[item for budget_row in budget_values for item in budget_row],
            quarter_end,
            quarter_end,
            divisions,
        ),
    )
    budget = [
        {
            **row,
            "variance_percent": round(
                100 * (row["actual_headcount"] - row["headcount_budget"])
                / row["headcount_budget"],
                1,
            ),
        }
        for row in budget
    ]
    return {
        "visible_divisions": divisions,
        "kpis_by_division": normalize(kpis),
        "monthly_exits_trend_last_36_months": normalize(monthly),
        "top_10_titles_latest_window": normalize(top_titles),
        "revenue_at_risk_by_account": normalize(revenue),
        "overdue_rate_by_business_unit": normalize(overdue_rates),
        "headcount_vs_budget_at_quarter_end": normalize(budget),
    }


def main() -> int:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    connection = connect_supabase("tableau_reader")
    results = ["Power BI parity verification (independent SQL aggregates)"]
    exec_observed = None
    try:
        for identity in IDENTITIES:
            divisions = visible_divisions(connection, identity)
            observed = parity_rows(connection, identity, divisions, expected)
            compare(expected["view_as"][identity], observed, identity)
            if identity == "exec@gdit-demo.example":
                exec_observed = observed
            results.append(f"PASS {identity}: KPIs, trend, top titles, revenue, training, budget")
        if exec_observed is None:
            raise AssertionError("Exec parity results were not collected")
        all_account_risk = sum(
            Decimal(str(row["revenue_at_risk_usd"]))
            for row in exec_observed["revenue_at_risk_by_account"]
        )
        army_navy_risk = sum(
            Decimal(str(row["revenue_at_risk_usd"]))
            for row in exec_observed["revenue_at_risk_by_account"]
            if row["account_name"] in {"Army", "Navy"}
        )
        compare(
            expected["revenue_at_risk_won_usd"],
            float(all_account_risk),
            "revenue_at_risk_won_usd",
        )
        compare(
            expected["army_navy_revenue_at_risk_usd"],
            float(army_navy_risk),
            "army_navy_revenue_at_risk_usd",
        )
        results.append(f"PASS revenue_at_risk_won_usd: ${all_account_risk:,.2f}")
        results.append(f"PASS army_navy_revenue_at_risk_usd: ${army_navy_risk:,.2f}")
    finally:
        connection.close()
    text = "\n".join(results) + "\n"
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"Evidence: {EVIDENCE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
