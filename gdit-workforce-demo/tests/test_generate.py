from datetime import date

import numpy as np
import pandas as pd

from data.generate import _assign_filled_workers


def test_filled_workers_are_qualified_distinct_and_leave_open_candidates():
    today = date(2026, 10, 19)
    workers = pd.DataFrame(
        [
            ("W001", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W002", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W003", "Defense", "Software Engineering", "TS", date(2020, 1, 1), None),
            ("W004", "Defense", "Systems Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W005", "Intelligence", "Software Engineering", "TS/SCI", date(2020, 1, 1), None),
            ("W006", "Defense", "Software Engineering", "TS/SCI", date(2020, 1, 1), today),
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
        },
        {
            "req_id": "REQ000002",
            "division": "Defense",
            "job_family": "Software Engineering",
            "clearance_required": "TS",
            "status": "Filled",
        },
        {
            "req_id": "REQ000003",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS/SCI",
            "status": "Filled",
        },
        {
            "req_id": "REQ000004",
            "division": "Defense",
            "job_family": "Software Engineering",
            "clearance_required": "TS/SCI",
            "status": "Open",
        },
        {
            "req_id": "REQ000005",
            "division": "Defense",
            "job_family": "Cyber",
            "clearance_required": "TS/SCI",
            "status": "Open",
        },
    ]

    _assign_filled_workers(rows, workers, np.random.default_rng(2026), today)

    filled = [row for row in rows if row["status"] == "Filled"]
    assignments = [row["filled_worker_id"] for row in filled]
    assert assignments[0] and assignments[1]
    assert assignments[2] is None
    assert len({worker_id for worker_id in assignments if worker_id is not None}) == 2

    worker_by_id = workers.set_index("worker_id")
    ranks = {"None": 0, "Public Trust": 1, "Secret": 2, "TS": 3, "TS/SCI": 4}
    for row in filled:
        worker_id = row["filled_worker_id"]
        if worker_id is None:
            continue
        worker = worker_by_id.loc[worker_id]
        assert worker["division"] == row["division"]
        assert worker["job_family"] == row["job_family"]
        assert ranks[worker["clearance_level"]] >= ranks[row["clearance_required"]]
        assert worker["hire_date"] <= today
        assert pd.isna(worker["term_date"]) or worker["term_date"] > today

    assigned = set(assignments)
    for row in rows:
        if row["status"] != "Open":
            continue
        qualified = workers.loc[
            workers["division"].eq(row["division"])
            & workers["job_family"].eq(row["job_family"])
            & workers["hire_date"].le(today)
            & (workers["term_date"].isna() | workers["term_date"].gt(today))
            & workers["clearance_level"].map(ranks).ge(ranks[row["clearance_required"]])
            & ~workers["worker_id"].isin(assigned)
        ]
        assert not qualified.empty
