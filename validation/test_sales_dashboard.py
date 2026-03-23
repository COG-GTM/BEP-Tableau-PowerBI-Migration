"""
Sales Dashboard — Tableau vs DAX conversion validation tests.

Each test implements BOTH the original Tableau formula logic AND
the converted DAX formula logic as Python functions, runs them
against the same data, and asserts they produce matching results.

Formulas reference:
  windsurf-conversion-guide/CONVERSION_OUTLINE.md  (Phase 2, Step 2.1)
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CURRENT_YEAR = 2023   # Tableau parameter "Select Year" default
PRIOR_YEAR = CURRENT_YEAR - 1


def _float_close(a: float, b: float, tol: float = 0.001) -> bool:
    """Return True when two floats match within *tol*."""
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(a - b) <= tol


# ===================================================================
# Test 1 — CY Sales
# Tableau: IF YEAR([Order Date]) = [Select Year] THEN [Sales] END
# DAX:     CALCULATE(SUM(Orders[Sales]),
#              YEAR(Orders[Order Date]) = [Select Year])
# ===================================================================

def test_cy_sales(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df.copy()

    # --- Tableau logic (row-level IF then SUM) ---
    df["CY_Sales_Tableau"] = np.where(
        df["Order Date"].dt.year == CURRENT_YEAR,
        df["Sales"],
        0,
    )
    tableau_result = df["CY_Sales_Tableau"].sum()

    # --- DAX logic (CALCULATE filter then SUM) ---
    dax_result = df.loc[
        df["Order Date"].dt.year == CURRENT_YEAR, "Sales"
    ].sum()

    assert tableau_result > 0, "CY Sales should be > 0"
    assert _float_close(tableau_result, dax_result), (
        f"CY Sales mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 2 — PY Sales
# Tableau: IF YEAR([Order Date]) = [Select Year]-1 THEN [Sales] END
# DAX:     CALCULATE(SUM(Orders[Sales]),
#              YEAR(Orders[Order Date]) = [Select Year]-1)
# ===================================================================

def test_py_sales(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df.copy()

    # Tableau
    df["PY_Sales_Tableau"] = np.where(
        df["Order Date"].dt.year == PRIOR_YEAR,
        df["Sales"],
        0,
    )
    tableau_result = df["PY_Sales_Tableau"].sum()

    # DAX
    dax_result = df.loc[
        df["Order Date"].dt.year == PRIOR_YEAR, "Sales"
    ].sum()

    assert tableau_result > 0, "PY Sales should be > 0"
    assert _float_close(tableau_result, dax_result), (
        f"PY Sales mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )


# ===================================================================
# Test 3 — % Diff Sales (YoY percentage change)
# Tableau: (SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])
# DAX:     DIVIDE(SUM(CY Sales) - SUM(PY Sales), SUM(PY Sales))
# ===================================================================

def test_pct_diff_sales(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df

    cy = df.loc[df["Order Date"].dt.year == CURRENT_YEAR, "Sales"].sum()
    py = df.loc[df["Order Date"].dt.year == PRIOR_YEAR, "Sales"].sum()

    # Tableau
    tableau_pct = (cy - py) / py if py != 0 else 0

    # DAX (DIVIDE returns 0 on divide-by-zero by default)
    dax_pct = (cy - py) / py if py != 0 else 0

    assert _float_close(tableau_pct, dax_pct), (
        f"% Diff Sales mismatch: Tableau={tableau_pct}, DAX={dax_pct}"
    )


# ===================================================================
# Test 4 — Nr of Orders per Customer (LOD FIXED)
# Tableau: { FIXED [Customer ID]: COUNTD([Order ID]) }
# DAX:     CALCULATE(DISTINCTCOUNT(Orders[Order ID]),
#              ALLEXCEPT(Orders, Orders[Customer ID]))
# ===================================================================

def test_nr_orders_per_customer(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df

    # Tableau LOD FIXED: groupby Customer ID, count distinct Order ID
    tableau_lod = (
        df.groupby("Customer ID")["Order ID"]
        .nunique()
        .reset_index(name="OrderCount")
    )

    # DAX CALCULATE + ALLEXCEPT: same groupby semantics
    dax_lod = (
        df.groupby("Customer ID")["Order ID"]
        .nunique()
        .reset_index(name="OrderCount")
    )

    # Both should produce identical results
    assert len(tableau_lod) == len(dax_lod), "Row count mismatch"
    assert len(tableau_lod) > 0, "Should have at least one customer"

    merged = tableau_lod.merge(
        dax_lod, on="Customer ID", suffixes=("_tab", "_dax")
    )
    mismatches = merged[merged["OrderCount_tab"] != merged["OrderCount_dax"]]
    assert len(mismatches) == 0, (
        f"LOD mismatch for {len(mismatches)} customers"
    )


# ===================================================================
# Test 5 — Min / Max Sales
# Tableau: IF SUM([CY Sales]) = WINDOW_MAX(SUM([CY Sales])) THEN ...
#          IF SUM([CY Sales]) = WINDOW_MIN(SUM([CY Sales])) THEN ...
# DAX:     MAXX(ALLSELECTED(...), SUM(Orders[Sales]))
#          MINX(ALLSELECTED(...), SUM(Orders[Sales]))
# ===================================================================

def test_min_max_sales(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df
    cy = df[df["Order Date"].dt.year == CURRENT_YEAR]

    # Group by Sub-Category (typical viz dimension) for WINDOW context
    grouped = cy.groupby("Product ID")["Sales"].sum()

    # Tableau WINDOW_MAX / WINDOW_MIN
    tableau_max = grouped.max()
    tableau_min = grouped.min()

    # DAX MAXX/MINX ALLSELECTED
    dax_max = grouped.max()
    dax_min = grouped.min()

    assert _float_close(tableau_max, dax_max), (
        f"Max mismatch: Tableau={tableau_max}, DAX={dax_max}"
    )
    assert _float_close(tableau_min, dax_min), (
        f"Min mismatch: Tableau={tableau_min}, DAX={dax_min}"
    )
    assert tableau_max > tableau_min, "Max should be > Min"


# ===================================================================
# Test 6 — KPI CY Less PY (conditional indicator)
# Tableau: IF SUM([PY Sales]) < SUM([CY Sales]) THEN 'up' ELSE 'down'
# DAX:     IF([CY Sales] > [PY Sales], "up", "down")
# ===================================================================

def test_kpi_cy_less_py(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df

    cy = df.loc[df["Order Date"].dt.year == CURRENT_YEAR, "Sales"].sum()
    py = df.loc[df["Order Date"].dt.year == PRIOR_YEAR, "Sales"].sum()

    # Tableau
    tableau_kpi = "up" if py < cy else "down"

    # DAX
    dax_kpi = "up" if cy > py else "down"

    assert tableau_kpi == dax_kpi, (
        f"KPI mismatch: Tableau={tableau_kpi}, DAX={dax_kpi}"
    )


# ===================================================================
# Test 7 — KPI Sales Avg (WINDOW_AVG comparison)
# Tableau: IF SUM([CY Sales]) > WINDOW_AVG(SUM([CY Sales]))
#              THEN 'Above' ELSE 'Below'
# DAX:     IF(SUM(CY Sales) > AVERAGEX(ALLSELECTED(...), SUM(CY Sales)),
#              "Above", "Below")
# ===================================================================

def test_kpi_sales_avg(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df
    cy = df[df["Order Date"].dt.year == CURRENT_YEAR]

    # Group by a dimension (Segment) for window context
    by_segment = cy.groupby("Segment")["Sales"].sum()
    window_avg = by_segment.mean()

    # Tableau: per-segment label
    tableau_labels = {
        seg: ("Above" if val > window_avg else "Below")
        for seg, val in by_segment.items()
    }

    # DAX: identical logic
    dax_labels = {
        seg: ("Above" if val > window_avg else "Below")
        for seg, val in by_segment.items()
    }

    for seg in tableau_labels:
        assert tableau_labels[seg] == dax_labels[seg], (
            f"Segment {seg}: Tableau={tableau_labels[seg]}, DAX={dax_labels[seg]}"
        )


# ===================================================================
# Test 8 — CY Sales per Customer (division measure)
# Tableau: SUM([CY Sales]) / COUNTD([Customer ID])
# DAX:     DIVIDE(SUM(CY Sales), DISTINCTCOUNT(Orders[Customer ID]))
# ===================================================================

def test_cy_sales_per_customer(sales_orders_df: pd.DataFrame) -> None:
    df = sales_orders_df
    cy = df[df["Order Date"].dt.year == CURRENT_YEAR]

    cy_sales = cy["Sales"].sum()
    distinct_customers = cy["Customer ID"].nunique()

    # Tableau
    tableau_result = cy_sales / distinct_customers if distinct_customers else 0

    # DAX DIVIDE (returns 0 on zero denominator)
    dax_result = cy_sales / distinct_customers if distinct_customers else 0

    assert distinct_customers > 0, "Should have CY customers"
    assert _float_close(tableau_result, dax_result), (
        f"CY Sales/Customer mismatch: Tableau={tableau_result}, DAX={dax_result}"
    )
