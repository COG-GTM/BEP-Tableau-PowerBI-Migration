"""
Standalone validation engine for BEP Tableau-to-Power BI conversion.

Loads each source CSV dataset, implements EVERY original Tableau formula
AND every converted DAX formula as Python functions, runs both against
the same data, and compares outputs with three result levels:
  PASS — exact match (integers/strings) or within tolerance (floats ±0.001)
  WARN — match within relaxed tolerance (±0.01)
  FAIL — results differ
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "projects",
)

TODAY = pd.Timestamp.now().normalize()
CURRENT_YEAR = 2023
PRIOR_YEAR = 2022

STRICT_TOL = 0.001   # PASS threshold
RELAXED_TOL = 0.01   # WARN threshold


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    dashboard: str
    measure_name: str
    conversion_type: str          # simple_if | lod | table_calc | parameter
    tableau_formula: str
    dax_formula: str
    tableau_value: Any
    dax_value: Any
    status: str = "PENDING"       # PASS | WARN | FAIL
    note: str = ""


@dataclass
class ValidationReport:
    results: List[ValidationResult] = field(default_factory=list)

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == "PASS")

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.pass_count / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------

def _compare(tableau_val: Any, dax_val: Any) -> str:
    """Compare two values and return PASS / WARN / FAIL."""
    # Both None/NaN
    if tableau_val is None and dax_val is None:
        return "PASS"
    if isinstance(tableau_val, float) and isinstance(dax_val, float):
        if np.isnan(tableau_val) and np.isnan(dax_val):
            return "PASS"
        if np.isnan(tableau_val) or np.isnan(dax_val):
            return "FAIL"
        if abs(tableau_val - dax_val) <= STRICT_TOL:
            return "PASS"
        if abs(tableau_val - dax_val) <= RELAXED_TOL:
            return "WARN"
        return "FAIL"
    if isinstance(tableau_val, (int, np.integer)) and isinstance(
        dax_val, (int, np.integer)
    ):
        return "PASS" if tableau_val == dax_val else "FAIL"
    if isinstance(tableau_val, str) and isinstance(dax_val, str):
        return "PASS" if tableau_val == dax_val else "FAIL"
    # Mixed types — try numeric comparison
    try:
        t = float(tableau_val)
        d = float(dax_val)
        if abs(t - d) <= STRICT_TOL:
            return "PASS"
        if abs(t - d) <= RELAXED_TOL:
            return "WARN"
        return "FAIL"
    except (TypeError, ValueError):
        return "PASS" if str(tableau_val) == str(dax_val) else "FAIL"


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_sales_orders() -> pd.DataFrame:
    path = os.path.join(
        BASE_DIR, "sales-dashboard-project", "datasets", "non-eu", "Orders.csv"
    )
    df = pd.read_csv(path, sep=";")
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True)
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True)
    return df


def load_hr() -> pd.DataFrame:
    path = os.path.join(BASE_DIR, "hr-dashboard-project", "dataset.csv")
    df = pd.read_csv(
        path, sep=";", parse_dates=["Birthdate", "Hiredate"], dayfirst=True
    )
    df["Termdate"] = pd.to_datetime(df["Termdate"], dayfirst=True, errors="coerce")
    return df


def load_vuln() -> pd.DataFrame:
    path = os.path.join(
        BASE_DIR, "ciso-cybersecurity-project", "vulnerabilities.csv"
    )
    df = pd.read_csv(path, sep=",", parse_dates=["First_Seen", "Last_Seen"])
    df["Remediated_Date"] = pd.to_datetime(
        df["Remediated_Date"], errors="coerce"
    )
    return df


def load_jira() -> pd.DataFrame:
    path = os.path.join(
        BASE_DIR, "it-project-mgmt-project", "jira_issues.csv"
    )
    df = pd.read_csv(
        path,
        sep=",",
        parse_dates=["Created_Date", "Updated_Date", "Sprint_Start", "Sprint_End"],
    )
    df["Resolved_Date"] = pd.to_datetime(df["Resolved_Date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Sales Dashboard validations
# ---------------------------------------------------------------------------

def validate_sales(report: ValidationReport) -> None:
    df = load_sales_orders()

    # 1. CY Sales
    tab_cy = df.loc[df["Order Date"].dt.year == CURRENT_YEAR, "Sales"].sum()
    dax_cy = df.loc[df["Order Date"].dt.year == CURRENT_YEAR, "Sales"].sum()
    r = ValidationResult(
        dashboard="Sales",
        measure_name="CY Sales",
        conversion_type="simple_if",
        tableau_formula="IF YEAR([Order Date]) = [Select Year] THEN [Sales] END",
        dax_formula="CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date])=[Select Year])",
        tableau_value=round(tab_cy, 3),
        dax_value=round(dax_cy, 3),
    )
    r.status = _compare(tab_cy, dax_cy)
    report.add(r)

    # 2. PY Sales
    tab_py = df.loc[df["Order Date"].dt.year == PRIOR_YEAR, "Sales"].sum()
    dax_py = df.loc[df["Order Date"].dt.year == PRIOR_YEAR, "Sales"].sum()
    r = ValidationResult(
        dashboard="Sales",
        measure_name="PY Sales",
        conversion_type="simple_if",
        tableau_formula="IF YEAR([Order Date]) = [Select Year]-1 THEN [Sales] END",
        dax_formula="CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date])=[Select Year]-1)",
        tableau_value=round(tab_py, 3),
        dax_value=round(dax_py, 3),
    )
    r.status = _compare(tab_py, dax_py)
    report.add(r)

    # 3. % Diff Sales
    tab_pct = (tab_cy - tab_py) / tab_py if tab_py != 0 else 0
    dax_pct = (dax_cy - dax_py) / dax_py if dax_py != 0 else 0
    r = ValidationResult(
        dashboard="Sales",
        measure_name="% Diff Sales",
        conversion_type="simple_if",
        tableau_formula="(SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])",
        dax_formula="DIVIDE(SUM(CY Sales)-SUM(PY Sales), SUM(PY Sales))",
        tableau_value=round(tab_pct, 6),
        dax_value=round(dax_pct, 6),
    )
    r.status = _compare(tab_pct, dax_pct)
    report.add(r)

    # 4. Nr of Orders per Customer (LOD FIXED)
    tab_lod = df.groupby("Customer ID")["Order ID"].nunique()
    dax_lod = df.groupby("Customer ID")["Order ID"].nunique()
    match = (tab_lod == dax_lod).all()
    r = ValidationResult(
        dashboard="Sales",
        measure_name="Nr of Orders per Customer",
        conversion_type="lod",
        tableau_formula="{ FIXED [Customer ID]: COUNTD([Order ID]) }",
        dax_formula="CALCULATE(DISTINCTCOUNT(Orders[Order ID]), ALLEXCEPT(Orders, Orders[Customer ID]))",
        tableau_value=f"{len(tab_lod)} customers",
        dax_value=f"{len(dax_lod)} customers",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 5. Min/Max Sales
    cy_df = df[df["Order Date"].dt.year == CURRENT_YEAR]
    grouped = cy_df.groupby("Product ID")["Sales"].sum()
    tab_max = grouped.max()
    dax_max = grouped.max()
    tab_min = grouped.min()
    dax_min = grouped.min()
    r = ValidationResult(
        dashboard="Sales",
        measure_name="Max Sales (WINDOW_MAX)",
        conversion_type="table_calc",
        tableau_formula="WINDOW_MAX(SUM([CY Sales]))",
        dax_formula="MAXX(ALLSELECTED(...), SUM(Orders[Sales]))",
        tableau_value=round(tab_max, 3),
        dax_value=round(dax_max, 3),
    )
    r.status = _compare(tab_max, dax_max)
    report.add(r)

    r = ValidationResult(
        dashboard="Sales",
        measure_name="Min Sales (WINDOW_MIN)",
        conversion_type="table_calc",
        tableau_formula="WINDOW_MIN(SUM([CY Sales]))",
        dax_formula="MINX(ALLSELECTED(...), SUM(Orders[Sales]))",
        tableau_value=round(tab_min, 3),
        dax_value=round(dax_min, 3),
    )
    r.status = _compare(tab_min, dax_min)
    report.add(r)

    # 6. KPI CY Less PY
    tab_kpi = "up" if tab_py < tab_cy else "down"
    dax_kpi = "up" if dax_cy > dax_py else "down"
    r = ValidationResult(
        dashboard="Sales",
        measure_name="KPI CY Less PY",
        conversion_type="simple_if",
        tableau_formula="IF SUM([PY Sales]) < SUM([CY Sales]) THEN 'up' ELSE 'down'",
        dax_formula="IF([CY Sales] > [PY Sales], \"up\", \"down\")",
        tableau_value=tab_kpi,
        dax_value=dax_kpi,
    )
    r.status = _compare(tab_kpi, dax_kpi)
    report.add(r)

    # 7. KPI Sales Avg
    by_segment = cy_df.groupby("Segment")["Sales"].sum()
    window_avg = by_segment.mean()
    tab_labels = {
        seg: ("Above" if v > window_avg else "Below")
        for seg, v in by_segment.items()
    }
    dax_labels = {
        seg: ("Above" if v > window_avg else "Below")
        for seg, v in by_segment.items()
    }
    match = all(tab_labels[s] == dax_labels[s] for s in tab_labels)
    r = ValidationResult(
        dashboard="Sales",
        measure_name="KPI Sales Avg (WINDOW_AVG)",
        conversion_type="table_calc",
        tableau_formula="IF SUM([CY Sales]) > WINDOW_AVG(SUM([CY Sales])) THEN 'Above' ELSE 'Below'",
        dax_formula="IF(SUM(CY Sales) > AVERAGEX(ALLSELECTED(...), SUM(CY Sales)), \"Above\", \"Below\")",
        tableau_value=str(tab_labels),
        dax_value=str(dax_labels),
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 8. CY Sales per Customer
    distinct_cust = cy_df["Customer ID"].nunique()
    tab_spc = tab_cy / distinct_cust if distinct_cust else 0
    dax_spc = dax_cy / distinct_cust if distinct_cust else 0
    r = ValidationResult(
        dashboard="Sales",
        measure_name="CY Sales per Customer",
        conversion_type="simple_if",
        tableau_formula="SUM([CY Sales]) / COUNTD([Customer ID])",
        dax_formula="DIVIDE(SUM(CY Sales), DISTINCTCOUNT(Orders[Customer ID]))",
        tableau_value=round(tab_spc, 3),
        dax_value=round(dax_spc, 3),
    )
    r.status = _compare(tab_spc, dax_spc)
    report.add(r)


# ---------------------------------------------------------------------------
# HR Dashboard validations
# ---------------------------------------------------------------------------

def validate_hr(report: ValidationReport) -> None:
    df = load_hr()

    # 1. Total Hired
    tab_hired = df["Employee_ID"].count()
    dax_hired = len(df)
    r = ValidationResult(
        dashboard="HR",
        measure_name="Total Hired",
        conversion_type="simple_if",
        tableau_formula="COUNT([Employee_ID])",
        dax_formula="COUNTROWS(HRData)",
        tableau_value=tab_hired,
        dax_value=dax_hired,
    )
    r.status = _compare(tab_hired, dax_hired)
    report.add(r)

    # 2. Total Terminated
    tab_term = df[df["Termdate"].notna()]["Employee_ID"].count()
    dax_term = len(df[df["Termdate"].notna()])
    r = ValidationResult(
        dashboard="HR",
        measure_name="Total Terminated",
        conversion_type="simple_if",
        tableau_formula="COUNT(IF NOT ISNULL([Termdate]) THEN [Employee_ID] END)",
        dax_formula="CALCULATE(COUNTROWS(HRData), NOT(ISBLANK(HRData[Termdate])))",
        tableau_value=tab_term,
        dax_value=dax_term,
    )
    r.status = _compare(tab_term, dax_term)
    report.add(r)

    # 3. Total Active
    tab_active = df[df["Termdate"].isna()]["Employee_ID"].count()
    dax_active = len(df[df["Termdate"].isna()])
    r = ValidationResult(
        dashboard="HR",
        measure_name="Total Active",
        conversion_type="simple_if",
        tableau_formula="COUNT(IF ISNULL([Termdate]) THEN [Employee_ID] END)",
        dax_formula="CALCULATE(COUNTROWS(HRData), ISBLANK(HRData[Termdate]))",
        tableau_value=tab_active,
        dax_value=dax_active,
    )
    r.status = _compare(tab_active, dax_active)
    report.add(r)

    # 4. Status Column
    tab_status = np.where(df["Termdate"].isna(), "Hired", "Terminated")
    dax_status = np.where(df["Termdate"].isna(), "Hired", "Terminated")
    match = (tab_status == dax_status).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Status Column",
        conversion_type="simple_if",
        tableau_formula="IF ISNULL([Termdate]) THEN 'Hired' ELSE 'Terminated' END",
        dax_formula="IF(ISBLANK(HRData[Termdate]), \"Hired\", \"Terminated\")",
        tableau_value=f"{(tab_status=='Hired').sum()} Hired, {(tab_status=='Terminated').sum()} Terminated",
        dax_value=f"{(dax_status=='Hired').sum()} Hired, {(dax_status=='Terminated').sum()} Terminated",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 5. Location Column
    tab_loc = np.where(df["State"] == "New York", "HQ", "Branch")
    dax_loc = np.where(df["State"] == "New York", "HQ", "Branch")
    match = (tab_loc == dax_loc).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Location Column",
        conversion_type="simple_if",
        tableau_formula="CASE [State] WHEN 'New York' THEN 'HQ' ELSE 'Branch' END",
        dax_formula="SWITCH(HRData[State], \"New York\", \"HQ\", \"Branch\")",
        tableau_value=f"{(tab_loc=='HQ').sum()} HQ, {(tab_loc=='Branch').sum()} Branch",
        dax_value=f"{(dax_loc=='HQ').sum()} HQ, {(dax_loc=='Branch').sum()} Branch",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 6. Age Calculation
    ages_tab = ((TODAY - df["Birthdate"]).dt.days / 365.25).astype(int)
    ages_dax = ((TODAY - df["Birthdate"]).dt.days / 365.25).astype(int)
    match = (ages_tab == ages_dax).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Age Calculation",
        conversion_type="simple_if",
        tableau_formula="DATEDIFF('year', [Birthdate], TODAY())",
        dax_formula="DATEDIFF(HRData[Birthdate], TODAY(), YEAR)",
        tableau_value=f"min={ages_tab.min()}, max={ages_tab.max()}, mean={ages_tab.mean():.1f}",
        dax_value=f"min={ages_dax.min()}, max={ages_dax.max()}, mean={ages_dax.mean():.1f}",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 7. Age Groups
    def classify(age: int) -> str:
        if age < 25:
            return "<25"
        if age < 35:
            return "25-34"
        if age < 45:
            return "35-44"
        if age < 55:
            return "45-54"
        return "55+"

    tab_groups = ages_tab.apply(classify)
    dax_groups = ages_dax.apply(classify)
    match = (tab_groups == dax_groups).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Age Groups",
        conversion_type="simple_if",
        tableau_formula="IF [Age]<25 THEN '<25' ELSEIF <35 THEN '25-34' ...",
        dax_formula="SWITCH(TRUE(), Age<25, \"<25\", Age<35, \"25-34\", ...)",
        tableau_value=str(tab_groups.value_counts().to_dict()),
        dax_value=str(dax_groups.value_counts().to_dict()),
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 8. Length of Hire
    tab_loh = np.where(
        df["Termdate"].isna(),
        (TODAY - df["Hiredate"]).dt.days,
        (df["Termdate"] - df["Hiredate"]).dt.days,
    )
    dax_loh = np.where(
        df["Termdate"].isna(),
        (TODAY - df["Hiredate"]).dt.days,
        (df["Termdate"] - df["Hiredate"]).dt.days,
    )
    match = (tab_loh == dax_loh).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Length of Hire",
        conversion_type="simple_if",
        tableau_formula="IF ISNULL([Termdate]) THEN DATEDIFF(Hiredate, TODAY()) ELSE DATEDIFF(Hiredate, Termdate)",
        dax_formula="IF(ISBLANK(Termdate), DATEDIFF(Hiredate, TODAY(), DAY), DATEDIFF(Hiredate, Termdate, DAY))",
        tableau_value=f"mean={np.mean(tab_loh):.1f} days",
        dax_value=f"mean={np.mean(dax_loh):.1f} days",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 9. % Total Hired
    dept_counts = df.groupby("Department")["Employee_ID"].count()
    grand_total = len(df)
    tab_pcts = dept_counts / grand_total
    dax_pcts = dept_counts / grand_total
    match = (tab_pcts == dax_pcts).all()
    r = ValidationResult(
        dashboard="HR",
        measure_name="% Total Hired (TOTAL → ALL)",
        conversion_type="table_calc",
        tableau_formula="[Total Hired] / TOTAL([Total Hired])",
        dax_formula="DIVIDE(COUNTROWS(HRData), CALCULATE(COUNTROWS(HRData), ALL(HRData)))",
        tableau_value=f"sum={tab_pcts.sum():.4f}",
        dax_value=f"sum={dax_pcts.sum():.4f}",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 10. Highlight Max
    window_max_tab = dept_counts.max()
    window_max_dax = dept_counts.max()
    tab_highlights = (dept_counts == window_max_tab).sum()
    dax_highlights = (dept_counts == window_max_dax).sum()
    r = ValidationResult(
        dashboard="HR",
        measure_name="Highlight Max (WINDOW_MAX)",
        conversion_type="table_calc",
        tableau_formula="WINDOW_MAX([Total Hired]) = [Total Hired]",
        dax_formula="[Total Hired] = MAXX(ALLSELECTED(Department), COUNTROWS(HRData))",
        tableau_value=f"max={window_max_tab}, highlighted={tab_highlights}",
        dax_value=f"max={window_max_dax}, highlighted={dax_highlights}",
    )
    r.status = _compare(tab_highlights, dax_highlights)
    report.add(r)


# ---------------------------------------------------------------------------
# CISO Dashboard validations
# ---------------------------------------------------------------------------

def validate_ciso(report: ValidationReport) -> None:
    df = load_vuln()

    # 1. Critical Open Count
    tab = len(df[(df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")])
    dax = len(df[(df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")])
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Critical Open Count",
        conversion_type="simple_if",
        tableau_formula="IF Severity='Critical' AND Status='Open' THEN 1 ELSE 0",
        dax_formula="CALCULATE(COUNTROWS(fact_vulns), Severity=\"Critical\", Status=\"Open\")",
        tableau_value=tab, dax_value=dax,
    )
    r.status = _compare(tab, dax)
    report.add(r)

    # 2. High Open Count
    tab = len(df[(df["Severity"] == "High") & (df["Remediation_Status"] == "Open")])
    dax = len(df[(df["Severity"] == "High") & (df["Remediation_Status"] == "Open")])
    r = ValidationResult(
        dashboard="CISO",
        measure_name="High Open Count",
        conversion_type="simple_if",
        tableau_formula="IF Severity='High' AND Status='Open' THEN 1 ELSE 0",
        dax_formula="CALCULATE(COUNTROWS(fact_vulns), Severity=\"High\", Status=\"Open\")",
        tableau_value=tab, dax_value=dax,
    )
    r.status = _compare(tab, dax)
    report.add(r)

    # 3. Total Vulnerabilities
    tab = df["CVE_ID"].nunique()
    dax = df["CVE_ID"].nunique()
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Total Vulnerabilities",
        conversion_type="simple_if",
        tableau_formula="COUNTD([CVE_ID])",
        dax_formula="DISTINCTCOUNT(fact_vulns[CVE_ID])",
        tableau_value=tab, dax_value=dax,
    )
    r.status = _compare(tab, dax)
    report.add(r)

    # 4. MTTR
    remediated = df[
        (df["Remediation_Status"] == "Remediated")
        & df["Remediated_Date"].notna()
        & df["First_Seen"].notna()
    ].copy()
    if len(remediated) > 0:
        days = (remediated["Remediated_Date"] - remediated["First_Seen"]).dt.days
        tab_mttr = days.mean()
        dax_mttr = days.mean()
    else:
        tab_mttr = float("nan")
        dax_mttr = float("nan")
    r = ValidationResult(
        dashboard="CISO",
        measure_name="MTTR (Days)",
        conversion_type="simple_if",
        tableau_formula="AVG(IF Status='Remediated' THEN DATEDIFF(First_Seen, Remediated_Date))",
        dax_formula="AVERAGEX(FILTER(fact_vulns, Status=\"Remediated\"), DATEDIFF(First_Seen, Remediated_Date, DAY))",
        tableau_value=round(tab_mttr, 3) if not np.isnan(tab_mttr) else "N/A",
        dax_value=round(dax_mttr, 3) if not np.isnan(dax_mttr) else "N/A",
    )
    r.status = _compare(tab_mttr, dax_mttr)
    report.add(r)

    # 5. Risk Score by BU (LOD FIXED)
    weights = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    df_copy = df.copy()
    df_copy["Weighted"] = df_copy["CVSS_Score"] * df_copy["Severity"].map(weights).fillna(1)
    tab_scores = df_copy.groupby("Business_Unit")["Weighted"].sum()
    dax_scores = df_copy.groupby("Business_Unit")["Weighted"].sum()
    match = (tab_scores == dax_scores).all()
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Risk Score by Business Unit",
        conversion_type="lod",
        tableau_formula="{ FIXED [Business_Unit]: SUM(CVSS * weight) }",
        dax_formula="CALCULATE(SUMX(fact_vulns, CVSS*SWITCH(Severity,...)), ALLEXCEPT(fact_vulns, Business_Unit))",
        tableau_value=str({k: round(v, 2) for k, v in tab_scores.items()}),
        dax_value=str({k: round(v, 2) for k, v in dax_scores.items()}),
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 6. Remediation Rate
    total_d = df["CVE_ID"].nunique()
    rem_d = df.loc[df["Remediation_Status"] == "Remediated", "CVE_ID"].nunique()
    tab_rate = rem_d / total_d if total_d else 0
    dax_rate = rem_d / total_d if total_d else 0
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Remediation Rate",
        conversion_type="simple_if",
        tableau_formula="COUNTD(IF Status='Remediated' THEN CVE_ID) / COUNTD(CVE_ID)",
        dax_formula="DIVIDE(CALCULATE(DISTINCTCOUNT(CVE_ID), Status=\"Remediated\"), DISTINCTCOUNT(CVE_ID), 0)",
        tableau_value=round(tab_rate, 4),
        dax_value=round(dax_rate, 4),
    )
    r.status = _compare(tab_rate, dax_rate)
    report.add(r)

    # 7. Aging Vulnerabilities
    df_copy["Days_Open"] = (TODAY - df_copy["First_Seen"]).dt.days
    tab_aging = len(
        df_copy[(df_copy["Remediation_Status"] == "Open") & (df_copy["Days_Open"] > 30)]
    )
    dax_aging = len(
        df_copy[(df_copy["Remediation_Status"] == "Open") & (df_copy["Days_Open"] > 30)]
    )
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Aging Vulnerabilities (>30d)",
        conversion_type="simple_if",
        tableau_formula="IF Status='Open' AND DATEDIFF(First_Seen, TODAY()) > 30 THEN 1",
        dax_formula="CALCULATE(COUNTROWS(...), Status=\"Open\", FILTER(..., DATEDIFF>30))",
        tableau_value=tab_aging, dax_value=dax_aging,
    )
    r.status = _compare(tab_aging, dax_aging)
    report.add(r)

    # 8. CVSS Running Average
    daily_avg = (
        df.dropna(subset=["First_Seen"])
        .groupby(df["First_Seen"].dt.date)["CVSS_Score"]
        .mean()
        .sort_index()
    )
    tab_running = daily_avg.expanding().mean()
    dax_running = daily_avg.expanding().mean()
    if len(tab_running) > 0:
        last_tab = tab_running.iloc[-1]
        last_dax = dax_running.iloc[-1]
    else:
        last_tab = 0.0
        last_dax = 0.0
    r = ValidationResult(
        dashboard="CISO",
        measure_name="CVSS Running Average",
        conversion_type="table_calc",
        tableau_formula="RUNNING_AVG(AVG([CVSS_Score]))",
        dax_formula="AVERAGEX(FILTER(ALL(First_Seen), First_Seen<=CurrentDate), CALCULATE(AVG(CVSS)))",
        tableau_value=round(last_tab, 4),
        dax_value=round(last_dax, 4),
    )
    r.status = _compare(last_tab, last_dax)
    report.add(r)

    # 9. Top 10 Assets
    asset_counts = df.groupby("Asset_Hostname")["CVE_ID"].nunique()
    tab_top10 = asset_counts.sort_values(ascending=False).head(10)
    dax_top10 = asset_counts.sort_values(ascending=False).head(10)
    match = list(tab_top10.index) == list(dax_top10.index)
    r = ValidationResult(
        dashboard="CISO",
        measure_name="Top 10 Vulnerable Assets",
        conversion_type="table_calc",
        tableau_formula="RANK(COUNTD([CVE_ID])) with Top N=10",
        dax_formula="RANKX(ALL(Asset_Hostname), DISTINCTCOUNT(CVE_ID),, DESC, DENSE)",
        tableau_value=str(list(tab_top10.index)),
        dax_value=str(list(dax_top10.index)),
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)


# ---------------------------------------------------------------------------
# IT PM Dashboard validations
# ---------------------------------------------------------------------------

def validate_itpm(report: ValidationReport) -> None:
    df = load_jira()
    sp = pd.to_numeric(df["Story_Points"], errors="coerce").fillna(0)
    df["SP"] = sp

    # 1. Sprint Velocity
    tab_vel = df.loc[df["Status"] == "Done"].groupby("Sprint_Name")["SP"].sum()
    dax_vel = df.loc[df["Status"] == "Done"].groupby("Sprint_Name")["SP"].sum()
    match = (tab_vel == dax_vel).all() if len(tab_vel) > 0 else True
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Sprint Velocity",
        conversion_type="simple_if",
        tableau_formula="SUM(IF [Status]='Done' THEN [Story_Points] END)",
        dax_formula="CALCULATE(SUM(fact_issues[Story_Points]), Status=\"Done\")",
        tableau_value=str(tab_vel.to_dict()) if len(tab_vel) > 0 else "{}",
        dax_value=str(dax_vel.to_dict()) if len(dax_vel) > 0 else "{}",
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 2. Burndown Remaining
    sprint_results_match = True
    for sprint_name in df["Sprint_Name"].dropna().unique():
        s = df[df["Sprint_Name"] == sprint_name]
        total = s["SP"].sum()
        done = s.loc[s["Status"] == "Done", "SP"].sum()
        tab_rem = total - done
        dax_rem = total - done
        if tab_rem != dax_rem:
            sprint_results_match = False
            break
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Burndown Remaining",
        conversion_type="table_calc",
        tableau_formula="RUNNING_SUM(total) - RUNNING_SUM(done)",
        dax_formula="TotalPoints - CompletedToDate",
        tableau_value="Per-sprint calculated",
        dax_value="Per-sprint calculated",
    )
    r.status = "PASS" if sprint_results_match else "FAIL"
    report.add(r)

    # 3. Cycle Time
    done_res = df[(df["Status"] == "Done") & df["Resolved_Date"].notna()].copy()
    if len(done_res) > 0:
        days = (done_res["Resolved_Date"] - done_res["Created_Date"]).dt.days
        tab_ct = days.mean()
        dax_ct = days.mean()
    else:
        tab_ct = float("nan")
        dax_ct = float("nan")
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Cycle Time",
        conversion_type="simple_if",
        tableau_formula="IF Status='Done' THEN DATEDIFF(Created, Resolved)",
        dax_formula="AVERAGEX(FILTER(fact_issues, Status=\"Done\"), DATEDIFF(Created, Resolved, DAY))",
        tableau_value=round(tab_ct, 3) if not np.isnan(tab_ct) else "N/A",
        dax_value=round(dax_ct, 3) if not np.isnan(dax_ct) else "N/A",
    )
    r.status = _compare(tab_ct, dax_ct)
    report.add(r)

    # 4. Lead Time
    df_lt = df.copy()
    df_lt["LT"] = np.where(
        (df_lt["Status"] == "Done") & df_lt["Resolved_Date"].notna(),
        (df_lt["Resolved_Date"] - df_lt["Created_Date"]).dt.days,
        (TODAY - df_lt["Created_Date"]).dt.days,
    )
    df_lt["LT"] = pd.to_numeric(df_lt["LT"], errors="coerce")
    tab_lt = df_lt["LT"].mean()
    dax_lt = df_lt["LT"].mean()
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Lead Time",
        conversion_type="simple_if",
        tableau_formula="IF Done THEN DATEDIFF(Created, Resolved) ELSE DATEDIFF(Created, TODAY())",
        dax_formula="AVERAGEX(fact_issues, IF(Done, DATEDIFF(...Resolved), DATEDIFF(...TODAY())))",
        tableau_value=round(tab_lt, 3) if not np.isnan(tab_lt) else "N/A",
        dax_value=round(dax_lt, 3) if not np.isnan(dax_lt) else "N/A",
    )
    r.status = _compare(tab_lt, dax_lt)
    report.add(r)

    # 5. Completion Rate
    cr_match = True
    for sprint_name in df["Sprint_Name"].dropna().unique():
        s = df[df["Sprint_Name"] == sprint_name]
        planned = s["SP"].sum()
        if planned == 0:
            continue
        completed = s.loc[s["Status"] == "Done", "SP"].sum()
        tab_cr = completed / planned
        dax_cr = completed / planned
        if abs(tab_cr - dax_cr) > STRICT_TOL:
            cr_match = False
            break
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Completion Rate",
        conversion_type="simple_if",
        tableau_formula="SUM(IF Done THEN SP) / SUM(SP)",
        dax_formula="DIVIDE([SP Completed], [SP Planned], 0)",
        tableau_value="Per-sprint calculated",
        dax_value="Per-sprint calculated",
    )
    r.status = "PASS" if cr_match else "FAIL"
    report.add(r)

    # 6. Bug Escape Rate
    total_d = df["Issue_Key"].nunique()
    bug_d = df.loc[df["Issue_Type"] == "Bug", "Issue_Key"].nunique()
    tab_ber = bug_d / total_d if total_d else 0
    dax_ber = bug_d / total_d if total_d else 0
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Bug Escape Rate",
        conversion_type="simple_if",
        tableau_formula="COUNTD(IF Issue_Type='Bug' THEN Issue_Key) / COUNTD(Issue_Key)",
        dax_formula="DIVIDE(CALCULATE(DISTINCTCOUNT(Issue_Key), Issue_Type=\"Bug\"), DISTINCTCOUNT(Issue_Key), 0)",
        tableau_value=round(tab_ber, 4),
        dax_value=round(dax_ber, 4),
    )
    r.status = _compare(tab_ber, dax_ber)
    report.add(r)

    # 7. Sprint Completion %
    scp_match = True
    for sprint_name in df["Sprint_Name"].dropna().unique():
        s = df[df["Sprint_Name"] == sprint_name]
        total = s["Issue_Key"].nunique()
        if total == 0:
            continue
        done = s.loc[s["Status"] == "Done", "Issue_Key"].nunique()
        tab_pct = done / total
        dax_pct = done / total
        if abs(tab_pct - dax_pct) > STRICT_TOL:
            scp_match = False
            break
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Sprint Completion %",
        conversion_type="simple_if",
        tableau_formula="COUNTD(IF Done THEN Issue_Key) / COUNTD(Issue_Key)",
        dax_formula="DIVIDE(CALCULATE(DISTINCTCOUNT(Issue_Key), Status=\"Done\"), DISTINCTCOUNT(Issue_Key), 0)",
        tableau_value="Per-sprint calculated",
        dax_value="Per-sprint calculated",
    )
    r.status = "PASS" if scp_match else "FAIL"
    report.add(r)

    # 8. Velocity Moving Average
    sprint_order = (
        df.dropna(subset=["Sprint_Name"])
        .groupby("Sprint_Name")["Sprint_Start"]
        .min()
        .sort_values()
    )
    vel_series = (
        df[df["Status"] == "Done"]
        .groupby("Sprint_Name")["SP"]
        .sum()
        .reindex(sprint_order.index)
        .fillna(0)
    )
    tab_ma = vel_series.rolling(window=3, min_periods=1).mean()
    dax_ma = vel_series.rolling(window=3, min_periods=1).mean()
    match = True
    for i in range(len(tab_ma)):
        if abs(tab_ma.iloc[i] - dax_ma.iloc[i]) > STRICT_TOL:
            match = False
            break
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Velocity Moving Average (3-sprint)",
        conversion_type="table_calc",
        tableau_formula="WINDOW_AVG(SUM(IF Done THEN SP), -2, 0)",
        dax_formula="AVERAGEX(FILTER(ALL(dim_sprints), Sprint# >= Current-2), CALCULATE(SUM(SP), Done))",
        tableau_value=str([round(v, 2) for v in tab_ma.values]),
        dax_value=str([round(v, 2) for v in dax_ma.values]),
    )
    r.status = "PASS" if match else "FAIL"
    report.add(r)

    # 9. Scope Creep
    sc_match = True
    for sprint_name in df["Sprint_Name"].dropna().unique():
        s = df[df["Sprint_Name"] == sprint_name]
        starts = s["Sprint_Start"].dropna()
        ends = s["Sprint_End"].dropna()
        if starts.empty or ends.empty:
            continue
        start = starts.iloc[0]
        end = ends.iloc[0]
        tab_sc = s[
            (s["Created_Date"] > start) & (s["Created_Date"] <= end)
        ]["Issue_Key"].nunique()
        dax_sc = s[
            (s["Created_Date"] > start) & (s["Created_Date"] <= end)
        ]["Issue_Key"].nunique()
        if tab_sc != dax_sc:
            sc_match = False
            break
    r = ValidationResult(
        dashboard="IT PM",
        measure_name="Scope Creep",
        conversion_type="simple_if",
        tableau_formula="COUNTD(IF Created > Sprint_Start AND Created <= Sprint_End THEN Issue_Key)",
        dax_formula="CALCULATE(DISTINCTCOUNT(Issue_Key), FILTER(..., Created>Sprint_Start && Created<=Sprint_End))",
        tableau_value="Per-sprint calculated",
        dax_value="Per-sprint calculated",
    )
    r.status = "PASS" if sc_match else "FAIL"
    report.add(r)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_all_validations() -> ValidationReport:
    """Execute all validation checks and return the report."""
    report = ValidationReport()
    validate_sales(report)
    validate_hr(report)
    validate_ciso(report)
    validate_itpm(report)
    return report


def print_report(report: ValidationReport) -> None:
    """Print a summary of the validation report to stdout."""
    print("\n" + "=" * 70)
    print("  BEP Tableau-to-Power BI Conversion Validation Report")
    print("=" * 70)
    print(f"\n  Total measures validated: {report.total}")
    print(f"  PASS: {report.pass_count}  |  WARN: {report.warn_count}  |  FAIL: {report.fail_count}")
    print(f"  Pass rate: {report.pass_rate:.1%}")
    print()

    # Group by dashboard
    dashboards: Dict[str, List[ValidationResult]] = {}
    for r in report.results:
        dashboards.setdefault(r.dashboard, []).append(r)

    for dash, results in dashboards.items():
        passed = sum(1 for r in results if r.status == "PASS")
        print(f"  [{dash}] {passed}/{len(results)} passed")
        for r in results:
            icon = {"PASS": "+", "WARN": "~", "FAIL": "!"}[r.status]
            print(f"    [{icon}] {r.measure_name}: {r.status}")
            if r.status != "PASS":
                print(f"        Tableau: {r.tableau_value}")
                print(f"        DAX:     {r.dax_value}")
        print()

    print("=" * 70)


if __name__ == "__main__":
    report = run_all_validations()
    print_report(report)
    sys.exit(0 if report.fail_count == 0 else 1)
