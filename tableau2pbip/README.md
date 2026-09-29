# Tableau to PBIP converter

## Add another workbook

Scaffold a starter layout and override directory, convert the workbook, validate
the semantic model with Microsoft's TOM serializer, then open the generated
`.pbip` file in Power BI Desktop:

```powershell
python -m tableau2pbip scaffold "projects/my-workbook.twbx" --out migrations/my-workbook
python -m tableau2pbip convert "projects/my-workbook.twbx" --out migrations/my-workbook/output
powershell -File tableau2pbip/validate_tmdl.ps1 "migrations/my-workbook/output/My Workbook.SemanticModel/definition"
```

Scaffolding refuses to replace an existing `layout.yml`; pass `--force` to
regenerate it. It copies workbook images into `migrations/my-workbook/images/`
and writes `SCAFFOLD_REPORT.md` with mapped dashboard zones, placeholders, and
calculations that need attention.

Scaffolded `native` visuals provide an editable starting point. To refine a
visual, replace its `type: native` entry in `layout.yml` with `type: deneb`,
choose a component and fields, and add the corresponding Deneb `spec`. Add
measure, calculated-column, calculated-table, or relationship refinements to
the sibling `overrides/` YAML files; conversion discovers those files by
default.
