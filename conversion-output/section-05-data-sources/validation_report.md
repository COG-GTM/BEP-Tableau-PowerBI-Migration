# Section 05 — Data Sources — Conversion Validation Report

> **Source**: `tableau-source/course/tableau-files/Section 05 - Data Sources/extracted/Section 5 - Data Sources.twb`
> **Output**: `conversion-output/section-05-data-sources/`
> **Generated**: 2026-04-01
> **Status**: Conversion Complete — PASS

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 1 |
| Parameters Converted | 0 |
| Dashboards Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

---

## Calculated Fields Validation

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` | `IF(Orders[Sales] < 400, TRUE(), FALSE())` | PASS |

---

## Data Source Connections

The original Tableau workbook (`Section 5 - Data Sources.twb`) defines a federated data source named "Big Data Source" with the following CSV connections:

| Table | Source File | Delimiter | Encoding | Join Key |
|-------|-----------|-----------|----------|----------|
| Orders.csv | `C:/Tableau Data/Tableau-Sales-Dataset-Big/Orders.csv` | `;` (semicolon) | UTF-8 | — (fact table) |
| Customers.csv | Same directory | `;` (semicolon) | UTF-8 | Customer_ID |
| Products.csv | Same directory | `;` (semicolon) | UTF-8 | Product_ID |

### Data Source Details (from TWB XML)
- **Connection class**: `textscan` (CSV flat-file connection)
- **Locale**: `en_DE` (European number formatting: comma decimal, period thousands)
- **Currency**: Euro
- **Collection type**: Multi-table federated join (Orders — Customers — Products)

---

## Artifacts Generated

1. `dax_measures.dax` — 1 calculated column (Logic 400)
2. `model.tmdl` — Semantic model with Orders, Customers, Products, Date tables and relationships
3. `layout.json` — Single-page report layout with 4 visuals
4. `theme.json` — Tableau 10 color palette theme
5. `power_query.pq` — Power Query M scripts for 4 tables (Orders, Customers, Products, Date)
6. `validation_report.md` — This file

---

## Conversion Notes

### 1. Boolean Field Conversion
Tableau's `[Sales] < 400` creates a boolean dimension. In DAX, this is converted to a calculated column using `IF(Orders[Sales] < 400, TRUE(), FALSE())` which produces explicit TRUE/FALSE values for filtering and display.

### 2. Federated Data Source
The TWB defines a single federated connection (`federated.0mdvf951gd6rk51a49vsr1li2q1f`) that joins Orders, Customers, and Products CSVs. In Power BI, these are modeled as separate tables with explicit relationships in the TMDL model.

### 3. European Locale Handling
The source data uses `en_DE` locale with semicolon delimiters and comma decimal separators. Power Query M scripts handle this via `Delimiter=";"` and `Encoding=65001` (UTF-8).
