-- Example 3 — Window functions
-- Run:
--   python scripts/run_sql.py sql/examples/03_window_functions.sql
--
-- A window function computes a value across related rows and does not collapse
-- them. GROUP BY collapses. When you need both, aggregate in a CTE first,
-- then window the aggregated rows.
--
-- PARTITION BY starts the calculation over inside each group.
-- ORDER BY tells the window which way "previous" and "running" point.
-- The frame ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW means
-- "from the first row in this order through the current row".
--
-- SQLite's default frame is RANGE, and tied sort keys share one running total.
-- Name a unique tie-break (here, sub_category) or set the frame to ROWS
-- when the running total must move one row at a time.

-- Rank inside a category, and each sub-category's share of that category.
-- SUM(revenue) OVER (PARTITION BY category) is the category total, repeated
-- on every sub-category row. Dividing by it gives the share.

WITH sub AS (
  SELECT
    category,
    sub_category,
    SUM(sales) AS revenue,
    SUM(profit) AS profit
  FROM orders
  GROUP BY category, sub_category
)
SELECT
  category,
  sub_category,
  ROUND(revenue, 2) AS revenue,
  ROUND(profit, 2) AS profit,
  RANK() OVER (
    PARTITION BY category
    ORDER BY revenue DESC
  ) AS revenue_rank_in_category,
  ROUND(
    revenue / SUM(revenue) OVER (PARTITION BY category),
    4
  ) AS share_of_category_revenue
FROM sub
ORDER BY category, revenue_rank_in_category, sub_category;

-- Running revenue from the first month through the current month,
-- and the change versus the immediately previous month.
-- LAG looks backward along ORDER BY. With no PARTITION BY, the previous
-- row is the previous month in time.
--
-- Exercise 4 asks for the same month last year. That is still LAG.
-- The partition changes: partition by the month number, order by the year,
-- so "previous" means "this month, one year earlier" rather than "last month".

WITH monthly AS (
  SELECT
    strftime('%Y-%m', order_date) AS order_month,
    SUM(sales) AS revenue
  FROM orders
  GROUP BY strftime('%Y-%m', order_date)
)
SELECT
  order_month,
  ROUND(revenue, 2) AS revenue,
  ROUND(
    SUM(revenue) OVER (
      ORDER BY order_month
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ),
    2
  ) AS running_revenue,
  ROUND(
    LAG(revenue) OVER (ORDER BY order_month),
    2
  ) AS prior_month_revenue,
  ROUND(
    revenue - LAG(revenue) OVER (ORDER BY order_month),
    2
  ) AS mom_change
FROM monthly
ORDER BY order_month;
