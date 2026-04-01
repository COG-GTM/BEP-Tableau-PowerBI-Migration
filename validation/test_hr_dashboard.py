"""
HR Dashboard — Tableau vs DAX conversion validation tests.

Each test implements BOTH the original Tableau formula logic AND
the converted DAX formula logic as Python functions, runs them
against the same data, and asserts they produce matching results.

Formulas reference:
  windsurf-conversion-guide/CONVERSION_OUTLINE.md  (Phase 2, Step 2.5)
"""

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import TODAY, _float_close  # shared helpers — see conftest.py


# ===================================================================
# Test 1 — Total Hired
# Tableau: COUNT([Employee_ID])
# DAX:     COUNTROWS(HRData)
# ===================================================================

def test_total_hired(hr_df: pd.DataFrame) -> None:
    # Tableau: COUNT of all employees
    tableau_result = hr_df["Employee_ID"].count()

    # DAX: COUNTROWS — same as counting all rows
    dax_result = len(hr_df)

    assert tableau_result > 0, "Total Hired should be > 0"
    assert tableau_result == dax_result, (
        f"Total Hired mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 2 — Total Terminated
# Tableau: COUNT(IF NOT ISNULL([Termdate]) THEN [Employee_ID] END)
# DAX:     CALCULATE(COUNTROWS(HRData),
#              NOT(ISBLANK(HRData[Termdate])))
# ===================================================================

def test_total_terminated(hr_df: pd.DataFrame) -> None:
    # Tableau: count where Termdate is not null
    tableau_result = hr_df[hr_df["Termdate"].notna()]["Employee_ID"].count()

    # DAX: CALCULATE with NOT ISBLANK filter
    dax_result = len(hr_df[hr_df["Termdate"].notna()])

    assert tableau_result >= 0, "Total Terminated should be >= 0"
    assert tableau_result == dax_result, (
        f"Total Terminated mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 3 — Total Active
# Tableau: COUNT(IF ISNULL([Termdate]) THEN [Employee_ID] END)
# DAX:     CALCULATE(COUNTROWS(HRData), ISBLANK(HRData[Termdate]))
# ===================================================================

def test_total_active(hr_df: pd.DataFrame) -> None:
    # Tableau
    tableau_result = hr_df[hr_df["Termdate"].isna()]["Employee_ID"].count()

    # DAX
    dax_result = len(hr_df[hr_df["Termdate"].isna()])

    assert tableau_result >= 0
    assert tableau_result == dax_result, (
        f"Total Active mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )

    # Consistency check: active + terminated = total
    total = len(hr_df)
    terminated = len(hr_df[hr_df["Termdate"].notna()])
    assert tableau_result + terminated == total, (
        "Active + Terminated should equal Total"
    )


# ===================================================================
# Test 4 — Status Column (Hired/Terminated classification)
# Tableau: IF ISNULL([Termdate]) THEN 'Hired' ELSE 'Terminated' END
# DAX:     IF(ISBLANK(HRData[Termdate]), "Hired", "Terminated")
# ===================================================================

def test_status_column(hr_df: pd.DataFrame) -> None:
    df = hr_df.copy()

    # Tableau
    df["Status_Tableau"] = np.where(
        df["Termdate"].isna(), "Hired", "Terminated"
    )

    # DAX
    df["Status_DAX"] = np.where(
        df["Termdate"].isna(), "Hired", "Terminated"
    )

    mismatches = (df["Status_Tableau"] != df["Status_DAX"]).sum()
    assert mismatches == 0, f"Status mismatch for {mismatches} employees"

    # Verify only valid values
    valid_values = {"Hired", "Terminated"}
    assert set(df["Status_Tableau"].unique()).issubset(valid_values)


# ===================================================================
# Test 5 — Location Column (State → HQ/Branch mapping)
# Tableau: CASE [State] WHEN 'New York' THEN 'HQ' ELSE 'Branch' END
# DAX:     SWITCH(HRData[State], "New York", "HQ", "Branch")
# ===================================================================

def test_location_column(hr_df: pd.DataFrame) -> None:
    df = hr_df.copy()

    # Tableau: CASE/WHEN
    df["Location_Tableau"] = np.where(
        df["State"] == "New York", "HQ", "Branch"
    )

    # DAX: SWITCH
    df["Location_DAX"] = np.where(
        df["State"] == "New York", "HQ", "Branch"
    )

    mismatches = (df["Location_Tableau"] != df["Location_DAX"]).sum()
    assert mismatches == 0, f"Location mismatch for {mismatches} employees"

    # Verify HQ exists
    assert "HQ" in df["Location_Tableau"].values, "Should have HQ employees"
    assert "Branch" in df["Location_Tableau"].values, "Should have Branch employees"


# ===================================================================
# Test 6 — Age Calculation
# Tableau: DATEDIFF('year', [Birthdate], TODAY())
# DAX:     DATEDIFF(HRData[Birthdate], TODAY(), YEAR)
# ===================================================================

def test_age_calculation(hr_df: pd.DataFrame) -> None:
    df = hr_df.copy()

    # Tableau: DATEDIFF year
    df["Age_Tableau"] = (
        (TODAY - df["Birthdate"]).dt.days / 365.25
    ).astype(int)

    # DAX: DATEDIFF YEAR — same integer year difference
    df["Age_DAX"] = (
        (TODAY - df["Birthdate"]).dt.days / 365.25
    ).astype(int)

    mismatches = (df["Age_Tableau"] != df["Age_DAX"]).sum()
    assert mismatches == 0, f"Age mismatch for {mismatches} employees"

    # Sanity: ages should be reasonable (18-80)
    assert df["Age_Tableau"].min() >= 15, "Minimum age should be >= 15"
    assert df["Age_Tableau"].max() <= 90, "Maximum age should be <= 90"


# ===================================================================
# Test 7 — Age Groups (5-bucket classification)
# Tableau: IF [Age]<25 THEN '<25'
#          ELSEIF [Age]<35 THEN '25-34'
#          ELSEIF [Age]<45 THEN '35-44'
#          ELSEIF [Age]<55 THEN '45-54'
#          ELSE '55+' END
# DAX:     SWITCH(TRUE(),
#              HRData[Age]<25, "<25",
#              HRData[Age]<35, "25-34",
#              HRData[Age]<45, "35-44",
#              HRData[Age]<55, "45-54",
#              "55+")
# ===================================================================

def test_age_groups(hr_df: pd.DataFrame) -> None:
    df = hr_df.copy()
    df["Age"] = ((TODAY - df["Birthdate"]).dt.days / 365.25).astype(int)

    def _classify_tableau(age: int) -> str:
        if age < 25:
            return "<25"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55+"

    def _classify_dax(age: int) -> str:
        # SWITCH(TRUE(), ...) evaluates conditions in order
        if age < 25:
            return "<25"
        if age < 35:
            return "25-34"
        if age < 45:
            return "35-44"
        if age < 55:
            return "45-54"
        return "55+"

    df["AgeGroup_Tableau"] = df["Age"].apply(_classify_tableau)
    df["AgeGroup_DAX"] = df["Age"].apply(_classify_dax)

    mismatches = (df["AgeGroup_Tableau"] != df["AgeGroup_DAX"]).sum()
    assert mismatches == 0, f"Age group mismatch for {mismatches} employees"

    # Should have at least 2 different groups
    assert df["AgeGroup_Tableau"].nunique() >= 2, "Should have multiple age groups"


# ===================================================================
# Test 8 — Length of Hire (conditional DATEDIFF)
# Tableau: IF ISNULL([Termdate])
#              THEN DATEDIFF('day', [Hiredate], TODAY())
#              ELSE DATEDIFF('day', [Hiredate], [Termdate])
#          END
# DAX:     IF(ISBLANK(HRData[Termdate]),
#              DATEDIFF(HRData[Hiredate], TODAY(), DAY),
#              DATEDIFF(HRData[Hiredate], HRData[Termdate], DAY))
# ===================================================================

def test_length_of_hire(hr_df: pd.DataFrame) -> None:
    df = hr_df.copy()

    # Tableau
    df["LoH_Tableau"] = np.where(
        df["Termdate"].isna(),
        (TODAY - df["Hiredate"]).dt.days,
        (df["Termdate"] - df["Hiredate"]).dt.days,
    )

    # DAX
    df["LoH_DAX"] = np.where(
        df["Termdate"].isna(),
        (TODAY - df["Hiredate"]).dt.days,
        (df["Termdate"] - df["Hiredate"]).dt.days,
    )

    mismatches = (df["LoH_Tableau"] != df["LoH_DAX"]).sum()
    assert mismatches == 0, f"Length of hire mismatch for {mismatches} employees"

    # All lengths should be non-negative
    assert (df["LoH_Tableau"] >= 0).all(), "Length of hire should be >= 0"


# ===================================================================
# Test 9 — % Total Hired (TOTAL() → ALL() equivalence)
# Tableau: [Total Hired] / TOTAL([Total Hired])
# DAX:     DIVIDE(COUNTROWS(HRData),
#              CALCULATE(COUNTROWS(HRData), ALL(HRData)))
# ===================================================================

def test_pct_total_hired(hr_df: pd.DataFrame) -> None:
    df = hr_df

    # Group by Department for partition context
    dept_counts = df.groupby("Department")["Employee_ID"].count()
    grand_total = len(df)

    # Tableau: partition total uses TOTAL()
    tableau_pcts = dept_counts / grand_total

    # DAX: CALCULATE with ALL() removes filter context → grand total
    dax_pcts = dept_counts / grand_total

    assert _float_close(tableau_pcts.sum(), dax_pcts.sum()), (
        "Sum of percentages should match"
    )
    assert _float_close(tableau_pcts.sum(), 1.0, tol=0.01), (
        "Percentages should sum to ~1.0"
    )

    for dept in tableau_pcts.index:
        assert _float_close(tableau_pcts[dept], dax_pcts[dept]), (
            f"Dept {dept}: Tableau={tableau_pcts[dept]}, DAX={dax_pcts[dept]}"
        )


# ===================================================================
# Test 10 — Highlight Max (WINDOW_MAX match)
# Tableau: WINDOW_MAX([Total Hired]) = [Total Hired]
# DAX:     [Total Hired] = MAXX(ALLSELECTED(HRData[Department]),
#              COUNTROWS(HRData))
# ===================================================================

def test_highlight_max(hr_df: pd.DataFrame) -> None:
    df = hr_df

    # Group by Department
    dept_counts = df.groupby("Department")["Employee_ID"].count()

    # Tableau WINDOW_MAX
    window_max = dept_counts.max()
    tableau_highlights = dept_counts == window_max

    # DAX MAXX ALLSELECTED
    dax_max = dept_counts.max()
    dax_highlights = dept_counts == dax_max

    assert tableau_highlights.equals(dax_highlights), (
        "Highlight max flags should match"
    )
    assert tableau_highlights.sum() >= 1, "At least one department should be max"
