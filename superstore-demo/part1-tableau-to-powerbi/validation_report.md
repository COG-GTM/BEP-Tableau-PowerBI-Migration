# PBIP validation report

- Tables: 7  |  Measures: 32  |  JSON documents: 28
- Checks passed: 227/227

All checks passed.


## What was checked

- every JSON/PBIR/PBISM file parses and declares `$schema`
- every TMDL table has a partition; every measure's DAX has balanced `()`/`[]`
- every `Table[Column]` and `[Measure]` referenced in DAX resolves to the model
- every field bound to a report visual resolves to a model column or measure
- every relationship end points at an existing column

Not checked here (needs Power BI Desktop / Fabric): DAX evaluation, rendering. Number parity is covered by `scripts/number_check.py`.
