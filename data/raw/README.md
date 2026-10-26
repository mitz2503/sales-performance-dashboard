# Raw data

This folder is empty in git on purpose.

## Source

The analysis uses **Tableau Sample Superstore**, a fictitious office-supplies retailer (furniture, office supplies, and technology) with US and Canadian customers.

| | |
| --- | --- |
| Publisher | Tableau (Salesforce) |
| Description | Products, sales, and profits for a fictitious company, plus a returns list and four regional managers |
| Sample-data page | https://public.tableau.com/app/learn/sample-data |
| File the script downloads | https://public.tableau.com/app/sample-data/sample_-_superstore.xls |
| Sheets | `Orders` (one row per order line), `People` (regional manager), `Returns` (returned order ids) |

## License

This workbook is **Tableau sample data**, published so people can learn Tableau. It is not released under an open license such as MIT, CC0, or CC BY. Tableau's site terms do not grant a general right to redistribute their materials, so this project does not commit the workbook or the CSVs derived from it.

The download script fetches the file from Tableau onto your machine. Credit Tableau when you publish the dashboard. A caption you can paste:

> Source: Tableau Sample Superstore (fictitious data), Tableau Public sample data. https://public.tableau.com/app/learn/sample-data

## What shows up here after you run the download

| File | What it is |
| --- | --- |
| `sample_superstore.xls` | The workbook, unchanged |
| `orders.csv` | Order lines, with stable column names and ISO dates |
| `people.csv` | One row per region |
| `returns.csv` | One row per returned order |

The CSVs are a lightly cleaned extract so SQLite and Excel can read them without Excel installed. Cleaning is limited to column names, date format, and postal codes stored as text (US ZIP codes that Excel had stored as numbers are padded back to 5 digits; Canadian codes are letters and are left as written). No rows are dropped.

If Tableau moves the URL, download **Superstore Sales** yourself from the sample-data page and save the `.xls` as `data/raw/sample_superstore.xls`. Then run `python data/download_data.py` again. The script will convert the local file.
