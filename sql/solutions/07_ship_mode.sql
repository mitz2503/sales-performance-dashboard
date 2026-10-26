-- Solution 7 — Ship mode
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/07_ship_mode.sql
--
-- one_order is one row per order. Averaging ship_days there gives each order
-- one vote. The second query is then a normal GROUP BY on four rows' worth
-- of groups (the four ship modes).
-- Compare this result to output/kpi_ship_mode.csv.
-- Read avg_ship_days next to margin_pct and avg_order_value.

WITH one_order AS (
  SELECT
    order_id,
    ship_mode,
    julianday(MIN(ship_date)) - julianday(MIN(order_date)) AS ship_days,
    SUM(sales) AS revenue,
    SUM(profit) AS profit
  FROM orders
  GROUP BY order_id, ship_mode
)
SELECT
  ship_mode,
  COUNT(*) AS orders,
  ROUND(AVG(ship_days), 2) AS avg_ship_days,
  ROUND(SUM(revenue), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(revenue), 4) AS margin_pct,
  ROUND(SUM(revenue) / COUNT(*), 2) AS avg_order_value
FROM one_order
GROUP BY ship_mode
ORDER BY avg_ship_days, ship_mode;
