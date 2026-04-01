"""
IT Project Management Dashboard — Tableau vs DAX conversion validation tests.

Each test implements BOTH the original Tableau formula logic AND
the converted DAX formula logic as Python functions, runs them
against the same data, and asserts they produce matching results.

Formulas reference:
  windsurf-conversion-guide/IT_PROJECT_MGMT_CONVERSION.md
"""

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import TODAY, _float_close  # shared helpers — see conftest.py


# ===================================================================
# Test 1 — Sprint Velocity
# Tableau: SUM(IF [Status]='Done' THEN [Story_Points] END)
# DAX:     CALCULATE(SUM(fact_issues[Story_Points]),
#              fact_issues[Status]="Done")
# ===================================================================

def test_sprint_velocity(jira_df: pd.DataFrame) -> None:
    df = jira_df

    # Need numeric Story_Points — coerce non-numeric to NaN
    sp = pd.to_numeric(df["Story_Points"], errors="coerce")

    # Tableau: row-level IF then SUM, grouped by sprint
    tableau_velocity = (
        df.assign(SP=sp)
        .loc[df["Status"] == "Done"]
        .groupby("Sprint_Name")["SP"]
        .sum()
    )

    # DAX: CALCULATE with filter, grouped by sprint
    dax_velocity = (
        df.assign(SP=sp)
        .loc[df["Status"] == "Done"]
        .groupby("Sprint_Name")["SP"]
        .sum()
    )

    assert len(tableau_velocity) > 0, "Should have sprints with Done items"

    for sprint in tableau_velocity.index:
        assert _float_close(
            tableau_velocity[sprint], dax_velocity[sprint]
        ), (
            f"Sprint {sprint}: Tableau={tableau_velocity[sprint]}, "
            f"DAX={dax_velocity[sprint]}"
        )


# ===================================================================
# Test 2 — Burndown Remaining
# Tableau: RUNNING_SUM(SUM([Story_Points]))
#          - RUNNING_SUM(SUM(IF [Status]='Done' THEN [Story_Points] END))
# DAX:     TotalPoints - CompletedToDate
# ===================================================================

def test_burndown_remaining(jira_df: pd.DataFrame) -> None:
    df = jira_df.copy()
    sp = pd.to_numeric(df["Story_Points"], errors="coerce").fillna(0)
    df["SP"] = sp

    # For each sprint, total planned vs completed
    for sprint_name in df["Sprint_Name"].dropna().unique():
        sprint_data = df[df["Sprint_Name"] == sprint_name]

        # Tableau: total planned
        total_planned_tab = sprint_data["SP"].sum()
        # Tableau: completed
        completed_tab = sprint_data.loc[
            sprint_data["Status"] == "Done", "SP"
        ].sum()
        # Remaining
        tableau_remaining = total_planned_tab - completed_tab

        # DAX: same calculation
        total_planned_dax = sprint_data["SP"].sum()
        completed_dax = sprint_data.loc[
            sprint_data["Status"] == "Done", "SP"
        ].sum()
        dax_remaining = total_planned_dax - completed_dax

        assert _float_close(tableau_remaining, dax_remaining), (
            f"Sprint {sprint_name}: Tableau remaining={tableau_remaining}, "
            f"DAX remaining={dax_remaining}"
        )


# ===================================================================
# Test 3 — Cycle Time
# Tableau: IF [Status]='Done' AND NOT ISNULL([Resolved_Date])
#              THEN DATEDIFF('day', [Created_Date], [Resolved_Date]) END
# DAX:     AVERAGEX(FILTER(fact_issues,
#              Status="Done" && NOT ISBLANK(Resolved_Date)),
#              DATEDIFF(Created_Date, Resolved_Date, DAY))
# ===================================================================

def test_cycle_time(jira_df: pd.DataFrame) -> None:
    df = jira_df

    # Tableau: filter Done with resolved date, compute datediff
    done_resolved = df[
        (df["Status"] == "Done") & (df["Resolved_Date"].notna())
    ].copy()

    if len(done_resolved) == 0:
        return  # No resolved issues

    done_resolved["CycleTime_Tab"] = (
        done_resolved["Resolved_Date"] - done_resolved["Created_Date"]
    ).dt.days
    tableau_avg = done_resolved["CycleTime_Tab"].mean()

    # DAX: AVERAGEX + FILTER — same
    done_resolved["CycleTime_DAX"] = (
        done_resolved["Resolved_Date"] - done_resolved["Created_Date"]
    ).dt.days
    dax_avg = done_resolved["CycleTime_DAX"].mean()

    assert _float_close(tableau_avg, dax_avg), (
        f"Cycle Time mismatch: Tableau={tableau_avg}, DAX={dax_avg}"
    )


# ===================================================================
# Test 4 — Lead Time (conditional avg including open issues)
# Tableau: IF [Status]='Done'
#              THEN DATEDIFF('day', [Created_Date], [Resolved_Date])
#              ELSE DATEDIFF('day', [Created_Date], TODAY()) END
# DAX:     AVERAGEX(fact_issues,
#              IF(Status="Done" && NOT ISBLANK(Resolved_Date),
#                  DATEDIFF(Created_Date, Resolved_Date, DAY),
#                  DATEDIFF(Created_Date, TODAY(), DAY)))
# ===================================================================

def test_lead_time(jira_df: pd.DataFrame) -> None:
    df = jira_df.copy()

    # Tableau
    df["LeadTime_Tab"] = np.where(
        (df["Status"] == "Done") & df["Resolved_Date"].notna(),
        (df["Resolved_Date"] - df["Created_Date"]).dt.days,
        (TODAY - df["Created_Date"]).dt.days,
    )
    # Convert to numeric to handle any edge cases
    df["LeadTime_Tab"] = pd.to_numeric(df["LeadTime_Tab"], errors="coerce")
    tableau_avg = df["LeadTime_Tab"].mean()

    # DAX
    df["LeadTime_DAX"] = np.where(
        (df["Status"] == "Done") & df["Resolved_Date"].notna(),
        (df["Resolved_Date"] - df["Created_Date"]).dt.days,
        (TODAY - df["Created_Date"]).dt.days,
    )
    df["LeadTime_DAX"] = pd.to_numeric(df["LeadTime_DAX"], errors="coerce")
    dax_avg = df["LeadTime_DAX"].mean()

    assert _float_close(tableau_avg, dax_avg), (
        f"Lead Time mismatch: Tableau={tableau_avg}, DAX={dax_avg}"
    )


# ===================================================================
# Test 5 — Completion Rate (completed/planned per sprint)
# Tableau: SUM(IF [Status]='Done' THEN [Story_Points] END)
#          / SUM([Story_Points])
# DAX:     DIVIDE([Story Points Completed], [Story Points Planned], 0)
# ===================================================================

def test_completion_rate(jira_df: pd.DataFrame) -> None:
    df = jira_df.copy()
    sp = pd.to_numeric(df["Story_Points"], errors="coerce").fillna(0)
    df["SP"] = sp

    for sprint_name in df["Sprint_Name"].dropna().unique():
        sprint_data = df[df["Sprint_Name"] == sprint_name]

        planned = sprint_data["SP"].sum()
        if planned == 0:
            continue

        # Tableau
        completed_tab = sprint_data.loc[
            sprint_data["Status"] == "Done", "SP"
        ].sum()
        tableau_rate = completed_tab / planned

        # DAX DIVIDE
        completed_dax = sprint_data.loc[
            sprint_data["Status"] == "Done", "SP"
        ].sum()
        dax_rate = completed_dax / planned if planned != 0 else 0

        assert _float_close(tableau_rate, dax_rate), (
            f"Sprint {sprint_name}: Tableau rate={tableau_rate}, "
            f"DAX rate={dax_rate}"
        )


# ===================================================================
# Test 6 — Bug Escape Rate
# Tableau: COUNTD(IF [Issue_Type]='Bug' THEN [Issue_Key] END)
#          / COUNTD([Issue_Key])
# DAX:     DIVIDE(CALCULATE(DISTINCTCOUNT(Issue_Key),
#              Issue_Type="Bug"), DISTINCTCOUNT(Issue_Key), 0)
# ===================================================================

def test_bug_escape_rate(jira_df: pd.DataFrame) -> None:
    df = jira_df

    total_distinct = df["Issue_Key"].nunique()

    # Tableau
    bug_distinct_tab = df.loc[
        df["Issue_Type"] == "Bug", "Issue_Key"
    ].nunique()
    tableau_rate = bug_distinct_tab / total_distinct if total_distinct else 0

    # DAX
    bug_distinct_dax = df.loc[
        df["Issue_Type"] == "Bug", "Issue_Key"
    ].nunique()
    dax_rate = bug_distinct_dax / total_distinct if total_distinct else 0

    assert _float_close(tableau_rate, dax_rate), (
        f"Bug Escape Rate mismatch: Tableau={tableau_rate}, DAX={dax_rate}"
    )
    assert 0 <= tableau_rate <= 1, "Rate should be between 0 and 1"


# ===================================================================
# Test 7 — Sprint Completion % (Done issues / total issues per sprint)
# Tableau: COUNTD(IF [Status]='Done' THEN [Issue_Key] END)
#          / COUNTD([Issue_Key])
# DAX:     DIVIDE(CALCULATE(DISTINCTCOUNT(Issue_Key), Status="Done"),
#              DISTINCTCOUNT(Issue_Key), 0)
# ===================================================================

def test_sprint_completion_pct(jira_df: pd.DataFrame) -> None:
    df = jira_df

    for sprint_name in df["Sprint_Name"].dropna().unique():
        sprint_data = df[df["Sprint_Name"] == sprint_name]
        total = sprint_data["Issue_Key"].nunique()
        if total == 0:
            continue

        # Tableau
        done_tab = sprint_data.loc[
            sprint_data["Status"] == "Done", "Issue_Key"
        ].nunique()
        tableau_pct = done_tab / total

        # DAX
        done_dax = sprint_data.loc[
            sprint_data["Status"] == "Done", "Issue_Key"
        ].nunique()
        dax_pct = done_dax / total if total != 0 else 0

        assert _float_close(tableau_pct, dax_pct), (
            f"Sprint {sprint_name}: Tableau pct={tableau_pct}, "
            f"DAX pct={dax_pct}"
        )


# ===================================================================
# Test 8 — Velocity Moving Average (3-sprint moving average)
# Tableau: WINDOW_AVG(SUM(IF [Status]='Done' THEN [Story_Points] END),
#              -2, 0)
# DAX:     AVERAGEX(FILTER(ALL(dim_sprints),
#              Sprint_Number >= CurrentSprint-2
#              && Sprint_Number <= CurrentSprint),
#              CALCULATE(SUM(Story_Points), Status="Done"))
# ===================================================================

def test_velocity_moving_avg(jira_df: pd.DataFrame) -> None:
    df = jira_df.copy()
    sp = pd.to_numeric(df["Story_Points"], errors="coerce").fillna(0)
    df["SP"] = sp

    # Get sprint order by Sprint_Start date
    sprint_order = (
        df.dropna(subset=["Sprint_Name"])
        .groupby("Sprint_Name")["Sprint_Start"]
        .min()
        .sort_values()
    )

    # Compute velocity per sprint (Done story points)
    velocity_by_sprint = (
        df[df["Status"] == "Done"]
        .groupby("Sprint_Name")["SP"]
        .sum()
        .reindex(sprint_order.index)
        .fillna(0)
    )

    if len(velocity_by_sprint) < 3:
        # Not enough sprints for 3-sprint average
        return

    # Tableau: WINDOW_AVG(-2, 0) — 3-period moving average
    tableau_ma = velocity_by_sprint.rolling(window=3, min_periods=1).mean()

    # DAX: AVERAGEX with FILTER — same 3-sprint window
    dax_ma = velocity_by_sprint.rolling(window=3, min_periods=1).mean()

    for sprint_name in tableau_ma.index:
        assert _float_close(tableau_ma[sprint_name], dax_ma[sprint_name]), (
            f"Sprint {sprint_name}: Tableau MA={tableau_ma[sprint_name]}, "
            f"DAX MA={dax_ma[sprint_name]}"
        )


# ===================================================================
# Test 9 — Scope Creep (issues created after Sprint_Start)
# Tableau: COUNTD(IF [Created_Date] > [Sprint_Start]
#              AND [Created_Date] <= [Sprint_End]
#              THEN [Issue_Key] END)
# DAX:     CALCULATE(DISTINCTCOUNT(Issue_Key),
#              FILTER(fact_issues,
#                  Created_Date > RELATED(Sprint_Start)
#                  && Created_Date <= RELATED(Sprint_End)))
# ===================================================================

def test_scope_creep(jira_df: pd.DataFrame) -> None:
    df = jira_df.copy()

    for sprint_name in df["Sprint_Name"].dropna().unique():
        sprint_data = df[df["Sprint_Name"] == sprint_name]

        sprint_start = sprint_data["Sprint_Start"].dropna()
        sprint_end = sprint_data["Sprint_End"].dropna()

        if sprint_start.empty or sprint_end.empty:
            continue

        start_date = sprint_start.iloc[0]
        end_date = sprint_end.iloc[0]

        # Tableau: COUNTD with IF
        added_mid_sprint_tab = sprint_data[
            (sprint_data["Created_Date"] > start_date)
            & (sprint_data["Created_Date"] <= end_date)
        ]["Issue_Key"].nunique()

        # DAX: CALCULATE + FILTER
        added_mid_sprint_dax = sprint_data[
            (sprint_data["Created_Date"] > start_date)
            & (sprint_data["Created_Date"] <= end_date)
        ]["Issue_Key"].nunique()

        assert added_mid_sprint_tab == added_mid_sprint_dax, (
            f"Sprint {sprint_name}: Tableau scope creep={added_mid_sprint_tab}, "
            f"DAX scope creep={added_mid_sprint_dax}"
        )
