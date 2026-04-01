# Validation Report — Section 13: Multi-Measures

## Summary
- **Total Calculated Fields**: 0
- **Converted**: 0 (no calculated fields in source)
- **Source**: Multi-Measures.twb
- **Dashboard**: "Dashboard 1" with 4 visual zones

## Workbook Characteristics
This workbook demonstrates Tableau's **Measure Names / Measure Values** pattern
for displaying multiple measures on a shared axis. No user-defined calculated
fields are present.

## Dashboard Zones (from .twb XML)
| Zone | Type | Description |
|------|------|-------------|
| Dual Axis | Line Chart | Sales & Profit on dual Y-axes over time |
| Individual Axis | Line Chart | Sales, Profit, Quantity each with own scale |
| Mixed | Combo Chart | Bar (Sales) + Line (Profit) over time |
| Single Axis (Measure Names) | Line Chart | Multiple measures on shared axis via Measure Names |

## Power BI Conversion Notes

### Measure Names / Measure Values -> Field Parameters
Tableau's Measure Names/Values is a built-in feature with no direct Power BI equivalent.
The recommended approach in Power BI is **Field Parameters**:

1. **Create a Field Parameter**: Modeling > New Parameter > Fields
2. **Add measures**: Select Sales, Profit, Quantity, Discount
3. **Use in visuals**: Place the Field Parameter on the axis, parameter values on the values well
4. **Result**: Users can dynamically select which measures appear on the chart

### Dual Axis -> Secondary Y-Axis
Tableau's dual axis maps to Power BI's secondary Y-axis feature:
- In a line/bar chart, drag a second measure to the "Line y-axis" well
- Right-click the visual > Format > Y-axis > Show secondary

### Combined Axis
For charts showing multiple measures on the same axis:
- Use Field Parameters (preferred)
- Or add multiple measures to the Values well of a line chart

## Standard Measures Used
| Measure | Formula | Description |
|---------|---------|-------------|
| Total Sales | `SUM(Orders[Sales])` | Sum of sales amount |
| Total Profit | `SUM(Orders[Profit])` | Sum of profit amount |
| Total Quantity | `SUM(Orders[Quantity])` | Sum of quantity |
| Total Discount | `SUM(Orders[Discount])` | Sum of discount |

## Data Sources
- **Orders**: `course/datasets/non-eu-dataset/small-dataset/Orders.csv`
- **Customers**: `course/datasets/non-eu-dataset/small-dataset/Customers.csv`
- **Products**: `course/datasets/non-eu-dataset/small-dataset/Products.csv`
