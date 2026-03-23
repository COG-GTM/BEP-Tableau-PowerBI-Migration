# CISO Cybersecurity Dashboard — Tableau-to-Power BI Conversion Guide

> **Source Data**: Tenable.io vulnerability export (`/vulns/export` endpoint)
> **Target**: Power BI Desktop / Power BI Service (GCC High)
> **Dataset**: `projects/ciso-cybersecurity-project/vulnerabilities.csv` (mock Tenable data)

---

## Data Model

### Star Schema Design

```
                    ┌─────────────────┐
                    │  dim_severity   │
                    │─────────────────│
                    │ Severity        │
                    │ CVSS_Range_Low  │
                    │ CVSS_Range_High │
                    │ Color_Code      │
                    │ Sort_Order      │
                    └────────┬────────┘
                             │
┌─────────────────┐    ┌─────┴──────────────┐    ┌─────────────────────┐
│ dim_business_   │    │  fact_vulnerabilities│    │    dim_assets        │
│   units         │    │────────────────────  │    │─────────────────────│
│─────────────────│    │ CVE_ID (PK)         │    │ Asset_Hostname (PK) │
│ Business_Unit   │◄───│ Severity (FK)       │───►│ Asset_OS            │
│  (PK)           │    │ Asset_Hostname (FK)  │    │ Asset_IP            │
│ BU_Head         │    │ Plugin_ID            │    │ Business_Unit (FK)  │
│ Risk_Tolerance  │    │ Plugin_Name          │    │ Asset_Type          │
└─────────────────┘    │ First_Seen           │    │ Criticality         │
                       │ Last_Seen            │    └─────────────────────┘
                       │ Remediated_Date      │
                       │ Remediation_Status   │
                       │ CVSS_Score           │
                       │ Business_Unit (FK)   │
                       └──────────────────────┘
```

### Relationships

| From Table | From Column | To Table | To Column | Cardinality | Cross-filter |
|-----------|-------------|----------|-----------|-------------|--------------|
| fact_vulnerabilities | Severity | dim_severity | Severity | Many-to-1 | Single |
| fact_vulnerabilities | Asset_Hostname | dim_assets | Asset_Hostname | Many-to-1 | Single |
| fact_vulnerabilities | Business_Unit | dim_business_units | Business_Unit | Many-to-1 | Single |

---

## Tableau Calculated Fields → DAX Conversion

### 1. Critical Open Count

**Tableau:**
```
IF [Severity] = 'Critical' AND [Remediation_Status] = 'Open'
THEN 1
ELSE 0
END
```

**DAX Measure:**
```dax
Critical Open Count =
CALCULATE(
    COUNTROWS(fact_vulnerabilities),
    fact_vulnerabilities[Severity] = "Critical",
    fact_vulnerabilities[Remediation_Status] = "Open"
)
```

### 2. High Open Count

**Tableau:**
```
IF [Severity] = 'High' AND [Remediation_Status] = 'Open'
THEN 1
ELSE 0
END
```

**DAX Measure:**
```dax
High Open Count =
CALCULATE(
    COUNTROWS(fact_vulnerabilities),
    fact_vulnerabilities[Severity] = "High",
    fact_vulnerabilities[Remediation_Status] = "Open"
)
```

### 3. Total Vulnerabilities

**Tableau:**
```
COUNTD([CVE_ID])
```

**DAX Measure:**
```dax
Total Vulnerabilities =
DISTINCTCOUNT(fact_vulnerabilities[CVE_ID])
```

### 4. Mean Time to Remediate (MTTR)

**Tableau:**
```
AVG(
    IF [Remediation_Status] = 'Remediated'
    THEN DATEDIFF('day', [First_Seen], [Remediated_Date])
    END
)
```

**DAX Measure:**
```dax
MTTR (Days) =
AVERAGEX(
    FILTER(
        fact_vulnerabilities,
        fact_vulnerabilities[Remediation_Status] = "Remediated"
            && NOT(ISBLANK(fact_vulnerabilities[Remediated_Date]))
    ),
    DATEDIFF(
        fact_vulnerabilities[First_Seen],
        fact_vulnerabilities[Remediated_Date],
        DAY
    )
)
```

### 5. Risk Score by Business Unit (LOD FIXED)

**Tableau (LOD Expression):**
```
{ FIXED [Business_Unit]:
    SUM(
        IF [Severity] = 'Critical' THEN [CVSS_Score] * 4
        ELSEIF [Severity] = 'High' THEN [CVSS_Score] * 3
        ELSEIF [Severity] = 'Medium' THEN [CVSS_Score] * 2
        ELSE [CVSS_Score] * 1
        END
    )
}
```

**DAX Measure:**
```dax
Risk Score by Business Unit =
CALCULATE(
    SUMX(
        fact_vulnerabilities,
        fact_vulnerabilities[CVSS_Score] *
        SWITCH(
            fact_vulnerabilities[Severity],
            "Critical", 4,
            "High", 3,
            "Medium", 2,
            1
        )
    ),
    ALLEXCEPT(fact_vulnerabilities, fact_vulnerabilities[Business_Unit])
)
```

**Conversion Notes:**
- Tableau's `{ FIXED [Business_Unit]: ... }` computes a value at the Business Unit grain regardless of viz-level filters
- DAX `CALCULATE` + `ALLEXCEPT` achieves the same effect: it removes all filter context except Business_Unit
- The `SWITCH` function replaces Tableau's nested `IF/ELSEIF` for cleaner code

### 6. Severity Distribution

**Tableau:**
```
COUNTD([CVE_ID])   // placed on Severity dimension
```

**DAX Measure:**
```dax
Vuln Count by Severity =
DISTINCTCOUNT(fact_vulnerabilities[CVE_ID])

// Used with Severity on axis/legend — DAX automatically slices by filter context
```

### 7. Remediation Rate

**Tableau:**
```
COUNTD(IF [Remediation_Status] = 'Remediated' THEN [CVE_ID] END)
/
COUNTD([CVE_ID])
```

**DAX Measure:**
```dax
Remediation Rate =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(fact_vulnerabilities[CVE_ID]),
        fact_vulnerabilities[Remediation_Status] = "Remediated"
    ),
    DISTINCTCOUNT(fact_vulnerabilities[CVE_ID]),
    0
)
```

### 8. Aging Vulnerabilities (>30 Days Open)

**Tableau:**
```
IF [Remediation_Status] = 'Open'
   AND DATEDIFF('day', [First_Seen], TODAY()) > 30
THEN 1
ELSE 0
END
```

**DAX Measure:**
```dax
Aging Vulnerabilities (>30d) =
CALCULATE(
    COUNTROWS(fact_vulnerabilities),
    fact_vulnerabilities[Remediation_Status] = "Open",
    DATEDIFF(
        fact_vulnerabilities[First_Seen],
        TODAY(),
        DAY
    ) > 30
)
```

### 9. CVSS Score Trend (Running Average)

**Tableau (Table Calculation):**
```
RUNNING_AVG(AVG([CVSS_Score]))
```

**DAX Measure:**
```dax
CVSS Running Average =
VAR CurrentDate = MAX(fact_vulnerabilities[First_Seen])
RETURN
AVERAGEX(
    FILTER(
        ALL(fact_vulnerabilities[First_Seen]),
        fact_vulnerabilities[First_Seen] <= CurrentDate
    ),
    CALCULATE(AVERAGE(fact_vulnerabilities[CVSS_Score]))
)
```

**Conversion Notes:**
- Tableau's `RUNNING_AVG` is a table calculation that operates across the visualization's partition
- DAX requires explicit date filtering via `FILTER(ALL(...))` to compute a running window
- Consider using the newer `WINDOW` DAX function (available in Power BI 2023+) for cleaner syntax

### 10. Top 10 Vulnerable Assets

**Tableau:**
```
RANK(COUNTD([CVE_ID]))   // with Top N filter = 10
```

**DAX Measure:**
```dax
Asset Vulnerability Rank =
RANKX(
    ALL(fact_vulnerabilities[Asset_Hostname]),
    DISTINCTCOUNT(fact_vulnerabilities[CVE_ID]),
    ,
    DESC,
    DENSE
)

// Apply visual-level filter: Asset Vulnerability Rank <= 10
```

---

## Power Query M Script — Tenable.io API Connection

```m
// Tenable.io Vulnerability Export — Power Query M Template
// Endpoint: https://cloud.tenable.com/vulns/export
// Auth: API Key (X-ApiKeys header)
// Note: For FedRAMP/GCC High, use the FedRAMP Tenable endpoint

let
    // --- Configuration ---
    // IMPORTANT: Store API keys in Power BI Parameters, NOT hardcoded
    TenableBaseUrl = "https://cloud.tenable.com",
    AccessKey = Text.From(Excel.CurrentWorkbook(){[Name="TenableAccessKey"]}[Content]{0}[Column1]),
    SecretKey = Text.From(Excel.CurrentWorkbook(){[Name="TenableSecretKey"]}[Content]{0}[Column1]),

    // --- Step 1: Initiate Export ---
    ExportRequest = Json.Document(
        Web.Contents(
            TenableBaseUrl & "/vulns/export",
            [
                Headers = [
                    #"X-ApiKeys" = "accessKey=" & AccessKey & ";secretKey=" & SecretKey,
                    #"Content-Type" = "application/json",
                    #"Accept" = "application/json"
                ],
                Content = Json.FromValue([
                    filters = [
                        severity = {"Critical", "High", "Medium", "Low"},
                        state = {"open", "reopened", "fixed"}
                    ],
                    num_assets = 500
                ])
            ]
        )
    ),
    ExportUUID = ExportRequest[export_uuid],

    // --- Step 2: Poll Export Status ---
    // In production, implement a polling loop; here we show the pattern
    StatusCheck = Json.Document(
        Web.Contents(
            TenableBaseUrl & "/vulns/export/" & ExportUUID & "/status",
            [
                Headers = [
                    #"X-ApiKeys" = "accessKey=" & AccessKey & ";secretKey=" & SecretKey
                ]
            ]
        )
    ),

    // --- Step 3: Download Chunks ---
    // Each chunk contains up to 10,000 vulnerabilities
    ChunkList = StatusCheck[chunks_available],
    DownloadChunk = (chunkId as number) =>
        Json.Document(
            Web.Contents(
                TenableBaseUrl & "/vulns/export/" & ExportUUID & "/chunks/" & Text.From(chunkId),
                [
                    Headers = [
                        #"X-ApiKeys" = "accessKey=" & AccessKey & ";secretKey=" & SecretKey
                    ]
                ]
            )
        ),

    // --- Step 4: Combine All Chunks ---
    AllChunks = List.Transform(ChunkList, each DownloadChunk(_)),
    CombinedData = List.Combine(AllChunks),
    AsTable = Table.FromList(CombinedData, Splitter.SplitByNothing(), {"Record"}),
    ExpandedRecords = Table.ExpandRecordColumn(AsTable, "Record", {
        "asset", "plugin", "severity", "severity_id",
        "first_found", "last_found", "state"
    }),

    // --- Step 5: Flatten Nested Fields ---
    ExpandAsset = Table.ExpandRecordColumn(ExpandedRecords, "asset", {
        "hostname", "ipv4", "operating_system", "fqdn"
    }, {"Asset_Hostname", "Asset_IP", "Asset_OS", "Asset_FQDN"}),

    ExpandPlugin = Table.ExpandRecordColumn(ExpandAsset, "plugin", {
        "id", "name", "cve", "cvss_base_score"
    }, {"Plugin_ID", "Plugin_Name", "CVE_ID", "CVSS_Score"}),

    // --- Step 6: Data Type Conversions ---
    TypedTable = Table.TransformColumnTypes(ExpandPlugin, {
        {"Plugin_ID", Int64.Type},
        {"CVSS_Score", type number},
        {"first_found", type datetime},
        {"last_found", type datetime},
        {"severity", type text}
    }),

    // --- Step 7: Rename and Clean ---
    RenamedCols = Table.RenameColumns(TypedTable, {
        {"first_found", "First_Seen"},
        {"last_found", "Last_Seen"},
        {"severity", "Severity"},
        {"state", "Remediation_Status"}
    }),

    // Capitalize severity values
    CleanedSeverity = Table.TransformColumns(RenamedCols, {
        {"Severity", each Text.Proper(_), type text}
    })
in
    CleanedSeverity
```

---

## Dashboard Layout Specification

### Page 1: Executive Summary

```
┌──────────────────────────────────────────────────────────────┐
│  CISO CYBERSECURITY VULNERABILITY DASHBOARD                  │
│  [Date Range Slicer]  [Business Unit Slicer]  [OS Slicer]   │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ CRITICAL │   HIGH   │  MEDIUM  │   LOW    │  TOTAL VULNS     │
│   ██     │    ██    │    ██    │    ██    │     ██           │
│  (red)   │ (orange) │ (yellow) │ (green)  │   (blue)         │
├──────────┴──────────┴──────────┼──────────┴──────────────────┤
│                                │                              │
│   Severity Distribution        │   Remediation Rate           │
│   [Donut Chart]                │   [KPI Card + Gauge]         │
│                                │                              │
│   ● Critical  5%              │   60% Remediated             │
│   ● High     15%              │   ████████████░░░░░░         │
│   ● Medium   40%              │                              │
│   ● Low      40%              │   MTTR: XX days              │
│                                │                              │
├────────────────────────────────┼──────────────────────────────┤
│                                │                              │
│   MTTR Trend Over Time         │   Top 10 Vulnerable Assets   │
│   [Line Chart]                 │   [Horizontal Bar Chart]     │
│                                │                              │
│   ──────/\───/──\──            │   SRV-IT-001  ████████ 12   │
│                                │   DC-CORE-003 ███████  10   │
│   X: Month                     │   WEB-DMZ-002 ██████    8   │
│   Y: Avg Days to Remediate     │   ...                       │
│                                │                              │
├────────────────────────────────┴──────────────────────────────┤
│                                                                │
│   Remediation Funnel                                           │
│   [Funnel Chart]                                               │
│                                                                │
│   Total (200) ──► Open (60) ──► In Progress ──► Remediated    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Page 2: Risk Heatmap by Business Unit

```
┌──────────────────────────────────────────────────────────────┐
│  RISK HEATMAP — BUSINESS UNIT × SEVERITY                     │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   [Matrix Visual with Conditional Formatting]                  │
│                                                                │
│                 Critical   High   Medium   Low    Risk Score   │
│   ─────────────────────────────────────────────────────────    │
│   Enterprise IT    ██3     ██8    ██15    ██12      187        │
│   Finance          ██1     ██4    ██10    ██8       98         │
│   Manufacturing    ██2     ██6    ██12    ██10      142        │
│   R&D              ██1     ██3    ██8     ██6       76         │
│   Supply Chain     ██0     ██2    ██6     ██5       48         │
│   ...                                                          │
│                                                                │
│   Color Scale: Green (low risk) → Yellow → Red (high risk)    │
│                                                                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   Aging Vulnerabilities (>30 Days Open)                        │
│   [Scatter Plot: X=Days Open, Y=CVSS Score, Size=Count]       │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Validation Approach

### Automated Validation Steps

1. **Row Count Check**: Verify Power BI imports all 200 rows from `vulnerabilities.csv`
2. **KPI Validation**: Compare Critical/High/Medium/Low counts between Python baseline and DAX measures
3. **MTTR Calculation**: Compute MTTR independently in Python and compare to DAX result (tolerance: ±0.1 days)
4. **LOD Validation**: Verify Risk Score by Business Unit matches Python `groupby` calculation
5. **Remediation Rate**: Cross-check percentage against manual count
6. **Top 10 Assets**: Verify ranking order matches Python `value_counts().head(10)`

### Python Validation Script Pattern

```python
import pandas as pd

df = pd.read_csv("vulnerabilities.csv")

# KPI validation
critical_open = len(df[(df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")])
high_open = len(df[(df["Severity"] == "High") & (df["Remediation_Status"] == "Open")])

# MTTR validation
remediated = df[df["Remediation_Status"] == "Remediated"].copy()
remediated["First_Seen"] = pd.to_datetime(remediated["First_Seen"])
remediated["Remediated_Date"] = pd.to_datetime(remediated["Remediated_Date"])
mttr = (remediated["Remediated_Date"] - remediated["First_Seen"]).dt.days.mean()

# Risk Score by Business Unit
df["Weighted_CVSS"] = df.apply(
    lambda r: r["CVSS_Score"] * {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}[r["Severity"]],
    axis=1
)
risk_by_bu = df.groupby("Business_Unit")["Weighted_CVSS"].sum()

print(f"Critical Open: {critical_open}")
print(f"High Open: {high_open}")
print(f"MTTR: {mttr:.1f} days")
print(f"\nRisk Score by BU:\n{risk_by_bu}")
```

### IV&V Compliance Artifacts

| Artifact | Description | NIST Control |
|----------|-------------|--------------|
| `conversion_validation_report.md` | Automated test results for all DAX measures | SA-11 |
| `data_type_mapping.md` | Column-level type comparison (Tableau → Power BI) | SI-12 |
| `kpi_baseline_values.json` | Frozen baseline values for regression testing | SA-11(1) |
| `audit_trail.log` | Timestamped log of all conversion steps | AU-2 |
