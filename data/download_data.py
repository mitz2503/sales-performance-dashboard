#!/usr/bin/env python3
"""Download Tableau's Sample Superstore workbook and write clean CSVs.

The workbook is fictitious sample data. It is not an open-license file, so it
is written under data/raw/ and left out of git. See data/raw/README.md.

Run from the project root:

    python data/download_data.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DEFAULT_XLS = RAW_DIR / "sample_superstore.xls"
SOURCE_URL = "https://public.tableau.com/app/sample-data/sample_-_superstore.xls"
SOURCE_PAGE = "https://public.tableau.com/app/learn/sample-data"

# Names on the Orders sheet of the Tableau workbook, as of the file
# published for the public sample-data page.
ORDER_COLUMNS = [
    "Row ID",
    "Order ID",
    "Order Date",
    "Ship Date",
    "Ship Mode",
    "Customer ID",
    "Customer Name",
    "Segment",
    "Country/Region",
    "City",
    "State/Province",
    "Postal Code",
    "Region",
    "Product ID",
    "Category",
    "Sub-Category",
    "Product Name",
    "Sales",
    "Quantity",
    "Discount",
    "Profit",
]


def require_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(
            "pandas is not installed.\n"
            "From the project root, with the virtual environment active:\n"
            "  pip install -r requirements.txt"
        ) from exc
    return pd


def looks_like_excel(path: Path) -> bool:
    """True for the legacy .xls OLE header or a .xlsx zip header."""
    with path.open("rb") as handle:
        signature = handle.read(8)
    return signature.startswith(b"\xD0\xCF\x11\xE0") or signature.startswith(b"PK\x03\x04")


def download_workbook(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + ".partial")
    print(f"Downloading\n  {SOURCE_URL}")
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "sales-performance-dashboard educational download"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            temporary.write_bytes(response.read())
    except Exception as exc:  # network, HTTP, and filesystem errors
        temporary.unlink(missing_ok=True)
        raise SystemExit(
            "Could not download the sample workbook.\n"
            f"Download Superstore Sales yourself from\n  {SOURCE_PAGE}\n"
            f"save the .xls file as\n  {dest}\n"
            "and run this script again.\n"
            f"Reason: {exc}"
        ) from exc
    if not looks_like_excel(temporary):
        temporary.unlink(missing_ok=True)
        raise SystemExit(
            "The download did not look like an Excel workbook (the server may have "
            "returned a web page). Download the file in a browser from\n"
            f"  {SOURCE_PAGE}\n"
            f"and save it as\n  {dest}"
        )
    temporary.replace(dest)
    print(f"Saved {dest} ({dest.stat().st_size:,} bytes)")


def clean_postal(value: object) -> str:
    """Store postal codes as text.

    Excel stored most US ZIP codes as numbers, so a code like 02134 was already
    shortened to 2134 in the source. Numeric codes are padded back to 5 digits.
    Canadian codes contain letters (for example M7A) and are kept as written.
    """
    pd = sys.modules.get("pandas")
    if value is None:
        return ""
    if pd is not None and not isinstance(value, str):
        try:
            if bool(pd.isna(value)):
                return ""
        except (TypeError, ValueError):
            pass
    if isinstance(value, str):
        text = value.strip()
        return text.zfill(5) if text.isdigit() else text
    if isinstance(value, float):
        if not value.is_integer():
            return str(value).strip()
        value = int(value)
    try:
        number = int(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        return text.zfill(5) if text.isdigit() else text
    return f"{number:05d}"


def require_columns(frame, required: list[str], sheet: str) -> None:
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise SystemExit(
            f"The {sheet} sheet is missing columns {missing}. "
            f"Found: {list(frame.columns)}. "
            "Tableau may have changed the sample file. Update the column list "
            "in data/download_data.py before continuing."
        )


def write_csvs(xls_path: Path) -> None:
    pd = require_pandas()
    try:
        workbook = pd.ExcelFile(xls_path, engine="calamine")
    except Exception as exc:
        raise SystemExit(
            "Could not read the workbook with the calamine engine.\n"
            "Install dependencies with: pip install -r requirements.txt\n"
            f"Detail: {exc}"
        ) from exc

    expected = {"Orders", "People", "Returns"}
    missing_sheets = expected.difference(workbook.sheet_names)
    if missing_sheets:
        raise SystemExit(
            f"Workbook is missing sheets {sorted(missing_sheets)}. "
            f"Found: {workbook.sheet_names}"
        )

    orders_raw = pd.read_excel(workbook, "Orders")
    people_raw = pd.read_excel(workbook, "People")
    returns_raw = pd.read_excel(workbook, "Returns")
    require_columns(orders_raw, ORDER_COLUMNS, "Orders")
    require_columns(people_raw, ["Regional Manager", "Region"], "People")
    require_columns(returns_raw, ["Order ID", "Returned"], "Returns")

    order_dates = pd.to_datetime(orders_raw["Order Date"], errors="coerce")
    ship_dates = pd.to_datetime(orders_raw["Ship Date"], errors="coerce")
    if order_dates.isna().any() or ship_dates.isna().any():
        raise SystemExit("Some order dates or ship dates could not be parsed.")

    orders = pd.DataFrame(
        {
            "row_id": orders_raw["Row ID"].astype(int),
            "order_id": orders_raw["Order ID"].astype(str).str.strip(),
            "order_date": order_dates.dt.strftime("%Y-%m-%d"),
            "ship_date": ship_dates.dt.strftime("%Y-%m-%d"),
            "ship_mode": orders_raw["Ship Mode"].astype(str).str.strip(),
            "customer_id": orders_raw["Customer ID"].astype(str).str.strip(),
            "customer_name": orders_raw["Customer Name"].astype(str).str.strip(),
            "segment": orders_raw["Segment"].astype(str).str.strip(),
            "country_region": orders_raw["Country/Region"].astype(str).str.strip(),
            "city": orders_raw["City"].astype(str).str.strip(),
            "state_province": orders_raw["State/Province"].astype(str).str.strip(),
            "postal_code": orders_raw["Postal Code"].map(clean_postal),
            "region": orders_raw["Region"].astype(str).str.strip(),
            "product_id": orders_raw["Product ID"].astype(str).str.strip(),
            "category": orders_raw["Category"].astype(str).str.strip(),
            "sub_category": orders_raw["Sub-Category"].astype(str).str.strip(),
            "product_name": orders_raw["Product Name"].astype(str).str.strip(),
            "sales": orders_raw["Sales"].astype(float),
            "quantity": orders_raw["Quantity"].astype(int),
            "discount": orders_raw["Discount"].astype(float),
            "profit": orders_raw["Profit"].astype(float),
        }
    )
    if orders["row_id"].duplicated().any():
        raise SystemExit("Orders sheet has duplicate Row ID values.")

    people = pd.DataFrame(
        {
            "region": people_raw["Region"].astype(str).str.strip(),
            "regional_manager": people_raw["Regional Manager"].astype(str).str.strip(),
        }
    )
    if people["region"].duplicated().any():
        raise SystemExit(
            "People sheet has more than one manager for a region. "
            "Joining it to orders would double-count revenue."
        )

    returns = pd.DataFrame(
        {
            "order_id": returns_raw["Order ID"].astype(str).str.strip(),
            "returned": returns_raw["Returned"].astype(str).str.strip(),
        }
    )
    if returns["order_id"].duplicated().any():
        raise SystemExit(
            "Returns sheet has duplicate order ids. "
            "Joining it to orders would double-count those lines."
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    orders.to_csv(RAW_DIR / "orders.csv", index=False)
    people.to_csv(RAW_DIR / "people.csv", index=False)
    returns.to_csv(RAW_DIR / "returns.csv", index=False)
    print(
        "Wrote CSVs into data/raw/:\n"
        f"  orders.csv   {len(orders):,} lines\n"
        f"  people.csv   {len(people):,} regions\n"
        f"  returns.csv  {len(returns):,} returned orders"
    )
    print(
        "\nSource: Tableau Sample Superstore (fictitious).\n"
        f"Page: {SOURCE_PAGE}\n"
        "The data stays in data/raw/ and is gitignored."
    )
    print("Next: python data/load_sqlite.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download the workbook again even if a local copy exists.",
    )
    parser.add_argument(
        "--xls",
        type=Path,
        help="Use this workbook instead of downloading. It is copied into data/raw/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.xls:
        source = args.xls.expanduser().resolve()
        if not source.is_file():
            raise SystemExit(f"File not found: {source}")
        if not looks_like_excel(source):
            raise SystemExit(f"{source} does not look like an Excel workbook.")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        if source != DEFAULT_XLS.resolve():
            shutil.copyfile(source, DEFAULT_XLS)
            print(f"Copied workbook to {DEFAULT_XLS}")
        xls_path = DEFAULT_XLS
    elif DEFAULT_XLS.is_file() and looks_like_excel(DEFAULT_XLS) and not args.force:
        print(f"Using existing workbook {DEFAULT_XLS}")
        xls_path = DEFAULT_XLS
    else:
        download_workbook(DEFAULT_XLS)
        xls_path = DEFAULT_XLS
    write_csvs(xls_path)


if __name__ == "__main__":
    main()
