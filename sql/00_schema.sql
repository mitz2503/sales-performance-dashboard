-- Local warehouse for the Tableau Sample Superstore workbook.
-- Rebuild is safe: this database is a copy you can delete and load again.
--
-- Grain
--   orders   one row = one product line on an order (not one order)
--   people   one row = one sales region and its manager
--   returns  one row = one order id that was returned
--
-- An order id appears on several rows of orders when the customer bought
-- more than one product. Returns are recorded at order id, not at line.
-- The line's sales and profit stay in orders even when the order is returned.
--
-- Dates are ISO text (YYYY-MM-DD). SQLite has no separate DATE type.
-- strftime and julianday understand this format.
--
-- order_id is not a primary key. A primary key has to be unique, and an
-- order has many lines. row_id is the unique key of a line.
-- people.region can be a primary key because the download script rejects
-- a workbook that has two managers for one region. returns.order_id is
-- unique for the same reason. There is no foreign key from orders.order_id
-- to returns: most orders are absent from returns, and orders.order_id
-- itself is not unique, so it cannot be the parent side of a foreign key.

DROP VIEW IF EXISTS v_order_lines;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS people;
DROP TABLE IF EXISTS returns;

CREATE TABLE orders (
  row_id INTEGER PRIMARY KEY,
  order_id TEXT NOT NULL,
  order_date TEXT NOT NULL,
  ship_date TEXT NOT NULL,
  ship_mode TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  segment TEXT NOT NULL,
  country_region TEXT NOT NULL,
  city TEXT NOT NULL,
  state_province TEXT NOT NULL,
  postal_code TEXT,
  region TEXT NOT NULL,
  product_id TEXT NOT NULL,
  category TEXT NOT NULL,
  sub_category TEXT NOT NULL,
  product_name TEXT NOT NULL,
  sales REAL NOT NULL,
  quantity INTEGER NOT NULL,
  discount REAL NOT NULL,
  profit REAL NOT NULL
);

CREATE TABLE people (
  region TEXT PRIMARY KEY,
  regional_manager TEXT NOT NULL
);

CREATE TABLE returns (
  order_id TEXT PRIMARY KEY,
  returned TEXT NOT NULL
);

-- Helpful for the joins and filters in the exercises.
-- On a 10,000-line file the difference is tiny. The habit matters on a
-- company table that is a thousand times larger.
CREATE INDEX idx_orders_order_id ON orders (order_id);
CREATE INDEX idx_orders_order_date ON orders (order_date);
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_orders_region ON orders (region);
CREATE INDEX idx_orders_category ON orders (category);

-- A convenience view for exploration and for the Power BI extract.
-- Exercises that are about joins or about the discount CASE ask you to
-- write that logic against the base tables. Use the view after that,
-- when you want the flags already attached.
--
-- line_margin_pct is the margin of a single line. It is the wrong number
-- to average when someone asks for "the" margin. Sum profit and sum sales
-- first, then divide. The name is awkward on purpose.
CREATE VIEW v_order_lines AS
SELECT
  o.row_id,
  o.order_id,
  o.order_date,
  o.ship_date,
  CAST(julianday(o.ship_date) - julianday(o.order_date) AS INTEGER) AS ship_days,
  o.ship_mode,
  o.customer_id,
  o.customer_name,
  o.segment,
  o.country_region,
  o.city,
  o.state_province,
  o.postal_code,
  o.region,
  p.regional_manager,
  o.product_id,
  o.category,
  o.sub_category,
  o.product_name,
  o.sales,
  o.quantity,
  o.discount,
  o.profit,
  CASE
    WHEN o.sales = 0 THEN NULL
    ELSE o.profit / o.sales
  END AS line_margin_pct,
  CASE WHEN r.order_id IS NOT NULL THEN 1 ELSE 0 END AS is_returned,
  CASE WHEN r.order_id IS NOT NULL THEN 'Returned' ELSE 'Kept' END AS return_status,
  CAST(strftime('%Y', o.order_date) AS INTEGER) AS order_year,
  strftime('%Y-%m', o.order_date) AS order_month,
  CASE
    WHEN o.discount = 0 THEN 'No discount'
    WHEN o.discount <= 0.20 THEN 'Up to 20%'
    WHEN o.discount <= 0.40 THEN '20% to 40%'
    ELSE 'Over 40%'
  END AS discount_band,
  CASE
    WHEN o.discount = 0 THEN 1
    WHEN o.discount <= 0.20 THEN 2
    WHEN o.discount <= 0.40 THEN 3
    ELSE 4
  END AS band_sort
FROM orders AS o
LEFT JOIN people AS p ON p.region = o.region
LEFT JOIN returns AS r ON r.order_id = o.order_id;
