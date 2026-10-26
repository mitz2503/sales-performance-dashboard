-- Solution 1 — Monthly revenue trend
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/01_monthly_revenue_trend.sql
--
-- Check your result against output/kpi_monthly.csv after you export.
-- Money is rounded to the cent. Ratios keep four decimal places (0.1256 = 12.56%).

SELECT
  strftime('%Y-%m', order_date) AS order_month,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
  SUM(quantity) AS quantity
FROM orders
GROUP BY strftime('%Y-%m', order_date)
ORDER BY order_month;
