// ============================================================================
// CISO Cybersecurity Dashboard — Power Query M Scripts
// Source: windsurf-conversion-guide/CISO_CYBERSECURITY_CONVERSION.md
// ============================================================================


// ============================================================================
// SECTION 1: CSV Import (Local Data — vulnerabilities.csv)
// ============================================================================
// Use this query for local/demo data from the project dataset.
// File: projects/ciso-cybersecurity-project/vulnerabilities.csv

let
    // --- Step 1: Import CSV ---
    Source = Csv.Document(
        File.Contents("vulnerabilities.csv"),
        [Delimiter = ",", Columns = 13, Encoding = 65001, QuoteStyle = QuoteStyle.None]
    ),

    // --- Step 2: Promote Headers ---
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // --- Step 3: Set Data Types ---
    TypedColumns = Table.TransformColumnTypes(PromotedHeaders, {
        {"CVE_ID", type text},
        {"Severity", type text},
        {"Asset_Hostname", type text},
        {"Plugin_ID", Int64.Type},
        {"Plugin_Name", type text},
        {"First_Seen", type date},
        {"Last_Seen", type date},
        {"Remediated_Date", type date},
        {"Remediation_Status", type text},
        {"CVSS_Score", type number},
        {"Asset_OS", type text},
        {"Asset_IP", type text},
        {"Business_Unit", type text}
    }),

    // --- Step 4: Trim & Clean Text Columns ---
    TrimmedColumns = Table.TransformColumns(TypedColumns, {
        {"CVE_ID", Text.Trim, type text},
        {"Severity", Text.Trim, type text},
        {"Asset_Hostname", Text.Trim, type text},
        {"Plugin_Name", Text.Trim, type text},
        {"Remediation_Status", Text.Trim, type text},
        {"Asset_OS", Text.Trim, type text},
        {"Asset_IP", Text.Trim, type text},
        {"Business_Unit", Text.Trim, type text}
    }),

    // --- Step 5: Standardize Severity Values ---
    StandardizedSeverity = Table.TransformColumns(TrimmedColumns, {
        {"Severity", each Text.Proper(_), type text}
    }),

    // --- Step 6: Add Computed Columns ---
    AddDaysOpen = Table.AddColumn(StandardizedSeverity, "Days_Open", each
        if [Remediation_Status] = "Open" or [Remediation_Status] = "Accepted" then
            Duration.Days(DateTime.LocalNow() - DateTime.From([First_Seen]))
        else if [Remediated_Date] <> null then
            Duration.Days(DateTime.From([Remediated_Date]) - DateTime.From([First_Seen]))
        else
            null
    , Int64.Type),

    AddRemediationDays = Table.AddColumn(AddDaysOpen, "Remediation_Days", each
        if [Remediated_Date] <> null and [First_Seen] <> null then
            Duration.Days(DateTime.From([Remediated_Date]) - DateTime.From([First_Seen]))
        else
            null
    , Int64.Type),

    AddSLAStatus = Table.AddColumn(AddRemediationDays, "SLA_Status", each
        if [Remediation_Status] <> "Open" then "N/A"
        else if [Severity] = "Critical" and [Days_Open] > 7 then "Breached"
        else if [Severity] = "High" and [Days_Open] > 30 then "Breached"
        else if [Severity] = "Medium" and [Days_Open] > 90 then "Breached"
        else if [Severity] = "Low" and [Days_Open] > 180 then "Breached"
        else "Within SLA"
    , type text),

    // --- Step 7: Sort by Severity and CVSS Score ---
    SortedTable = Table.Sort(AddSLAStatus, {
        {"Severity", Order.Ascending},
        {"CVSS_Score", Order.Descending}
    })
in
    SortedTable


// ============================================================================
// SECTION 2: Dimension Table — dim_severity
// ============================================================================

let
    Source = #table(
        type table [
            Severity = text,
            CVSS_Range_Low = number,
            CVSS_Range_High = number,
            Color_Code = text,
            Sort_Order = Int64.Type
        ],
        {
            {"Critical", 9.0, 10.0, "#D32F2F", 1},
            {"High",     7.0,  8.9, "#FF6D00", 2},
            {"Medium",   4.0,  6.9, "#FFB300", 3},
            {"Low",      0.1,  3.9, "#388E3C", 4},
            {"Info",     0.0,  0.0, "#1976D2", 5}
        }
    )
in
    Source


// ============================================================================
// SECTION 3: Dimension Table — dim_assets
// ============================================================================

let
    Source = Csv.Document(
        File.Contents("vulnerabilities.csv"),
        [Delimiter = ",", Columns = 13, Encoding = 65001, QuoteStyle = QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // Select asset-relevant columns
    SelectedColumns = Table.SelectColumns(PromotedHeaders, {
        "Asset_Hostname", "Asset_OS", "Asset_IP", "Business_Unit"
    }),

    // Deduplicate by hostname
    UniqueAssets = Table.Distinct(SelectedColumns, {"Asset_Hostname"}),

    // Derive Asset_Type from hostname prefix
    AddAssetType = Table.AddColumn(UniqueAssets, "Asset_Type", each
        if Text.StartsWith([Asset_Hostname], "SRV") then "Server"
        else if Text.StartsWith([Asset_Hostname], "WEB") then "Web Server"
        else if Text.StartsWith([Asset_Hostname], "DB") then "Database"
        else if Text.StartsWith([Asset_Hostname], "DC") then "Domain Controller"
        else if Text.StartsWith([Asset_Hostname], "APP") then "Application"
        else if Text.StartsWith([Asset_Hostname], "WKS") then "Workstation"
        else if Text.StartsWith([Asset_Hostname], "PLC") then "PLC/ICS"
        else if Text.StartsWith([Asset_Hostname], "HMI") then "HMI/ICS"
        else if Text.StartsWith([Asset_Hostname], "LAB") then "Lab System"
        else if Text.StartsWith([Asset_Hostname], "WMS") then "Warehouse Mgmt"
        else if Text.StartsWith([Asset_Hostname], "DEV") then "Development"
        else "Other"
    , type text),

    // Derive Criticality from hostname prefix
    AddCriticality = Table.AddColumn(AddAssetType, "Criticality", each
        if Text.StartsWith([Asset_Hostname], "DC") then "Critical"
        else if Text.StartsWith([Asset_Hostname], "DB") then "Critical"
        else if Text.StartsWith([Asset_Hostname], "WEB") then "High"
        else if Text.StartsWith([Asset_Hostname], "SRV") then "High"
        else if Text.StartsWith([Asset_Hostname], "APP") then "High"
        else if Text.StartsWith([Asset_Hostname], "PLC") then "High"
        else if Text.StartsWith([Asset_Hostname], "HMI") then "Medium"
        else if Text.StartsWith([Asset_Hostname], "WKS") then "Medium"
        else "Low"
    , type text),

    // Set column types
    TypedTable = Table.TransformColumnTypes(AddCriticality, {
        {"Asset_Hostname", type text},
        {"Asset_OS", type text},
        {"Asset_IP", type text},
        {"Business_Unit", type text},
        {"Asset_Type", type text},
        {"Criticality", type text}
    })
in
    TypedTable


// ============================================================================
// SECTION 4: Dimension Table — dim_business_units
// ============================================================================

let
    Source = #table(
        type table [
            Business_Unit = text,
            BU_Head = text,
            Risk_Tolerance = text
        ],
        {
            {"Enterprise IT",            "VP of Infrastructure",     "Low"},
            {"Finance & Accounting",     "CFO",                      "Very Low"},
            {"Manufacturing Operations", "VP of Manufacturing",      "Medium"},
            {"Human Resources",          "CHRO",                     "Medium"},
            {"Research & Development",   "CTO",                      "High"},
            {"Supply Chain",             "VP of Supply Chain",       "Medium"},
            {"Legal & Compliance",       "General Counsel",          "Very Low"},
            {"Executive Office",         "COO",                      "Low"}
        }
    )
in
    Source


// ============================================================================
// SECTION 5: Tenable.io API Connection (Production Template)
// ============================================================================
// Endpoint: https://cloud.tenable.com/vulns/export
// Auth: API Key (X-ApiKeys header)
// Note: For FedRAMP/GCC High, use the FedRAMP Tenable endpoint
// IMPORTANT: Store API keys in Power BI Parameters, NOT hardcoded

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
