# Number check — selected year 2023

Same question asked of three independent engines. Tableau's Hyper engine reads the original extract; Postgres is what the new dashboards query; the DAX replica re-evaluates the translated measures.

| Measure | Tableau extract (Hyper) | Postgres | DAX replica | Match |
|---|---|---|---|---|
| CY Sales | 733,215.26 | 733,215.26 | 733,215.26 | ✅ |
| PY Sales | 609,205.60 | 609,205.60 | 609,205.60 | ✅ |
| CY Profit | 93,439.27 | 93,439.27 | 93,439.27 | ✅ |
| CY Quantity | 12,476 | 12,476 | 12,476 | ✅ |
| CY Orders | 1,687 | 1,687 | 1,687 | ✅ |
| CY Customers | 693 | 693 | 693 | ✅ |
| CY Sales per Customer | 1,058.03 | 1,058.03 | 1,058.03 | ✅ |

## CY Sales by Sub-Category (2023)

| Sub-Category | Tableau extract | Postgres | DAX replica | Match |
|---|---|---|---|---|
| Accessories | 59,946.23 | 59,946.23 | 59,946.23 | ✅ |
| Appliances | 42,926.93 | 42,926.93 | 42,926.93 | ✅ |
| Art | 8,863.07 | 8,863.07 | 8,863.07 | ✅ |
| Binders | 72,788.04 | 72,788.04 | 72,788.04 | ✅ |
| Bookcases | 30,024.28 | 30,024.28 | 30,024.28 | ✅ |
| Chairs | 95,554.35 | 95,554.35 | 95,554.35 | ✅ |
| Copiers | 62,899.39 | 62,899.39 | 62,899.39 | ✅ |
| Envelopes | 3,378.57 | 3,378.57 | 3,378.57 | ✅ |
| Fasteners | 857.59 | 857.59 | 857.59 | ✅ |
| Furnishings | 28,915.09 | 28,915.09 | 28,915.09 | ✅ |
| Labels | 3,861.22 | 3,861.22 | 3,861.22 | ✅ |
| Machines | 43,544.67 | 43,544.68 | 43,544.68 | ✅ |
| Paper | 27,694.72 | 27,694.72 | 27,694.72 | ✅ |
| Phones | 105,340.52 | 105,340.52 | 105,340.52 | ✅ |
| Storage | 69,677.62 | 69,677.62 | 69,677.62 | ✅ |
| Supplies | 16,049.41 | 16,049.41 | 16,049.41 | ✅ |
| Tables | 60,893.54 | 60,893.54 | 60,893.54 | ✅ |

**Result: all numbers match** (tolerance 0.01).
