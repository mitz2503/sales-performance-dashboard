# Dashboard guide

Build one small KPI dashboard from `output/fact_order_lines.csv`. Power BI Desktop is the main path. Tableau Public is a full alternative and the practical choice on a Mac, or whenever you want a public URL.

Do the SQL exercises first. The summary CSVs in `output/` are the answer tables for those exercises, and they are also how you check the dashboard. The report itself connects to the line-level file so that a Region slicer can filter every visual. A monthly summary with no region column cannot do that.

You are ready to start when this command has printed `Reconciliation passed`:

```bash
python scripts/export_kpis.py
```

## What you are building

Two pages.

**Page 1, Performance**

- Slicers: year, region, category, segment, return status
- Cards: revenue, profit, margin, orders, average order value, revenue year-over-year
- Line: revenue and profit by month
- Bar: top sub-categories by revenue
- Matrix: category by region, with revenue and margin

**Page 2, Drivers**

- Margin by discount band
- Seasonal overlay: month on the axis, one line per year (this is the picture of the year-over-year SQL)
- Revenue by category, split into Returned and Kept
- Average ship days by ship mode, checked against `output/kpi_ship_mode.csv`

Leave the default colors. Sorted axes, units, and titles that say what the chart is measuring matter more than a custom palette.

Title ideas, as questions the chart can answer:

- Revenue and profit by month
- Which sub-categories bring in the revenue?
- Margin by category and region
- Margin by discount band

Write the answers in the README findings. Keep the chart titles as questions.

## Spreadsheet check (about 20 minutes)

This is the Excel step, before any BI tool. Google Sheets works if you do not have Excel. The names below are Excel's.

1. Open `output/fact_order_lines.csv`.
2. Click any cell in the data, then Insert > PivotTable > New Worksheet.
3. Rows: `order_month`. Values: Sum of `sales`, Sum of `profit`.
4. Open `output/kpi_monthly.csv` beside it.
5. January 2023 (or the first month in your file) should match to the cent.

That pivot is `GROUP BY` order month. If it disagrees with the CSV, the pivot is counting the wrong column or the CSV was filtered.

## Install Power BI Desktop

Power BI Desktop is free and runs on 64-bit Windows 10 or Windows 11. It is not available as a native Mac app. On a Mac, use the Tableau Public section below for the visual project. The SQL and Python steps are the same on both.

Two official install paths:

- Microsoft Store, which updates itself: start from [Download Power BI Desktop](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop)
- Direct installer: [Microsoft Download Center, Power BI Desktop](https://www.microsoft.com/en-us/download/details.aspx?id=58494)

Microsoft ships a new Desktop build about once a month, so a button sometimes moves. Use the search box in the Power BI title bar and type the command name (`Mark as date table`, `New measure`). Match the words in this guide to the command, not to a screenshot from a single release.

You can build and screenshot the report with no account. Publishing to the Power BI service needs a work or school account. A public link is simpler in Tableau Public. Both options are at the end.

## Load the fact table

1. Home > Get data > Text/CSV.
2. Choose `output/fact_order_lines.csv`.
3. In the preview, set File Origin to 65001: Unicode (UTF-8) if the product names look garbled, and set Delimiter to Comma.
4. Load.

You should see on the order of 10,000 rows and these columns:

`row_id`, `order_id`, `order_date`, `ship_date`, `ship_days`, `ship_mode`, `customer_id`, `customer_name`, `segment`, `country_region`, `city`, `state_province`, `postal_code`, `region`, `regional_manager`, `product_id`, `category`, `sub_category`, `product_name`, `sales`, `quantity`, `discount`, `profit`, `line_margin_pct`, `is_returned`, `return_status`, `order_year`, `order_month`, `discount_band`, `band_sort`

If the column list is shorter, you loaded a `kpi_*.csv` summary. Remove it and load `fact_order_lines.csv`.

### Set data types

Open the Data view (table icon on the left).

| Column | Type |
| --- | --- |
| `order_date`, `ship_date` | Date |
| `sales`, `profit`, `discount`, `line_margin_pct` | Decimal number |
| `quantity`, `ship_days`, `is_returned`, `order_year`, `band_sort` | Whole number |
| `postal_code` and the name columns | Text |

`discount` should display as `0.2`, not as `20%`. Leave the column as a decimal. You will format the **margin measure** as a percentage later. Formatting the discount column as a percentage and also storing `0.2` would show 20%, which is right only if you remember you did not also multiply by 100. Easiest path: leave `discount` as a decimal number.

If the dates stayed as text: Home > Transform data, select `order_date`, Transform > Data Type > Date, repeat for `ship_date`, then Home > Close & Apply.

## Date table

Year-over-year math needs a calendar table. Slicers and the month axis should use this table, not `order_year` on the fact table. If the year slicer is a column on the fact table, `SAMEPERIODLASTYEAR` often returns a blank or ignores the comparison.

1. Home > New table, or the Table tools equivalent. This is a table, not a measure.
2. Name it `Dates` and paste:

```dax
Dates =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2023, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Year Month", FORMAT ( [Date], "YYYY-MM" ),
    "Year Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] )
)
```

If your loader printed a different first or last year, change the two `DATE(...)` bounds to cover your file. A date table that stops before the data, or starts after it, drops months out of the line chart.

3. Select the `Dates` table. Table tools > Mark as date table. Choose the `Date` column. Confirm.
4. Model view. Drag `fact_order_lines[order_date]` onto `Dates[Date]`.
5. Double-click the relationship. Cardinality: many fact rows to one date. Cross-filter direction: single, from `Dates` to the fact table. The date is on the "one" side. If Power BI offers the reverse, delete the line and create it again from the date column.
6. Data view, select `Dates[Month]`. Column tools > Sort by column > `Month Number`.
7. Select `Dates[Year Month]`. Sort by column > `Year Month Sort`. `YYYY-MM` already sorts in time as text; the sort column keeps the axis stable if the format ever changes.
8. `FORMAT` uses the Windows language. If month names come out in a language you did not expect, use `Year Month` on the chart axis. That column is `2023-01` style and does not depend on locale.

`Month` names do not sort alphabetically into calendar order. The sort-by-column step is what makes April follow March.

## Measures

Right-click `fact_order_lines` in the Data pane > New measure. Put every measure on that table so you can find them. Create them one at a time so a syntax error is easy to see.

`DIVIDE` returns blank when the denominator is zero or missing, instead of infinity. Use it for every ratio.

```dax
Total Revenue = SUM ( fact_order_lines[sales] )
```

Line revenue after discount, summed over whatever the slicers currently show.

```dax
Total Profit = SUM ( fact_order_lines[profit] )
```

```dax
Profit Margin % = DIVIDE ( [Total Profit], [Total Revenue] )
```

Select this measure. Measure tools > Format > Percentage, one decimal place. The value stays a fraction in the model. The format turns `0.126` into `12.6%`. Do not also multiply by 100 inside the formula.

```dax
Order Count = DISTINCTCOUNT ( fact_order_lines[order_id] )
```

Distinct orders in the current filter. A five-line order counts once.

```dax
Avg Order Value = DIVIDE ( [Total Revenue], [Order Count] )
```

Format as currency.

```dax
Revenue Last Year =
CALCULATE (
    [Total Revenue],
    SAMEPERIODLASTYEAR ( 'Dates'[Date] )
)
```

`CALCULATE` changes the filter, then evaluates the measure. `SAMEPERIODLASTYEAR` shifts the dates on the marked date table back one year. It needs the relationship and the "mark as date table" step.

```dax
Revenue YoY % =
DIVIDE (
    [Total Revenue] - [Revenue Last Year],
    [Revenue Last Year]
)
```

Format as percentage. For the first year in the file this card is blank. That blank matches the SQL `NULL`. It means "no prior year in the data," not "growth was zero."

```dax
Avg Ship Days =
AVERAGEX (
    VALUES ( fact_order_lines[order_id] ),
    CALCULATE ( MAX ( fact_order_lines[ship_days] ) )
)
```

This is the measure that matches exercise 7. `VALUES` lists the order ids in the current filter. For each id, `MAX(ship_days)` takes the number once (every line on the order has the same value). `AVERAGEX` averages those orders. `AVERAGE(ship_days)` would let a 10-line order vote ten times. Format as a decimal number, two places.

### A measure that should disagree

Create this, put it on a card next to `Profit Margin %`, and look at both with all slicers cleared:

```dax
Wrong Margin = AVERAGE ( fact_order_lines[line_margin_pct] )
```

They differ. `line_margin_pct` is the margin of one line, and `AVERAGE` gives a small line the same vote as a large one. `Profit Margin %` weights each dollar. Write one sentence on that difference in your notes, then delete `Wrong Margin` before you take screenshots.

### Sort the discount bands

Data view > select `fact_order_lines[discount_band]` > Column tools > Sort by column > `band_sort`.

The bands are `No discount`, `Up to 20%`, `20% to 40%`, `Over 40%`. The numeric `band_sort` column (1–4) is the order. You can right-click `band_sort` and hide it in report view after the sort is set. Hiding a column removes it from the field list. It does not delete it.

## Page 1

View > Page view > Fit to page. The default 16:9 canvas is fine. Rename the page to `Performance` (double-click the tab).

**Slicers.** Insert a slicer five times. Field, in order: `Dates[Year]`, `fact_order_lines[region]`, `fact_order_lines[category]`, `fact_order_lines[segment]`, `fact_order_lines[return_status]`. The year slicer must be `Dates[Year]`.

**Cards.** Insert a card for each of `Total Revenue`, `Total Profit`, `Profit Margin %`, `Order Count`, `Avg Order Value`, `Revenue YoY %`. Format revenue, profit, and average order value as currency. Zero decimal places on the revenue and profit cards are easier to read. Keep one decimal on the margin and on year-over-year.

**Monthly line.** Line chart.

- X-axis: `Dates[Year Month]`
- Y-axis: `Total Revenue` and `Total Profit`

**Sub-categories.** Clustered bar chart.

- Y-axis: `sub_category`
- X-axis: `Total Revenue`
- Tooltip: `Profit Margin %`
- Sort the visual by `Total Revenue` descending
- Filters on this visual > `sub_category` > Filter type > Top N > Show items: 10 > By value: `Total Revenue`

The top-N filter is a display choice. The other sub-categories are still in the data. Say that if you talk about concentration. Exercise 8 is the full ranking.

**Matrix.** 

- Rows: `category`
- Columns: `region`
- Values: `Total Revenue`, `Profit Margin %`

Turn on row totals if they are off (Format visual > Subtotals). Read this beside exercise 3. The numbers should match when no extra slicer is applied. The SQL result is unfiltered. A selected year on the slicer will change the matrix, which is what you want, and it will stop matching the full-period CSV until you clear the slicer.

Click a sub-category bar. The other visuals should filter. That cross-filtering is the default. Leave it on. Format > Edit interactions is where you would turn a single arrow off. You do not need to.

## Page 2

Duplicate nothing blindly. New page, name it `Drivers`. Copy the slicers across (select them, Ctrl+C, Ctrl+V) or recreate them, still with `Dates[Year]` for the year.

**Discount margin.** Clustered bar chart.

- Y-axis: `discount_band`
- X-axis: `Profit Margin %`

A negative margin extends the other way. Add `Total Revenue` as a tooltip so a tiny, ugly band is not confused with a large one.

**Seasonal overlay.** Line chart.

- X-axis: `Dates[Month]`
- Legend: `Dates[Year]`
- Y-axis: `Total Revenue`

Each line is a year. The vertical gap between lines in, say, November is the year-over-year change for November. That is the picture of `LAG` partitioned by month in exercise 4. The `Revenue YoY %` card is the number for whatever date filter is active.

**Returns.** Clustered bar chart.

- Y-axis: `category`
- Legend: `return_status`
- X-axis: `Total Revenue`

This is exercise 6, part B, as a chart. Remember the order-count warning from that exercise if you switch the axis to `Order Count`: an order with two categories is in both bars.

**Ship mode.** Clustered bar chart.

- Y-axis: `ship_mode`
- X-axis: `Avg Ship Days`
- Tooltip: `Profit Margin %`, `Avg Order Value`

Open `output/kpi_ship_mode.csv`. With slicers cleared, Standard Class average days on the chart should match `avg_ship_days` in the CSV to two decimals. If it matches `AVERAGE` of the line-level column instead, the measure is still the wrong grain.

## Check the cards

1. Clear every slicer.
2. Read the revenue line from `python data/load_sqlite.py` (run it again if you did not keep the printout) or the `Reconciliation passed` revenue from the export script.
3. `Total Revenue` should agree to the nearest dollar. A larger gap means a filter is still on, the date table is cutting off a year, or the file is not `fact_order_lines.csv`.
4. Sum of `revenue` in `output/kpi_monthly.csv` agrees with that total to the cent, aside from half-cent rounding across months.
5. Pick one discount band and compare `Profit Margin %` on the chart with `margin_pct` in `output/kpi_discount_bands.csv`.

Write the company total you actually see into the README. Do not copy a number from someone else's write-up of Superstore. Tableau refreshes the sample, and a memorized total from an old blog will not match your file.

## Caption, save, screenshots

Add a text box at the bottom of page 1:

> Source: Tableau Sample Superstore (fictitious data), Tableau Public sample data. https://public.tableau.com/app/learn/sample-data. Analysis and any errors are mine.

File > Save as. A sensible local path is `dashboard/office_supplies_kpis.pbix`. The `.pbix` embeds a copy of the data. This project gitignores `*.pbix` because the sample data is not licensed for redistribution. Commit the screenshots and, if you publish, the link in the README.

Take three screenshots with the slicers cleared, unless a screenshot is specifically "with Central selected" and your finding says so:

- `docs/images/overview.png` — page 1, full page
- `docs/images/margin_matrix.png` — the category by region matrix
- `docs/images/discount_bands.png` — the discount chart

Embed them in the README where the TODOs are.

## Publish

A local report is enough if the README says the dashboard is local. Add a public link when you publish.

**Tableau Public** is the free public link. Use the section below, publish, and paste the URL into the README.

**Power BI service.** Home > Publish sends the report to a workspace. That needs a work or school account, or a trial that includes a workspace. File > Embed report > Publish to web creates a public link and makes the data public. Only do that with this fictitious sample, and expect some tenants to have Publish to web switched off. If the menu is missing, that is a tenant setting, not a mistake in your report. Fall back to screenshots or to Tableau Public.

## Tableau Public alternative

Use this path on a Mac, or when you want a public URL. The charts are the same. The clicks are different. Install the free desktop app from [Tableau Public](https://www.tableau.com/products/public/download). It runs on Windows and Mac.

### Connect

1. Connect > To a file > Text file > `output/fact_order_lines.csv`.
2. Open a sheet. Confirm `order_date` has a date icon. If it is a string (`Abc`), click the icon and choose Date.
3. Confirm `discount` is a number around `0.2`, and `sales` is a dollar amount.

### Calculated fields

Analysis > Create Calculated Field. Create these three, then format margin as a percentage and the money fields as currency (right-click the field > Default Properties > Number Format).

Profit Margin:

```
SUM([profit]) / SUM([sales])
```

Order Count:

```
COUNTD([order_id])
```

Average Order Value:

```
SUM([sales]) / [Order Count]
```

Average ship days, one vote per order. `{ INCLUDE }` fixes the grain the way `AVERAGEX` did in DAX: average the per-order ship days, not the lines.

```
AVG({INCLUDE [order_id]: MIN([ship_days])})
```

If that formula is rejected by your Tableau version, skip it and plot `output/kpi_ship_mode.csv` for the ship-mode chart. The average in that file is taken at order grain.

### Build the sheets

Create each view as its own sheet, then Dashboard > New Dashboard, and drag the sheets on. Floating text boxes hold the title and the source caption.

| Sheet | Columns / rows | Notes |
| --- | --- | --- |
| Monthly trend | Columns: `order_date` as continuous month. Rows: `SUM(sales)` and `SUM(profit)` | Dual axis if you want both lines in one pane. Right-click the second pill > Dual Axis, then synchronize only if the scales should match. Profit is much smaller than sales, so two axes are reasonable. Say so if you use them |
| Seasonal overlay | Columns: discrete month of `order_date` (the `MONTH` pill, not the year). Rows: `SUM(sales)`. Color: year of `order_date` | Remove a year pill if Tableau adds one next to month. The gap between colors is the year-over-year gap |
| Sub-categories | Rows: `sub_category`. Columns: `SUM(sales)`. Sort descending | Filter to the top 10 by `SUM(sales)` if the bar chart is too long |
| Category by region | Rows: `category`. Columns: `region`. Text and color: `SUM(sales)` and Profit Margin | This is the matrix |
| Discount bands | Rows: `discount_band`. Columns: Profit Margin | Manual sort: No discount, Up to 20%, 20% to 40%, Over 40%. Right-click the header > Sort |
| Returns | Rows: `category`. Columns: `SUM(sales)`. Color: `return_status` | |
| Ship mode | Rows: `ship_mode`. Columns: average ship days | Check against `kpi_ship_mode.csv` |

Show filters for year, region, category, segment, and return status: right-click the field > Show Filter, then on the dashboard use them as slicers. Apply a filter to all sheets that use the fact table (filter card > Apply to Worksheets > All Using This Data Source) so the pages behave like the Power BI slicers.

Year-over-year as a single percentage: the seasonal sheet shows the same comparison as the year-over-year SQL. A table calculation (right-click a year pill > Quick Table Calculation > Percent Difference) is Tableau's version of `LAG`. If the table calculation jumps the wrong direction, open Compute Using and point it across the year. If it will not behave, use the percentage from `output/kpi_yoy_monthly.csv`. That figure was calculated in SQL.

### Publish

1. Server > Tableau Public > Save to Tableau Public.
2. Create a free account if you need one.
3. The workbook, including the extract of the CSV, becomes public. This sample is fictitious data Tableau already distributes for learning. Keep the citation on the dashboard anyway.
4. Copy the URL into the README dashboard section.

Do not add a second data source that contains anything from your own life or from an employer.

## If you get stuck

| What you see | What to check |
| --- | --- |
| `run_sql.py` says the exercise has no SQL yet | The file is waiting for your `SELECT`. That message is expected |
| Database not found | `python data/download_data.py` then `python data/load_sqlite.py` |
| Card is blank | Data type of `order_date`, the relationship, and whether `Dates` is marked as a date table |
| Year-over-year is blank for every year, including later years | The year slicer is probably `order_year` on the fact table. Move it to `Dates[Year]` |
| Year-over-year is blank only for 2023 | Expected on this file. There is no 2022 |
| Revenue card is far from the loader total | A slicer is on, or the date table does not cover the first and last order dates |
| Discount axis is in alphabetical order | Sort `discount_band` by `band_sort` |
| Margin shows `0.1%` when you expected about `12%` | The measure was divided by 100 and also formatted as a percentage. Keep the fraction, format as percentage |
| Map of states looks scrambled | `state_province` contains Canadian provinces. Filter `country_region` to United States, or skip the map. The project does not need one |
| Tableau month axis is a single year trend instead of 12 month names | You used continuous month. Switch the pill to discrete month and put year on Color |
