-- Example 1 — Joins
-- Run:
--   python scripts/run_sql.py sql/examples/01_joins.sql
--
-- Business question
--   For each region, who is the manager, how much revenue and profit did the
--   region book, and how much of that revenue sits on orders that were returned?
--
-- Two lookup tables
--   people   one manager per region. Join on region.
--   returns  one row per returned order id. Join on order_id.
--            Most orders are not in this table.
--
-- LEFT JOIN keeps every order line even when the lookup row is missing.
-- An INNER JOIN to returns would throw away every order that was not returned,
-- and the revenue total would collapse to "returned revenue" without warning.
-- INNER JOIN to people would also be fine today, because every region has a
-- manager. LEFT JOIN is the habit: a new region in a future file should show
-- up with a blank manager, not vanish.
--
-- Grain check
--   Do this before you trust any SUM. If the joins duplicate lines, every
--   total below is inflated. people is unique on region and returns is unique
--   on order_id, so each order line should still be one row after both joins.

SELECT
  (SELECT COUNT(*) FROM orders) AS order_lines,
  (
    SELECT COUNT(*)
    FROM orders AS o
    LEFT JOIN people AS p ON p.region = o.region
    LEFT JOIN returns AS r ON r.order_id = o.order_id
  ) AS lines_after_joins;

-- Regional scorecard.
-- returned_sales is a line-level amount, zero when that line's order was kept.
-- The share is computed after the sums, from dollars, not by averaging flags.

WITH lines AS (
  SELECT
    o.region,
    p.regional_manager,
    o.sales,
    o.profit,
    o.order_id,
    CASE WHEN r.order_id IS NOT NULL THEN o.sales ELSE 0 END AS returned_sales
  FROM orders AS o
  LEFT JOIN people AS p ON p.region = o.region
  LEFT JOIN returns AS r ON r.order_id = o.order_id
)
SELECT
  region,
  regional_manager,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(returned_sales), 2) AS returned_revenue,
  ROUND(SUM(returned_sales) / SUM(sales), 4) AS returned_revenue_share
FROM lines
GROUP BY region, regional_manager
ORDER BY revenue DESC;
