# Sales KPI analysis for an office-supplies distributor

SQL, Python, and a Power BI or Tableau dashboard over four years of line-item sales for a fictitious office-supplies company (furniture, office supplies, and technology).

> **Status: the analysis is yours to finish.** The findings, screenshots, and dashboard link below are marked TODO. They stay blank until the queries have been run and the numbers are filled in from this file.

## Business question

Where does this distributor make money, and where do discounts, returns, region, and product mix give it back?

A useful answer names a KPI, the grain it was calculated at, the time range, and one decision a sales manager could take. "Revenue went up" is a start. "Revenue went up while margin in one category went negative, and the deep-discount lines are where the profit disappeared" is an analysis.

## Dataset

**Tableau Sample Superstore.** Fictitious retail data published by Tableau for learning. It behaves like an office-supplies distributor: categories are Furniture, Office Supplies, and Technology; customers fall into Consumer, Corporate, and Home Office; geography is US states plus a smaller set of Canadian provinces, rolled into four sales regions.

| | |
| --- | --- |
| Publisher | Tableau (Salesforce) |
| Sample-data page | https://public.tableau.com/app/learn/sample-data |
| File the script downloads | https://public.tableau.com/app/sample-data/sample_-_superstore.xls |
| Sheets | `Orders`, `People` (regional managers), `Returns` |
| Coverage of the October 2026 file | Order dates from 2023-01-03 through 2026-12-30, all 12 months in each year |

The October 2026 file has 10,194 order lines, 5,111 orders, 4 regions, and 296 returned order ids. If your download prints different counts, Tableau has refreshed the sample. Keep going and write findings from the file you have.

### License

Tableau sample data is provided for learning. It is **not** under MIT, CC0, or Creative Commons. This repository does not contain the workbook. `data/download_data.py` fetches it from Tableau onto your machine, and `.gitignore` keeps it there. Credit Tableau on the dashboard:

> Source: Tableau Sample Superstore (fictitious data), Tableau Public sample data. https://public.tableau.com/app/learn/sample-data

Details: [data/raw/README.md](data/raw/README.md).

### Grain

One row of `orders` is **one product line on an order**, not one order. This made-up pair of lines is only here to show the shape. These are not rows from the file.

| row_id | order_id | order_date | customer_id | category | sales | quantity | discount | profit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CA-1001 | 2023-01-04 | AB-10015 | Office Supplies | 20.00 | 2 | 0.00 | 6.00 |
| 2 | CA-1001 | 2023-01-04 | AB-10015 | Furniture | 200.00 | 1 | 0.20 | -15.00 |

Those two lines are one order. Revenue is $220. Profit is -$9. Margin is -9 / 220, not the average of 6/20 and -15/200.

`people` is one row per region. `returns` is one row per returned order id. A returned order is still present in `orders` with its original sales and profit. The flag does not reverse the sale.

### Column dictionary

Names below are the ones in `orders.csv` and in SQLite, after the download script renames the Excel headers.

| Column | Meaning |
| --- | --- |
| `row_id` | Unique id of the line |
| `order_id` | Order. Repeats once per line on that order |
| `order_date`, `ship_date` | ISO dates (`YYYY-MM-DD`) |
| `ship_mode` | Same Day, First Class, Second Class, or Standard Class |
| `customer_id`, `customer_name` | Customer. The id is the key |
| `segment` | Consumer, Corporate, or Home Office. One segment per customer id |
| `country_region` | United States or Canada |
| `city`, `state_province`, `postal_code` | Destination. Postal code is text |
| `region` | Central, East, South, or West |
| `product_id`, `category`, `sub_category`, `product_name` | What was sold |
| `sales` | Line revenue **after** discount. Do not multiply by `(1 - discount)` again |
| `quantity` | Units on the line |
| `discount` | Discount **rate**. `0.20` means 20% |
| `profit` | Line profit. Negative means the line lost money |

`people.regional_manager` is the manager for `people.region`. `returns.returned` is `Yes` for every row in that sheet; the presence of the order id is the flag.

### Quirks worth being able to explain

- **Customer ids.** Each customer id has one name and one segment. Most customers buy in more than one region, so region is not a customer attribute. One name, Harry Olson, has five ids (`HO-15230` through `HO-15234`): 10 lines across 4 orders. Two of those orders carry more than one of his ids. Ranking by name merges him. Ranking by id, which the exercises do, keeps the ids split.
- **Postal codes.** Excel had stored most US ZIP codes as numbers, which drops a leading zero. The loader pads numeric codes back to 5 digits. Canadian codes contain letters and are unchanged.
- **Canada.** The October 2026 file has 200 Canadian lines, assigned to East, West, or Central. A map of `state_province` mixes provinces and states.
- **Returns.** Headline `SUM(sales)` includes returned orders. Filter on the return flag when you want a "kept" total, and say which one you are quoting.
- **Dates.** The company is fictitious. A file that contains December 2026 is not a forecast. It is the sample's calendar. Confirm each year has 12 months before you call a comparison year-over-year.

## KPI definitions

Use these definitions everywhere: SQL, the CSV extracts, Excel, and the dashboard. A ratio is a fraction in the data (`0.1256`) and a percentage only in the visual format (`12.6%`).

| KPI | Definition | Watch-out |
| --- | --- | --- |
| Revenue | `SUM(sales)` | Already after discount |
| Profit | `SUM(profit)` | Can be negative |
| Profit margin | `SUM(profit) / SUM(sales)` | Average of line margins is a different statistic |
| Orders | `COUNT(DISTINCT order_id)` | `COUNT(*)` counts lines |
| Average order value | Revenue / orders | `AVG(sales)` is the average line |
| Discount band | Rate on the line, in four bands | An order can sit in several bands |
| Return share | Returned order ids / all order ids | Recorded at order id, not at line |
| Ship days | `ship_date - order_date`, averaged **per order** | A 10-line order is still one shipment |
| YoY growth | This month versus the same month last year | The first year has no prior year. Leave that null |

The same ideas in the three tools:

| Idea | SQL | DAX | Tableau |
| --- | --- | --- | --- |
| Revenue | `SUM(sales)` | `SUM(fact_order_lines[sales])` | `SUM([sales])` |
| Margin | `SUM(profit) / SUM(sales)` | `DIVIDE([Total Profit], [Total Revenue])` | `SUM([profit]) / SUM([sales])` |
| Orders | `COUNT(DISTINCT order_id)` | `DISTINCTCOUNT(fact_order_lines[order_id])` | `COUNTD([order_id])` |

Click-by-click instructions, including the date table and the year-over-year measure, are in [docs/dashboard_guide.md](docs/dashboard_guide.md).

## Project structure

```
README.md                          this page
requirements.txt                   pandas + the Excel reader
data/download_data.py              fetch the Tableau workbook, write CSVs
data/load_sqlite.py                build data/superstore.db
data/raw/                          workbook and CSVs (not in git)
sql/00_schema.sql                  tables, indexes, and v_order_lines
sql/examples/                      three worked queries (joins, GROUP BY, windows)
sql/exercises/                     eight questions and hints, no answer SQL
sql/solutions/                     reference queries, after you have tried
scripts/run_sql.py                 run a SQL file without the sqlite3 CLI
scripts/export_kpis.py             write output/*.csv from the database
docs/dashboard_guide.md            Power BI Desktop, then Tableau Public
docs/images/                       your screenshots
output/                            generated KPI CSVs (not in git)
```

| Example | What it teaches |
| --- | --- |
| `sql/examples/01_joins.sql` | `LEFT JOIN`, grain, and a row-count check before you trust a total |
| `sql/examples/02_group_by.sql` | Aggregates, margin as a ratio of sums, `WHERE` versus `HAVING` |
| `sql/examples/03_window_functions.sql` | `RANK`, share of total, running sum, `LAG` |

| Exercise | Business question |
| --- | --- |
| 01 | Monthly revenue, profit, margin, orders, average order value |
| 02 | Top 10 customer ids by revenue, with profit and share of total |
| 03 | Margin by category and region, with the regional manager |
| 04 | Year-over-year revenue by month |
| 05 | Revenue and margin by discount band |
| 06 | Returned orders, overall and by category |
| 07 | Ship mode: speed, margin, and average order value at order grain |
| 08 | Which sub-categories make up the first 80% of revenue, and their margin |

## How to run

You need Python 3.11 or newer. Nothing else has to be installed for the SQL and Python portion. SQLite is in the Python standard library. Power BI Desktop is a separate free install on Windows. Tableau Public is a separate free install on Windows or Mac. A spreadsheet is optional and used once, as a check.

### 1. Environment

Windows (PowerShell), from this folder:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python` works and `python3` does not, use `python`. On Windows, `py -3` is the reliable launcher.

### 2. Data and database

```bash
python data/download_data.py
python data/load_sqlite.py
```

The loader prints revenue, profit, margin, the date range, and the line count. Copy those into your notes. They are the company totals your dashboard cards have to match.

If the download fails, save the workbook yourself from the [sample-data page](https://public.tableau.com/app/learn/sample-data) as `data/raw/sample_superstore.xls` and run `python data/download_data.py` again.

Optional GUI for the database: [DB Browser for SQLite](https://sqlitebrowser.org/). You do not need it. `scripts/run_sql.py` prints results in the terminal.

### 3. SQL

```bash
python scripts/run_sql.py sql/examples/01_joins.sql
python scripts/run_sql.py sql/examples/02_group_by.sql
python scripts/run_sql.py sql/examples/03_window_functions.sql
python scripts/run_sql.py sql/exercises/01_monthly_revenue_trend.sql
```

The exercise command prints a reminder until you write a `SELECT` in the file. Add `--limit 0` to print every row of a long result.

### 4. KPI extracts

After you have attempted the exercises:

```bash
python scripts/export_kpis.py
```

This writes `output/`. The script checks that the fact file, the monthly file, and the ship-mode file still add up to `SUM(sales)` on `orders`. `output/fact_order_lines.csv` is the table the dashboard connects to. The `kpi_*.csv` files are the exercise results in table form.

## Order of work

1. Read the grain, the KPI table, and the quirks above.
2. Load the database and keep the printed totals. A line is one product on an order. An order is `COUNT(DISTINCT order_id)`.
3. Run the three examples.
4. Do exercises 1–8 in order. Write a query that runs before you open the file with the same name in `sql/solutions/`.
5. Export the CSVs and compare your result to the matching `output/kpi_*.csv`. Money is rounded to the cent in both places.
6. Do the short spreadsheet check in the dashboard guide, then build the dashboard.
7. Fill in Findings, embed screenshots, and add the dashboard link.

### Checklist

- [ ] Virtual environment created and `requirements.txt` installed
- [ ] Workbook downloaded; the dashboard cites Tableau, and the file is not committed
- [ ] `data/superstore.db` loads, and the printed totals are written down
- [ ] Exercises 1–8 each ran before the matching solution was opened
- [ ] Results match `output/kpi_*.csv` after the export
- [ ] A spreadsheet pivot of the fact file matches one SQL month
- [ ] Power BI or Tableau page is built from the measures in the dashboard guide
- [ ] The revenue card matches the loader total with the slicers cleared
- [ ] Findings below use numbers calculated from this file, with the time range and the grain
- [ ] Screenshots are saved in `docs/images/` and embedded here
- [ ] Dashboard link is filled in, or the README says the report is local and why

## Findings

Write these after the exercises. Include the time range, the grain, and the figure.

> **TODO.** Overall performance. State total revenue, profit, and margin for the full period from your loader output. Say whether the monthly trend is steady, and name one month or year that surprised you. Point at exercise 1 and exercise 4.

> **TODO.** Where profit is weak. Name the category, sub-category, or region where margin is weak or negative, and compare it with the company margin. Point at exercise 3 and exercise 8.

> **TODO.** Discounts. Say which discount bands still make money and which give it back. One sentence on what you would tell a sales manager. Point at exercise 5.

> **TODO.** Customers and returns. Say how concentrated revenue is (top 10 customer ids as a share of revenue) and what share of orders and of revenue sits on returned orders. Point at exercise 2 and exercise 6.

## Dashboard

Build it by following [docs/dashboard_guide.md](docs/dashboard_guide.md). Power BI Desktop is free and Windows-only. Tableau Public is free on Windows and Mac and is the straightforward way to get a public link.

> **TODO.** Public dashboard URL:

**Overview screenshot:** TODO. Save `docs/images/overview.png`, then embed it:

```markdown
![KPI overview](docs/images/overview.png)
```

**Margin by category and region:** TODO. Save `docs/images/margin_matrix.png`.

**Discount bands:** TODO. Save `docs/images/discount_bands.png`.

Suggested footer on the report itself:

> Source: Tableau Sample Superstore (fictitious data), Tableau Public sample data. Analysis and any errors are mine.

## License of this repository

The SQL, Python, and writing in this repository are published under the MIT License. Copyright is held by the repository owner. You can use, copy, and modify the code with attribution.

That license does **not** cover the Sample Superstore data. The data remains Tableau sample data, is downloaded at runtime, and is gitignored. See [data/raw/README.md](data/raw/README.md).
