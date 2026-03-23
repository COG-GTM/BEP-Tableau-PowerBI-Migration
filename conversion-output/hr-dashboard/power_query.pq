// =============================================
// HR DASHBOARD — Power Query M Script
// Imports dataset.csv with semicolon delimiter
// Converts DD/MM/YYYY dates to proper datetime
// Source: projects/hr-dashboard-project/dataset.csv
// =============================================

let
    // Step 1: Import CSV with semicolon delimiter
    Source = Csv.Document(
        File.Contents("projects/hr-dashboard-project/dataset.csv"),
        [
            Delimiter = ";",
            Columns = 14,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.None
        ]
    ),

    // Step 2: Promote first row as headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // Step 3: Trim whitespace from all text columns
    TrimmedColumns = Table.TransformColumns(
        PromotedHeaders,
        List.Transform(
            Table.ColumnNames(PromotedHeaders),
            each {_, Text.Trim, type text}
        )
    ),

    // Step 4: Parse DD/MM/YYYY date strings to proper Date type
    // Custom function to convert DD/MM/YYYY format
    ParseEUDate = (dateText as nullable text) as nullable date =>
        if dateText = null or dateText = "" then
            null
        else
            let
                Parts = Text.Split(dateText, "/"),
                Day = Number.From(Parts{0}),
                Month = Number.From(Parts{1}),
                Year = Number.From(Parts{2})
            in
                #date(Year, Month, Day),

    // Step 5: Apply date parsing to Birthdate column
    ParsedBirthdate = Table.TransformColumns(
        TrimmedColumns,
        {{"Birthdate", each ParseEUDate(_), type date}}
    ),

    // Step 6: Apply date parsing to Hiredate column
    ParsedHiredate = Table.TransformColumns(
        ParsedBirthdate,
        {{"Hiredate", each ParseEUDate(_), type date}}
    ),

    // Step 7: Apply date parsing to Termdate column (handles nulls/blanks)
    ParsedTermdate = Table.TransformColumns(
        ParsedHiredate,
        {{"Termdate", each ParseEUDate(_), type nullable date}}
    ),

    // Step 8: Set correct data types for all columns
    TypedColumns = Table.TransformColumnTypes(
        ParsedTermdate,
        {
            {"Employee_ID", type text},
            {"First Name", type text},
            {"Last Name", type text},
            {"Gender", type text},
            {"State", type text},
            {"City", type text},
            {"Education Level", type text},
            {"Birthdate", type date},
            {"Hiredate", type date},
            {"Termdate", type date},
            {"Department", type text},
            {"Job Title", type text},
            {"Salary", Currency.Type},
            {"Performance Rating", type text}
        }
    ),

    // Step 9: Replace any remaining null/empty text values in Termdate
    // (already handled by ParseEUDate function returning null)
    CleanedTermdate = Table.ReplaceValue(
        TypedColumns,
        "",
        null,
        Replacer.ReplaceValue,
        {"Termdate"}
    ),

    // Step 10: Ensure Salary is parsed as a number (remove any formatting)
    CleanedSalary = Table.TransformColumns(
        CleanedTermdate,
        {{"Salary", each if _ = null then 0 else Number.From(_), type number}}
    ),

    // Step 11: Final output with validated schema
    Output = Table.Buffer(CleanedSalary)
in
    Output
