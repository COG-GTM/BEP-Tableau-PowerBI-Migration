// =============================================================================
// IT Project Management Dashboard — Power Query M Scripts
// Source: windsurf-conversion-guide/IT_PROJECT_MGMT_CONVERSION.md
// =============================================================================
// This file contains two data source approaches:
//   1. Local CSV Import (for development / demo with jira_issues.csv)
//   2. JIRA REST API Template (for production use)
// =============================================================================


// =============================================================================
// SECTION 1: LOCAL CSV IMPORT — fact_issues
// =============================================================================
// Imports the local jira_issues.csv dataset with proper data type conversions.
// Use this for development, testing, and demo scenarios.
// =============================================================================

let
    // --- Step 1: Import CSV ---
    Source = Csv.Document(
        File.Contents("projects/it-project-mgmt-project/jira_issues.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // --- Step 2: Data Type Conversions ---
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"Issue_Key", type text},
        {"Issue_Type", type text},
        {"Summary", type text},
        {"Status", type text},
        {"Priority", type text},
        {"Sprint_Name", type text},
        {"Sprint_Start", type date},
        {"Sprint_End", type date},
        {"Story_Points", Int64.Type},
        {"Assignee", type text},
        {"Reporter", type text},
        {"Created_Date", type date},
        {"Updated_Date", type date},
        {"Resolved_Date", type date},
        {"Epic_Key", type text},
        {"Labels", type text},
        {"Component", type text}
    }),

    // --- Step 3: Clean Null Values ---
    CleanedTable = Table.ReplaceValue(
        TypedTable, null, "Unassigned",
        Replacer.ReplaceValue, {"Assignee"}
    ),
    CleanedLabels = Table.ReplaceValue(
        CleanedTable, null, "",
        Replacer.ReplaceValue, {"Labels"}
    ),
    CleanedComponent = Table.ReplaceValue(
        CleanedLabels, null, "",
        Replacer.ReplaceValue, {"Component"}
    )
in
    CleanedComponent;


// =============================================================================
// SECTION 2: SPRINT DIMENSION EXTRACTION — dim_sprints
// =============================================================================
// Extracts distinct sprints from the issues data and adds Sprint_Number
// for ordering. Used by the Velocity 3-Sprint Moving Avg DAX measure.
// =============================================================================

let
    // --- Step 1: Import Source Data ---
    Source = Csv.Document(
        File.Contents("projects/it-project-mgmt-project/jira_issues.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // --- Step 2: Select Sprint Columns ---
    SelectedCols = Table.SelectColumns(PromotedHeaders, {
        "Sprint_Name", "Sprint_Start", "Sprint_End"
    }),

    // --- Step 3: Get Distinct Sprints ---
    DistinctSprints = Table.Distinct(SelectedCols),

    // --- Step 4: Filter Out Null Sprint Names ---
    FilteredSprints = Table.SelectRows(DistinctSprints, each
        [Sprint_Name] <> null and [Sprint_Name] <> ""
    ),

    // --- Step 5: Convert Date Types ---
    TypedDates = Table.TransformColumnTypes(FilteredSprints, {
        {"Sprint_Start", type date},
        {"Sprint_End", type date}
    }),

    // --- Step 6: Sort by Sprint Start Date ---
    SortedSprints = Table.Sort(TypedDates, {{"Sprint_Start", Order.Ascending}}),

    // --- Step 7: Add Sprint_Number (1-based index for DAX ordering) ---
    AddSprintNumber = Table.AddIndexColumn(
        SortedSprints, "Sprint_Number", 1, 1, Int64.Type
    )
in
    AddSprintNumber;


// =============================================================================
// SECTION 3: ASSIGNEE DIMENSION EXTRACTION — dim_assignees
// =============================================================================
// Extracts distinct assignees and enriches with team/role/capacity metadata.
// =============================================================================

let
    Source = Csv.Document(
        File.Contents("projects/it-project-mgmt-project/jira_issues.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    SelectedCols = Table.SelectColumns(PromotedHeaders, {"Assignee"}),
    DistinctAssignees = Table.Distinct(SelectedCols),
    FilteredNulls = Table.SelectRows(DistinctAssignees, each
        [Assignee] <> null and [Assignee] <> ""
    ),
    AddTeam = Table.AddColumn(FilteredNulls, "Team", each "Engineering", type text),
    AddRole = Table.AddColumn(AddTeam, "Role", each "Developer", type text),
    AddCapacity = Table.AddColumn(AddRole, "Capacity_Points", each 13, Int64.Type)
in
    AddCapacity;


// =============================================================================
// SECTION 4: EPIC DIMENSION EXTRACTION — dim_epics
// =============================================================================
// Extracts Epic-type issues as dimension rows with summary, status, and owner.
// =============================================================================

let
    Source = Csv.Document(
        File.Contents("projects/it-project-mgmt-project/jira_issues.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    FilteredEpics = Table.SelectRows(PromotedHeaders, each [Issue_Type] = "Epic"),
    SelectedCols = Table.SelectColumns(FilteredEpics, {
        "Issue_Key", "Summary", "Status", "Assignee"
    }),
    RenamedCols = Table.RenameColumns(SelectedCols, {
        {"Issue_Key", "Epic_Key"},
        {"Summary", "Epic_Summary"},
        {"Status", "Epic_Status"},
        {"Assignee", "Epic_Owner"}
    }),
    DistinctEpics = Table.Distinct(RenamedCols),
    TypedCols = Table.TransformColumnTypes(DistinctEpics, {
        {"Epic_Key", type text},
        {"Epic_Summary", type text},
        {"Epic_Status", type text},
        {"Epic_Owner", type text}
    })
in
    TypedCols;


// =============================================================================
// SECTION 5: JIRA REST API TEMPLATE (Production Use)
// =============================================================================
// Template for connecting directly to JIRA Cloud REST API.
// Endpoints:
//   - Sprints: /rest/agile/1.0/board/{boardId}/sprint
//   - Issues:  /rest/api/3/search
// Auth: Basic Auth (email:API_token) or OAuth 2.0
// Note: For FedRAMP environments, use JIRA Data Center behind VPN.
//
// IMPORTANT: Store credentials in Power BI Parameters, not inline.
// =============================================================================

let
    // --- Configuration ---
    // IMPORTANT: Store credentials in Power BI Parameters
    JiraBaseUrl = "https://your-instance.atlassian.net",
    BoardId = "926",  // Target board ID
    Email = Text.From(Excel.CurrentWorkbook(){[Name="JiraEmail"]}[Content]{0}[Column1]),
    ApiToken = Text.From(Excel.CurrentWorkbook(){[Name="JiraApiToken"]}[Content]{0}[Column1]),
    AuthHeader = "Basic " & Binary.ToText(
        Text.ToBinary(Email & ":" & ApiToken, TextEncoding.Utf8),
        BinaryEncoding.Base64
    ),

    // --- Step 1: Get All Sprints ---
    SprintsResponse = Json.Document(
        Web.Contents(
            JiraBaseUrl & "/rest/agile/1.0/board/" & BoardId & "/sprint",
            [
                Headers = [
                    #"Authorization" = AuthHeader,
                    #"Accept" = "application/json"
                ],
                Query = [state = "active,closed,future", maxResults = "50"]
            ]
        )
    ),
    SprintsList = SprintsResponse[values],

    // --- Step 2: Get Issues via JQL Search ---
    // Paginated — handle startAt and maxResults
    GetIssuesPage = (startAt as number) =>
        Json.Document(
            Web.Contents(
                JiraBaseUrl & "/rest/api/3/search",
                [
                    Headers = [
                        #"Authorization" = AuthHeader,
                        #"Content-Type" = "application/json",
                        #"Accept" = "application/json"
                    ],
                    Content = Json.FromValue([
                        jql = "project = UF ORDER BY created DESC",
                        startAt = startAt,
                        maxResults = 100,
                        fields = {
                            "issuetype", "summary", "status", "priority",
                            "customfield_10020", // Sprint
                            "story_points", "customfield_10028", // Story points
                            "assignee", "reporter", "created", "updated",
                            "resolutiondate", "customfield_10014", // Epic Link
                            "labels", "components"
                        }
                    ])
                ]
            )
        ),

    // --- Step 3: Paginate Through All Issues ---
    FirstPage = GetIssuesPage(0),
    TotalIssues = FirstPage[total],
    PageCount = Number.RoundUp(TotalIssues / 100),
    AllPages = List.Generate(
        () => [page = 0, data = FirstPage],
        each [page] < PageCount,
        each [
            page = [page] + 1,
            data = GetIssuesPage(([page] + 1) * 100)
        ],
        each [data][issues]
    ),
    AllIssues = List.Combine(AllPages),

    // --- Step 4: Convert to Table ---
    IssuesTable = Table.FromList(AllIssues, Splitter.SplitByNothing(), {"Record"}),
    ExpandedIssues = Table.ExpandRecordColumn(IssuesTable, "Record", {
        "key", "fields"
    }, {"Issue_Key", "fields"}),

    // --- Step 5: Expand Fields ---
    ExpandedFields = Table.ExpandRecordColumn(ExpandedIssues, "fields", {
        "issuetype", "summary", "status", "priority",
        "customfield_10020", "customfield_10028",
        "assignee", "reporter", "created", "updated",
        "resolutiondate", "customfield_10014", "labels", "components"
    }),

    // Flatten nested records (issuetype, status, priority, assignee, reporter)
    FlatType = Table.TransformColumns(ExpandedFields, {
        {"issuetype", each try _[name] otherwise null},
        {"status", each try _[name] otherwise null},
        {"priority", each try _[name] otherwise null},
        {"assignee", each try _[displayName] otherwise "Unassigned"},
        {"reporter", each try _[displayName] otherwise "Unknown"}
    }),

    // --- Step 6: Clean and Rename ---
    RenamedCols = Table.RenameColumns(FlatType, {
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

    // --- Step 7: Data Types ---
    TypedTable = Table.TransformColumnTypes(RenamedCols, {
        {"Story_Points", Int64.Type},
        {"Created_Date", type datetime},
        {"Updated_Date", type datetime},
        {"Resolved_Date", type datetime}
    })
in
    TypedTable
