with date_fixtures as (
    select *
    from (
        values
            (date '2023-01-01', 1),
            (date '2023-01-02', 2),
            (date '2020-01-01', 1),
            (date '2020-01-06', 2)
    ) as values_table(order_date, expected_week)
),
calculated as (
    select
        order_date,
        expected_week,
        (
            (
                dayofyear(order_date) - 1
                + isodow(make_date(year(order_date), 1, 1)) - 1
            ) // 7
        ) + 1 as actual_week
    from date_fixtures
)
select *
from calculated
where actual_week != expected_week
