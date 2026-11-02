"""Generate data/shop.db with realistic fake data for demos.

Usage:
    uv run scripts/seed_db.py
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

DB_PATH = Path(__file__).parents[1] / "data" / "shop.db"
N_CUSTOMERS = 60
N_PRODUCTS = 20
N_ORDERS = 300

CITIES = ["Jaipur", "Udaipur", "Delhi", "Mumbai", "Bengaluru", "Pune", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad"]
CATEGORIES = ["Electronics", "Home & Kitchen", "Office", "Sports", "Toys", "Books"]

Faker.seed(42)
random.seed(42)
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
            city TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            order_date TEXT NOT NULL
        );
    """)

    today = date.today()

    seen_emails = set()
    customers = []
    while len(customers) < N_CUSTOMERS:
        email = fake.unique.email()
        if email in seen_emails:
            continue
        seen_emails.add(email)
        created_at = today - timedelta(days=random.randint(30, 730))
        customers.append((fake.name(), email, random.choice(CITIES), created_at.isoformat()))
    cur.executemany(
        "INSERT INTO customers (name, email, city, created_at) VALUES (?, ?, ?, ?)",
        customers,
    )

    products = [
        (fake.catch_phrase(), random.choice(CATEGORIES), round(random.uniform(5, 500), 2))
        for _ in range(N_PRODUCTS)
    ]
    cur.executemany(
        "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
        products,
    )

    product_prices = [p[2] for p in products]
    orders = []
    for _ in range(N_ORDERS):
        customer_id = random.randint(1, N_CUSTOMERS)
        product_id = random.randint(1, N_PRODUCTS)
        quantity = random.randint(1, 5)
        total = round(product_prices[product_id - 1] * quantity, 2)
        order_date = today - timedelta(days=random.randint(0, 182))
        orders.append((customer_id, product_id, quantity, total, order_date.isoformat()))
    cur.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, total, order_date) VALUES (?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn)
    finally:
        conn.close()
    print(f"Seeded {DB_PATH} with {N_CUSTOMERS} customers, {N_PRODUCTS} products, {N_ORDERS} orders")


if __name__ == "__main__":
    main()
