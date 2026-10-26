-- Solution 4 — Year-over-year growth
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/04_yoy_growth.sql
--
-- PARTITION BY month_number makes LAG jump back a year instead of a month.
-- prior_year_revenue is NULL for the first year. The division stays NULL too.
-- Compare this result to output/kpi_yoy_monthly.csv.

WITH monthly AS (
  SELECT
    strftime('%Y-%m', order_date) AS order_month,
    CAST(strftime('%Y', order_date) AS INTEGER) AS order_year,
    CAST(strftime('%m', order_date) AS INTEGER) AS month_number,
    SUM(sales) AS revenue,
    SUM(profit) AS profit
  FROM orders
  GROUP BY
    strftime('%Y-%m', order_date),
    CAST(strftime('%Y', order_date) AS INTEGER),
    CAST(strftime('%m', order_date) AS INTEGER)
),
with_prior AS (
  SELECT
    monthly.order_month,
    monthly.order_year,
    monthly.month_number,
    monthly.revenue,
    monthly.profit,
    LAG(monthly.revenue) OVER (
      PARTITION BY monthly.month_number
      ORDER BY monthly.order_year
    ) AS prior_year_revenue
  FROM monthly
)
SELECT
  order_month,
  order_year,
  month_number,
  ROUND(revenue, 2) AS revenue,
  ROUND(profit, 2) AS profit,
  ROUND(prior_year_revenue, 2) AS prior_year_revenue,
  ROUND(revenue - prior_year_revenue, 2) AS yoy_change,
  ROUND((revenue - prior_year_revenue) / prior_year_revenue, 4) AS yoy_pct
FROM with_prior
ORDER BY order_year, month_number;
