-- Solution 3 — Margin by category and region
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/03_margin_by_category_region.sql
--
-- people is unique on region, so this LEFT JOIN does not duplicate lines.
-- If you ever doubt that, count orders before and after the join (example 1).
-- Compare this result to output/kpi_category_region.csv.

SELECT
  o.category,
  o.region,
  p.regional_manager,
  ROUND(SUM(o.sales), 2) AS revenue,
  ROUND(SUM(o.profit), 2) AS profit,
  ROUND(SUM(o.profit) / SUM(o.sales), 4) AS margin_pct,
  COUNT(DISTINCT o.order_id) AS orders
FROM orders AS o
LEFT JOIN people AS p ON p.region = o.region
GROUP BY o.category, o.region, p.regional_manager
ORDER BY o.region, o.category;
