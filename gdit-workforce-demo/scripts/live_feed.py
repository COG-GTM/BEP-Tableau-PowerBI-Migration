#!/usr/bin/env python3
"""Write synthetic workforce changes to the live Supabase demo tables."""

from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))

from data.generate import FIRST_NAMES, LAST_NAMES
from load_postgres import connect_supabase


def years_ago(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year - n)
    except ValueError:
        return d.replace(year=d.year - n, day=28)


def insert_worker_event(cursor, worker_id: str, event_type: str, from_value: str | None, to_value: str) -> None:
    cursor.execute(
        """
        INSERT INTO workday.worker_events
            (event_id, worker_id, event_date, event_type, from_value, to_value)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (f"LIVE-{uuid.uuid4().hex}", worker_id, date.today(), event_type, from_value, to_value),
    )


def termination(cursor, specific: bool = False) -> str:
    family_filter = "AND job_family = 'Software Engineering'" if specific else ""
    cursor.execute(
        f"""
        SELECT worker_id, division, job_family, clearance_level
        FROM workday.workers
        WHERE term_date IS NULL
          AND division = 'Defense'
          AND clearance_level = 'TS/SCI'
          {family_filter}
        ORDER BY worker_id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("No active Defense TS/SCI worker is available for a termination.")
    worker_id, division, family, clearance = row
    cursor.execute(
        """
        UPDATE workday.workers
        SET term_date = %s, term_type = 'Voluntary', last_updated = now()
        WHERE worker_id = %s
        """,
        (date.today(), worker_id),
    )
    insert_worker_event(
        cursor,
        worker_id,
        "Termination",
        f"{division}; {family}; {clearance}",
        "Voluntary",
    )
    return f"Termination: {worker_id} ({division}, {clearance} {family})"


def hire(cursor) -> str:
    cursor.execute(
        """
        SELECT worker_id, gender, education_level, division, business_unit,
               cost_center, location_state, location_city, remote_flag,
               job_family, job_title, job_level, manager_id, clearance_level,
               base_salary, performance_rating
        FROM workday.workers
        WHERE term_date IS NULL
        ORDER BY random()
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    )
    template = cursor.fetchone()
    if template is None:
        raise RuntimeError("No active worker is available as a hire template.")
    (
        source_worker_id,
        gender,
        education_level,
        division,
        business_unit,
        cost_center,
        location_state,
        location_city,
        remote_flag,
        family,
        job_title,
        job_level,
        manager_id,
        clearance_level,
        base_salary,
        performance_rating,
    ) = template
    today = date.today()
    earliest_birthdate = years_ago(today, 60)
    latest_birthdate = years_ago(today, 22)
    birthdate = earliest_birthdate + timedelta(
        days=random.randint(0, (latest_birthdate - earliest_birthdate).days)
    )
    new_worker_id = f"W-LIVE-{uuid.uuid4().hex}"
    cursor.execute(
        """
        INSERT INTO workday.workers
            (worker_id, first_name, last_name, gender, birthdate, education_level,
             hire_date, term_date, term_type, division, business_unit, cost_center,
             location_state, location_city, remote_flag, job_family, job_title,
             job_level, manager_id, clearance_level, base_salary, performance_rating,
             last_updated)
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, NULL, NULL, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, now()
        )
        """,
        (
            new_worker_id,
            random.choice(FIRST_NAMES),
            random.choice(LAST_NAMES),
            gender,
            birthdate,
            education_level,
            today,
            division,
            business_unit,
            cost_center,
            location_state,
            location_city,
            remote_flag,
            family,
            job_title,
            job_level,
            manager_id,
            clearance_level,
            round(float(base_salary) * random.uniform(0.9, 1.1), 2),
            performance_rating,
        ),
    )
    insert_worker_event(cursor, new_worker_id, "Hire", "New worker", division)
    return f"Hire: {new_worker_id} from {source_worker_id} ({division}, {family})"


def fill_staffing_request(cursor, request_id: str | None = None) -> str | None:
    cursor.execute(
        """
        SELECT req_id, opp_id, division, job_family, clearance_required,
               headcount, opened_date, needed_by
        FROM salesforce.staffing_requests
        WHERE status = 'Open' AND (%s::text IS NULL OR req_id = %s)
        ORDER BY req_id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """,
        (request_id, request_id),
    )
    request = cursor.fetchone()
    if request is None:
        return None
    (
        req_id,
        opp_id,
        division,
        job_family,
        clearance_required,
        headcount,
        opened_date,
        needed_by,
    ) = request
    cursor.execute(
        """
        SELECT worker_id
        FROM workday.workers
        WHERE division = %s
          AND job_family = %s
          AND hire_date <= current_date
          AND (term_date IS NULL OR term_date > current_date)
          AND CASE clearance_level
                WHEN 'None' THEN 0
                WHEN 'Public Trust' THEN 1
                WHEN 'Secret' THEN 2
                WHEN 'TS' THEN 3
                WHEN 'TS/SCI' THEN 4
                ELSE -1
              END >= CASE %s
                WHEN 'None' THEN 0
                WHEN 'Public Trust' THEN 1
                WHEN 'Secret' THEN 2
                WHEN 'TS' THEN 3
                WHEN 'TS/SCI' THEN 4
                ELSE 99
              END
        ORDER BY worker_id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """,
        (division, job_family, clearance_required),
    )
    worker = cursor.fetchone()
    if worker is None:
        return None
    if headcount <= 1:
        cursor.execute(
            """
            UPDATE salesforce.staffing_requests
            SET status = 'Filled', filled_date = %s, filled_worker_id = %s
            WHERE req_id = %s
            """,
            (date.today(), worker[0], req_id),
        )
        return f"Staffing request filled: {req_id}"

    cursor.execute(
        "UPDATE salesforce.staffing_requests SET headcount = headcount - 1 WHERE req_id = %s",
        (req_id,),
    )
    filled_req_id = f"LIVE-REQ-{uuid.uuid4().hex}"
    cursor.execute(
        """
        INSERT INTO salesforce.staffing_requests
            (req_id, opp_id, division, job_family, clearance_required, headcount,
             opened_date, needed_by, status, filled_date, filled_worker_id)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s, 'Filled', %s, %s)
        """,
        (
            filled_req_id,
            opp_id,
            division,
            job_family,
            clearance_required,
            opened_date,
            needed_by,
            date.today(),
            worker[0],
        ),
    )
    return f"Staffing request filled: {req_id} (split {filled_req_id})"


def update_staffing_request(cursor) -> str | None:
    if random.random() < 0.5:
        return fill_staffing_request(cursor)

    cursor.execute(
        """
        SELECT opp_id, division
        FROM salesforce.staffing_requests
        ORDER BY req_id
        LIMIT 1
        """
    )
    source = cursor.fetchone()
    if source is None:
        return None
    req_id = f"LIVE-REQ-{uuid.uuid4().hex}"
    cursor.execute(
        """
        INSERT INTO salesforce.staffing_requests
            (req_id, opp_id, division, job_family, clearance_required, headcount,
             opened_date, needed_by, status, filled_date, filled_worker_id)
        VALUES (%s, %s, %s, %s, 'Secret', %s, %s, %s, 'Open', NULL, NULL)
        """,
        (
            req_id,
            source[0],
            source[1],
            random.choice(
                [
                    "Software Engineering",
                    "Cyber",
                    "Data & AI",
                    "Program Management",
                    "Systems Engineering",
                ]
            ),
            random.randint(1, 4),
            date.today(),
            date.today() + timedelta(days=random.randint(30, 120)),
        ),
    )
    return f"Staffing request opened: {req_id}"


def run_batch(connection, once: bool) -> list[str]:
    messages = []
    with connection.cursor() as cursor:
        if once:
            messages.append(termination(cursor, specific=True))
        else:
            for _ in range(random.randint(1, 3)):
                messages.append(
                    termination(cursor)
                    if random.random() < 0.35
                    else hire(cursor)
                )
            if random.random() < 0.5:
                staffing_message = update_staffing_request(cursor)
                if staffing_message:
                    messages.append(staffing_message)
    connection.commit()
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between feed batches")
    parser.add_argument("--once", action="store_true", help="write one visible Defense termination and exit")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    connection = connect_supabase("feed_writer")
    try:
        while True:
            for message in run_batch(connection, args.once):
                print(message, flush=True)
            if args.once:
                break
            time.sleep(args.interval)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
