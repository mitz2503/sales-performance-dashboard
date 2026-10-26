#!/usr/bin/env python3
"""Load data/raw CSVs into a local SQLite database.

SQLite ships with Python, so this does not need a database server.
The schema lives in sql/00_schema.sql and is applied on every run.
Running this script again rebuilds data/superstore.db from the CSVs.

    python data/download_data.py
    python data/load_sqlite.py
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "superstore.db"
SCHEMA_PATH = ROOT / "sql" / "00_schema.sql"

# Row counts of the Tableau sample file this project was written against
# (downloaded October 2026). A different count means Tableau refreshed the
# file. The queries still run. Your numbers will differ from these notes.
REFERENCE_COUNTS = {
    "orders.csv": 10194,
    "people.csv": 4,
    "returns.csv": 296,
}

ORDER_FIELDS = [
    "row_id",
    "order_id",
    "order_date",
    "ship_date",
    "ship_mode",
    "customer_id",
    "customer_name",
    "segment",
    "country_region",
    "city",
    "state_province",
    "postal_code",
    "region",
    "product_id",
    "category",
    "sub_category",
    "product_name",
    "sales",
    "quantity",
    "discount",
    "profit",
]


def load_csv(path: Path, required: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(
            f"Missing {path.relative_to(ROOT)}.\n"
            "Create the CSVs first:\n"
            "  python data/download_data.py"
        )
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = [name for name in required if name not in fieldnames]
        if missing:
            raise SystemExit(f"{path.name} is missing columns {missing}. Found {fieldnames}.")
        return list(reader)


def blank_to_none(value: str) -> str | None:
    text = value.strip()
    return text if text else None


def order_tuple(row: dict[str, str]) -> tuple:
    try:
        return (
            int(row["row_id"]),
            row["order_id"].strip(),
            row["order_date"].strip(),
            row["ship_date"].strip(),
            row["ship_mode"].strip(),
            row["customer_id"].strip(),
            row["customer_name"].strip(),
            row["segment"].strip(),
            row["country_region"].strip(),
            row["city"].strip(),
            row["state_province"].strip(),
            blank_to_none(row["postal_code"]),
            row["region"].strip(),
            row["product_id"].strip(),
            row["category"].strip(),
            row["sub_category"].strip(),
            row["product_name"].strip(),
            float(row["sales"]),
            int(row["quantity"]),
            float(row["discount"]),
            float(row["profit"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"Could not parse order row {row.get('row_id')!r}: {exc}") from exc


def print_reference_note(name: str, actual: int) -> None:
    expected = REFERENCE_COUNTS[name]
    if actual == expected:
        print(f"  {name}: {actual:,} rows (matches the October 2026 sample)")
    else:
        print(
            f"  {name}: {actual:,} rows.\n"
            f"    The October 2026 sample had {expected:,}. Tableau may have "
            "updated the file. Keep going, and write findings from your file."
        )


def sanity_report(conn: sqlite3.Connection) -> None:
    print("\nSanity check (write these totals down; they belong in your findings):")
    row = conn.execute(
        """
        SELECT
          COUNT(*) AS lines,
          COUNT(DISTINCT order_id) AS orders,
          COUNT(DISTINCT customer_id) AS customers,
          MIN(order_date) AS first_order,
          MAX(order_date) AS last_order,
          ROUND(SUM(sales), 2) AS revenue,
          ROUND(SUM(profit), 2) AS profit,
          ROUND(SUM(profit) / SUM(sales), 4) AS margin_pct
        FROM orders
        """
    ).fetchone()
    labels = [
        "lines",
        "orders",
        "customers",
        "first_order",
        "last_order",
        "revenue",
        "profit",
        "margin_pct",
    ]
    for label, value in zip(labels, row):
        print(f"  {label}: {value}")

    unmatched = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders AS o
        LEFT JOIN people AS p ON p.region = o.region
        WHERE p.region IS NULL
        """
    ).fetchone()[0]
    if unmatched:
        print(
            f"  WARNING: {unmatched:,} order lines have a region with no manager. "
            "A join to people will leave those lines without a name."
        )
    else:
        print("  every order line matches a regional manager")

    returned_orders, return_rows = conn.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM returns AS r
            WHERE EXISTS (SELECT 1 FROM orders AS o WHERE o.order_id = r.order_id)),
          (SELECT COUNT(*) FROM returns)
        """
    ).fetchone()
    print(f"  returned order ids that match an order: {returned_orders} of {return_rows}")

    print("\nLines by country:")
    for country, count in conn.execute(
        "SELECT country_region, COUNT(*) FROM orders GROUP BY country_region ORDER BY 2 DESC"
    ):
        print(f"  {country}: {count:,}")


def main() -> None:
    if not SCHEMA_PATH.is_file():
        raise SystemExit(f"Missing schema file: {SCHEMA_PATH}")

    order_rows = load_csv(RAW_DIR / "orders.csv", ORDER_FIELDS)
    people_rows = load_csv(RAW_DIR / "people.csv", ["region", "regional_manager"])
    return_rows = load_csv(RAW_DIR / "returns.csv", ["order_id", "returned"])

    print("CSV row counts:")
    print_reference_note("orders.csv", len(order_rows))
    print_reference_note("people.csv", len(people_rows))
    print_reference_note("returns.csv", len(return_rows))

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        with conn:
            conn.executemany(
                """
                INSERT INTO orders (
                  row_id, order_id, order_date, ship_date, ship_mode,
                  customer_id, customer_name, segment, country_region,
                  city, state_province, postal_code, region, product_id,
                  category, sub_category, product_name, sales, quantity,
                  discount, profit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [order_tuple(row) for row in order_rows],
            )
            conn.executemany(
                "INSERT INTO people (region, regional_manager) VALUES (?, ?)",
                [
                    (row["region"].strip(), row["regional_manager"].strip())
                    for row in people_rows
                ],
            )
            conn.executemany(
                "INSERT INTO returns (order_id, returned) VALUES (?, ?)",
                [(row["order_id"].strip(), row["returned"].strip()) for row in return_rows],
            )
        sanity_report(conn)
    finally:
        conn.close()
    print(f"\nRebuilt {DB_PATH.relative_to(ROOT)}")
    print("Next: python scripts/run_sql.py sql/examples/01_joins.sql")


if __name__ == "__main__":
    main()
