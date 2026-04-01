// =============================================
// SECTION 10 -- PARAMETERS -- POWER QUERY M
// =============================================
// POWER QUERY M — Import and transform data sources
// Source: course/datasets/non-eu-dataset/small-dataset/
// =============================================
// NOTE: All CSVs use semicolon (;) as delimiter
// NOTE: Date format is DD/MM/YYYY
// =============================================

// -------------------------------------------
// TABLE 1: Orders (Fact Table)
// -------------------------------------------
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Orders.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
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
    AddedDaysToShip = Table.AddColumn(ParsedOrderDate, "Days to Ship",
        each Duration.Days([Ship Date] - [Order Date]), Int64.Type),
    RemovedDuplicates = Table.Distinct(AddedDaysToShip, {"Row ID"}),
    TrimmedText = Table.TransformColumns(RemovedDuplicates, {
        {"Order ID", Text.Trim, type text},
        {"Customer ID", Text.Trim, type text},
        {"Product ID", Text.Trim, type text}
    })
in
    TrimmedText;


// -------------------------------------------
// TABLE 2: Customers (Dimension Table)
// -------------------------------------------
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Customers.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Customer ID", type text},
        {"Customer Name", type text}
    }),
    TrimmedText = Table.TransformColumns(ChangedTypes, {
        {"Customer ID", Text.Trim, type text},
        {"Customer Name", Text.Trim, type text}
    }),
    RemovedDuplicates = Table.Distinct(TrimmedText, {"Customer ID"})
in
    RemovedDuplicates;


// -------------------------------------------
// TABLE 3: Products (Dimension Table)
// -------------------------------------------
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Products.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Product ID", type text},
        {"Category", type text},
        {"Sub-Category", type text},
        {"Product Name", type text}
    }),
    TrimmedText = Table.TransformColumns(ChangedTypes, {
        {"Product ID", Text.Trim, type text},
        {"Category", Text.Trim, type text},
        {"Sub-Category", Text.Trim, type text},
        {"Product Name", Text.Trim, type text}
    }),
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
    AddedQuarter = Table.AddColumn(AddedMonthName, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddedDayOfWeek = Table.AddColumn(AddedQuarter, "Day of Week", each Date.DayOfWeekName([Date]), type text)
in
    AddedDayOfWeek;


// -------------------------------------------
// TABLE 5: Choose Dimension (Disconnected Parameter Table)
// TWB: Parameter 1, string list: "Country", "Category"
// -------------------------------------------
let
    Source = Table.FromRows(
        {{"Country"}, {"Category"}},
        {"Choose Dimension"}
    ),
    ChangedType = Table.TransformColumnTypes(Source, {{"Choose Dimension", type text}})
in
    ChangedType;


// -------------------------------------------
// TABLE 6: Choose Measure (Disconnected Parameter Table)
// TWB: Parameter 2, string list: "Sales", "Profit", "Quantity"
// -------------------------------------------
let
    Source = Table.FromRows(
        {{"Sales"}, {"Profit"}, {"Quantity"}},
        {"Choose Measure"}
    ),
    ChangedType = Table.TransformColumnTypes(Source, {{"Choose Measure", type text}})
in
    ChangedType;
