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

WORKER_COUNT = 16_500
TARGET_PROFILE_SHARE = 0.24
TARGET_LATEST_VOLUNTARY_HAZARD = 0.45
OPENING_COHORT_HIRE_WEIGHT = 8.0
PLANTED_STAFFING_REQUESTS = 60
DIVISION_TERM_HAZARDS = {
    "Defense": {"Voluntary": 0.10, "Involuntary": 0.025, "Retirement": 0.01},
    "Intelligence": {"Voluntary": 0.095, "Involuntary": 0.025, "Retirement": 0.01},
    "Civilian": {"Voluntary": 0.09, "Involuntary": 0.03, "Retirement": 0.01},
    "Health": {"Voluntary": 0.105, "Involuntary": 0.02, "Retirement": 0.01},
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
FIRST_NAMES = ["Avery", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn", "Cameron", "Alex"]
LAST_NAMES = ["Carter", "Reed", "Brooks", "Hayes", "Morgan", "Bennett", "Price", "Foster", "Perry", "Ross"]
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
CLEARANCE_RANK = {
    "None": 0,
    "Public Trust": 1,
    "Secret": 2,
    "TS": 3,
    "TS/SCI": 4,
}
DIVISION_WEIGHTS = [0.35, 0.25, 0.25, 0.15]
DIVISION_NAMES = ["Defense", "Intelligence", "Civilian", "Health"]


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


def draw_termination_history(
    rng: np.random.Generator,
    hire_dates: np.ndarray,
    divisions: np.ndarray,
    focus_mask: np.ndarray,
    today: date,
) -> tuple[list[date | None], list[str | None]]:
    worker_count = len(hire_dates)
    term_dates: list[date | None] = [None] * worker_count
    term_types: list[str | None] = [None] * worker_count
    terminated = np.zeros(worker_count, dtype=bool)
    annual_hazards = {
        event_type: np.array(
            [DIVISION_TERM_HAZARDS[str(division)][event_type] for division in divisions]
        )
        for event_type in ("Voluntary", "Involuntary", "Retirement")
    }
    current_month = today.replace(day=1)
    latest_start = add_months(current_month, -3)
    latest_end = current_month - timedelta(days=1)

    month_start = HISTORY_START
    while month_start <= today:
        month_end = min(add_months(month_start, 1) - timedelta(days=1), today)
        active_indices = np.flatnonzero(
            np.fromiter(
                (hire_date <= month_end for hire_date in hire_dates),
                dtype=bool,
                count=worker_count,
            )
            & ~terminated
        )
        if active_indices.size:
            exposure_starts = [
                max(hire_dates[index], month_start) for index in active_indices
            ]
            exposure_years = np.array(
                [
                    (month_end - exposure_start).days + 1
                    for exposure_start in exposure_starts
                ],
                dtype=float,
            ) / 365.25
            voluntary_hazards = annual_hazards["Voluntary"][active_indices].copy()
            if month_start >= latest_start and month_end <= latest_end:
                target_workers = focus_mask[active_indices]
                voluntary_hazards[target_workers] = TARGET_LATEST_VOLUNTARY_HAZARD
            total_hazards = (
                voluntary_hazards
                + annual_hazards["Involuntary"][active_indices]
                + annual_hazards["Retirement"][active_indices]
            )
            event_probability = -np.expm1(-total_hazards * exposure_years)
            event_mask = rng.random(active_indices.size) < event_probability
            event_indices = active_indices[event_mask]
            if event_indices.size:
                event_hazards = total_hazards[event_mask]
                cause_draws = rng.random(event_indices.size) * event_hazards
                voluntary_for_events = voluntary_hazards[event_mask]
                involuntary_for_events = annual_hazards["Involuntary"][event_indices]
                event_types = np.where(
                    cause_draws < voluntary_for_events,
                    "Voluntary",
                    np.where(
                        cause_draws < voluntary_for_events + involuntary_for_events,
                        "Involuntary",
                        "Retirement",
                    ),
                )
                event_starts = np.asarray(exposure_starts, dtype=object)[event_mask]
                for index, event_type, event_start in zip(
                    event_indices, event_types, event_starts
                ):
                    term_dates[index] = random_day(rng, event_start, month_end)
                    term_types[index] = str(event_type)
                terminated[event_indices] = True
        month_start = add_months(month_start, 1)

    return term_dates, term_types


def make_workers(rng: np.random.Generator, today: date) -> pd.DataFrame:
    divisions = rng.choice(
        DIVISION_NAMES, size=WORKER_COUNT, p=DIVISION_WEIGHTS
    )
    focus_mask = (divisions == "Defense") & (
        rng.random(WORKER_COUNT) < TARGET_PROFILE_SHARE
    )
    hire_calendar = [
        HISTORY_START + timedelta(days=offset)
        for offset in range((today - HISTORY_START).days + 1)
    ]
    opening_cohort_end = add_months(HISTORY_START, 12)
    hire_weights = np.array(
        [
            (OPENING_COHORT_HIRE_WEIGHT if hire_day < opening_cohort_end else 1.0)
            * (1.35 if hire_day.month in (1, 2, 3, 7, 8, 9) else 1.0)
            for hire_day in hire_calendar
        ]
    )
    hire_dates = rng.choice(
        np.asarray(hire_calendar, dtype=object),
        size=WORKER_COUNT,
        p=hire_weights / hire_weights.sum(),
    )
    term_dates, term_types = draw_termination_history(
        np.random.default_rng(SEED + 1),
        hire_dates,
        divisions,
        focus_mask,
        today,
    )
    worker_rows = []

    for index, division in enumerate(divisions):
        worker_id = f"W{index + 1:06d}"
        is_focus = bool(focus_mask[index])
        if is_focus:
            family = str(rng.choice(["Software Engineering", "Cyber"], p=[0.55, 0.45]))
            level = int(rng.choice([2, 3]))
            clearance = "TS/SCI"
            state = str(rng.choice(["VA", "MD"]))
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

        hire_date = hire_dates[index]
        term_date = term_dates[index]
        term_type = term_types[index]
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
                "first_name": str(rng.choice(FIRST_NAMES)),
                "last_name": str(rng.choice(LAST_NAMES)),
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


def _assign_filled_workers(
    rows: list[dict],
    workers: pd.DataFrame,
    rng: np.random.Generator,
    today: date,
) -> tuple[int, int]:
    workers_by_family: dict[
        tuple[str, str], list[tuple[str, int, date, date | None]]
    ] = {}
    for worker in workers.itertuples(index=False):
        key = (str(worker.division), str(worker.job_family))
        term_date = None if pd.isna(worker.term_date) else worker.term_date
        workers_by_family.setdefault(key, []).append(
            (
                str(worker.worker_id),
                CLEARANCE_RANK.get(str(worker.clearance_level), -1),
                worker.hire_date,
                term_date,
            )
        )
    for candidates in workers_by_family.values():
        candidates.sort()

    qualified_cache: dict[tuple[str, str, str, date], list[str]] = {}

    def candidates_for(key: tuple[str, str, str], active_date: date) -> list[str]:
        cache_key = (*key, active_date)
        if cache_key not in qualified_cache:
            division, job_family, clearance_required = key
            required_rank = CLEARANCE_RANK.get(clearance_required, 99)
            qualified_cache[cache_key] = [
                worker_id
                for worker_id, clearance_rank, hire_date, term_date in workers_by_family.get(
                    (division, job_family), []
                )
                if clearance_rank >= required_rank
                and hire_date <= active_date
                and (term_date is None or term_date > active_date)
            ]
        return qualified_cache[cache_key]

    def request_key(row: dict) -> tuple[str, str, str]:
        return (
            str(row["division"]),
            str(row["job_family"]),
            str(row["clearance_required"]),
        )

    def alternate_families(
        key: tuple[str, str, str], start_date: date
    ) -> list[tuple[str, date]]:
        division, _, clearance_required = key
        alternatives = []
        for family in JOB_FAMILIES:
            family_key = (division, family, clearance_required)
            active_date = earliest_active_date(family_key, start_date)
            if active_date is None:
                continue
            candidates = candidates_for(family_key, active_date)
            if candidates:
                alternatives.append((family, active_date, candidates))
        return [
            (family, active_date)
            for family, active_date, _ in sorted(
                alternatives, key=lambda item: (item[1], -len(item[2]))
            )
        ]

    def earliest_active_date(
        key: tuple[str, str, str], start_date: date
    ) -> date | None:
        division, job_family, clearance_required = key
        required_rank = CLEARANCE_RANK.get(clearance_required, 99)
        active_dates = []
        for _, clearance_rank, hire_date, term_date in workers_by_family.get(
            (division, job_family), []
        ):
            if clearance_rank < required_rank:
                continue
            active_date = max(start_date, hire_date)
            if (
                active_date <= today
                and (term_date is None or term_date > active_date)
            ):
                active_dates.append(active_date)
        return min(active_dates) if active_dates else None

    for row in rows:
        row["filled_worker_id"] = None
        if row["status"] != "Open":
            continue
        key = request_key(row)
        if candidates_for(key, today):
            continue
        alternatives = alternate_families(key, today)
        if not alternatives:
            raise ValueError(
                f"No active qualified workers are available for open request {row['req_id']}"
            )
        row["job_family"] = alternatives[0][0]

    open_keys = {request_key(row) for row in rows if row["status"] == "Open"}
    remaining_candidates = {
        key: len(candidates_for(key, today))
        for key in open_keys
    }
    open_keys_by_worker: dict[str, list[tuple[str, str, str]]] = {}
    for key in open_keys:
        for worker_id in candidates_for(key, today):
            open_keys_by_worker.setdefault(worker_id, []).append(key)

    filled_rows = [row for row in rows if row["status"] == "Filled"]
    original_filled_dates = {}
    original_filled_families = {}
    fallbacks: dict[str, list[tuple[str, date]]] = {}
    for row in filled_rows:
        if row.get("filled_date") is None or pd.isna(row["filled_date"]):
            raise ValueError(f"Filled request {row['req_id']} has no filled_date")
        original_filled_dates[row["req_id"]] = row["filled_date"]
        original_filled_families[row["req_id"]] = row["job_family"]
        key = request_key(row)
        original_date = row["filled_date"]
        if candidates_for(key, original_date):
            continue

        opened_date = row.get("opened_date")
        if opened_date is None or pd.isna(opened_date):
            opened_date = original_date
        start_date = max(original_date, opened_date)
        shifted_date = earliest_active_date(key, start_date)
        if shifted_date is not None:
            row["filled_date"] = shifted_date
            continue

        alternatives = alternate_families(key, start_date)
        if not alternatives:
            raise ValueError(
                f"No qualified worker is active for filled request {row['req_id']} "
                f"on or after {start_date}; no alternate family has qualified workers"
            )
        fallbacks[row["req_id"]] = alternatives
        row["job_family"], row["filled_date"] = alternatives[0]

    filled_rows.sort(
        key=lambda row: (
            row["filled_date"],
            len(candidates_for(request_key(row), row["filled_date"])),
            str(row["req_id"]),
        )
    )
    assignment_dates: dict[str, list[date]] = {}
    recent_open_assignments: set[str] = set()
    recent_cutoff = today - timedelta(days=90)

    def safe_workers(qualified: list[str], filled_date: date) -> list[str]:
        safe_for_open = [
            worker_id
            for worker_id in qualified
            if worker_id in recent_open_assignments
            or all(
                remaining_candidates[key] > 1
                for key in open_keys_by_worker.get(worker_id, [])
            )
        ]
        if safe_for_open:
            return safe_for_open
        if recent_cutoff <= filled_date <= today:
            return []
        return qualified

    for row in filled_rows:
        filled_date = row["filled_date"]
        fallback_options = fallbacks.get(row["req_id"])
        if fallback_options is not None:
            safe_for_open = []
            for family, candidate_date in fallback_options:
                key = (
                    str(row["division"]),
                    family,
                    str(row["clearance_required"]),
                )
                qualified = candidates_for(key, candidate_date)
                safe_for_open = safe_workers(qualified, candidate_date)
                if safe_for_open:
                    row["job_family"] = family
                    row["filled_date"] = candidate_date
                    filled_date = candidate_date
                    break
            if not safe_for_open:
                raise ValueError(
                    f"Filling request {row['req_id']} would leave an open request "
                    "without a qualified candidate"
                )
        else:
            key = request_key(row)
            qualified = candidates_for(key, filled_date)
            if not qualified:
                raise ValueError(
                    f"No qualified worker is active for filled request {row['req_id']} "
                    f"on {filled_date}"
                )
            safe_for_open = safe_workers(qualified, filled_date)
            if not safe_for_open:
                raise ValueError(
                    f"Filling request {row['req_id']} would leave an open request "
                    "without a qualified candidate"
                )

        affects_open_candidates = recent_cutoff <= filled_date <= today

        assignment_cutoff = filled_date - timedelta(days=90)
        preferred = [
            worker_id
            for worker_id in safe_for_open
            if not any(
                assignment_cutoff <= assigned_date <= filled_date
                for assigned_date in assignment_dates.get(worker_id, [])
            )
        ]
        worker_id = str(rng.choice(preferred or safe_for_open))
        row["filled_worker_id"] = worker_id
        assignment_dates.setdefault(worker_id, []).append(filled_date)
        if affects_open_candidates and worker_id not in recent_open_assignments:
            recent_open_assignments.add(worker_id)
            for key in open_keys_by_worker.get(worker_id, []):
                remaining_candidates[key] -= 1

    if any(count < 1 for count in remaining_candidates.values()):
        raise AssertionError("Filled worker assignments exhausted an open request's candidates")
    if any(row["filled_worker_id"] is None for row in filled_rows):
        raise AssertionError("Filled requests must have a qualified worker")

    return (
        sum(row["filled_date"] != original_filled_dates[row["req_id"]] for row in filled_rows),
        sum(
            row["job_family"] != original_filled_families[row["req_id"]]
            for row in filled_rows
        ),
    )


def make_staffing_requests(
    rng: np.random.Generator,
    opportunities: pd.DataFrame,
    workers: pd.DataFrame,
    today: date,
) -> pd.DataFrame:
    target_opps = opportunities.loc[
        opportunities["account_name"].isin(["Army", "Navy"])
        & opportunities["stage"].eq("Won")
        & opportunities["required_clearance"].isin(["TS", "TS/SCI"]),
        "opp_id",
    ].to_numpy()
    planted_request_count = int(rng.poisson(PLANTED_STAFFING_REQUESTS))
    planted_indices = set(
        rng.choice(9000, size=planted_request_count, replace=False).tolist()
    )
    active_workers = workers.loc[workers["term_date"].isna()]
    worker_ids_by_division = {
        division: group["worker_id"].to_numpy()
        for division, group in active_workers.groupby("division")
    }
    opp_lookup = opportunities.set_index("opp_id")
    rows = []
    for index in range(9000):
        is_target = index in planted_indices
        opp_id = str(rng.choice(target_opps)) if is_target else str(
            rng.choice(opportunities["opp_id"].to_numpy())
        )
        opp = opp_lookup.loc[opp_id]
        division = str(opp["division"])
        if is_target:
            job_family = str(
                rng.choice(
                    JOB_FAMILIES,
                    p=[0.45, 0.40, 0.05, 0.04, 0.03, 0.02, 0.01],
                )
            )
            status = "Open"
            needed_by = today - timedelta(days=int(rng.integers(1, 61)))
            opened_date = random_day(
                rng, max(HISTORY_START, needed_by - timedelta(days=90)), needed_by
            )
            headcount = int(rng.integers(2, 7))
        else:
            job_family = str(rng.choice(JOB_FAMILIES))
            opened_date = random_day(rng, HISTORY_START, today)
            if opened_date < today - timedelta(days=150):
                status = str(
                    rng.choice(
                        ["Open", "Filled", "Cancelled"],
                        p=[0.015, 0.685, 0.30],
                    )
                )
            else:
                status = str(
                    rng.choice(
                        ["Open", "Filled", "Cancelled"],
                        p=[0.45, 0.43, 0.12],
                    )
                )
            if status == "Open" and opened_date < today and rng.random() < 0.02:
                needed_by = random_day(
                    rng,
                    max(opened_date, today - timedelta(days=60)),
                    today - timedelta(days=1),
                )
            elif status == "Open":
                needed_by = random_day(
                    rng, today + timedelta(days=1), today + timedelta(days=150)
                )
            else:
                needed_by = random_day(
                    rng, opened_date, today + timedelta(days=150)
                )
            headcount = int(rng.integers(1, 9))
        filled_date = None
        if status == "Filled":
            filled_date = random_day(rng, opened_date, today)
            rng.choice(worker_ids_by_division[division])
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
                "filled_worker_id": None,
            }
        )

    shifted_dates, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(SEED), today
    )
    print(
        f"staffing allocation adjustments: {shifted_dates} filled dates shifted, "
        f"{changed_families} job families changed"
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


def make_budget(
    rng: np.random.Generator, workers: pd.DataFrame, today: date
) -> pd.DataFrame:
    rows = []
    current_quarter_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    latest_quarter_end = current_quarter_start - timedelta(days=1)
    non_civilian_divisions = [
        division for division in BUSINESS_UNITS if division != "Civilian"
    ]
    for year in range(2022, 2028):
        for quarter in range(1, 5):
            quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
            quarter_end = add_months(quarter_start, 3) - timedelta(days=1)
            point_in_time = min(quarter_end, today)
            variance_signs = rng.choice([-1, 1], size=len(non_civilian_divisions))
            if np.all(variance_signs == variance_signs[0]):
                variance_signs[int(rng.integers(0, len(variance_signs)))] *= -1
            division_variances = {
                division: int(sign)
                * float(rng.uniform(0.005, 0.02))
                for division, sign in zip(non_civilian_divisions, variance_signs)
            }
            if quarter_end == latest_quarter_end:
                division_variances["Civilian"] = -0.06
            else:
                division_variances["Civilian"] = (
                    int(rng.choice([-1, 1])) * float(rng.uniform(0.005, 0.02))
                )
            for division, business_units in BUSINESS_UNITS.items():
                for business_unit in business_units:
                    group = workers.loc[
                        workers["division"].eq(division)
                        & workers["business_unit"].eq(business_unit)
                        & workers["hire_date"].le(point_in_time)
                        & (workers["term_date"].isna() | workers["term_date"].gt(point_in_time))
                    ]
                    actual_headcount = len(group)
                    actual_to_budget = 1.0 + division_variances[division]
                    budget_headcount = max(5, 5 * round(max(1, actual_headcount) / actual_to_budget / 5))
                    avg_salary = float(group["base_salary"].mean()) if actual_headcount else 80000.0
                    if quarter_end > today:
                        years_forward = (quarter_end - today).days / 365.25
                        budget_headcount *= 1.0 + min(years_forward * 0.025, 0.08)
                        avg_salary *= 1.0 + min(years_forward * 0.03, 0.10)
                        budget_headcount = max(5, 5 * round(budget_headcount / 5))
                    rows.append(
                        {
                            "division": division,
                            "business_unit": business_unit,
                            "fiscal_year": f"FY{year % 100:02d}",
                            "fiscal_quarter": f"Q{quarter}",
                            "headcount_budget": int(budget_headcount),
                            "labor_budget_usd": int(
                                round(budget_headcount * avg_salary * 1.30 / 1000) * 1000
                            ),
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
    budget = make_budget(rng, workers, today)

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
