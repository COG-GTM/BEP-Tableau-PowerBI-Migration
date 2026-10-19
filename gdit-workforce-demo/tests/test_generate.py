from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from data.generate import _assign_filled_workers


def test_filled_workers_are_historically_qualified_and_leave_open_candidates():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W002", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W003", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W004", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), date(2026, 8, 15)),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Software Engineering",
            "clearance_required": "TS/SCI",
            "status": "Filled",
            "filled_date": date(2026, 8, 20),
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Software Engineering",
            "clearance_required": "TS/SCI",
            "status": "Filled",
            "filled_date": date(2026, 9, 1),
        },
        {
            "req_id": "REQ000003",
            "division": "Defense",
            "job_family": "Software Engineering",
            "clearance_required": "TS/SCI",
            "status": "Open",
            "filled_date": None,
        },
    ]

    _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)

    filled = [row for row in rows if row["status"] == "Filled"]
    assignments = [row["filled_worker_id"] for row in filled]
    assert all(assignments)
    assert assignments[0] != assignments[1]

    worker_by_id = workers.set_index("worker_id")
    ranks = {"None": 0, "Public Trust": 1, "Secret": 2, "TS": 3, "TS/SCI": 4}
    for row in filled:
        worker = worker_by_id.loc[row["filled_worker_id"]]
        assert worker["division"] == row["division"]
        assert worker["job_family"] == row["job_family"]
        assert ranks[worker["clearance_level"]] >= ranks[row["clearance_required"]]
        assert worker["hire_date"] <= row["filled_date"]
        assert pd.isna(worker["term_date"]) or worker["term_date"] > row["filled_date"]

    recent_cutoff = today - timedelta(days=90)
    open_row = next(row for row in rows if row["status"] == "Open")
    recently_filled = {
        row["filled_worker_id"]
        for row in filled
        if row["filled_date"] >= recent_cutoff
    }
    open_candidates = workers.loc[
        workers["division"].eq(open_row["division"])
        & workers["job_family"].eq(open_row["job_family"])
        & workers["hire_date"].le(today)
        & (workers["term_date"].isna() | workers["term_date"].gt(today))
        & workers["clearance_level"].map(ranks).ge(ranks[open_row["clearance_required"]])
        & ~workers["worker_id"].isin(recently_filled)
    ]
    assert not open_candidates.empty


def test_filled_worker_reuse_falls_back_when_no_nonrecent_candidate_exists():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2020, 1, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": f"REQ{i:06d}",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "filled_date": date(2026, 9, day),
        }
        for i, day in enumerate((1, 2), start=1)
    ]

    _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)

    assert [row["filled_worker_id"] for row in rows] == ["W001", "W001"]


def test_filled_date_moves_to_first_date_with_an_active_qualified_worker():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2021, 3, 5), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2021, 2, 15),
            "filled_date": date(2021, 3, 1),
        }
    ]

    shifted_dates, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["filled_date"] == date(2021, 3, 5)
    assert rows[0]["filled_worker_id"] == "W001"
    assert (shifted_dates, changed_families) == (1, 0)


def test_filled_date_shift_does_not_precede_request_opened_date():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2021, 3, 5), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2021, 3, 10),
            "filled_date": date(2021, 3, 1),
        }
    ]

    shifted_dates, _ = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["filled_date"] == date(2021, 3, 10)
    assert shifted_dates == 1


def test_filled_request_uses_family_with_most_candidates_when_original_has_none():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Systems Engineering", "TS", date(2020, 1, 1), None),
            ("W002", "Defense", "Systems Engineering", "TS", date(2020, 1, 1), None),
            ("W003", "Defense", "Help Desk", "TS", date(2020, 1, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2021, 3, 10),
            "filled_date": date(2021, 3, 1),
        }
    ]

    shifted_dates, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["job_family"] == "Systems Engineering"
    assert rows[0]["filled_worker_id"] in {"W001", "W002"}
    assert rows[0]["filled_date"] == date(2021, 3, 10)
    assert (shifted_dates, changed_families) == (1, 1)


def test_filled_request_prefers_earliest_alternate_family_date():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Help Desk", "TS", date(2020, 1, 1), None),
            ("W002", "Defense", "Systems Engineering", "TS", date(2021, 4, 1), None),
            ("W003", "Defense", "Systems Engineering", "TS", date(2021, 4, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2021, 2, 15),
            "filled_date": date(2021, 3, 1),
        }
    ]

    shifted_dates, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["job_family"] == "Help Desk"
    assert rows[0]["filled_date"] == date(2021, 3, 1)
    assert rows[0]["filled_worker_id"] == "W001"
    assert (shifted_dates, changed_families) == (0, 1)


def test_recent_filled_fallback_retries_after_open_candidate_reservation():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Help Desk", "TS", date(2020, 1, 1), None),
            ("W002", "Defense", "Systems Engineering", "TS", date(2026, 10, 2), None),
            ("W003", "Defense", "Systems Engineering", "TS", date(2026, 10, 2), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2026, 9, 30),
            "filled_date": date(2026, 10, 1),
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Help Desk",
            "clearance_required": "TS",
            "status": "Open",
            "opened_date": date(2026, 10, 1),
            "filled_date": None,
        },
    ]

    shifted_dates, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["job_family"] == "Systems Engineering"
    assert rows[0]["filled_date"] == date(2026, 10, 2)
    assert rows[0]["filled_worker_id"] in {"W002", "W003"}
    assert rows[1]["filled_worker_id"] is None
    assert (shifted_dates, changed_families) == (1, 1)


def test_recent_fill_still_fails_if_it_would_exhaust_open_candidates():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2020, 1, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2026, 10, 1),
            "filled_date": date(2026, 10, 10),
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Open",
            "opened_date": date(2026, 10, 1),
            "filled_date": None,
        },
    ]

    with pytest.raises(ValueError, match="without a qualified candidate"):
        _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)


def test_recent_fill_can_reuse_worker_already_unavailable_to_open_requests():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2020, 1, 1), None),
            ("W002", "Defense", "Cyber", "TS", date(2020, 1, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2026, 10, 1),
            "filled_date": date(2026, 10, 10),
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2026, 10, 1),
            "filled_date": date(2026, 10, 12),
        },
        {
            "req_id": "REQ000003",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Open",
            "opened_date": date(2026, 10, 1),
            "filled_date": None,
        },
    ]

    _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)

    assert rows[0]["filled_worker_id"] == rows[1]["filled_worker_id"]


def test_old_fill_can_use_worker_reserved_as_open_candidate():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2020, 1, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2020, 1, 1),
            "filled_date": date(2020, 3, 1),
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Open",
            "opened_date": date(2026, 10, 1),
            "filled_date": None,
        },
    ]

    _, changed_families = _assign_filled_workers(
        rows, workers, np.random.default_rng(2026), today
    )

    assert rows[0]["filled_worker_id"] == "W001"
    assert changed_families == 0


def test_filled_request_without_historically_qualified_worker_fails():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Cyber", "TS", date(2026, 11, 1), None),
        ],
        columns=[
            "worker_id",
            "division",
            "job_family",
            "clearance_level",
            "hire_date",
            "term_date",
        ],
    )
    rows = [
        {
            "req_id": "REQ000001",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS",
            "status": "Filled",
            "opened_date": date(2026, 6, 1),
            "filled_date": date(2026, 7, 1),
        }
    ]

    with pytest.raises(ValueError, match="No qualified worker is active"):
        _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)
