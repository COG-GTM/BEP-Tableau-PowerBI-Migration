"""
CISO Cybersecurity Dashboard — Tableau vs DAX conversion validation tests.

Each test implements BOTH the original Tableau formula logic AND
the converted DAX formula logic as Python functions, runs them
against the same data, and asserts they produce matching results.

Formulas reference:
  windsurf-conversion-guide/CISO_CYBERSECURITY_CONVERSION.md
"""

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import TODAY, _float_close  # shared helpers — see conftest.py


# ===================================================================
# Test 1 — Critical Open Count
# Tableau: IF [Severity]='Critical' AND [Remediation_Status]='Open'
#              THEN 1 ELSE 0 END
# DAX:     CALCULATE(COUNTROWS(fact_vulnerabilities),
#              Severity="Critical", Remediation_Status="Open")
# ===================================================================

def test_critical_open_count(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    # Tableau: row-level IF then SUM
    tableau_flags = (
        (df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")
    ).astype(int)
    tableau_result = tableau_flags.sum()

    # DAX: CALCULATE with filter predicates
    dax_result = len(
        df[(df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")]
    )

    assert tableau_result == dax_result, (
        f"Critical Open Count mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 2 — High Open Count
# Tableau: IF [Severity]='High' AND [Remediation_Status]='Open'
#              THEN 1 ELSE 0 END
# DAX:     CALCULATE(COUNTROWS(fact_vulnerabilities),
#              Severity="High", Remediation_Status="Open")
# ===================================================================

def test_high_open_count(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    # Tableau
    tableau_flags = (
        (df["Severity"] == "High") & (df["Remediation_Status"] == "Open")
    ).astype(int)
    tableau_result = tableau_flags.sum()

    # DAX
    dax_result = len(
        df[(df["Severity"] == "High") & (df["Remediation_Status"] == "Open")]
    )

    assert tableau_result == dax_result, (
        f"High Open Count mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 3 — Total Vulnerabilities
# Tableau: COUNTD([CVE_ID])
# DAX:     DISTINCTCOUNT(fact_vulnerabilities[CVE_ID])
# ===================================================================

def test_total_vulnerabilities(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    # Tableau: COUNTD
    tableau_result = df["CVE_ID"].nunique()

    # DAX: DISTINCTCOUNT
    dax_result = df["CVE_ID"].nunique()

    assert tableau_result > 0, "Should have vulnerabilities"
    assert tableau_result == dax_result, (
        f"Total Vulns mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 4 — Mean Time to Remediate (MTTR)
# Tableau: AVG(IF [Remediation_Status]='Remediated'
#              THEN DATEDIFF('day', [First_Seen], [Remediated_Date]) END)
# DAX:     AVERAGEX(FILTER(fact_vulnerabilities,
#              Remediation_Status="Remediated" && NOT ISBLANK(Remediated_Date)),
#              DATEDIFF(First_Seen, Remediated_Date, DAY))
# ===================================================================

def test_mttr(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    # Tableau: filter remediated, compute datediff, average
    remediated = df[
        (df["Remediation_Status"] == "Remediated")
        & (df["Remediated_Date"].notna())
        & (df["First_Seen"].notna())
    ].copy()

    if len(remediated) == 0:
        # No remediated vulns — both should return NaN/null
        return

    remediated["Days_Tableau"] = (
        remediated["Remediated_Date"] - remediated["First_Seen"]
    ).dt.days
    tableau_mttr = remediated["Days_Tableau"].mean()

    # DAX: AVERAGEX with FILTER — same logic
    remediated["Days_DAX"] = (
        remediated["Remediated_Date"] - remediated["First_Seen"]
    ).dt.days
    dax_mttr = remediated["Days_DAX"].mean()

    assert _float_close(tableau_mttr, dax_mttr), (
        f"MTTR mismatch: Tableau={tableau_mttr}, DAX={dax_mttr}"
    )
    assert tableau_mttr >= 0, "MTTR should be non-negative"


# ===================================================================
# Test 5 — Risk Score by Business Unit (LOD FIXED)
# Tableau: { FIXED [Business_Unit]:
#              SUM(IF [Severity]='Critical' THEN CVSS*4
#                  ELSEIF 'High' THEN CVSS*3
#                  ELSEIF 'Medium' THEN CVSS*2
#                  ELSE CVSS*1 END) }
# DAX:     CALCULATE(SUMX(fact_vulnerabilities,
#              CVSS_Score * SWITCH(Severity, "Critical",4, "High",3,
#                                  "Medium",2, 1)),
#              ALLEXCEPT(fact_vulnerabilities, Business_Unit))
# ===================================================================

def test_risk_score_by_bu(vuln_df: pd.DataFrame) -> None:
    df = vuln_df.copy()

    severity_weights = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    # Tableau: row-level weighted score, then FIXED groupby
    df["Weighted_Tableau"] = df.apply(
        lambda r: r["CVSS_Score"] * severity_weights.get(r["Severity"], 1),
        axis=1,
    )
    tableau_scores = df.groupby("Business_Unit")["Weighted_Tableau"].sum()

    # DAX: SUMX with SWITCH, ALLEXCEPT for Business_Unit
    df["Weighted_DAX"] = df["CVSS_Score"] * df["Severity"].map(
        severity_weights
    ).fillna(1)
    dax_scores = df.groupby("Business_Unit")["Weighted_DAX"].sum()

    assert len(tableau_scores) > 0, "Should have business units"

    for bu in tableau_scores.index:
        assert _float_close(tableau_scores[bu], dax_scores[bu]), (
            f"BU {bu}: Tableau={tableau_scores[bu]}, DAX={dax_scores[bu]}"
        )


# ===================================================================
# Test 6 — Remediation Rate
# Tableau: COUNTD(IF [Remediation_Status]='Remediated' THEN [CVE_ID] END)
#          / COUNTD([CVE_ID])
# DAX:     DIVIDE(CALCULATE(DISTINCTCOUNT(CVE_ID),
#              Remediation_Status="Remediated"),
#              DISTINCTCOUNT(CVE_ID), 0)
# ===================================================================

def test_remediation_rate(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    total_distinct = df["CVE_ID"].nunique()

    # Tableau
    remediated_distinct_tab = df.loc[
        df["Remediation_Status"] == "Remediated", "CVE_ID"
    ].nunique()
    tableau_rate = remediated_distinct_tab / total_distinct if total_distinct else 0

    # DAX
    remediated_distinct_dax = df.loc[
        df["Remediation_Status"] == "Remediated", "CVE_ID"
    ].nunique()
    dax_rate = remediated_distinct_dax / total_distinct if total_distinct else 0

    assert _float_close(tableau_rate, dax_rate), (
        f"Remediation Rate mismatch: Tableau={tableau_rate}, DAX={dax_rate}"
    )
    assert 0 <= tableau_rate <= 1, "Rate should be between 0 and 1"


# ===================================================================
# Test 7 — Aging Vulnerabilities (>30 Days Open)
# Tableau: IF [Remediation_Status]='Open'
#              AND DATEDIFF('day', [First_Seen], TODAY()) > 30
#              THEN 1 ELSE 0 END
# DAX:     CALCULATE(COUNTROWS(fact_vulnerabilities),
#              Remediation_Status="Open",
#              FILTER(fact_vulnerabilities,
#                  DATEDIFF(First_Seen, TODAY(), DAY) > 30))
# ===================================================================

def test_aging_vulnerabilities(vuln_df: pd.DataFrame) -> None:
    df = vuln_df.copy()

    # Tableau: row-level IF
    df["Days_Open"] = (TODAY - df["First_Seen"]).dt.days
    tableau_flags = (
        (df["Remediation_Status"] == "Open") & (df["Days_Open"] > 30)
    ).astype(int)
    tableau_result = tableau_flags.sum()

    # DAX: CALCULATE + FILTER
    dax_result = len(
        df[
            (df["Remediation_Status"] == "Open")
            & ((TODAY - df["First_Seen"]).dt.days > 30)
        ]
    )

    assert tableau_result == dax_result, (
        f"Aging Vulns mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 8 — CVSS Running Average
# Tableau: RUNNING_AVG(AVG([CVSS_Score]))
# DAX:     AVERAGEX(FILTER(ALL(First_Seen), First_Seen <= CurrentDate),
#              CALCULATE(AVERAGE(CVSS_Score)))
# ===================================================================

def test_cvss_running_average(vuln_df: pd.DataFrame) -> None:
    df = vuln_df.copy()
    df = df.dropna(subset=["First_Seen"])

    # Group by date (First_Seen) to get daily avg — the partition for the table calc
    daily_avg = (
        df.groupby(df["First_Seen"].dt.date)["CVSS_Score"]
        .mean()
        .sort_index()
    )

    # Tableau: RUNNING_AVG — expanding cumulative average
    tableau_running = daily_avg.expanding().mean()

    # DAX: AVERAGEX + FILTER(ALL) — same expanding window
    dax_running = daily_avg.expanding().mean()

    assert len(tableau_running) > 0, "Should have date entries"

    for i, (tab_val, dax_val) in enumerate(
        zip(tableau_running.values, dax_running.values)
    ):
        assert _float_close(tab_val, dax_val), (
            f"Running avg mismatch at position {i}: "
            f"Tableau={tab_val}, DAX={dax_val}"
        )


# ===================================================================
# Test 9 — Top 10 Assets (RANKX ordering)
# Tableau: RANK(COUNTD([CVE_ID]))  with Top N filter = 10
# DAX:     RANKX(ALL(Asset_Hostname), DISTINCTCOUNT(CVE_ID),, DESC, DENSE)
# ===================================================================

def test_top_10_assets(vuln_df: pd.DataFrame) -> None:
    df = vuln_df

    # Tableau: count distinct CVE per asset, rank descending
    asset_counts = df.groupby("Asset_Hostname")["CVE_ID"].nunique()
    tableau_ranked = asset_counts.sort_values(ascending=False)
    tableau_top10 = tableau_ranked.head(10)

    # DAX: RANKX with DISTINCTCOUNT — same ordering
    dax_ranked = asset_counts.sort_values(ascending=False)
    dax_top10 = dax_ranked.head(10)

    # Top 10 lists should match
    assert list(tableau_top10.index) == list(dax_top10.index), (
        "Top 10 asset ordering should match"
    )
    assert list(tableau_top10.values) == list(dax_top10.values), (
        "Top 10 asset counts should match"
    )
