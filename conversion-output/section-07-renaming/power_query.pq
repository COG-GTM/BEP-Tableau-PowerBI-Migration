// =============================================
// SECTION 07 — RENAMING — POWER QUERY M
// Import and transform CSV data sources
// Source: tableau-source/course/tableau-files/Section 07 - Renaming/extracted/Section 7 - Renaming.twb
// =============================================
// NOTE: All CSVs use semicolon (;) as delimiter
// NOTE: Date format is DD/MM/YYYY
// NOTE: Locale en_DE — comma decimal separator, period thousands separator
// NOTE: This workbook demonstrates field renaming/aliasing
// =============================================

// -------------------------------------------
// TABLE 1: Orders (Fact Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Orders.csv"),
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
        {"Country", type text},
        {"City", type text},
        {"State", type text},
        {"Postal Code", Int64.Type},
        {"Region", type text},
        {"Product ID", type text},
        {"Category", type text},
        {"Sub-Category", type text},
        {"Product Name", type text},
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
                    Text.Split(Text.From(_), "/"){2},
                    Text.Split(Text.From(_), "/"){1},
                    Text.Split(Text.From(_), "/"){0}
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

    // Step 5: Remove duplicates on Row ID (primary key validation)
    RemovedDuplicates = Table.Distinct(ParsedOrderDate, {"Row ID"}),

    // Step 6: Trim whitespace from text columns
    TrimmedText = Table.TransformColumns(RemovedDuplicates, {
        {"Order ID", Text.Trim, type text},
        {"Ship Mode", Text.Trim, type text},
        {"Customer ID", Text.Trim, type text},
        {"Segment", Text.Trim, type text},
        {"Product ID", Text.Trim, type text}
    }),

    // Step 7: Replace null Sales/Profit/Quantity with 0
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
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Customers.csv"),
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
    RemovedDuplicates = Table.Distinct(TrimmedText, {"Customer ID"})
in
    RemovedDuplicates;


// -------------------------------------------
// TABLE 3: Products (Dimension Table)
// -------------------------------------------
let
    // Step 1: Load CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Products.csv"),
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
// TABLE 4: Date (Auto-generated Calendar Table)
// -------------------------------------------
let
    StartDate = #date(2020, 1, 1),
    EndDate = #date(2023, 12, 31),
    NumberOfDays = Duration.Days(EndDate - StartDate) + 1,

    DateList = List.Dates(StartDate, NumberOfDays, #duration(1, 0, 0, 0)),

    DateTable = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),

    ChangedType = Table.TransformColumnTypes(DateTable, {{"Date", type date}}),

    AddedYear = Table.AddColumn(ChangedType, "Year", each Date.Year([Date]), Int64.Type),
    AddedMonth = Table.AddColumn(AddedYear, "Month", each Date.Month([Date]), Int64.Type),
    AddedMonthName = Table.AddColumn(AddedMonth, "Month Name", each Date.MonthName([Date]), type text),
    AddedQuarter = Table.AddColumn(AddedMonthName, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text)
in
    AddedQuarter;
