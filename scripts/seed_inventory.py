"""Generate data/inventory.db with realistic fake data for demos.

Usage:
    uv run scripts/seed_inventory.py
"""

import random
from datetime import date, timedelta
from pathlib import Path
import sqlite3

from faker import Faker

DB_PATH = Path(__file__).parents[1] / "data" / "inventory.db"
N_WAREHOUSES = 500
N_SUPPLIERS = 500
N_CATEGORIES = 500
N_ITEMS = 500
N_STOCK_LEVELS = 500
N_SHIPMENTS = 500

SHIPMENT_STATUSES = ["pending", "in_transit", "delivered", "cancelled"]

Faker.seed(7)
random.seed(7)
fake = Faker()


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS shipments;
        DROP TABLE IF EXISTS stock_levels;
        DROP TABLE IF EXISTS items;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS suppliers;
        DROP TABLE IF EXISTS warehouses;

        CREATE TABLE warehouses (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            capacity INTEGER NOT NULL
        );

        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            contact_email TEXT NOT NULL UNIQUE,
            rating INTEGER NOT NULL
        );

        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
            unit_cost REAL NOT NULL,
            reorder_level INTEGER NOT NULL
        );

        CREATE TABLE stock_levels (
            id INTEGER PRIMARY KEY,
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            item_id INTEGER NOT NULL REFERENCES items(id),
            quantity INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        );

        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY,
            supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            item_id INTEGER NOT NULL REFERENCES items(id),
            quantity INTEGER NOT NULL,
            shipped_date TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)

    today = date.today()

    warehouses = [
        (f"{fake.city()} Distribution Center", fake.city(), fake.country(), random.randint(1000, 50000))
        for _ in range(N_WAREHOUSES)
    ]
    cur.executemany(
        "INSERT INTO warehouses (name, city, country, capacity) VALUES (?, ?, ?, ?)",
        warehouses,
    )

    seen_emails = set()
    suppliers = []
    while len(suppliers) < N_SUPPLIERS:
        email = fake.unique.company_email()
        if email in seen_emails:
            continue
        seen_emails.add(email)
        suppliers.append((fake.company(), fake.country(), email, random.randint(1, 5)))
    cur.executemany(
        "INSERT INTO suppliers (name, country, contact_email, rating) VALUES (?, ?, ?, ?)",
        suppliers,
    )

    categories = [
        (fake.word().capitalize() + " " + fake.word().capitalize(), fake.sentence())
        for _ in range(N_CATEGORIES)
    ]
    cur.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        categories,
    )

    items = [
        (
            fake.catch_phrase(),
            random.randint(1, N_CATEGORIES),
            random.randint(1, N_SUPPLIERS),
            round(random.uniform(2, 1000), 2),
            random.randint(5, 200),
        )
        for _ in range(N_ITEMS)
    ]
    cur.executemany(
        "INSERT INTO items (name, category_id, supplier_id, unit_cost, reorder_level) VALUES (?, ?, ?, ?, ?)",
        items,
    )

    stock_levels = []
    for _ in range(N_STOCK_LEVELS):
        warehouse_id = random.randint(1, N_WAREHOUSES)
        item_id = random.randint(1, N_ITEMS)
        quantity = random.randint(0, 5000)
        last_updated = today - timedelta(days=random.randint(0, 60))
        stock_levels.append((warehouse_id, item_id, quantity, last_updated.isoformat()))
    cur.executemany(
        "INSERT INTO stock_levels (warehouse_id, item_id, quantity, last_updated) VALUES (?, ?, ?, ?)",
        stock_levels,
    )

    shipments = []
    for _ in range(N_SHIPMENTS):
        supplier_id = random.randint(1, N_SUPPLIERS)
        warehouse_id = random.randint(1, N_WAREHOUSES)
        item_id = random.randint(1, N_ITEMS)
        quantity = random.randint(10, 2000)
        shipped_date = today - timedelta(days=random.randint(0, 365))
        status = random.choice(SHIPMENT_STATUSES)
        shipments.append((supplier_id, warehouse_id, item_id, quantity, shipped_date.isoformat(), status))
    cur.executemany(
        "INSERT INTO shipments (supplier_id, warehouse_id, item_id, quantity, shipped_date, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        shipments,
    )

    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn)
    finally:
        conn.close()
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    main()
