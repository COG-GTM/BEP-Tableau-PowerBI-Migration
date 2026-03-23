# Devin Batch Automation Workflow for Tableau-to-Power BI Migration

> **Purpose**: Document how Devin serves as the batch automation engine for at-scale Tableau-to-Power BI conversions, complementing Windsurf as the interactive development tool.

---

## Overview: Windsurf + Devin — Two Tools, One Workflow

| Capability | Windsurf | Devin |
|-----------|----------|-------|
| **Role** | Interactive development & conversion | Batch automation & scaling |
| **Use Case** | Convert a single workbook with developer oversight | Convert 10-120 workbooks automatically |
| **Interaction** | Real-time IDE with AI pair programming | Autonomous agent with PR-based output |
| **Output** | Code changes in the editor | Pull requests with full conversion artifacts |
| **Best For** | Complex dashboards requiring human judgment | Repeatable conversions at scale |
| **FedRAMP** | IL4 authorized | IL4 authorized (same security boundary) |

### How They Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                    Migration Workflow                             │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │  1. Windsurf  │    │  2. Windsurf  │    │  3. Devin    │        │
│  │  Prototype    │───►│  Refine      │───►│  Scale       │        │
│  │              │    │              │    │              │        │
│  │ Convert 1-2  │    │ Perfect the  │    │ Run batch    │        │
│  │ workbooks    │    │ conversion   │    │ conversion   │        │
│  │ interactively│    │ patterns     │    │ across all   │        │
│  │              │    │              │    │ workbooks    │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│  Sales Dashboard      CISO Dashboard       120 Production        │
│  (reference impl)     (pattern refined)     Dashboards           │
│                                              (batch PRs)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Batch Conversion Workflow

### Phase 1: Manifest-Driven Processing

Devin reads a manifest file listing all `.twbx` files to convert. The manifest includes metadata that guides conversion complexity and priority.

**Manifest File Format** (`migration_manifest.yaml`):

```yaml
# Tableau-to-Power BI Migration Manifest
# Devin reads this file to determine which workbooks to convert

project: BEP-MES-Migration
target_format: power_bi_dax_tmdl
validation: enabled
pr_strategy: single  # "single" = one PR for all, "per_workbook" = one PR each

workbooks:
  - path: projects/sales-dashboard-project/Sales & Customer Dashboards.twbx
    complexity: high
    priority: 1
    calculated_fields: 30
    lod_expressions: 5
    dashboards: 2
    notes: "Reference implementation — use as conversion pattern template"

  - path: projects/hr-dashboard-project/HR Dashboard.twbx
    complexity: medium
    priority: 2
    calculated_fields: 20
    lod_expressions: 2
    dashboards: 2
    notes: "Workforce analytics — maps to BEP ECF/WCF staffing"

  - path: course/tableau-files/Section 12 - LOD Expressions.twbx
    complexity: high
    priority: 3
    calculated_fields: 8
    lod_expressions: 8
    dashboards: 0
    notes: "Pure LOD conversion — FIXED, INCLUDE, EXCLUDE patterns"

  - path: course/tableau-files/Section 12 - Table Calculations.twbx
    complexity: high
    priority: 4
    calculated_fields: 15
    lod_expressions: 0
    dashboards: 0
    notes: "RUNNING_SUM, RANK, LOOKUP — requires DAX window functions"

  # ... additional workbooks listed here
```

### Phase 2: 7-Phase Pipeline (Per Workbook)

For each workbook in the manifest, Devin executes the same 7-phase pipeline documented in `CONVERSION_OUTLINE.md`:

```
┌─────────────────────────────────────────────────────────────────┐
│  Devin Pipeline — Per Workbook                                   │
│                                                                   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐   │
│  │Phase │  │Phase │  │Phase │  │Phase │  │Phase │  │Phase │   │
│  │  1   │─►│  2   │─►│  3   │─►│  4   │─►│  5   │─►│  6   │   │
│  │Parse │  │Calc  │  │Data  │  │Layout│  │Filter│  │Valid-│   │
│  │.twbx │  │Field │  │Model │  │& Viz │  │& Int │  │ation │   │
│  │      │  │→ DAX │  │→ TMDL│  │→ JSON│  │→ Spec│  │Script│   │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘   │
│                                                       │          │
│                                                       ▼          │
│                                                  ┌──────┐        │
│                                                  │Phase │        │
│                                                  │  7   │        │
│                                                  │Output│        │
│                                                  │Files │        │
│                                                  └──────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Artifact Generation

For each converted workbook, Devin produces:

| Artifact | Format | Description |
|----------|--------|-------------|
| DAX measures file | `.dax` | All converted calculated fields |
| TMDL model | `.tmdl` (directory) | Full Power BI data model |
| Layout specification | `.json` | Dashboard layout for Power BI |
| Theme file | `.json` | Visual styling and color palette |
| Power Query M scripts | `.pq` | Data source connection templates |
| Validation script | `.py` | Automated conversion accuracy tests |
| Validation report | `.md` | Test results with pass/fail summary |

### Phase 4: PR Creation

Devin creates a Pull Request with all conversion artifacts organized by workbook:

```
conversion-output/
├── sales-dashboard/
│   ├── dax_measures.dax
│   ├── model.tmdl
│   ├── layout.json
│   ├── theme.json
│   ├── power_query.pq
│   ├── validate.py
│   └── validation_report.md
├── hr-dashboard/
│   ├── dax_measures.dax
│   ├── model.tmdl
│   └── ...
├── migration_tracker.md         ← Overall status
├── conversion_summary.md        ← Executive summary
└── validation_summary.md        ← Aggregate test results
```

---

## Migration Tracker Template

Use this template to track conversion progress across all workbooks.

| Dashboard Name | Complexity | Calc Fields | LOD Expr | Status | PR Link | Notes |
|---------------|-----------|-------------|----------|--------|---------|-------|
| Sales & Customer Dashboards | High | 30+ | 5 | Converted | [PR #1](#) | Reference implementation |
| HR Dashboard | Medium | 20+ | 2 | Converted | [PR #1](#) | Workforce analytics |
| CISO Cybersecurity Dashboard | High | 10 | 1 | Converted | [PR #2](#) | Tenable data source |
| IT Project Management Dashboard | High | 10 | 0 | Converted | [PR #2](#) | JIRA data source |
| LOD Expressions | High | 8 | 8 | Pending | — | Pure LOD patterns |
| Table Calculations | High | 15 | 0 | Pending | — | Window functions |
| Row Level Calculations | Medium | 131 | 0 | Pending | — | High field count |
| Aggregate Calculations | Low | 14 | 0 | Pending | — | Standard aggregations |
| Parameters | Medium | 12 | 0 | Pending | — | What-If parameters |
| 63 Charts | High | 39 | 0 | Pending | — | Complex visualizations |
| Dashboard Layout | Low | 3 | 0 | Pending | — | Container patterns |
| Actions | Medium | 9 | 0 | Pending | — | Filter/highlight/URL |
| Filtering Data | Low | 5 | 0 | Pending | — | Dimension/measure filters |
| Organizing Data | Low | 0 | 0 | Pending | — | Groups, sets, bins |
| Renaming | Low | 0 | 0 | Pending | — | Aliases, formatting |
| Metadata | Low | 2 | 0 | Pending | — | Data types |
| Data Sources | Low | 1 | 0 | Pending | — | Joins, unions |

**Summary**: 4/17 Converted | 0 In Progress | 13 Pending

---

## Sample Devin Session Prompts

### Prompt A: Full Batch Conversion

```
Convert all .twbx files in this repository to Power BI DAX and TMDL format.

For each workbook:
1. Parse the .twbx archive and extract the .twb XML
2. Inventory all calculated fields, data sources, and dashboard layouts
3. Convert each Tableau calculated field to an equivalent DAX measure
4. Generate a TMDL data model with proper relationships and a Date table
5. Create a Power BI layout specification (JSON)
6. Write a Python validation script that proves conversion accuracy
7. Run the validation and include the report

Follow the conversion patterns established in CONVERSION_OUTLINE.md.
Output all artifacts under conversion-output/{workbook-name}/.
Create a single PR with all conversions and include a migration tracker.
```

### Prompt B: Migration Inventory Report

```
Generate a comprehensive migration inventory report for all Tableau workbooks
in this repository.

For each .twbx file:
1. Parse the archive structure (list internal files and sizes)
2. Count calculated fields and classify by type:
   - Simple (IF/THEN, aggregations)
   - LOD expressions (FIXED, INCLUDE, EXCLUDE)
   - Table calculations (RUNNING_SUM, RANK, WINDOW_*)
   - Parameters
3. Count dashboards and worksheets
4. Identify data source types (CSV, Hyper, live connection)
5. Estimate conversion complexity (Low/Medium/High)
6. Estimate conversion effort (hours)

Output a migration_inventory.md with:
- Summary statistics (total fields, total LODs, etc.)
- Per-workbook breakdown table
- Complexity distribution chart (markdown)
- Recommended conversion order (dependencies, complexity)
- Total estimated effort
```

### Prompt C: Validation Suite

```
Run validation scripts across all converted dashboards and produce a summary
report.

For each conversion in conversion-output/:
1. Execute the validate_*.py script
2. Capture pass/fail/warn results
3. For any failures, provide:
   - The Tableau formula
   - The DAX formula
   - Expected value
   - Actual value
   - Suggested fix

Generate validation_summary.md with:
- Overall pass rate (target: 100%)
- Results grouped by conversion type (simple, LOD, table calc, parameter)
- Any fields requiring manual review
- Regression comparison against previous run (if available)

This report will be provided to the IV&V team as evidence of conversion
accuracy per NIST SA-11 requirements.
```

---

## Scaling Narrative: 17 Workbooks → 120 Production Dashboards

### Current State (Demo Repository)

```
17 sample workbooks → ~300 calculated fields → Devin converts in ~2 hours
```

### Target State (BEP Production)

```
120 production dashboards → ~2,000+ calculated fields → Devin converts in ~2 weeks
```

### How Devin Scales

| Dimension | 17 Workbooks (Demo) | 120 Dashboards (Production) |
|-----------|--------------------|-----------------------------|
| Calculated Fields | ~300 | ~2,000+ |
| LOD Expressions | ~20 | ~200+ |
| Table Calculations | ~30 | ~300+ |
| Data Sources | CSV files | Oracle ODI, SCADA, APIs |
| Devin Sessions | 1 session | 10-15 parallel sessions |
| PRs Created | 1 PR | 10-20 PRs (batched by domain) |
| Validation Tests | ~100 | ~1,000+ |
| Elapsed Time | ~2 hours | ~2 weeks |
| Human Review | 1 developer | 2-3 developers (review PRs) |

### Parallel Processing Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│  Devin Batch Processing — Parallel Sessions                      │
│                                                                   │
│  Session 1: Production dashboards (10 workbooks)                 │
│  Session 2: Quality dashboards (8 workbooks)                     │
│  Session 3: Distribution dashboards (12 workbooks)               │
│  Session 4: Workforce dashboards (6 workbooks)                   │
│  Session 5: Executive dashboards (5 workbooks)                   │
│  ...                                                              │
│  Session N: Remaining workbooks                                   │
│                                                                   │
│  Each session:                                                    │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │ Parse  │─►│Convert │─►│Validate│─►│Generate│─►│  PR    │    │
│  │ .twbx  │  │ → DAX  │  │ Tests  │  │ Output │  │ Create │    │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## FedRAMP Compliance

### Security Boundary

Devin operates within the same FedRAMP IL4 security boundary as Windsurf:

| Control | Implementation |
|---------|----------------|
| **AC-2** Account Management | Devin sessions authenticated via organization SSO |
| **AU-2** Audit Events | All Devin actions logged with timestamps and session IDs |
| **CM-3** Configuration Change Control | All changes delivered via Pull Requests — no direct commits |
| **IA-2** Identification & Authentication | Multi-factor authentication required |
| **SC-8** Transmission Confidentiality | All data in transit encrypted via TLS 1.2+ |
| **SC-28** Protection of Information at Rest | Data at rest encrypted via AES-256 |
| **SI-10** Information Input Validation | All generated code validated against conversion rules |

### Key Compliance Features

1. **PR-Based Workflow**: Every conversion is delivered as a Pull Request, creating an auditable chain of custody. No code is deployed without human review.

2. **Validation Artifacts**: Each conversion includes automated validation scripts that serve as IV&V evidence per NIST SA-11.

3. **No Data Exfiltration**: Devin processes data within the FedRAMP boundary. Source data (Tableau workbooks, CSVs) never leaves the accredited environment.

4. **Session Isolation**: Each Devin session runs in an isolated environment. Sessions cannot access data from other sessions or organizations.

5. **Audit Trail**: Complete session logs are available for compliance review, including every file read, every command executed, and every PR created.

---

## Integration with Existing Tooling

### Git-Based Workflow

```
Developer                    Devin                     GitHub
   │                          │                          │
   │  1. Push manifest.yaml   │                          │
   │─────────────────────────►│                          │
   │                          │                          │
   │                          │  2. Parse manifest       │
   │                          │  3. Process workbooks    │
   │                          │  4. Generate artifacts   │
   │                          │                          │
   │                          │  5. Push branch          │
   │                          │─────────────────────────►│
   │                          │                          │
   │                          │  6. Create PR            │
   │                          │─────────────────────────►│
   │                          │                          │
   │  7. Review PR                                       │
   │◄────────────────────────────────────────────────────│
   │                          │                          │
   │  8. Approve & Merge                                 │
   │────────────────────────────────────────────────────►│
```

### JIRA Integration

Devin can automatically update JIRA tickets as workbooks are converted:

- **On Start**: Move ticket to "In Progress"
- **On Completion**: Move ticket to "In Review", attach PR link
- **On Validation Pass**: Add comment with test results
- **On Merge**: Move ticket to "Done"
