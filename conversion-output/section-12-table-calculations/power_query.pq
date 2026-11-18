// =============================================
// Power Query M Scripts — Section 12: Table Calculations
// Data Source: course/datasets/non-eu-dataset/small-dataset/
// Delimiter: ";" | Encoding: 65001 (UTF-8)
// =============================================

// --- Orders Table (with Product join for Sub-Category) ---
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Orders.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ParsedOrderDate = Table.TransformColumns(PromotedHeaders, {
        {"Order_Date", each Date.From(
            DateTime.From(
                Text.Combine({Text.Range(_, 6, 4), Text.Range(_, 3, 2), Text.Range(_, 0, 2)}, "-")
            )
        ), type date}
    }),
    ParsedShipDate = Table.TransformColumns(ParsedOrderDate, {
        {"Shipping_Date", each Date.From(
            DateTime.From(
                Text.Combine({Text.Range(_, 6, 4), Text.Range(_, 3, 2), Text.Range(_, 0, 2)}, "-")
            )
        ), type date}
    }),
    ChangedTypes = Table.TransformColumnTypes(ParsedShipDate, {
        {"Order_ID", type text},
        {"Customer_ID", type text},
        {"Product_ID", type text},
        {"Sales", type number},
        {"Quantity", Int64.Type},
        {"Discount", type number},
        {"Profit", type number},
        {"Unit_Price", type number}
    }),
    // Join Products for Sub-Category
    ProductsSource = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Products.csv"),
        [Delimiter=";", Encoding=65001]
    ),
    ProductsHeaders = Table.PromoteHeaders(ProductsSource, [PromoteAllScalars=true]),
    Joined = Table.NestedJoin(ChangedTypes, {"Product_ID"}, ProductsHeaders, {"Product_ID"}, "ProductDetails", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "ProductDetails", {"Product_Name", "Category"}, {"Product Name", "Category"}),
    RenamedColumns = Table.RenameColumns(Expanded, {
        {"Order_ID", "Order ID"},
        {"Customer_ID", "Customer ID"},
        {"Product_ID", "Product ID"},
        {"Order_Date", "Order Date"},
        {"Shipping_Date", "Ship Date"},
        {"Unit_Price", "Unit Price"}
    })
in
    RenamedColumns

// --- Customers Table ---
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Customers.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Customer_ID", type text},
        {"First_Name", type text},
        {"Last_Name", type text},
        {"Country", type text},
        {"Score", Int64.Type}
    }),
    RenamedColumns = Table.RenameColumns(ChangedTypes, {
        {"Customer_ID", "Customer ID"},
        {"First_Name", "First Name"},
        {"Last_Name", "Last Name"}
    })
in
    RenamedColumns

// --- Products Table ---
let
    Source = Csv.Document(
        File.Contents("course/datasets/non-eu-dataset/small-dataset/Products.csv"),
        [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {
        {"Product_ID", type text},
        {"Product_Name", type text},
        {"Category", type text},
        {"Product_Image", type text}
    }),
    RenamedColumns = Table.RenameColumns(ChangedTypes, {
        {"Product_ID", "Product ID"},
        {"Product_Name", "Product Name"},
        {"Product_Image", "Product Image"}
    })
in
    RenamedColumns
