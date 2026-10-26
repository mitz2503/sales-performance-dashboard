-- Solution 6 — Returned orders
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/06_returned_orders.sql
--
-- Part A is company-wide, at order grain.
-- Part B splits lines by category. Order counts in Part B are not additive
-- across categories. Revenue is additive across categories.
-- Compare Part A to output/kpi_returns_overall.csv and Part B to
-- output/kpi_returns_by_category.csv.

SELECT
  COUNT(DISTINCT o.order_id) AS orders,
  COUNT(DISTINCT CASE WHEN r.order_id IS NOT NULL THEN o.order_id END) AS returned_orders,
  ROUND(
    1.0 * COUNT(DISTINCT CASE WHEN r.order_id IS NOT NULL THEN o.order_id END)
    / COUNT(DISTINCT o.order_id),
    4
  ) AS returned_order_share,
  ROUND(SUM(CASE WHEN r.order_id IS NOT NULL THEN o.sales ELSE 0 END), 2) AS returned_revenue,
  ROUND(SUM(o.sales), 2) AS revenue,
  ROUND(
    SUM(CASE WHEN r.order_id IS NOT NULL THEN o.sales ELSE 0 END) / SUM(o.sales),
    4
  ) AS returned_revenue_share
FROM orders AS o
LEFT JOIN returns AS r ON r.order_id = o.order_id;

SELECT
  o.category,
  CASE WHEN r.order_id IS NOT NULL THEN 'Returned' ELSE 'Kept' END AS return_status,
  COUNT(DISTINCT o.order_id) AS orders,
  ROUND(SUM(o.sales), 2) AS revenue,
  ROUND(SUM(o.profit), 2) AS profit,
  ROUND(SUM(o.profit) / SUM(o.sales), 4) AS margin_pct
FROM orders AS o
LEFT JOIN returns AS r ON r.order_id = o.order_id
GROUP BY
  o.category,
  CASE WHEN r.order_id IS NOT NULL THEN 'Returned' ELSE 'Kept' END
ORDER BY o.category, return_status;
