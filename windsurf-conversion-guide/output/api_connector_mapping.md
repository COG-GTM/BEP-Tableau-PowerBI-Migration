# API Connector Mapping: Tableau Data Sources → Power BI Equivalents

> **Purpose**: Map common Tableau data source connection types used in BEP's environment to their Power BI equivalents, including Power Query M code templates for API-based connections.

---

## Connector Mapping Overview

| # | Tableau Source | Power BI Equivalent | Connection Mode | Complexity |
|---|---------------|---------------------|-----------------|------------|
| 1 | Tenable.io API (REST) | Power Query M — `Web.Contents` with API key | Import (scheduled refresh) | Medium |
| 2 | JIRA REST API | Power Query M — `Web.Contents` with Basic/OAuth | Import (scheduled refresh) | Medium |
| 3 | Oracle Database (via ODI) | Power BI Oracle Connector or DirectQuery | DirectQuery or Import | Low |
| 4 | CSV / Excel Files | Power BI Import Mode — `Csv.Document` / `Excel.Workbook` | Import | Low |
| 5 | Tableau Hyper Extracts | Export to CSV → Power BI Import | Import | Medium |
| 6 | SQL Server | Power BI SQL Server Connector | DirectQuery or Import | Low |
| 7 | SharePoint Lists | Power BI SharePoint Connector | Import | Low |
| 8 | SCADA / OPC-UA (real-time) | Power BI Streaming Dataset or Azure IoT Hub | Push/Streaming | High |

---

## 1. Tenable.io API → Power Query M

### Tableau Connection (Current)
Tableau connects to Tenable via a Web Data Connector (WDC) or custom Python extract script that calls the `/vulns/export` API endpoint and writes results to a Hyper extract.

### Power BI Connection (Target)

**Connection Type**: Power Query M using `Web.Contents`
**Authentication**: API Key via `X-ApiKeys` header
**Refresh**: Scheduled refresh (minimum 1x daily for vulnerability data)

```m
// =====================================================
// Tenable.io Vulnerability Data — Power Query M
// =====================================================
// Prerequisites:
//   1. Create Power BI Parameters: TenableAccessKey, TenableSecretKey
//   2. Configure data source privacy: Organizational
//   3. For GCC High: Use FedRAMP Tenable endpoint
// =====================================================

let
    // Configuration — use Power BI Parameters for credentials
    BaseUrl = "https://cloud.tenable.com",
    
    // For FedRAMP environments, use:
    // BaseUrl = "https://fedcloud.tenable.com",
    
    AccessKey = Text.From(
        Excel.CurrentWorkbook(){[Name="TenableAccessKey"]}[Content]{0}[Column1]
    ),
    SecretKey = Text.From(
        Excel.CurrentWorkbook(){[Name="TenableSecretKey"]}[Content]{0}[Column1]
    ),
    ApiKeyHeader = "accessKey=" & AccessKey & ";secretKey=" & SecretKey,

    // Step 1: Initiate vulnerability export
    ExportBody = Json.FromValue([
        filters = [
            severity = {"Critical", "High", "Medium", "Low"}
        ],
        num_assets = 5000
    ]),
    
    ExportResponse = Json.Document(
        Web.Contents(BaseUrl & "/vulns/export", [
            Headers = [
                #"X-ApiKeys" = ApiKeyHeader,
                #"Content-Type" = "application/json"
            ],
            Content = ExportBody
        ])
    ),
    ExportUUID = ExportResponse[export_uuid],

    // Step 2: Wait for export completion
    // Note: In production, implement retry logic with Function.InvokeAfter
    StatusUrl = BaseUrl & "/vulns/export/" & ExportUUID & "/status",
    StatusResponse = Json.Document(
        Web.Contents(StatusUrl, [
            Headers = [#"X-ApiKeys" = ApiKeyHeader]
        ])
    ),
    AvailableChunks = StatusResponse[chunks_available],

    // Step 3: Download all chunks
    DownloadChunk = (chunkId as number) =>
        Json.Document(
            Web.Contents(
                BaseUrl & "/vulns/export/" & ExportUUID & "/chunks/" & Text.From(chunkId),
                [Headers = [#"X-ApiKeys" = ApiKeyHeader]]
            )
        ),
    
    AllData = List.Combine(
        List.Transform(AvailableChunks, each DownloadChunk(_))
    ),

    // Step 4: Convert to table and expand fields
    DataTable = Table.FromList(AllData, Splitter.SplitByNothing(), {"Record"}),
    Expanded = Table.ExpandRecordColumn(DataTable, "Record", {
        "asset", "plugin", "severity", "first_found", "last_found", "state"
    }),
    
    // Step 5: Flatten nested asset and plugin records
    ExpandAsset = Table.ExpandRecordColumn(Expanded, "asset", {
        "hostname", "ipv4", "operating_system"
    }, {"Asset_Hostname", "Asset_IP", "Asset_OS"}),
    
    ExpandPlugin = Table.ExpandRecordColumn(ExpandAsset, "plugin", {
        "id", "name", "cve", "cvss_base_score"
    }, {"Plugin_ID", "Plugin_Name", "CVE_List", "CVSS_Score"}),

    // Step 6: Extract first CVE from list
    AddCVE = Table.AddColumn(ExpandPlugin, "CVE_ID", each
        try Text.From(_[CVE_List]{0}) otherwise "N/A"
    ),

    // Step 7: Clean up and type
    CleanedTable = Table.SelectColumns(AddCVE, {
        "CVE_ID", "severity", "Asset_Hostname", "Plugin_ID", "Plugin_Name",
        "first_found", "last_found", "state", "CVSS_Score", "Asset_OS", "Asset_IP"
    }),
    
    TypedTable = Table.TransformColumnTypes(CleanedTable, {
        {"Plugin_ID", Int64.Type},
        {"CVSS_Score", type number},
        {"first_found", type datetime},
        {"last_found", type datetime}
    }),
    
    RenamedTable = Table.RenameColumns(TypedTable, {
        {"severity", "Severity"},
        {"first_found", "First_Seen"},
        {"last_found", "Last_Seen"},
        {"state", "Remediation_Status"}
    })
in
    RenamedTable
```

### FedRAMP Considerations
- Use `https://fedcloud.tenable.com` for FedRAMP Tenable instances
- API keys must be stored in Power BI Parameters or Azure Key Vault — never hardcoded
- Configure data source privacy as "Organizational" to prevent data leakage across queries
- Schedule refresh through Power BI Service in GCC High tenant

---

## 2. JIRA REST API → Power Query M

### Tableau Connection (Current)
Tableau connects to JIRA via a native JIRA connector or Web Data Connector that queries the `/rest/api/3/search` endpoint with JQL.

### Power BI Connection (Target)

**Connection Type**: Power Query M using `Web.Contents`
**Authentication**: Basic Auth (email + API token) or OAuth 2.0
**Refresh**: Scheduled refresh (1x-4x daily for project tracking)

```m
// =====================================================
// JIRA Cloud REST API — Power Query M
// =====================================================
// Prerequisites:
//   1. Create Power BI Parameters: JiraBaseUrl, JiraEmail, JiraApiToken
//   2. For JIRA Data Center (on-prem): Use different auth method
//   3. API Token: https://id.atlassian.com/manage-profile/security/api-tokens
// =====================================================

let
    // Configuration
    BaseUrl = Text.From(
        Excel.CurrentWorkbook(){[Name="JiraBaseUrl"]}[Content]{0}[Column1]
    ),
    Email = Text.From(
        Excel.CurrentWorkbook(){[Name="JiraEmail"]}[Content]{0}[Column1]
    ),
    ApiToken = Text.From(
        Excel.CurrentWorkbook(){[Name="JiraApiToken"]}[Content]{0}[Column1]
    ),
    
    // Basic Auth header
    AuthHeader = "Basic " & Binary.ToText(
        Text.ToBinary(Email & ":" & ApiToken, TextEncoding.Utf8),
        BinaryEncoding.Base64
    ),

    // JQL query — customize for your project
    JqlQuery = "project = UF ORDER BY created DESC",
    
    // Paginated fetch function
    GetPage = (startAt as number) =>
        let
            Response = Json.Document(
                Web.Contents(BaseUrl & "/rest/api/3/search", [
                    Headers = [
                        #"Authorization" = AuthHeader,
                        #"Accept" = "application/json"
                    ],
                    Query = [
                        jql = JqlQuery,
                        startAt = Text.From(startAt),
                        maxResults = "100",
                        fields = "issuetype,summary,status,priority,customfield_10020,customfield_10028,assignee,reporter,created,updated,resolutiondate,customfield_10014,labels,components"
                    ]
                ])
            )
        in
            Response,
    
    // Get first page to determine total
    FirstPage = GetPage(0),
    TotalIssues = FirstPage[total],
    
    // Generate all page offsets
    PageOffsets = List.Generate(
        () => 0,
        each _ < TotalIssues,
        each _ + 100
    ),
    
    // Fetch all pages
    AllPages = List.Transform(PageOffsets, each GetPage(_)),
    AllIssues = List.Combine(List.Transform(AllPages, each _[issues])),
    
    // Convert to table
    IssuesTable = Table.FromList(AllIssues, Splitter.SplitByNothing(), {"Record"}),
    
    // Expand key and fields
    ExpandKey = Table.ExpandRecordColumn(IssuesTable, "Record", {"key", "fields"}),
    
    // Expand issue fields
    ExpandFields = Table.ExpandRecordColumn(ExpandKey, "fields", {
        "issuetype", "summary", "status", "priority",
        "customfield_10028", "assignee", "reporter",
        "created", "updated", "resolutiondate",
        "customfield_10014", "labels", "components"
    }),
    
    // Flatten nested records
    FlattenRecords = Table.TransformColumns(ExpandFields, {
        {"issuetype", each try _[name] otherwise null},
        {"status", each try _[name] otherwise null},
        {"priority", each try _[name] otherwise null},
        {"assignee", each try _[displayName] otherwise "Unassigned"},
        {"reporter", each try _[displayName] otherwise "Unknown"},
        {"labels", each try Text.Combine(_, ",") otherwise ""},
        {"components", each try Text.Combine(List.Transform(_, each _[name]), ",") otherwise ""}
    }),
    
    // Rename columns
    RenamedTable = Table.RenameColumns(FlattenRecords, {
        {"key", "Issue_Key"},
        {"issuetype", "Issue_Type"},
        {"summary", "Summary"},
        {"status", "Status"},
        {"priority", "Priority"},
        {"customfield_10028", "Story_Points"},
        {"assignee", "Assignee"},
        {"reporter", "Reporter"},
        {"created", "Created_Date"},
        {"updated", "Updated_Date"},
        {"resolutiondate", "Resolved_Date"},
        {"customfield_10014", "Epic_Key"},
        {"labels", "Labels"},
        {"components", "Component"}
    }),
    
    // Set data types
    TypedTable = Table.TransformColumnTypes(RenamedTable, {
        {"Story_Points", Int64.Type},
        {"Created_Date", type datetime},
        {"Updated_Date", type datetime},
        {"Resolved_Date", type datetime}
    })
in
    TypedTable
```

### FedRAMP Considerations
- For JIRA Data Center (on-prem within FedRAMP boundary): Use `Web.Contents` with VPN/private endpoint
- For JIRA Cloud: Use OAuth 2.0 (3LO) for GCC High compliance
- Store API tokens in Azure Key Vault, reference via Power BI Parameters
- Restrict JQL queries to project-specific data to minimize data exposure

---

## 3. Oracle Database (via ODI) → Power BI Oracle Connector

### Tableau Connection (Current)
Tableau connects to Oracle via JDBC/ODBC driver, often through Oracle Data Integrator (ODI) staging tables.

### Power BI Connection (Target)

**Connection Type**: Power BI Oracle Database Connector
**Authentication**: Oracle wallet or username/password
**Mode**: DirectQuery (for real-time) or Import (for historical snapshots)

```
Power BI Desktop → Get Data → Oracle Database
  Server: oracle-db.bep.internal:1521/MESDB
  Mode: DirectQuery (recommended for production dashboards)
        Import (recommended for historical analysis)
  
  Advanced:
    SQL Statement: SELECT * FROM MES_OWNER.PRODUCTION_ORDERS WHERE ORDER_DATE >= SYSDATE - 365
```

### Prerequisites
- Install Oracle Client (32-bit and 64-bit) on the Power BI Gateway machine
- Configure `tnsnames.ora` with BEP database connection details
- For GCC High: Use Power BI On-premises Data Gateway within the FedRAMP boundary

---

## 4. CSV / Excel Files → Power BI Import Mode

### Tableau Connection (Current)
Tableau reads CSV files with configurable delimiters (semicolons for EU datasets in this repo).

### Power BI Connection (Target)

```m
// CSV Import with semicolon delimiter and EU number format
let
    Source = Csv.Document(
        File.Contents("C:\Data\Orders.csv"),
        [
            Delimiter = ";",
            Columns = 14,
            Encoding = 65001,  // UTF-8
            QuoteStyle = QuoteStyle.Csv
        ]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    
    // Handle EU decimal format (comma → period)
    FixDecimals = Table.TransformColumns(PromotedHeaders, {
        {"Sales", each Number.From(Text.Replace(_, ",", "."))},
        {"Profit", each Number.From(Text.Replace(_, ",", "."))},
        {"Discount", each Number.From(Text.Replace(_, ",", "."))}
    }),
    
    // Parse dates
    FixDates = Table.TransformColumnTypes(FixDecimals, {
        {"Order_Date", type date},
        {"Ship_Date", type date}
    })
in
    FixDates
```

### Key Differences from Tableau
- Tableau auto-detects delimiters; Power Query M requires explicit specification
- EU number formats (comma decimals) need manual `Text.Replace` before `Number.From`
- Power BI refreshes from file paths — use SharePoint or OneDrive for team access

---

## 5. Tableau Hyper Extracts → Power BI Import

### Conversion Approach

Tableau Hyper extracts (`.hyper` files) are proprietary binary files. They cannot be directly imported into Power BI. The conversion path is:

```
.twbx archive → Extract .hyper file → Convert to CSV → Import into Power BI
```

**Conversion Script (Python)**:

```python
# Requires: pip install tableauhyperapi
from tableauhyperapi import HyperProcess, Telemetry, Connection, TableName
import csv

def hyper_to_csv(hyper_path, output_csv):
    """Convert a Tableau Hyper extract to CSV."""
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, hyper_path) as connection:
            # Get all tables in the extract
            tables = connection.catalog.get_table_names("Extract")
            
            for table in tables:
                # Query all data
                result = connection.execute_list_query(
                    f"SELECT * FROM {table}"
                )
                
                # Get column names
                columns = connection.catalog.get_table_definition(table).columns
                col_names = [col.name.unescaped for col in columns]
                
                # Write to CSV
                with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(col_names)
                    writer.writerows(result)
    
    print(f"Converted {hyper_path} → {output_csv}")
```

### Power Query M for Converted CSV

```m
let
    Source = Csv.Document(
        File.Contents("converted_extract.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        // Add type conversions based on extracted schema
    })
in
    TypedTable
```

---

## FedRAMP Considerations for API Connections (GCC High)

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FedRAMP IL4 Boundary                                            │
│                                                                   │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │ Power BI     │    │ On-premises       │    │ Data Sources │   │
│  │ Service      │◄──►│ Data Gateway      │◄──►│              │   │
│  │ (GCC High)   │    │ (within boundary) │    │ - Oracle DB  │   │
│  │              │    │                    │    │ - SCADA      │   │
│  └──────────────┘    └──────────────────┘    │ - File Share │   │
│         │                                     │ - APIs       │   │
│         │                                     └──────────────┘   │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │ External APIs│ ← Must be FedRAMP authorized                   │
│  │ (via Gateway)│                                                │
│  │ - Tenable.io │                                                │
│  │ - JIRA Cloud │                                                │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Compliance Checklist for API Connections

| Requirement | Implementation |
|------------|----------------|
| **SC-8**: Encrypt in transit | All API calls use TLS 1.2+ |
| **IA-2**: Authenticate | API keys stored in Azure Key Vault, not in query text |
| **AU-2**: Audit API access | Power BI logs all refresh activities in audit log |
| **AC-4**: Information flow | On-premises Data Gateway controls data flow direction |
| **SC-28**: Encrypt at rest | Power BI GCC High encrypts all imported data |
| **CM-7**: Least functionality | API queries scoped to minimum required data |
| **SI-10**: Input validation | Power Query M validates API response schema |

### Recommended API Connection Pattern for GCC High

1. **Never hardcode credentials** in Power Query M scripts
2. **Use Power BI Parameters** for base URLs, project IDs, and non-sensitive config
3. **Use Azure Key Vault** for API keys, tokens, and passwords
4. **Configure On-premises Data Gateway** for all connections to internal systems
5. **Set data source privacy** to "Organizational" for all API connections
6. **Schedule refresh** during off-peak hours to minimize Gateway load
7. **Monitor refresh failures** via Power BI admin portal alerts
