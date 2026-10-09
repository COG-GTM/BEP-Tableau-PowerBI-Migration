# Tableau sheets → Power BI visuals

| Dashboard | Tableau worksheet | Tableau mark / shelves | Power BI visual | Fields |
|---|---|---|---|---|
| Sales Dashboard | Select Year (parameter) | parameter control | slicer (single select) | Select Year[Year] |
| Sales Dashboard | KPI Sales | Text / sparkline | 2 cards | [CY Sales], [% Diff Sales] |
| Sales Dashboard | KPI Profit | Text / sparkline | 2 cards | [CY Profit], [% Diff Profit] |
| Sales Dashboard | KPI Quantity | Text / sparkline | 2 cards | [CY Quantity], [% Diff Quantity] |
| Sales Dashboard | Weekly Trends | Line (WEEK(Order Date) x SUM(CY Sales), SUM(CY Profit)) | lineChart | Orders[Order Week] x [CY Sales], [CY Profit] |
| Sales Dashboard | Subcategory Comparison | Bar (Sub-Category x CY Sales, PY Sales, CY Profit; KPI CY Less PY marker) | clusteredBarChart + table | Products[Sub-Category] x [CY Sales], [PY Sales] |
| Sales Dashboard | Legend KPI / Legend Subcategory | legend sheets | tableEx (flags) — legends are native in Power BI | [KPI Sales Avg], [KPI CY Less PY] |
| Customer Dashboard | KPI Customers | Text / sparkline | 2 cards | [CY Customers], [% Diff Customers] |
| Customer Dashboard | KPI Orders | Text / sparkline | 2 cards | [CY Orders], [% Diff Orders] |
| Customer Dashboard | KPI Sales Per Customers | Text / sparkline | 2 cards | [CY Sales per Customer], [% Diff Sales per Customer] |
| Customer Dashboard | Customer Distribution | Bar (LOD orders-per-customer x COUNTD(CY Customers)) | clusteredColumnChart | 'Orders per Customer'[Orders] x [Customers with N Orders] |
| Customer Dashboard | Top Customers | Text table (INDEX() rank x Customer Name, MAX(Order Date), measures) | tableEx sorted by CY Sales | [Customer Rank], Customers[Customer Name], [CY Sales], [CY Profit], [CY Orders] |
| (not on a dashboard) | Test KPI | scratch sheet | not migrated — not referenced by any dashboard |  |
| (not on a dashboard) | Test KPI2 | scratch sheet | not migrated — not referenced by any dashboard |  |
| (not on a dashboard) | Test Max Min | scratch sheet | not migrated — not referenced by any dashboard |  |
