-- Example 2 — GROUP BY
-- Run:
--   python scripts/run_sql.py sql/examples/02_group_by.sql
--
-- Business question
--   How do revenue, profit, and margin compare across category and segment,
--   and which sub-categories lost money in total?
--
-- GROUP BY collapses many lines into one row per group. Everything in the
-- SELECT list is either a grouping column or an aggregate (SUM, COUNT, ...).
--
-- Margin is a ratio of sums.
--   SUM(profit) / SUM(sales)     weights each dollar equally
--   AVG(profit / sales)          gives a $10 line and a $10,000 line one vote each
-- When someone asks "what is the margin?", they mean the ratio of sums.
--
-- SQLite integer division
--   COUNT(*) / COUNT(*) is integer math and drops the fraction.
--   SUM(sales) is a real number, so profit / sales keeps the fraction.
--   When both sides are integers, multiply one side by 1.0.
--
-- COUNT(*) counts lines. COUNT(DISTINCT order_id) counts orders.
-- A five-line order is one order.

SELECT
  category,
  segment,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  COUNT(*) AS line_count,
  COUNT(DISTINCT order_id) AS orders,
  COUNT(DISTINCT customer_id) AS customers
FROM orders
GROUP BY category, segment
ORDER BY category, revenue DESC;

-- WHERE filters lines before they are grouped.
-- HAVING filters groups after the aggregate exists.
-- "Sub-categories that lost money" is a fact about the group, so it is HAVING.
--
-- Read this result and write one sentence, in your own words, about which
-- groups lost money and how large the loss is next to their revenue.
-- That sentence is a finding. The Pareto exercise later asks a different
-- question: which sub-categories make up most of the revenue, and are those
-- the same groups that make money?

SELECT
  category,
  sub_category,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct
FROM orders
GROUP BY category, sub_category
HAVING SUM(profit) < 0
ORDER BY profit;
