-- Solution 8 — Sub-category concentration
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/08_subcategory_pareto.sql
--
-- in_first_80_pct stays 1 through the row that pushes the running share
-- to or past 0.80, then switches to 0.
-- previous share = (running_revenue - revenue) / total_revenue
-- When that previous share is already at least 0.80, this row is past the cut.
-- Compare this result to output/kpi_subcategory.csv.
-- Then look at margin_pct on the rows where the flag is 1.

WITH sub AS (
  SELECT
    category,
    sub_category,
    SUM(sales) AS revenue,
    SUM(profit) AS profit
  FROM orders
  GROUP BY category, sub_category
),
ranked AS (
  SELECT
    sub.category,
    sub.sub_category,
    sub.revenue,
    sub.profit,
    sub.profit / sub.revenue AS margin_pct,
    SUM(sub.revenue) OVER () AS total_revenue,
    SUM(sub.revenue) OVER (
      ORDER BY sub.revenue DESC, sub.sub_category
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_revenue
  FROM sub
)
SELECT
  sub_category,
  category,
  ROUND(revenue, 2) AS revenue,
  ROUND(profit, 2) AS profit,
  ROUND(margin_pct, 4) AS margin_pct,
  ROUND(running_revenue / total_revenue, 4) AS cumulative_revenue_share,
  CASE
    WHEN (running_revenue - revenue) / total_revenue >= 0.80 THEN 0
    ELSE 1
  END AS in_first_80_pct
FROM ranked
ORDER BY revenue DESC, sub_category;
