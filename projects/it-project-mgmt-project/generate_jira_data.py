#!/usr/bin/env python3
"""
Generate mock JIRA-style dataset for IT Project Management dashboard demo.

Produces ~300 rows across ~6 sprints with realistic patterns:
- Issue types: Epic, Story, Task, Bug, Sub-task
- Velocity patterns that vary by sprint (ramping up then stabilizing)
- Realistic cycle times and lead times
- Sprint scope changes (stories added mid-sprint)

Usage:
    python generate_jira_data.py
"""

import csv
import random
import os
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)

# --- Configuration ---
NUM_ROWS = 300
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jira_issues.csv")

# Sprint definitions (6 sprints, 2-week cadence)
SPRINTS = [
    {
        "name": "Sprint 1 - Foundation",
        "start": datetime(2025, 10, 1),
        "end": datetime(2025, 10, 14),
        "velocity_target": 30,
    },
    {
        "name": "Sprint 2 - Core Features",
        "start": datetime(2025, 10, 15),
        "end": datetime(2025, 10, 28),
        "velocity_target": 38,
    },
    {
        "name": "Sprint 3 - Integration",
        "start": datetime(2025, 10, 29),
        "end": datetime(2025, 11, 11),
        "velocity_target": 42,
    },
    {
        "name": "Sprint 4 - Testing & QA",
        "start": datetime(2025, 11, 12),
        "end": datetime(2025, 11, 25),
        "velocity_target": 45,
    },
    {
        "name": "Sprint 5 - Hardening",
        "start": datetime(2025, 11, 26),
        "end": datetime(2025, 12, 9),
        "velocity_target": 40,
    },
    {
        "name": "Sprint 6 - Release Prep",
        "start": datetime(2025, 12, 10),
        "end": datetime(2025, 12, 23),
        "velocity_target": 35,
    },
]

# Issue type distribution
ISSUE_TYPE_WEIGHTS = {
    "Epic": 0.05,
    "Story": 0.40,
    "Task": 0.25,
    "Bug": 0.20,
    "Sub-task": 0.10,
}

# Status distribution (varies by sprint position — earlier sprints more Done)
STATUS_WEIGHTS_EARLY = {"To Do": 0.05, "In Progress": 0.05, "In Review": 0.05, "Done": 0.85}
STATUS_WEIGHTS_MID = {"To Do": 0.10, "In Progress": 0.15, "In Review": 0.10, "Done": 0.65}
STATUS_WEIGHTS_LATE = {"To Do": 0.25, "In Progress": 0.25, "In Review": 0.15, "Done": 0.35}

# Priority distribution
PRIORITY_WEIGHTS = {
    "Highest": 0.05,
    "High": 0.15,
    "Medium": 0.45,
    "Low": 0.25,
    "Lowest": 0.10,
}

# Story point values (Fibonacci-ish)
STORY_POINT_VALUES = [1, 2, 3, 5, 8, 13]
STORY_POINT_WEIGHTS = [0.10, 0.20, 0.30, 0.25, 0.10, 0.05]

# Team members
TEAM_MEMBERS = [
    "Alex Thompson",
    "Jordan Rivera",
    "Morgan Chen",
    "Casey Williams",
    "Taylor Kim",
    "Riley Patel",
    "Drew Nakamura",
    "Quinn Fitzgerald",
    "Avery Okafor",
    "Jamie Reeves",
]

# Reporters (includes PMs and stakeholders)
REPORTERS = TEAM_MEMBERS + [
    "Pat Morrison (PM)",
    "Sam Delgado (PO)",
    "Chris Albright (Tech Lead)",
]

# Components
COMPONENTS = [
    "Backend API",
    "Frontend UI",
    "Database",
    "Authentication",
    "Reporting",
    "Infrastructure",
    "Documentation",
    "DevOps",
]

# Labels
LABELS = [
    "security",
    "performance",
    "ux",
    "tech-debt",
    "compliance",
    "fedramp",
    "accessibility",
    "migration",
    "api",
    "data-pipeline",
]

# Epics
EPICS = [
    {"key": "PROJ-1", "summary": "User Authentication & SSO Integration"},
    {"key": "PROJ-2", "summary": "Dashboard Analytics Engine"},
    {"key": "PROJ-3", "summary": "Data Pipeline Migration"},
    {"key": "PROJ-4", "summary": "Reporting Module Overhaul"},
    {"key": "PROJ-5", "summary": "FedRAMP Compliance Hardening"},
    {"key": "PROJ-6", "summary": "Performance Optimization"},
    {"key": "PROJ-7", "summary": "API Gateway Implementation"},
    {"key": "PROJ-8", "summary": "Automated Testing Framework"},
]

# Story/Task/Bug summaries per epic theme
SUMMARIES = {
    "PROJ-1": [
        "Implement SAML 2.0 SSO flow",
        "Add MFA enrollment page",
        "Create session management service",
        "Build user profile settings page",
        "Integrate with Active Directory",
        "Add role-based access control",
        "Implement password policy enforcement",
        "Create login audit trail",
    ],
    "PROJ-2": [
        "Build real-time metrics aggregation",
        "Create chart rendering engine",
        "Implement drill-down navigation",
        "Add export to PDF functionality",
        "Build KPI card component",
        "Create time-series trend analysis",
        "Implement cross-filter interactions",
        "Add dashboard sharing permissions",
    ],
    "PROJ-3": [
        "Migrate ETL jobs to new pipeline",
        "Create data validation framework",
        "Build incremental load processor",
        "Implement change data capture",
        "Create data quality scoring",
        "Build pipeline monitoring dashboard",
        "Implement retry logic for failed jobs",
        "Create data lineage tracker",
    ],
    "PROJ-4": [
        "Redesign report template engine",
        "Add scheduled report delivery",
        "Create custom report builder",
        "Implement report caching layer",
        "Build report permissions model",
        "Add report versioning",
        "Create report parameter UI",
        "Implement A/B report comparison",
    ],
    "PROJ-5": [
        "Implement STIG compliance checks",
        "Add encryption at rest for PII",
        "Create security event logging",
        "Build vulnerability scan integration",
        "Implement secure file upload",
        "Add input sanitization middleware",
        "Create compliance audit report",
        "Implement certificate management",
    ],
    "PROJ-6": [
        "Optimize database query performance",
        "Implement API response caching",
        "Add lazy loading for dashboard widgets",
        "Optimize bundle size and code splitting",
        "Implement connection pooling",
        "Add CDN for static assets",
        "Optimize image compression pipeline",
        "Implement server-side rendering",
    ],
    "PROJ-7": [
        "Design API gateway architecture",
        "Implement rate limiting",
        "Add API versioning strategy",
        "Create API documentation portal",
        "Build API key management",
        "Implement request/response logging",
        "Add circuit breaker pattern",
        "Create API health check endpoints",
    ],
    "PROJ-8": [
        "Set up Cypress E2E test framework",
        "Create unit test coverage baseline",
        "Build integration test harness",
        "Implement visual regression testing",
        "Create performance test suite",
        "Build API contract testing",
        "Implement accessibility testing",
        "Create test data management system",
    ],
}

BUG_SUMMARIES = [
    "Fix null pointer in user session handler",
    "Resolve race condition in data sync",
    "Fix timezone display issue in reports",
    "Correct calculation error in KPI rollup",
    "Fix CSS overflow on mobile dashboard view",
    "Resolve memory leak in WebSocket handler",
    "Fix broken pagination on large datasets",
    "Correct date parsing for EU format inputs",
    "Fix authentication token refresh loop",
    "Resolve CORS policy blocking API calls",
    "Fix chart tooltip positioning on scroll",
    "Correct filter state persistence on navigation",
    "Fix export truncating long field values",
    "Resolve duplicate entries in audit log",
    "Fix slow query on compliance report page",
    "Correct role permission check for admin panel",
    "Fix file upload failing for files over 10MB",
    "Resolve intermittent 502 on dashboard load",
    "Fix search index not updating after data import",
    "Correct bar chart axis label overlap",
]

SUBTASK_PREFIXES = [
    "Write unit tests for",
    "Add error handling to",
    "Document API for",
    "Add logging to",
    "Review and refactor",
    "Add accessibility attributes to",
    "Create Storybook story for",
    "Add input validation to",
]


def random_date_between(start, end):
    """Generate a random date between start and end."""
    delta = end - start
    if delta.days <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta.days))


def get_status_weights(sprint_index):
    """Get status distribution based on sprint position."""
    if sprint_index <= 1:
        return STATUS_WEIGHTS_EARLY
    elif sprint_index <= 3:
        return STATUS_WEIGHTS_MID
    else:
        return STATUS_WEIGHTS_LATE


def generate_issue_key(index):
    """Generate a JIRA-style issue key."""
    return f"PROJ-{index}"


def generate_issues():
    """Generate the full JIRA issues dataset."""
    issue_types = list(ISSUE_TYPE_WEIGHTS.keys())
    issue_type_weights = list(ISSUE_TYPE_WEIGHTS.values())

    priorities = list(PRIORITY_WEIGHTS.keys())
    priority_weights = list(PRIORITY_WEIGHTS.values())

    rows = []
    issue_counter = len(EPICS) + 1  # Start after epic keys

    # First, generate the epics
    for epic in EPICS:
        sprint = random.choice(SPRINTS[:2])  # Epics start in early sprints
        created = random_date_between(
            sprint["start"] - timedelta(days=14), sprint["start"]
        )
        rows.append(
            {
                "Issue_Key": epic["key"],
                "Issue_Type": "Epic",
                "Summary": epic["summary"],
                "Status": "Done" if random.random() < 0.5 else "In Progress",
                "Priority": random.choices(priorities, weights=priority_weights, k=1)[0],
                "Sprint_Name": sprint["name"],
                "Sprint_Start": sprint["start"].strftime("%Y-%m-%d"),
                "Sprint_End": sprint["end"].strftime("%Y-%m-%d"),
                "Story_Points": "",
                "Assignee": random.choice(TEAM_MEMBERS),
                "Reporter": random.choice(REPORTERS),
                "Created_Date": created.strftime("%Y-%m-%d"),
                "Updated_Date": random_date_between(created, datetime(2025, 12, 23)).strftime(
                    "%Y-%m-%d"
                ),
                "Resolved_Date": "",
                "Epic_Key": "",
                "Labels": random.choice(LABELS),
                "Component": random.choice(COMPONENTS),
            }
        )

    # Generate remaining issues distributed across sprints
    issues_per_sprint = (NUM_ROWS - len(EPICS)) // len(SPRINTS)
    remainder = (NUM_ROWS - len(EPICS)) % len(SPRINTS)

    for sprint_idx, sprint in enumerate(SPRINTS):
        count = issues_per_sprint + (1 if sprint_idx < remainder else 0)

        status_weights_map = get_status_weights(sprint_idx)
        statuses = list(status_weights_map.keys())
        s_weights = list(status_weights_map.values())

        for _ in range(count):
            issue_type = random.choices(issue_types, weights=issue_type_weights, k=1)[0]

            # Skip Epic type since we already created them
            while issue_type == "Epic":
                issue_type = random.choices(issue_types, weights=issue_type_weights, k=1)[0]

            # Pick an epic
            epic = random.choice(EPICS)
            epic_key = epic["key"]

            # Generate summary based on type
            if issue_type == "Bug":
                summary = random.choice(BUG_SUMMARIES)
            elif issue_type == "Sub-task":
                parent_summary = random.choice(SUMMARIES[epic_key])
                prefix = random.choice(SUBTASK_PREFIXES)
                summary = f"{prefix} {parent_summary.lower()}"
            else:
                summary = random.choice(SUMMARIES[epic_key])

            # Status
            status = random.choices(statuses, weights=s_weights, k=1)[0]

            # Priority
            priority = random.choices(priorities, weights=priority_weights, k=1)[0]

            # Story points (not for sub-tasks)
            if issue_type in ("Story", "Task", "Bug"):
                story_points = random.choices(
                    STORY_POINT_VALUES, weights=STORY_POINT_WEIGHTS, k=1
                )[0]
            else:
                story_points = ""

            # Dates
            created = random_date_between(
                sprint["start"] - timedelta(days=7), sprint["start"] + timedelta(days=3)
            )
            updated = random_date_between(created, sprint["end"] + timedelta(days=5))

            # Resolved date (only if Done)
            if status == "Done":
                resolved = random_date_between(
                    created + timedelta(days=1),
                    min(sprint["end"] + timedelta(days=3), datetime(2025, 12, 23)),
                )
                resolved_date = resolved.strftime("%Y-%m-%d")
            else:
                resolved_date = ""

            # Assignee
            assignee = random.choice(TEAM_MEMBERS)

            # Reporter
            reporter = random.choice(REPORTERS)

            # Labels (1-2 labels)
            num_labels = random.choices([1, 2], weights=[0.7, 0.3], k=1)[0]
            issue_labels = ",".join(random.sample(LABELS, num_labels))

            # Component
            component = random.choice(COMPONENTS)

            issue_key = generate_issue_key(issue_counter)
            issue_counter += 1

            rows.append(
                {
                    "Issue_Key": issue_key,
                    "Issue_Type": issue_type,
                    "Summary": summary,
                    "Status": status,
                    "Priority": priority,
                    "Sprint_Name": sprint["name"],
                    "Sprint_Start": sprint["start"].strftime("%Y-%m-%d"),
                    "Sprint_End": sprint["end"].strftime("%Y-%m-%d"),
                    "Story_Points": story_points,
                    "Assignee": assignee,
                    "Reporter": reporter,
                    "Created_Date": created.strftime("%Y-%m-%d"),
                    "Updated_Date": updated.strftime("%Y-%m-%d"),
                    "Resolved_Date": resolved_date,
                    "Epic_Key": epic_key,
                    "Labels": issue_labels,
                    "Component": component,
                }
            )

    return rows


def main():
    """Generate JIRA issue data and write to CSV."""
    rows = generate_issues()

    fieldnames = [
        "Issue_Key",
        "Issue_Type",
        "Summary",
        "Status",
        "Priority",
        "Sprint_Name",
        "Sprint_Start",
        "Sprint_End",
        "Story_Points",
        "Assignee",
        "Reporter",
        "Created_Date",
        "Updated_Date",
        "Resolved_Date",
        "Epic_Key",
        "Labels",
        "Component",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print summary statistics
    type_counts = {}
    status_counts = {}
    sprint_counts = {}
    for row in rows:
        type_counts[row["Issue_Type"]] = type_counts.get(row["Issue_Type"], 0) + 1
        status_counts[row["Status"]] = status_counts.get(row["Status"], 0) + 1
        sprint_counts[row["Sprint_Name"]] = sprint_counts.get(row["Sprint_Name"], 0) + 1

    print(f"Generated {len(rows)} JIRA issues to {OUTPUT_FILE}")
    print("\nIssue Type Distribution:")
    for itype in ["Epic", "Story", "Task", "Bug", "Sub-task"]:
        count = type_counts.get(itype, 0)
        pct = count / len(rows) * 100
        print(f"  {itype}: {count} ({pct:.1f}%)")

    print("\nStatus Distribution:")
    for status in ["To Do", "In Progress", "In Review", "Done"]:
        count = status_counts.get(status, 0)
        pct = count / len(rows) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")

    print("\nIssues per Sprint:")
    for sprint in SPRINTS:
        count = sprint_counts.get(sprint["name"], 0)
        print(f"  {sprint['name']}: {count}")

    # Calculate velocity (sum of story points for Done items per sprint)
    print("\nSprint Velocity (Story Points Completed):")
    for sprint in SPRINTS:
        velocity = sum(
            int(r["Story_Points"])
            for r in rows
            if r["Sprint_Name"] == sprint["name"]
            and r["Status"] == "Done"
            and r["Story_Points"] != ""
        )
        print(f"  {sprint['name']}: {velocity} pts")


if __name__ == "__main__":
    main()
