// =============================================
// SALES & CUSTOMER DASHBOARD — POWER QUERY M
// Import and transform 4 CSV data sources
// Source: projects/sales-dashboard-project/datasets/non-eu/
// =============================================
// NOTE: All CSVs use semicolon (;) as delimiter
// NOTE: Date format is DD/MM/YYYY
// NOTE: Numeric values use period (.) as decimal separator (non-EU dataset)
// =============================================

// -------------------------------------------
// TABLE 1: Orders (Fact Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("projects/sales-dashboard-project/datasets/non-eu/Orders.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),

    // Step 2: Promote first row as column headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),

    // Step 3: Set data types for all columns
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Row ID", Int64.Type},
        {"Order ID", type text},
        {"Order Date", type text},
        {"Ship Date", type text},
        {"Ship Mode", type text},
        {"Customer ID", type text},
        {"Segment", type text},
        {"Postal Code", Int64.Type},
        {"Product ID", type text},
        {"Sales", type number},
        {"Quantity", Int64.Type},
        {"Discount", type number},
        {"Profit", type number}
    }),

    // Step 4: Parse dates from DD/MM/YYYY text format
    ParsedOrderDate = Table.TransformColumns(ChangedTypes, {
        {"Order Date", each Date.From(
            DateTime.From(
                Text.Combine({
                    Text.Split(Text.From(_), "/"){2},  // Year
                    Text.Split(Text.From(_), "/"){1},  // Month
                    Text.Split(Text.From(_), "/"){0}   // Day
                }, "-")
            )
        ), type date},
        {"Ship Date", each Date.From(
            DateTime.From(
                Text.Combine({
                    Text.Split(Text.From(_), "/"){2},
                    Text.Split(Text.From(_), "/"){1},
                    Text.Split(Text.From(_), "/"){0}
                }, "-")
            )
        ), type date}
    }),

    // Step 5: Add calculated column — Days to Ship
    AddedDaysToShip = Table.AddColumn(ParsedOrderDate, "Days to Ship",
        each Duration.Days([Ship Date] - [Order Date]),
        Int64.Type
    ),

    // Step 6: Add Year column for filtering/slicing
    AddedYear = Table.AddColumn(AddedDaysToShip, "Order Year",
        each Date.Year([Order Date]),
        Int64.Type
    ),

    // Step 7: Add Month column for time series
    AddedMonth = Table.AddColumn(AddedYear, "Order Month",
        each Date.Month([Order Date]),
        Int64.Type
    ),

    // Step 8: Remove duplicates on Row ID (primary key validation)
    RemovedDuplicates = Table.Distinct(AddedMonth, {"Row ID"}),

    // Step 9: Trim whitespace from text columns
    TrimmedText = Table.TransformColumns(RemovedDuplicates, {
        {"Order ID", Text.Trim, type text},
        {"Ship Mode", Text.Trim, type text},
        {"Customer ID", Text.Trim, type text},
        {"Segment", Text.Trim, type text},
        {"Product ID", Text.Trim, type text}
    }),

    // Step 10: Replace null Sales/Profit/Quantity with 0
    ReplacedNulls = Table.ReplaceValue(
        Table.ReplaceValue(
            Table.ReplaceValue(TrimmedText, null, 0, Replacer.ReplaceValue, {"Sales"}),
            null, 0, Replacer.ReplaceValue, {"Profit"}
        ),
        null, 0, Replacer.ReplaceValue, {"Quantity"}
    )
in
    ReplacedNulls;


// -------------------------------------------
// TABLE 2: Customers (Dimension Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("projects/sales-dashboard-project/datasets/non-eu/Customers.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),

    // Step 2: Promote first row as column headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),

    // Step 3: Set data types
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Customer ID", type text},
        {"Customer Name", type text}
    }),

    // Step 4: Trim whitespace
    TrimmedText = Table.TransformColumns(ChangedTypes, {
        {"Customer ID", Text.Trim, type text},
        {"Customer Name", Text.Trim, type text}
    }),

    // Step 5: Remove duplicates on Customer ID (ensure unique dimension key)
    RemovedDuplicates = Table.Distinct(TrimmedText, {"Customer ID"}),

    // Step 6: Split Customer Name into First Name and Last Name for additional analysis
    SplitName = Table.SplitColumn(
        RemovedDuplicates,
        "Customer Name",
        Splitter.SplitTextByEachDelimiter({" "}, QuoteStyle.None, false),
        {"First Name", "Last Name"}
    ),

    // Step 7: Re-add full Customer Name
    AddedFullName = Table.AddColumn(SplitName, "Customer Name",
        each [First Name] & " " & [Last Name],
        type text
    )
in
    AddedFullName;


// -------------------------------------------
// TABLE 3: Products (Dimension Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("projects/sales-dashboard-project/datasets/non-eu/Products.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),

    // Step 2: Promote first row as column headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),

    // Step 3: Set data types
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Product ID", type text},
        {"Category", type text},
        {"Sub-Category", type text},
        {"Product Name", type text}
    }),

    // Step 4: Trim whitespace
    TrimmedText = Table.TransformColumns(ChangedTypes, {
        {"Product ID", Text.Trim, type text},
        {"Category", Text.Trim, type text},
        {"Sub-Category", Text.Trim, type text},
        {"Product Name", Text.Trim, type text}
    }),

    // Step 5: Remove duplicates on Product ID (ensure unique dimension key)
    RemovedDuplicates = Table.Distinct(TrimmedText, {"Product ID"})
in
    RemovedDuplicates;


// -------------------------------------------
// TABLE 4: Location (Dimension Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("projects/sales-dashboard-project/datasets/non-eu/Location.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),

    // Step 2: Promote first row as column headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),

    // Step 3: Set data types
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Postal Code", Int64.Type},
        {"City", type text},
        {"State", type text},
        {"Region", type text},
        {"Country/Region", type text}
    }),

    // Step 4: Trim whitespace
    TrimmedText = Table.TransformColumns(ChangedTypes, {
        {"City", Text.Trim, type text},
        {"State", Text.Trim, type text},
        {"Region", Text.Trim, type text},
        {"Country/Region", Text.Trim, type text}
    }),

    // Step 5: Remove duplicates on Postal Code (ensure unique dimension key)
    RemovedDuplicates = Table.Distinct(TrimmedText, {"Postal Code"}),

    // Step 6: Add latitude/longitude placeholders for map visualization
    // Note: In production, use a geocoding service or reference table
    AddedLatitude = Table.AddColumn(RemovedDuplicates, "Latitude", each null, type number),
    AddedLongitude = Table.AddColumn(AddedLatitude, "Longitude", each null, type number)
in
    AddedLongitude;


// -------------------------------------------
// TABLE 5: Date (Auto-generated Calendar Table)
// -------------------------------------------
// NOTE: This table is generated via DAX in the model (CALENDAR function).
// The Power Query version below is an alternative if preferred:
let
    // Generate date range covering all order dates (2020-2023)
    StartDate = #date(2020, 1, 1),
    EndDate = #date(2023, 12, 31),
    NumberOfDays = Duration.Days(EndDate - StartDate) + 1,

    // Create list of dates
    DateList = List.Dates(StartDate, NumberOfDays, #duration(1, 0, 0, 0)),

    // Convert to table
    DateTable = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),

    // Set date type
    ChangedType = Table.TransformColumnTypes(DateTable, {{"Date", type date}}),

    // Add calendar columns
    AddedYear = Table.AddColumn(ChangedType, "Year", each Date.Year([Date]), Int64.Type),
    AddedMonth = Table.AddColumn(AddedYear, "Month", each Date.Month([Date]), Int64.Type),
    AddedMonthName = Table.AddColumn(AddedMonth, "Month Name", each Date.MonthName([Date]), type text),
    AddedQuarter = Table.AddColumn(AddedMonthName, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddedDayOfWeek = Table.AddColumn(AddedQuarter, "Day of Week", each Date.DayOfWeekName([Date]), type text),
    AddedWeekNumber = Table.AddColumn(AddedDayOfWeek, "Week Number", each Date.WeekOfYear([Date]), Int64.Type),
    AddedDayOfMonth = Table.AddColumn(AddedWeekNumber, "Day of Month", each Date.Day([Date]), Int64.Type),
    AddedIsWeekend = Table.AddColumn(AddedDayOfMonth, "Is Weekend",
        each if Date.DayOfWeek([Date], Day.Monday) >= 5 then true else false,
        type logical
    ),
    AddedFiscalYear = Table.AddColumn(AddedIsWeekend, "Fiscal Year",
        each if Date.Month([Date]) >= 10 then Date.Year([Date]) + 1 else Date.Year([Date]),
        Int64.Type
    ),
    AddedFiscalQuarter = Table.AddColumn(AddedFiscalYear, "Fiscal Quarter",
        each "FQ" & Text.From(
            Number.RoundUp((Date.Month([Date]) + 2) / 3)
        ),
        type text
    )
in
    AddedFiscalQuarter;
