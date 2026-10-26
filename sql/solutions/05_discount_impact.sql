-- Solution 5 — Discount impact
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/05_discount_impact.sql
--
-- CASE stops at the first true test, so the zero band has to come before
-- the "up to 20%" test. band_sort is only there so the reader sees the
-- bands in business order.
-- Compare this result to output/kpi_discount_bands.csv.
-- Read margin_pct down the list and write down which bands still clear zero.

WITH banded AS (
  SELECT
    sales,
    profit,
    discount,
    order_id,
    CASE
      WHEN discount = 0 THEN 'No discount'
      WHEN discount <= 0.20 THEN 'Up to 20%'
      WHEN discount <= 0.40 THEN '20% to 40%'
      ELSE 'Over 40%'
    END AS discount_band,
    CASE
      WHEN discount = 0 THEN 1
      WHEN discount <= 0.20 THEN 2
      WHEN discount <= 0.40 THEN 3
      ELSE 4
    END AS band_sort
  FROM orders
)
SELECT
  discount_band,
  COUNT(*) AS line_count,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  ROUND(AVG(discount), 4) AS avg_line_discount
FROM banded
GROUP BY discount_band, band_sort
ORDER BY band_sort;
