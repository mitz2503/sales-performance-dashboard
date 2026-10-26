#!/usr/bin/env python3
"""Run one or more SQL files against the local Superstore database.

    python scripts/run_sql.py sql/examples/01_joins.sql
    python scripts/run_sql.py sql/exercises/01_monthly_revenue_trend.sql
    python scripts/run_sql.py sql/solutions/01_monthly_revenue_trend.sql

The sqlite3 command-line program is not required. Python's standard library
is enough, which matters on a fresh Windows laptop.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "superstore.db"


def split_statements(sql: str) -> list[str]:
    """Split a script on semicolons, ignoring comments and quoted text."""
    statements: list[str] = []
    buffer: list[str] = []
    i = 0
    length = len(sql)
    in_single = False
    while i < length:
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < length else ""
        if in_single:
            buffer.append(char)
            if char == "'":
                if nxt == "'":
                    buffer.append(nxt)
                    i += 2
                    continue
                in_single = False
            i += 1
            continue
        if char == "'":
            in_single = True
            buffer.append(char)
            i += 1
            continue
        if char == "-" and nxt == "-":
            i += 2
            while i < length and sql[i] != "\n":
                i += 1
            continue
        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < length and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i = min(i + 2, length)
            continue
        if char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            i += 1
            continue
        buffer.append(char)
        i += 1
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def format_cell(value: object, width: int) -> str:
    if value is None:
        text = "NULL"
    else:
        text = str(value)
    if len(text) > width:
        return text[: width - 1] + "…"
    return text.ljust(width)


def print_rows(cursor: sqlite3.Cursor, limit: int) -> None:
    columns = [item[0] for item in cursor.description or []]
    if not columns:
        print("(statement ran, no result table)")
        return
    rows = cursor.fetchmany(limit + 1)
    truncated = len(rows) > limit
    shown = rows[:limit]
    widths = []
    for index, name in enumerate(columns):
        longest = len(name)
        for row in shown:
            cell = "NULL" if row[index] is None else str(row[index])
            longest = min(48, max(longest, len(cell)))
        widths.append(max(4, longest))
    header = "  ".join(name.ljust(widths[i])[: widths[i]] for i, name in enumerate(columns))
    print(header)
    print("  ".join("-" * width for width in widths))
    for row in shown:
        print("  ".join(format_cell(row[i], widths[i]) for i in range(len(columns))))
    if truncated:
        print(f"... showing the first {limit} rows. Re-run with --limit 0 to print every row.")
    else:
        print(f"({len(shown)} row{'s' if len(shown) != 1 else ''})")


def run_file(conn: sqlite3.Connection, path: Path, limit: int) -> None:
    sql = path.read_text(encoding="utf-8")
    statements = split_statements(sql)
    print(f"\n===== {path.as_posix()} =====")
    if not statements:
        print(
            "No SQL statements in this file yet.\n"
            "If it is an exercise, write your SELECT under the prompt, then run the file again."
        )
        return
    for number, statement in enumerate(statements, start=1):
        print(f"\n-- result {number}")
        try:
            cursor = conn.execute(statement)
        except sqlite3.Error as exc:
            print(f"SQLite error: {exc}", file=sys.stderr)
            print("Statement was:", file=sys.stderr)
            print(statement, file=sys.stderr)
            raise SystemExit(1) from exc
        if cursor.description:
            print_rows(cursor, limit if limit > 0 else 10**9)
        else:
            print("(statement ran, no result table)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_files", nargs="+", type=Path, help="SQL files to run, in order")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument(
        "--limit",
        type=int,
        default=60,
        help="Maximum rows to print per result. Use 0 for every row.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db if args.db.is_absolute() else ROOT / args.db
    if not db_path.is_file():
        raise SystemExit(
            f"Database not found at {db_path}.\n"
            "Build it first:\n"
            "  python data/download_data.py\n"
            "  python data/load_sqlite.py"
        )
    missing = [path for path in args.sql_files if not path.is_file()]
    if missing:
        raise SystemExit("SQL file not found:\n" + "\n".join(str(path) for path in missing))
    conn = sqlite3.connect(db_path)
    try:
        for path in args.sql_files:
            run_file(conn, path, args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
