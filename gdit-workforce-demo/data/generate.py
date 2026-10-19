#!/usr/bin/env python3
"""Generate the deterministic synthetic GDIT workforce demo data."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20261019
HISTORY_START = date(2021, 1, 1)
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "out"
FINANCE_FILE = ROOT / "data" / "finance" / "fy_headcount_budget.xlsx"

DIVISION_COUNTS = {
    "Defense": 4200,
    "Intelligence": 3000,
    "Civilian": 3000,
    "Health": 1800,
}
BUSINESS_UNITS = {
    "Defense": ["Army Programs", "Navy & Marine Corps", "Air & Space"],
    "Intelligence": ["Intelligence Programs", "National Security Solutions"],
    "Civilian": ["Federal Civilian", "Homeland Security", "Civilian Programs"],
    "Health": ["Health Programs", "VA Programs"],
}
JOB_FAMILIES = [
    "Software Engineering",
    "Cyber",
    "Data & AI",
    "Program Management",
    "Systems Engineering",
    "Help Desk",
    "Business Ops",
]
JOB_TITLES = {
    "Software Engineering": ["Software Engineer", "Senior Software Engineer", "Application Developer"],
    "Cyber": ["Cybersecurity Analyst", "Cyber Engineer", "Information Assurance Specialist"],
    "Data & AI": ["Data Engineer", "Data Scientist", "AI Solutions Architect"],
    "Program Management": ["Program Analyst", "Program Manager", "Project Scheduler"],
    "Systems Engineering": ["Systems Engineer", "Systems Architect", "Integration Engineer"],
    "Help Desk": ["Service Desk Analyst", "IT Support Specialist", "Desktop Support Technician"],
    "Business Ops": ["Financial Analyst", "Operations Analyst", "Business Process Analyst"],
}
STATES = ["VA", "MD", "TX", "CO", "CA", "FL", "DC", "PA", "AL", "NC"]
STATE_CITIES = {
    "VA": ["Fairfax", "Arlington", "Chantilly"],
    "MD": ["Bethesda", "Rockville", "Columbia"],
    "TX": ["San Antonio", "Austin", "Houston"],
    "CO": ["Colorado Springs", "Denver", "Aurora"],
    "CA": ["San Diego", "Los Angeles", "Sacramento"],
    "FL": ["Tampa", "Orlando", "Jacksonville"],
    "DC": ["Washington"],
    "PA": ["Philadelphia", "Pittsburgh"],
    "AL": ["Huntsville", "Birmingham"],
    "NC": ["Raleigh", "Fayetteville"],
}
FAMILY_BASE_SALARY = {
    "Software Engineering": 99000,
    "Cyber": 96000,
    "Data & AI": 103000,
    "Program Management": 91000,
    "Systems Engineering": 95000,
    "Help Desk": 58000,
    "Business Ops": 73000,
}
ACCOUNTS = ["Army", "Navy", "Air Force", "DHS", "VA", "IRS", "CMS", "State", "NGA", "DISA"]
ACCOUNT_DIVISION = {
    "Army": "Defense",
    "Navy": "Defense",
    "Air Force": "Defense",
    "DISA": "Defense",
    "NGA": "Intelligence",
    "DHS": "Civilian",
    "IRS": "Civilian",
    "State": "Civilian",
    "VA": "Health",
    "CMS": "Health",
}
STAGES = ["Prospecting", "Qualification", "Proposal", "Submitted", "Won", "Lost"]
CONTRACT_VEHICLES = ["OASIS+", "Alliant 2", "SEWP V", "CIO-SP3", "Agency IDIQ"]
CLEARANCES = ["None", "Public Trust", "Secret", "TS", "TS/SCI"]
DIVISION_WEIGHTS = [0.35, 0.25, 0.25, 0.15]


def add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month = divmod(month_index, 12)
    return date(year, month + 1, min(value.day, 28))


def random_day(rng: np.random.Generator, start: date, end: date) -> date:
    if end < start:
        return start
    return start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))


def date_column(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_datetime(frame[column]).dt.date
    return frame


def make_workers(rng: np.random.Generator, today: date) -> pd.DataFrame:
    divisions = np.concatenate(
        [np.repeat(division, count) for division, count in DIVISION_COUNTS.items()]
    )
    rng.shuffle(divisions)
    focus_ids = [
        f"W{index + 1:06d}"
        for index, division in enumerate(divisions)
        if division == "Defense"
    ][:500]
    focus_set = set(focus_ids)

    current_month = today.replace(day=1)
    latest_start = add_months(current_month, -3)
    prior_start = add_months(current_month, -6)
    latest_end = current_month - timedelta(days=1)
    prior_end = latest_start - timedelta(days=1)

    target_terms: dict[str, tuple[date, str]] = {}
    for index, worker_id in enumerate(focus_ids[:90]):
        if index < 30:
            term_date = random_day(rng, prior_start, prior_end)
        else:
            term_date = random_day(rng, latest_start, latest_end)
        target_terms[worker_id] = (term_date, "Voluntary")

    eligible_for_other_terms = [
        f"W{index + 1:06d}"
        for index in range(len(divisions))
        if f"W{index + 1:06d}" not in target_terms
    ]
    other_terminated = rng.choice(eligible_for_other_terms, size=2410, replace=False)
    terminated = set(target_terms) | set(other_terminated)
    worker_rows = []

    for index, division in enumerate(divisions):
        worker_id = f"W{index + 1:06d}"
        is_focus = worker_id in focus_set
        if is_focus:
            family = "Software Engineering" if index % 2 == 0 else "Cyber"
            level = 2 if (index // 2) % 2 == 0 else 3
            clearance = "TS/SCI"
            state = "VA" if index % 4 < 2 else "MD"
        else:
            family = str(
                rng.choice(
                    JOB_FAMILIES,
                    p=[0.21, 0.17, 0.12, 0.16, 0.15, 0.10, 0.09],
                )
            )
            level = int(rng.integers(1, 7))
            state = str(rng.choice(STATES, p=[0.20, 0.15, 0.15, 0.08, 0.10, 0.07, 0.06, 0.07, 0.05, 0.07]))
            if division == "Intelligence":
                clearance = str(rng.choice(CLEARANCES, p=[0.04, 0.08, 0.17, 0.27, 0.44]))
            elif division == "Defense":
                clearance = str(rng.choice(CLEARANCES, p=[0.08, 0.13, 0.36, 0.31, 0.12]))
            else:
                clearance = str(rng.choice(CLEARANCES, p=[0.17, 0.51, 0.20, 0.09, 0.03]))

        if is_focus and worker_id in target_terms:
            hire_date = random_day(rng, HISTORY_START, date(2023, 12, 31))
        else:
            hire_date = random_day(rng, HISTORY_START, today)
        term_date = None
        term_type = None
        if worker_id in target_terms:
            term_date, term_type = target_terms[worker_id]
        elif worker_id in terminated:
            term_date = random_day(rng, max(hire_date, HISTORY_START), today)
            if division == "Defense" and prior_start <= term_date <= latest_end:
                term_type = str(rng.choice(["Involuntary", "Retirement"]))
            else:
                term_type = str(rng.choice(["Voluntary", "Involuntary", "Retirement"], p=[0.48, 0.40, 0.12]))
        if term_date and hire_date > term_date:
            hire_date = random_day(rng, HISTORY_START, term_date)

        business_unit = str(rng.choice(BUSINESS_UNITS[division]))
        birthdate = random_day(rng, date(1958, 1, 1), date(2002, 12, 31))
        salary = FAMILY_BASE_SALARY[family] * (0.78 + 0.105 * level)
        salary *= {"VA": 1.08, "MD": 1.07, "DC": 1.12, "CA": 1.10}.get(state, 1.0)
        salary *= float(rng.uniform(0.94, 1.06))
        updated_at = datetime.combine(today, time(12), tzinfo=timezone.utc) - timedelta(
            days=int(rng.integers(0, 46))
        )
        manager_id = None
        if index > 0 and index % 11 != 0:
            manager_index = int(rng.integers(max(0, index - 75), index))
            if divisions[manager_index] == division:
                manager_id = f"W{manager_index + 1:06d}"

        worker_rows.append(
            {
                "worker_id": worker_id,
                "first_name": str(rng.choice(["Avery", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn", "Cameron", "Alex"])),
                "last_name": str(rng.choice(["Carter", "Reed", "Brooks", "Hayes", "Morgan", "Bennett", "Price", "Foster", "Perry", "Ross"])),
                "gender": str(rng.choice(["Female", "Male", "Non-binary", "Undisclosed"], p=[0.47, 0.47, 0.03, 0.03])),
                "birthdate": birthdate,
                "education_level": str(rng.choice(["High School", "Associate", "Bachelor", "Master", "Doctorate"], p=[0.12, 0.14, 0.43, 0.27, 0.04])),
                "hire_date": hire_date,
                "term_date": term_date,
                "term_type": term_type,
                "division": str(division),
                "business_unit": business_unit,
                "cost_center": f"CC-{int(rng.integers(1000, 9999))}",
                "location_state": state,
                "location_city": str(rng.choice(STATE_CITIES[state])),
                "remote_flag": bool(rng.random() < 0.28),
                "job_family": family,
                "job_title": str(rng.choice(JOB_TITLES[family])),
                "job_level": level,
                "manager_id": manager_id,
                "clearance_level": clearance,
                "base_salary": round(salary, 2),
                "performance_rating": int(rng.integers(1, 6)),
                "last_updated": updated_at,
            }
        )

    workers = pd.DataFrame(worker_rows)
    return date_column(workers, ["birthdate", "hire_date", "term_date"])


def make_worker_events(
    rng: np.random.Generator, workers: pd.DataFrame, today: date
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    by_id = workers.set_index("worker_id")
    for worker in workers.itertuples(index=False):
        rows.append(
            {
                "event_id": f"E{len(rows) + 1:06d}",
                "worker_id": worker.worker_id,
                "event_date": worker.hire_date,
                "event_type": "Hire",
                "from_value": None,
                "to_value": worker.division,
            }
        )
        if pd.notna(worker.term_date):
            rows.append(
                {
                    "event_id": f"E{len(rows) + 1:06d}",
                    "worker_id": worker.worker_id,
                    "event_date": worker.term_date,
                    "event_type": "Termination",
                    "from_value": worker.division,
                    "to_value": worker.term_type,
                }
            )

    event_types = ["Promotion", "Transfer", "Merit Increase"]
    for _ in range(30000 - len(rows)):
        worker = workers.iloc[int(rng.integers(0, len(workers)))]
        end_date = worker["term_date"] if pd.notna(worker["term_date"]) else today
        event_type = str(rng.choice(event_types, p=[0.36, 0.29, 0.35]))
        event_date = random_day(rng, worker["hire_date"], end_date)
        if event_type == "Merit Increase":
            april_years = [
                year
                for year in range(worker["hire_date"].year, end_date.year + 1)
                if date(year, 4, 1) <= end_date and date(year, 4, 30) >= worker["hire_date"]
            ]
            if april_years:
                year = int(rng.choice(april_years))
                event_date = random_day(
                    rng,
                    max(worker["hire_date"], date(year, 4, 1)),
                    min(end_date, date(year, 4, 30)),
                )
        if event_type == "Promotion":
            from_value, to_value = str(max(1, int(worker["job_level"]) - 1)), str(worker["job_level"])
        elif event_type == "Transfer":
            from_value, to_value = worker["business_unit"], str(rng.choice(BUSINESS_UNITS[worker["division"]]))
        else:
            from_value, to_value = "base_salary", f"{float(worker['base_salary']) * 1.03:.2f}"
        rows.append(
            {
                "event_id": f"E{len(rows) + 1:06d}",
                "worker_id": worker["worker_id"],
                "event_date": event_date,
                "event_type": event_type,
                "from_value": from_value,
                "to_value": to_value,
            }
        )
    events = pd.DataFrame(rows)
    return date_column(events, ["event_date"])


def make_opportunities(rng: np.random.Generator, today: date) -> pd.DataFrame:
    rows = []
    target_accounts = ["Army"] * 250 + ["Navy"] * 250
    for index in range(2400):
        account = target_accounts[index] if index < len(target_accounts) else str(rng.choice(ACCOUNTS))
        division = ACCOUNT_DIVISION[account]
        stage = "Won" if index < len(target_accounts) else str(
            rng.choice(STAGES, p=[0.22, 0.20, 0.20, 0.16, 0.15, 0.07])
        )
        business_unit = str(rng.choice(BUSINESS_UNITS[division]))
        created_date = random_day(rng, HISTORY_START, today)
        close_date = random_day(rng, created_date, today if stage in {"Won", "Lost"} else today + timedelta(days=240))
        amount = float(np.clip(rng.lognormal(mean=16.3, sigma=0.9), 250000, 180000000))
        rows.append(
            {
                "opp_id": f"OPP{index + 1:06d}",
                "account_name": account,
                "division": division,
                "business_unit": business_unit,
                "stage": stage,
                "amount": round(amount, 2),
                "probability": 100 if stage == "Won" else (0 if stage == "Lost" else int(rng.integers(10, 91))),
                "created_date": created_date,
                "close_date": close_date,
                "contract_vehicle": str(rng.choice(CONTRACT_VEHICLES)),
                "required_clearance": str(rng.choice(CLEARANCES, p=[0.06, 0.12, 0.34, 0.31, 0.17])),
            }
        )
    return date_column(pd.DataFrame(rows), ["created_date", "close_date"])


def make_staffing_requests(
    rng: np.random.Generator,
    opportunities: pd.DataFrame,
    workers: pd.DataFrame,
    today: date,
) -> pd.DataFrame:
    target_opps = opportunities.loc[
        opportunities["account_name"].isin(["Army", "Navy"])
        & opportunities["stage"].eq("Won"),
        "opp_id",
    ].to_numpy()
    active_workers = workers.loc[workers["term_date"].isna()]
    worker_ids_by_division = {
        division: group["worker_id"].to_numpy()
        for division, group in active_workers.groupby("division")
    }
    opp_lookup = opportunities.set_index("opp_id")
    rows = []
    for index in range(9000):
        is_target = index < 600
        opp_id = str(rng.choice(target_opps)) if is_target else str(
            rng.choice(opportunities["opp_id"].to_numpy())
        )
        opp = opp_lookup.loc[opp_id]
        division = str(opp["division"])
        if is_target:
            job_family = (
                str(rng.choice(["Software Engineering", "Cyber"]))
                if index < 480
                else str(rng.choice(JOB_FAMILIES[2:]))
            )
            status = "Open"
            needed_by = random_day(rng, HISTORY_START, today - timedelta(days=1))
            opened_date = random_day(rng, HISTORY_START, needed_by)
        else:
            job_family = str(rng.choice(JOB_FAMILIES))
            status = str(rng.choice(["Open", "Filled", "Cancelled"], p=[0.49, 0.40, 0.11]))
            opened_date = random_day(rng, HISTORY_START, today)
            needed_by = random_day(rng, opened_date, today + timedelta(days=150))
        headcount = int(rng.integers(1, 9))
        filled_date = None
        filled_worker_id = None
        if status == "Filled":
            filled_date = random_day(rng, opened_date, today)
            filled_worker_id = str(rng.choice(worker_ids_by_division[division]))
        rows.append(
            {
                "req_id": f"REQ{index + 1:06d}",
                "opp_id": opp_id,
                "division": division,
                "job_family": job_family,
                "clearance_required": str(opp["required_clearance"]),
                "headcount": headcount,
                "opened_date": opened_date,
                "needed_by": needed_by,
                "status": status,
                "filled_date": filled_date,
                "filled_worker_id": filled_worker_id,
            }
        )
    return date_column(pd.DataFrame(rows), ["opened_date", "needed_by", "filled_date"])


def make_courses() -> pd.DataFrame:
    categories = ["Compliance", "Security", "Technical", "Leadership"]
    rows = []
    for category in categories:
        for number in range(1, 11):
            rows.append(
                {
                    "course_code": f"{category[:3].upper()}{number:02d}",
                    "course_name": f"{category} Foundations {number:02d}",
                    "category": category,
                    "required": number <= 7,
                    "recurrence_months": [12, 24, 36, None][(number - 1) % 4],
                }
            )
    courses = pd.DataFrame(rows)
    courses["recurrence_months"] = courses["recurrence_months"].astype("Int64")
    return courses


def make_training_completions(
    rng: np.random.Generator,
    workers: pd.DataFrame,
    courses: pd.DataFrame,
    today: date,
) -> pd.DataFrame:
    worker_indices = rng.integers(0, len(workers), size=150000)
    course_indices = rng.integers(0, len(courses), size=150000)
    assigned_offsets = rng.integers(0, (today - HISTORY_START).days + 1, size=150000)
    duration_days = rng.integers(30, 366, size=150000)
    status_rolls = rng.random(150000)
    score_rolls = rng.integers(60, 101, size=150000)
    rows = []
    for index in range(150000):
        worker = workers.iloc[int(worker_indices[index])]
        course = courses.iloc[int(course_indices[index])]
        assigned_date = HISTORY_START + timedelta(days=int(assigned_offsets[index]))
        due_date = assigned_date + timedelta(days=int(duration_days[index]))
        is_target_security = (
            worker["division"] == "Intelligence"
            and worker["business_unit"] == "Intelligence Programs"
            and course["category"] == "Security"
        )
        if due_date > today:
            status = "In Progress"
            completed_date = None
        elif status_rolls[index] < (0.30 if is_target_security else 0.10):
            status = "Overdue"
            completed_date = None
        else:
            status = "Completed"
            completed_date = random_day(rng, assigned_date, today)
        rows.append(
            {
                "completion_id": f"TC{index + 1:06d}",
                "worker_id": worker["worker_id"],
                "course_code": course["course_code"],
                "assigned_date": assigned_date,
                "due_date": due_date,
                "completed_date": completed_date,
                "status": status,
                "score": int(score_rolls[index]) if status == "Completed" else None,
            }
        )
    completions = pd.DataFrame(rows)
    completions["score"] = completions["score"].astype("Int64")
    return date_column(completions, ["assigned_date", "due_date", "completed_date"])


def make_entitlements() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"user_email": "exec@gdit-demo.example", "division": "*"},
            {"user_email": "defense.lead@gdit-demo.example", "division": "Defense"},
            {"user_email": "intel.lead@gdit-demo.example", "division": "Intelligence"},
            {"user_email": "hr.analyst@gdit-demo.example", "division": "Defense"},
            {"user_email": "hr.analyst@gdit-demo.example", "division": "Civilian"},
        ]
    )


def make_budget(workers: pd.DataFrame, today: date) -> pd.DataFrame:
    rows = []
    current_quarter_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    latest_quarter_end = current_quarter_start - timedelta(days=1)
    for year in range(2022, 2028):
        for quarter in range(1, 5):
            quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
            quarter_end = add_months(quarter_start, 3) - timedelta(days=1)
            point_in_time = min(quarter_end, today)
            for division, business_units in BUSINESS_UNITS.items():
                for business_unit in business_units:
                    group = workers.loc[
                        workers["division"].eq(division)
                        & workers["business_unit"].eq(business_unit)
                        & workers["hire_date"].le(point_in_time)
                        & (workers["term_date"].isna() | workers["term_date"].gt(point_in_time))
                    ]
                    actual_headcount = len(group)
                    if (division == "Civilian" and quarter_end == latest_quarter_end):
                        actual_to_budget = 0.94
                    elif quarter_end == latest_quarter_end:
                        actual_to_budget = float(np.clip(1.0 + (sum(map(ord, business_unit)) % 5 - 2) * 0.005, 0.99, 1.01))
                    else:
                        actual_to_budget = float(
                            np.clip(1.0 + ((year + quarter + len(business_unit)) % 5 - 2) * 0.004, 0.99, 1.01)
                        )
                    budget_headcount = max(1.0, actual_headcount / actual_to_budget)
                    avg_salary = float(group["base_salary"].mean()) if actual_headcount else 80000.0
                    if quarter_end > today:
                        years_forward = (quarter_end - today).days / 365.25
                        budget_headcount *= 1.0 + min(years_forward * 0.025, 0.08)
                        avg_salary *= 1.0 + min(years_forward * 0.03, 0.10)
                    rows.append(
                        {
                            "division": division,
                            "business_unit": business_unit,
                            "fiscal_year": f"FY{year % 100:02d}",
                            "fiscal_quarter": f"Q{quarter}",
                            "headcount_budget": round(budget_headcount, 2),
                            "labor_budget_usd": round(budget_headcount * avg_salary * 1.30, 2),
                        }
                    )
    return pd.DataFrame(rows)


def write_frame(table_name: str, frame: pd.DataFrame) -> None:
    for column in frame.columns:
        if frame[column].dtype == "object" and any(
            isinstance(value, (datetime, pd.Timestamp)) for value in frame[column].dropna().head(10)
        ):
            frame[column] = pd.to_datetime(frame[column], utc=True)
    frame.to_csv(OUT_DIR / f"{table_name}.csv", index=False, date_format="%Y-%m-%dT%H:%M:%S%z")
    frame.to_parquet(OUT_DIR / f"{table_name}.parquet", index=False)


def generate(today: date | None = None) -> None:
    today = today or date.today()
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FINANCE_FILE.parent.mkdir(parents=True, exist_ok=True)

    workers = make_workers(rng, today)
    events = make_worker_events(rng, workers, today)
    opportunities = make_opportunities(rng, today)
    staffing_requests = make_staffing_requests(rng, opportunities, workers, today)
    courses = make_courses()
    training_completions = make_training_completions(rng, workers, courses, today)
    entitlements = make_entitlements()
    budget = make_budget(workers, today)

    tables = {
        "workday.workers": workers,
        "workday.worker_events": events,
        "salesforce.opportunities": opportunities,
        "salesforce.staffing_requests": staffing_requests,
        "oracle_lms.courses": courses,
        "oracle_lms.training_completions": training_completions,
        "security.entitlements": entitlements,
    }
    for table_name, frame in tables.items():
        write_frame(table_name, frame)
        print(f"{table_name}: {len(frame):,} rows")
    budget.to_excel(FINANCE_FILE, index=False, sheet_name="Headcount Budget")
    print(f"finance budget: {len(budget):,} rows -> {FINANCE_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        help="override the run date (YYYY-MM-DD); normally uses the system date",
    )
    args = parser.parse_args()
    generate(args.today)


if __name__ == "__main__":
    main()
