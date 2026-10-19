from __future__ import annotations

from pathlib import Path

import pandas as pd
from psycopg.rows import dict_row

from tableau.expected_values import quarter_end_for

DEMO_ROOT = Path(__file__).resolve().parents[1]


def fetch(connection, statement: str, params=()):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(statement, params)
        return cursor.fetchall()


def query_dashboard(connection, window_months: int = 3, account: str | None = None) -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_date")
        today = cursor.fetchone()[0]
    kpis = fetch(
        connection,
        """
        WITH bounds AS (
          SELECT (date_trunc('month', current_date) - make_interval(months => %s))::date AS latest_start,
                 (date_trunc('month', current_date) - make_interval(months => %s))::date AS prior_start,
                 date_trunc('month', current_date)::date AS month_start
        )
        SELECT w.division,
               count(*) FILTER (WHERE w.hire_date <= current_date
                    AND (w.term_date IS NULL OR w.term_date > current_date)) AS headcount,
               count(*) FILTER (WHERE w.term_type = 'Voluntary'
                    AND w.term_date >= b.latest_start AND w.term_date < b.month_start) AS vol_exits_latest,
               count(*) FILTER (WHERE w.term_type = 'Voluntary'
                    AND w.term_date >= b.prior_start AND w.term_date < b.latest_start) AS vol_exits_prior
        FROM workday.workers_v w CROSS JOIN bounds b
        GROUP BY w.division ORDER BY w.division
        """,
        (window_months, window_months * 2),
    )
    trend = fetch(
        connection,
        """
        WITH months AS (
          SELECT generate_series(
            date_trunc('month', current_date) - interval '36 months',
            date_trunc('month', current_date) - interval '1 month',
            interval '1 month'
          )::date AS month
        ), monthly AS (
          SELECT date_trunc('month', term_date)::date AS month, count(*) AS voluntary_exits
          FROM workday.workers_v
          WHERE term_type = 'Voluntary'
            AND term_date >= date_trunc('month', current_date) - interval '36 months'
            AND term_date < date_trunc('month', current_date)
          GROUP BY 1
        )
        SELECT m.month, coalesce(x.voluntary_exits, 0) AS voluntary_exits,
               sum(coalesce(x.voluntary_exits, 0)) OVER (ORDER BY m.month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
                 AS trailing_3m
        FROM months m LEFT JOIN monthly x USING (month) ORDER BY m.month
        """,
    )
    top_titles = fetch(
        connection,
        """
        SELECT job_title, count(*) AS voluntary_exits
        FROM workday.workers_v
        WHERE term_type = 'Voluntary'
          AND term_date >= date_trunc('month', current_date) - make_interval(months => %s)
          AND term_date < date_trunc('month', current_date)
        GROUP BY job_title ORDER BY voluntary_exits DESC, job_title LIMIT 10
        """,
        (window_months,),
    )
    heatmap = fetch(
        connection,
        """
        SELECT clearance_level, job_family, count(*) AS voluntary_exits
        FROM workday.workers_v
        WHERE term_type = 'Voluntary'
          AND term_date >= date_trunc('month', current_date) - make_interval(months => %s)
          AND term_date < date_trunc('month', current_date)
        GROUP BY clearance_level, job_family ORDER BY clearance_level, job_family
        """,
        (window_months,),
    )
    revenue = fetch(
        connection,
        """
        WITH opportunity_risk AS (
          SELECT o.opp_id, o.account_name, o.amount,
                 sum(r.headcount) AS requested_hc,
                 sum(r.headcount) FILTER (
                   WHERE r.status = 'Open' AND r.needed_by < current_date
                 ) AS past_due_hc
          FROM salesforce.opportunities_v o
          JOIN salesforce.staffing_requests_v r USING (opp_id)
          WHERE o.stage = 'Won'
          GROUP BY o.opp_id, o.account_name, o.amount
        )
        SELECT account_name,
               coalesce(sum(amount * past_due_hc / nullif(requested_hc, 0)), 0)
                 AS revenue_at_risk_usd,
               coalesce(sum(past_due_hc), 0) AS past_due_open_headcount
        FROM opportunity_risk GROUP BY account_name ORDER BY account_name
        """,
    )
    past_due = fetch(
        connection,
        """
        SELECT r.job_family, r.clearance_required, sum(r.headcount) AS headcount
        FROM salesforce.staffing_requests_v r
        JOIN salesforce.opportunities_v o USING (opp_id)
        WHERE r.status = 'Open' AND r.needed_by < current_date AND o.stage = 'Won'
        GROUP BY r.job_family, r.clearance_required
        ORDER BY headcount DESC, r.job_family, r.clearance_required
        """,
    )
    staffing_details = fetch(
        connection,
        """
        SELECT o.account_name, o.opp_id, r.req_id, r.job_family, r.clearance_required,
               r.headcount, r.needed_by
        FROM salesforce.opportunities_v o
        JOIN salesforce.staffing_requests_v r USING (opp_id)
        WHERE o.stage = 'Won' AND r.status = 'Open' AND r.needed_by < current_date
          AND (%s::text IS NULL OR o.account_name = %s)
        ORDER BY o.account_name, r.needed_by, r.req_id
        """,
        (account, account),
    )
    overdue = fetch(
        connection,
        """
        WITH grouped AS (
          SELECT w.division, w.business_unit,
               count(*) FILTER (WHERE t.status = 'Overdue') AS overdue,
               count(*) FILTER (WHERE t.status IN ('Completed', 'Overdue')) AS due
          FROM workday.workers_v w
          JOIN oracle_lms.training_completions_v t USING (worker_id)
          JOIN oracle_lms.courses_v c USING (course_code)
          WHERE c.category = 'Security'
          GROUP BY w.division, w.business_unit
        )
        SELECT division, business_unit, overdue, due,
               round(overdue::numeric / nullif(due, 0), 4) AS overdue_rate,
               round(sum(overdue) OVER (PARTITION BY division)::numeric
                 / nullif(sum(due) OVER (PARTITION BY division), 0), 4) AS division_baseline
        FROM grouped ORDER BY division, overdue_rate DESC, business_unit
        """,
    )
    quarter_end, fiscal_year, fiscal_quarter = quarter_end_for(today)
    budget_frame = pd.read_excel(DEMO_ROOT / "data/finance/fy_headcount_budget.xlsx")
    budget_mtime = (DEMO_ROOT / "data/finance/fy_headcount_budget.xlsx").stat().st_mtime
    budget_frame = budget_frame.loc[
        budget_frame.fiscal_year.eq(fiscal_year)
        & budget_frame.fiscal_quarter.eq(fiscal_quarter)
    ].groupby("division", as_index=False).headcount_budget.sum()
    budget_values = [(r.division, int(r.headcount_budget)) for r in budget_frame.itertuples()]
    budget = []
    if budget_values:
        placeholders = ", ".join(["(%s, %s)"] * len(budget_values))
        budget = fetch(
            connection,
            f"""
            WITH b(division, headcount_budget) AS (VALUES {placeholders})
            SELECT w.division, count(*) AS actual_headcount, b.headcount_budget,
                   round((count(*)::numeric / nullif(b.headcount_budget, 0) - 1) * 100, 1)
                     AS variance_percent
            FROM workday.workers_v w JOIN b USING (division)
            WHERE w.hire_date <= %s AND (w.term_date IS NULL OR w.term_date > %s)
            GROUP BY w.division, b.headcount_budget ORDER BY w.division
            """,
            (*[x for row in budget_values for x in row], quarter_end, quarter_end),
        )
    freshness = fetch(
        connection,
        """
        SELECT (SELECT max(last_updated) FROM workday.workers_v) AS worker_updated,
               (SELECT max(event_date) FROM workday.worker_events_v) AS event_date,
               (SELECT count(*) FROM workday.worker_events_v) AS event_count
        """,
    )[0]
    result = {
        "visible_divisions": [r["division"] for r in kpis],
        "kpis_by_division": kpis,
        "monthly_exits_trend_last_36_months": trend,
        "top_10_titles_latest_window": top_titles,
        "clearance_family_exits": heatmap,
        "revenue_at_risk_by_account": revenue,
        "past_due_open_headcount_by_family_clearance": past_due,
        "open_requests_detail": staffing_details,
        "overdue_rate_by_business_unit": overdue,
        "headcount_vs_budget_at_quarter_end": budget,
        "quarter_end": quarter_end.isoformat(),
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "budget_source": f"source: FP&A file, loaded {pd.Timestamp.fromtimestamp(budget_mtime).isoformat()}",
        "freshness": {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in freshness.items()
        },
        "window_months": window_months,
        "selected_account": account,
    }
    for row in kpis:
        row["latest_to_prior_ratio"] = (
            round(row["vol_exits_latest"] / row["vol_exits_prior"], 2)
            if row["vol_exits_prior"]
            else None
        )
    return result


def defense_attrition_question(connection) -> dict:
    rows = fetch(
        connection,
        """
        WITH bounds AS (
          SELECT (date_trunc('month', current_date) - interval '3 months')::date AS latest_start,
                 (date_trunc('month', current_date) - interval '6 months')::date AS prior_start,
                 date_trunc('month', current_date)::date AS month_start
        ), latest AS (
          SELECT division, count(*) AS exits
          FROM workday.workers_v, bounds
          WHERE term_type = 'Voluntary' AND term_date >= latest_start AND term_date < month_start
          GROUP BY division
        ), prior AS (
          SELECT division, count(*) AS exits
          FROM workday.workers_v, bounds
          WHERE term_type = 'Voluntary' AND term_date >= prior_start AND term_date < latest_start
          GROUP BY division
        )
        SELECT l.division, l.exits AS latest, coalesce(p.exits, 0) AS prior
        FROM latest l LEFT JOIN prior p USING (division) ORDER BY l.division
        """,
    )
    drivers = fetch(
        connection,
        """
        SELECT job_title, count(*) AS exits
        FROM workday.workers_v
        WHERE term_type = 'Voluntary'
          AND term_date >= date_trunc('month', current_date) - interval '3 months'
          AND term_date < date_trunc('month', current_date)
        GROUP BY job_title ORDER BY exits DESC, job_title LIMIT 10
        """,
    )
    return {
        "answer": "Voluntary exits in the latest three full months versus the prior three, by visible division.",
        "by_division": rows,
        "title_drivers": drivers,
        "sql": """WITH bounds AS (
  SELECT (date_trunc('month', current_date) - interval '3 months')::date AS latest_start,
         (date_trunc('month', current_date) - interval '6 months')::date AS prior_start,
         date_trunc('month', current_date)::date AS month_start
)
SELECT division,
       count(*) FILTER (WHERE term_date >= latest_start AND term_date < month_start) AS latest,
       count(*) FILTER (WHERE term_date >= prior_start AND term_date < latest_start) AS prior
FROM workday.workers_v CROSS JOIN bounds
WHERE term_type = 'Voluntary'
GROUP BY division ORDER BY division""",
        "chart": {
            "data": {"values": rows},
            "mark": "bar",
            "encoding": {
                "x": {"field": "division", "type": "nominal"},
                "y": {"field": "latest", "type": "quantitative"},
                "color": {"field": "division", "type": "nominal"},
            },
        },
    }
