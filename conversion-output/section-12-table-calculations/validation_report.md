# Validation Report — Section 12: Table Calculations

## Summary
- **Total Calculated Fields**: 14
- **Converted**: 14
- **Conversion Rate**: 100%
- **Source**: Section 12 - Table Calculations.twb

## Categories
| Category | Count |
|----------|-------|
| Period Difference (LOOKUP) | 3 |
| Running Sum (RUNNING_SUM) | 3 |
| Rank (RANK / RANK_PERCENTILE) | 2 |
| Position (FIRST / LAST / INDEX) | 4 |
| Percentage Change | 1 |
| Offset Lookup (LOOKUP with offset) | 1 |

## Measure-by-Measure Validation

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Calculation1 (Period Diff) | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `OFFSET(-1, ...) pattern` | Converted |
| 2 | Calculation2 (Running Sum) | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE(SUM(...), FILTER(ALL(...)))` | Converted |
| 3 | Calculation3 (Rank Percentile) | `RANK_PERCENTILE(SUM([Sales]))` | `DIVIDE(COUNTROWS(FILTER(...)), ...)` | Converted |
| 4 | Calculation4 (Period Diff 2) | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `OFFSET(-1, ...) pattern` | Converted |
| 5 | Calculation1_1 (Pct Change) | `(ZN(...) - LOOKUP(...)) / ABS(LOOKUP(...))` | `DIVIDE(Current - Prev, ABS(Prev))` | Converted |
| 6 | Calculation1_Big (Running Sum) | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE(SUM(...), FILTER(ALL(...)))` | Converted |
| 7 | Calculation2_Last | `LAST()` | `COUNTROWS(ALLSELECTED(...)) - RANKX(...)` | Converted |
| 8 | Lookup_Sales | `LOOKUP(SUM([Sales]), 2)` | `OFFSET(2, ALLSELECTED(...))` | Converted |
| 9 | First_Sales | `IF FIRST() = 0 THEN SUM([Sales]) END` | `IF(RANKX(...) = 1, SUM(...), BLANK())` | Converted |
| 10 | Rank_Sales | `RANK(SUM([Sales]))` | `RANKX(ALLSELECTED(...), ..., DESC, Dense)` | Converted |
| 11 | Last_Pos | `LAST()` | `COUNTROWS(...) - RANKX(...)` | Converted |
| 12 | First_Pos | `FIRST()` | `RANKX(..., ASC, Dense) - 1` | Converted |
| 13 | Index_Pos | `INDEX()` | `RANKX(..., ASC, Dense)` | Converted |
| 14 | Running_Sales | `RUNNING_SUM(SUM([Sales]))` | `SUMX(FILTER(ADDCOLUMNS(...)))` | Converted |

## DAX Pattern Reference

### Table Calculation Mapping
| Tableau Function | DAX Pattern |
|-----------------|------------|
| `RUNNING_SUM` | `CALCULATE(SUM(...), FILTER(ALL(date), date <= current))` |
| `RANK` | `RANKX(ALLSELECTED(dim), measure, , DESC, Dense)` |
| `RANK_PERCENTILE` | `DIVIDE(COUNTROWS(FILTER(below)), total - 1)` |
| `FIRST()` | `RANKX(ALLSELECTED(dim), measure, , ASC, Dense) - 1` |
| `LAST()` | `COUNTROWS(ALLSELECTED(dim)) - RANKX(...)` |
| `INDEX()` | `RANKX(ALLSELECTED(dim), measure, , ASC, Dense)` |
| `LOOKUP(expr, offset)` | `CALCULATE(expr, OFFSET(n, ALLSELECTED(dim), ORDERBY(...)))` |

## Notes
- Tableau `RUNNING_SUM` is a table calculation that accumulates values across a partition. DAX equivalent uses `CALCULATE` with `FILTER(ALL(...))`.
- Tableau `RANK` maps to DAX `RANKX` with `ALLSELECTED` for the partition.
- Tableau `FIRST()` returns 0 for the first row; mapped to `RANKX(..., ASC) - 1`.
- Tableau `LAST()` returns 0 for the last row; mapped to `COUNTROWS - RANKX`.
- Tableau `LOOKUP(expr, n)` offsets by n positions; mapped to DAX `OFFSET` function.
- Tableau `RANK_PERCENTILE` computed via counting values below current / (total - 1).

## Data Sources
- **Orders**: `course/datasets/non-eu-dataset/small-dataset/Orders.csv`
- **Customers**: `course/datasets/non-eu-dataset/small-dataset/Customers.csv`
- **Products**: `course/datasets/non-eu-dataset/small-dataset/Products.csv`
