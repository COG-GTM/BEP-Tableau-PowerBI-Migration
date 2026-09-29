# Sales & Customer lakehouse pipeline

This pipeline keeps the existing converter PBIP intact and produces a separate
PBIP backed by Gold Delta tables. It extracts raw Tableau Hyper rows to Bronze,
deduplicates relationship dimensions in dbt Silver, computes Tableau date-part
and FIXED-LOD logic in dbt Gold, and generates base Power BI measures from the
MetricFlow definitions.

## Environment

From the repository root, create and install the pinned Python 3.12 environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r lakehouse\requirements.txt
```

## Convert, build, and generate

Run these commands from the repository root, in order:

```powershell
.\.venv\Scripts\python.exe -m tableau2pbip convert "projects/sales-dashboard-project/Sales & Customer Dashboards.twbx" --out migrations/sales-customer-dashboards/output
.\.venv\Scripts\python.exe -m lakehouse.run_pipeline
.\.venv\Scripts\python.exe -m lakehouse.powerbi.build_pbip
```

The pipeline accepts an optional `--twbx` path; without one it uses the Sales &
Customer workbook above. Delta tables are written beneath
`lakehouse/onelake/SalesCustomer/`. The generated project is
`migrations/sales-customer-dashboards/lakehouse/Sales & Customer Dashboards
(Lakehouse).pbip`; it uses the same report definition as the converter project
and reads only the Gold Delta tables. The generated measure-source inventory is
`lakehouse/powerbi/measure_sources.md`.

MetricFlow metrics can be queried from the dbt project after the pipeline has
built its semantic manifest:

```powershell
Push-Location lakehouse/dbt
mf query --metrics sales,profit,quantity,customers,orders,sales_per_customer --group-by row_id__order_year
Pop-Location
```

The dual-model DAX parity verifier takes the local Analysis Services ports of
the converter and lakehouse Power BI Desktop instances:

```powershell
.\.venv\Scripts\python.exe lakehouse\verify\verify_parity.py --converter-port <port> --lakehouse-port <port>
```

It writes row-level comparisons to `lakehouse/verify/out/parity_values.csv`
and a summary to `lakehouse/verify/out/parity_summary.json`.
