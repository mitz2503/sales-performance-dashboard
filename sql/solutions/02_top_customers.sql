-- Solution 2 — Top customers
-- Open this after your own query runs.
--   python scripts/run_sql.py sql/solutions/02_top_customers.sql
--
-- Grain: one row per customer_id. Names that share several ids stay split.
-- The rank is computed inside scored, then filtered outside. SQL rejects
-- WHERE revenue_rank <= 10 in the same SELECT that defines the window.
--
-- output/kpi_customers.csv is this query without the rank filter, so the
-- top 10 here are the first rows of that file when the ranks are unique.

WITH customer AS (
  SELECT
    customer_id,
    customer_name,
    segment,
    SUM(sales) AS revenue,
    SUM(profit) AS profit,
    COUNT(DISTINCT order_id) AS orders
  FROM orders
  GROUP BY customer_id, customer_name, segment
),
scored AS (
  SELECT
    customer.customer_id,
    customer.customer_name,
    customer.segment,
    customer.revenue,
    customer.profit,
    customer.profit / customer.revenue AS margin_pct,
    customer.orders,
    customer.revenue / SUM(customer.revenue) OVER () AS revenue_share,
    RANK() OVER (ORDER BY customer.revenue DESC) AS revenue_rank
  FROM customer
)
SELECT
  revenue_rank,
  customer_id,
  customer_name,
  segment,
  ROUND(revenue, 2) AS revenue,
  ROUND(profit, 2) AS profit,
  ROUND(margin_pct, 4) AS margin_pct,
  orders,
  ROUND(revenue_share, 4) AS revenue_share
FROM scored
WHERE revenue_rank <= 10
ORDER BY revenue_rank, customer_id;
