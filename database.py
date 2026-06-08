"""
database.py
-----------
Builds and seeds a realistic SQLite business database with:
  - customers, products, orders, order_items, sales_reps, regions
Designed to support rich natural-language SQL queries.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = "business.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id   INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL,
    country     TEXT NOT NULL DEFAULT 'USA'
);

CREATE TABLE IF NOT EXISTS sales_reps (
    rep_id      INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    region_id   INTEGER REFERENCES regions(region_id),
    hire_date   TEXT,
    quota       REAL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT,
    segment      TEXT CHECK(segment IN ('Enterprise','Mid-Market','SMB','Consumer')),
    region_id    INTEGER REFERENCES regions(region_id),
    rep_id       INTEGER REFERENCES sales_reps(rep_id),
    join_date    TEXT,
    is_active    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT,
    unit_price   REAL NOT NULL,
    cost         REAL NOT NULL,
    is_active    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER REFERENCES customers(customer_id),
    rep_id       INTEGER REFERENCES sales_reps(rep_id),
    order_date   TEXT NOT NULL,
    status       TEXT CHECK(status IN ('Completed','Pending','Cancelled','Refunded')),
    payment_method TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id      INTEGER PRIMARY KEY,
    order_id     INTEGER REFERENCES orders(order_id),
    product_id   INTEGER REFERENCES products(product_id),
    quantity     INTEGER NOT NULL,
    unit_price   REAL NOT NULL,
    discount_pct REAL DEFAULT 0
);
"""

REGIONS = [
    (1, "Northeast", "USA"), (2, "Southeast", "USA"),
    (3, "Midwest",   "USA"), (4, "Southwest", "USA"),
    (5, "West Coast","USA"), (6, "Canada",    "Canada"),
]

SALES_REPS = [
    (1, "Sarah Chen",    1, "2020-03-15", 500000),
    (2, "Marcus Rivera", 2, "2019-07-01", 450000),
    (3, "Priya Patel",   3, "2021-01-10", 400000),
    (4, "James Okafor",  4, "2020-11-20", 420000),
    (5, "Emily Watson",  5, "2018-05-05", 600000),
    (6, "David Kim",     6, "2022-03-01", 350000),
    (7, "Lisa Thompson", 1, "2021-08-15", 480000),
    (8, "Raj Mehta",     3, "2019-12-01", 460000),
]

PRODUCTS = [
    (1,  "Analytics Pro Suite",   "Software",  12000,  2400),
    (2,  "Data Pipeline Engine",  "Software",   8500,  1700),
    (3,  "BI Dashboard License",  "Software",   4200,   840),
    (4,  "Cloud Storage — 1TB",   "Cloud",      1800,   360),
    (5,  "Cloud Storage — 5TB",   "Cloud",      7200,  1440),
    (6,  "API Access — Basic",    "API",        2400,   480),
    (7,  "API Access — Pro",      "API",        6000,  1200),
    (8,  "Consulting — 10hrs",    "Services",   5000,  2000),
    (9,  "Consulting — 40hrs",    "Services",  18000,  7200),
    (10, "Training Workshop",     "Services",   3500,  1400),
    (11, "Security Module",       "Software",   5500,  1100),
    (12, "Mobile SDK License",    "Software",   3200,   640),
]

SEGMENTS  = ["Enterprise", "Mid-Market", "SMB", "Consumer"]
SEG_W     = [0.15, 0.25, 0.40, 0.20]
STATUSES  = ["Completed", "Pending", "Cancelled", "Refunded"]
STATUS_W  = [0.75, 0.12, 0.08, 0.05]
PAYMENTS  = ["Credit Card", "Wire Transfer", "ACH", "Check"]


def random_date(start_days_ago: int = 730, end_days_ago: int = 0) -> str:
    base  = datetime.today() - timedelta(days=start_days_ago)
    delta = timedelta(days=random.randint(0, start_days_ago - end_days_ago))
    return (base + delta).strftime("%Y-%m-%d")


def build(db_path: str = DB_PATH, n_customers: int = 300, n_orders: int = 2000):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Regions & reps
    conn.executemany("INSERT INTO regions VALUES (?,?,?)", REGIONS)
    conn.executemany("INSERT INTO sales_reps VALUES (?,?,?,?,?)", SALES_REPS)

    # Products
    conn.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)",
                     [(p[0], p[1], p[2], p[3], p[4], 1) for p in PRODUCTS])

    # Customers
    first_names = ["Alice","Bob","Carol","David","Emma","Frank","Grace","Henry",
                   "Iris","Jack","Karen","Leo","Maya","Nick","Olivia","Paul",
                   "Quinn","Rachel","Sam","Tina","Uma","Victor","Wendy","Xander"]
    last_names  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
                   "Davis","Wilson","Taylor","Anderson","Thomas","Jackson","White"]

    customers = []
    for cid in range(1, n_customers + 1):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        seg  = random.choices(SEGMENTS, SEG_W)[0]
        rid  = random.randint(1, 6)
        rep  = random.randint(1, 8)
        customers.append((
            cid, name, f"{name.lower().replace(' ','.')}@example.com",
            seg, rid, rep, random_date(1095, 30), 1
        ))
    conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)", customers)

    # Orders + items
    orders, items = [], []
    item_id = 1
    for oid in range(1, n_orders + 1):
        cid    = random.randint(1, n_customers)
        rep    = customers[cid - 1][5]
        odate  = random_date(730, 0)
        status = random.choices(STATUSES, STATUS_W)[0]
        payment= random.choice(PAYMENTS)
        orders.append((oid, cid, rep, odate, status, payment))

        n_items = random.choices([1, 2, 3, 4], [0.50, 0.30, 0.15, 0.05])[0]
        chosen  = random.sample(PRODUCTS, min(n_items, len(PRODUCTS)))
        for prod in chosen:
            qty  = random.randint(1, 5)
            disc = random.choices([0, 0.05, 0.10, 0.15, 0.20],
                                  [0.60, 0.15, 0.12, 0.08, 0.05])[0]
            items.append((item_id, oid, prod[0], qty, prod[3], disc))
            item_id += 1

    conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    conn.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", items)

    # Add helpful views
    conn.executescript("""
        CREATE VIEW IF NOT EXISTS v_order_revenue AS
        SELECT
            o.order_id,
            o.order_date,
            o.status,
            o.customer_id,
            c.name      AS customer_name,
            c.segment,
            r.region_name,
            s.name      AS rep_name,
            SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)) AS revenue,
            SUM(oi.quantity * p.cost)                                  AS cogs,
            SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
              - SUM(oi.quantity * p.cost)                              AS gross_profit
        FROM orders o
        JOIN customers c  ON o.customer_id = c.customer_id
        JOIN regions r    ON c.region_id   = r.region_id
        JOIN sales_reps s ON o.rep_id      = s.rep_id
        JOIN order_items oi ON o.order_id  = oi.order_id
        JOIN products p     ON oi.product_id = p.product_id
        WHERE o.status = 'Completed'
        GROUP BY o.order_id;

        CREATE VIEW IF NOT EXISTS v_customer_summary AS
        SELECT
            c.customer_id,
            c.name,
            c.segment,
            r.region_name,
            s.name AS rep_name,
            COUNT(DISTINCT o.order_id)                                  AS total_orders,
            SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))   AS total_revenue,
            AVG(oi.quantity * oi.unit_price * (1 - oi.discount_pct))   AS avg_order_value,
            MAX(o.order_date)                                           AS last_order_date
        FROM customers c
        LEFT JOIN orders o      ON c.customer_id = o.customer_id AND o.status='Completed'
        LEFT JOIN order_items oi ON o.order_id   = oi.order_id
        LEFT JOIN regions r     ON c.region_id   = r.region_id
        LEFT JOIN sales_reps s  ON c.rep_id      = s.rep_id
        GROUP BY c.customer_id;
    """)

    conn.commit()
    conn.close()

    print(f"Database built: {db_path}")
    print(f"  Customers : {n_customers}")
    print(f"  Orders    : {n_orders}")
    print(f"  Order items: {item_id - 1}")


if __name__ == "__main__":
    build()
