#!/usr/bin/env python3
"""Export KPI tables from SQLite to CSV for Excel and the dashboard.

The metrics are defined in SQL so the CSVs, the exercises, and the dashboard
describe the same definitions. Python's job here is to run that SQL and
write the files. pandas is not used.

    python scripts/export_kpis.py

Output lands in output/ and is gitignored. Rebuild it any time.

The summary files are the answer tables for the SQL exercises. Finish a
first attempt at the exercise before you open the matching CSV.
fact_order_lines.csv is the table the dashboard guide connects to.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "superstore.db"
OUTPUT_DIR = ROOT / "output"

# Column order is the contract with docs/dashboard_guide.md.
FACT_SQL = """
SELECT
  row_id,
  order_id,
  order_date,
  ship_date,
  ship_days,
  ship_mode,
  customer_id,
  customer_name,
  segment,
  country_region,
  city,
  state_province,
  postal_code,
  region,
  regional_manager,
  product_id,
  category,
  sub_category,
  product_name,
  sales,
  quantity,
  discount,
  profit,
  line_margin_pct,
  is_returned,
  return_status,
  order_year,
  order_month,
  discount_band,
  band_sort
FROM v_order_lines
ORDER BY row_id
"""

MONTHLY_SQL = """
SELECT
  strftime('%Y-%m', order_date) AS order_month,
  CAST(strftime('%Y', order_date) AS INTEGER) AS order_year,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
  SUM(quantity) AS quantity
FROM orders
GROUP BY
  strftime('%Y-%m', order_date),
  CAST(strftime('%Y', order_date) AS INTEGER)
ORDER BY order_month
"""

CATEGORY_REGION_SQL = """
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
ORDER BY o.region, o.category
"""

CUSTOMERS_SQL = """
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
ORDER BY revenue_rank, customer_id
"""

DISCOUNT_SQL = """
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
  band_sort,
  COUNT(*) AS line_count,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(sales), 2) AS revenue,
  ROUND(SUM(profit), 2) AS profit,
  ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct,
  ROUND(AVG(discount), 4) AS avg_line_discount
FROM banded
GROUP BY discount_band, band_sort
ORDER BY band_sort
"""

YOY_SQL = """
WITH monthly AS (
  SELECT
    strftime('%Y-%m', order_date) AS order_month,
    CAST(strftime('%Y', order_date) AS INTEGER) AS order_year,
    CAST(strftime('%m', order_date) AS INTEGER) AS month_number,
    SUM(sales) AS revenue,
    SUM(profit) AS profit
  FROM orders
  GROUP BY
    strftime('%Y-%m', order_date),
    CAST(strftime('%Y', order_date) AS INTEGER),
    CAST(strftime('%m', order_date) AS INTEGER)
),
with_prior AS (
  SELECT
    monthly.order_month,
    monthly.order_year,
    monthly.month_number,
    monthly.revenue,
    monthly.profit,
    LAG(monthly.revenue) OVER (
      PARTITION BY monthly.month_number
      ORDER BY monthly.order_year
    ) AS prior_year_revenue
  FROM monthly
)
SELECT
  order_month,
  order_year,
  month_number,
  ROUND(revenue, 2) AS revenue,
  ROUND(profit, 2) AS profit,
  ROUND(prior_year_revenue, 2) AS prior_year_revenue,
  ROUND(revenue - prior_year_revenue, 2) AS yoy_change,
  ROUND((revenue - prior_year_revenue) / prior_year_revenue, 4) AS yoy_pct
FROM with_prior
ORDER BY order_year, month_number
"""

SHIP_SQL = """
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
ORDER BY avg_ship_days, ship_mode
"""

RETURNS_OVERALL_SQL = """
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
LEFT JOIN returns AS r ON r.order_id = o.order_id
"""

RETURNS_CATEGORY_SQL = """
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
ORDER BY o.category, return_status
"""

SUBCATEGORY_SQL = """
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
ORDER BY revenue DESC, sub_category
"""

EXPORTS: list[tuple[str, str, str]] = [
    (
        "fact_order_lines.csv",
        "One row per order line. Connect Power BI or Tableau to this file.",
        FACT_SQL,
    ),
    (
        "kpi_monthly.csv",
        "Exercise 1. One row per month.",
        MONTHLY_SQL,
    ),
    (
        "kpi_category_region.csv",
        "Exercise 3. One row per category and region.",
        CATEGORY_REGION_SQL,
    ),
    (
        "kpi_customers.csv",
        "Exercise 2 answer table for every customer, ranked. The exercise asks for the top 10.",
        CUSTOMERS_SQL,
    ),
    (
        "kpi_discount_bands.csv",
        "Exercise 5. One row per discount band.",
        DISCOUNT_SQL,
    ),
    (
        "kpi_yoy_monthly.csv",
        "Exercise 4. One row per month, with the same month last year.",
        YOY_SQL,
    ),
    (
        "kpi_ship_mode.csv",
        "Exercise 7. One row per ship mode, averaged at order grain.",
        SHIP_SQL,
    ),
    (
        "kpi_returns_overall.csv",
        "Exercise 6, part A. One row for the whole company.",
        RETURNS_OVERALL_SQL,
    ),
    (
        "kpi_returns_by_category.csv",
        "Exercise 6, part B. Category by returned vs kept.",
        RETURNS_CATEGORY_SQL,
    ),
    (
        "kpi_subcategory.csv",
        "Exercise 8. Sub-categories with a running share of revenue.",
        SUBCATEGORY_SQL,
    ),
]


def format_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text not in {"", "-"} else "0"
    return str(value)


def write_query(conn: sqlite3.Connection, filename: str, sql: str) -> tuple[int, list[str]]:
    cursor = conn.execute(sql)
    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()
    path = OUTPUT_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([format_cell(value) for value in row])
    return len(rows), columns


def scalar(conn: sqlite3.Connection, sql: str) -> float:
    value = conn.execute(sql).fetchone()[0]
    return float(value)


def reconcile(conn: sqlite3.Connection) -> None:
    """Fail the export if a join or a grouping changed the company total.

    Monthly and ship-mode files round each group to the cent, so the summed
    file can differ from the raw total by a few cents. A dollar of drift
    means a line was dropped or duplicated.
    """
    orders_lines = scalar(conn, "SELECT COUNT(*) FROM orders")
    fact_lines = scalar(conn, "SELECT COUNT(*) FROM v_order_lines")
    orders_sales = scalar(conn, "SELECT SUM(sales) FROM orders")
    fact_sales = scalar(conn, "SELECT SUM(sales) FROM v_order_lines")
    monthly_sales = scalar(conn, f"SELECT SUM(revenue) FROM ({MONTHLY_SQL}) AS monthly")
    ship_sales = scalar(conn, f"SELECT SUM(revenue) FROM ({SHIP_SQL}) AS ship")
    problems = []
    if orders_lines != fact_lines:
        problems.append(
            f"line count changed from {orders_lines:.0f} to {fact_lines:.0f} after the joins"
        )
    if abs(orders_sales - fact_sales) > 0.01:
        problems.append(f"fact sales {fact_sales} differ from orders sales {orders_sales}")
    if abs(orders_sales - monthly_sales) > 1:
        problems.append(f"monthly revenue {monthly_sales} differs from orders sales {orders_sales}")
    if abs(orders_sales - ship_sales) > 1:
        problems.append(f"ship-mode revenue {ship_sales} differs from orders sales {orders_sales}")
    if problems:
        raise SystemExit("Reconciliation failed:\n- " + "\n- ".join(problems))
    print(
        "\nReconciliation passed.\n"
        f"  lines: {orders_lines:.0f}\n"
        f"  revenue (unrounded sum of sales): {orders_sales:.2f}\n"
        "  fact file, monthly file, and ship-mode file agree with orders."
    )


def main() -> None:
    if not DEFAULT_DB.is_file():
        raise SystemExit(
            f"Database not found at {DEFAULT_DB.relative_to(ROOT)}.\n"
            "Build it first:\n"
            "  python data/download_data.py\n"
            "  python data/load_sqlite.py"
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEFAULT_DB)
    try:
        print("Writing output/ . Open the summary CSVs after you have tried the exercises.")
        for filename, description, sql in EXPORTS:
            count, _columns = write_query(conn, filename, sql)
            print(f"  {filename:<32} {count:>5} rows  {description}")
        reconcile(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
