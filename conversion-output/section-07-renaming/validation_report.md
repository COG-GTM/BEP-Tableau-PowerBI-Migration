# Section 07 — Renaming — Conversion Validation Report

> **Source**: `tableau-source/course/tableau-files/Section 07 - Renaming/extracted/Section 7 - Renaming.twb`
> **Output**: `conversion-output/section-07-renaming/`
> **Generated**: 2026-04-01
> **Status**: Conversion Complete — PASS

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 3 |
| Parameters Converted | 0 |
| Dashboards Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

---

## Calculated Fields Validation

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Category (Short) | `[Category]` with aliases: Furniture->"F", Office Supplies->"O", Technology->"T" | `SWITCH(Orders[Category], "Furniture", "F", "Office Supplies", "O", "Technology", "T", Orders[Category])` | PASS |
| 2 | Logic 400 | `[Sales] < 400` | `IF(Orders[Sales] < 400, TRUE(), FALSE())` | PASS |
| 3 | Country (Short) | `[Country]` with aliases: France->"FR", Germany->"DE" | `SWITCH(Orders[Country], "France", "FR", "Germany", "DE", Orders[Country])` | PASS |

---

## Alias Mappings (from TWB XML)

### Category (Short)
Extracted from `<aliases>` element on column `[Category (copy)_2029997560728297472]`:
```xml
<alias key='"Furniture"' value='F' />
<alias key='"Office Supplies"' value='O' />
<alias key='"Technology"' value='T' />
```

### Country (Short)
Extracted from `<aliases>` element on column `[Country (copy)_2029997560728530946]`:
```xml
<alias key='"France"' value='FR' />
<alias key='"Germany"' value='DE' />
```

---

## Worksheets in Workbook

The TWB contains 2 worksheets:

| # | Worksheet Name | Description |
|---|---------------|-------------|
| 1 | Sheet 2 | Default worksheet |
| 2 | Sheet 3 | Additional worksheet |

---

## Artifacts Generated

1. `dax_measures.dax` — 3 calculated columns (Category (Short), Logic 400, Country (Short))
2. `model.tmdl` — Semantic model with Orders, Customers, Products, Date tables and 3 calculated columns
3. `layout.json` — Single-page report layout with 5 visuals demonstrating alias fields
4. `theme.json` — Tableau 10 color palette theme
5. `power_query.pq` — Power Query M scripts for 4 tables
6. `validation_report.md` — This file

---

## Conversion Notes

### 1. Tableau Alias/Rename Pattern
In Tableau, the "Renaming" section demonstrates creating calculated fields that are copies of existing columns (`[Category]`, `[Country]`) and then applying display aliases via the `<aliases>` XML element. This allows short labels (F, O, T, FR, DE) while preserving the original values.

### 2. DAX SWITCH for Alias Mapping
In Power BI/DAX, the equivalent pattern uses `SWITCH()` to map original values to their alias equivalents. The final parameter provides the default (original value) for any unmapped entries. This is more explicit than Tableau's alias mechanism and produces the same visual results.

### 3. Calculated Column Names
The TWB uses internal names like `[Category (copy)_2029997560728297472]` with a `caption` attribute of "Category (Short)". The Power BI artifacts use the human-readable caption as the column name.
