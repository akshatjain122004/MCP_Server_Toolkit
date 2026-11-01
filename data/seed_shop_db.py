"""Generate data/shop.db with realistic fake data for demos.

Usage:
    uv run python data/seed_shop_db.py
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

DB_PATH = Path(__file__).parent / "shop.db"
N_CUSTOMERS = 60
N_PRODUCTS = 50
N_ORDERS = 90

CATEGORIES = ["Electronics", "Home & Kitchen", "Office", "Sports", "Toys", "Books"]
STATUSES = ["pending", "shipped", "delivered", "cancelled"]

fake = Faker()


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)

    seen_emails = set()
    customers = []
    while len(customers) < N_CUSTOMERS:
        email = fake.unique.email()
        if email in seen_emails:
            continue
        seen_emails.add(email)
        customers.append((fake.name(), email, fake.phone_number(), fake.city()))
    cur.executemany(
        "INSERT INTO customers (name, email, phone, city) VALUES (?, ?, ?, ?)",
        customers,
    )

    products = [
        (
            fake.catch_phrase(),
            random.choice(CATEGORIES),
            round(random.uniform(5, 500), 2),
            random.randint(0, 300),
        )
        for _ in range(N_PRODUCTS)
    ]
    cur.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        products,
    )

    today = date.today()
    orders = [
        (
            random.randint(1, N_CUSTOMERS),
            random.randint(1, N_PRODUCTS),
            random.randint(1, 5),
            (today - timedelta(days=random.randint(0, 365))).isoformat(),
            random.choice(STATUSES),
        )
        for _ in range(N_ORDERS)
    ]
    cur.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, order_date, status) VALUES (?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn)
    finally:
        conn.close()
    print(f"Seeded {DB_PATH} with {N_CUSTOMERS} customers, {N_PRODUCTS} products, {N_ORDERS} orders")


if __name__ == "__main__":
    main()
