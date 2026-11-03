"""Generate data/hr.db with realistic fake data for demos.

Usage:
    uv run scripts/seed_hr.py
"""

import random
from datetime import date, timedelta
from pathlib import Path
import sqlite3

from faker import Faker

DB_PATH = Path(__file__).parents[1] / "data" / "hr.db"
N_DEPARTMENTS = 500
N_EMPLOYEES = 500
N_PROJECTS = 500
N_ATTENDANCE = 500
N_LEAVE_REQUESTS = 500
N_PAYROLL = 500

JOB_TITLES = [
    "Software Engineer", "Product Manager", "Data Analyst", "Recruiter",
    "Accountant", "Sales Executive", "Operations Lead", "Designer",
    "QA Engineer", "Support Specialist",
]
ATTENDANCE_STATUSES = ["present", "absent", "half_day", "work_from_home"]
LEAVE_TYPES = ["sick", "vacation", "unpaid", "parental"]
LEAVE_STATUSES = ["pending", "approved", "rejected"]

Faker.seed(13)
random.seed(13)
fake = Faker()


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS payroll;
        DROP TABLE IF EXISTS leave_requests;
        DROP TABLE IF EXISTS attendance;
        DROP TABLE IF EXISTS projects;
        DROP TABLE IF EXISTS employees;
        DROP TABLE IF EXISTS departments;

        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL
        );

        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            job_title TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            salary REAL NOT NULL
        );

        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget REAL NOT NULL
        );

        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            date TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE leave_requests (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE payroll (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            month TEXT NOT NULL,
            base_salary REAL NOT NULL,
            bonus REAL NOT NULL,
            deductions REAL NOT NULL,
            net_pay REAL NOT NULL
        );
    """)

    today = date.today()

    departments = [
        (f"{fake.word().capitalize()} Department", fake.city())
        for _ in range(N_DEPARTMENTS)
    ]
    cur.executemany(
        "INSERT INTO departments (name, location) VALUES (?, ?)",
        departments,
    )

    seen_emails = set()
    employees = []
    while len(employees) < N_EMPLOYEES:
        email = fake.unique.email()
        if email in seen_emails:
            continue
        seen_emails.add(email)
        department_id = random.randint(1, N_DEPARTMENTS)
        job_title = random.choice(JOB_TITLES)
        hire_date = today - timedelta(days=random.randint(30, 3650))
        salary = round(random.uniform(30000, 180000), 2)
        employees.append((fake.name(), email, department_id, job_title, hire_date.isoformat(), salary))
    cur.executemany(
        "INSERT INTO employees (name, email, department_id, job_title, hire_date, salary) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        employees,
    )

    projects = []
    for _ in range(N_PROJECTS):
        department_id = random.randint(1, N_DEPARTMENTS)
        start_date = today - timedelta(days=random.randint(30, 730))
        end_date = start_date + timedelta(days=random.randint(30, 365))
        budget = round(random.uniform(5000, 500000), 2)
        projects.append((fake.catch_phrase(), department_id, start_date.isoformat(), end_date.isoformat(), budget))
    cur.executemany(
        "INSERT INTO projects (name, department_id, start_date, end_date, budget) VALUES (?, ?, ?, ?, ?)",
        projects,
    )

    attendance = []
    for _ in range(N_ATTENDANCE):
        employee_id = random.randint(1, N_EMPLOYEES)
        att_date = today - timedelta(days=random.randint(0, 180))
        status = random.choice(ATTENDANCE_STATUSES)
        attendance.append((employee_id, att_date.isoformat(), status))
    cur.executemany(
        "INSERT INTO attendance (employee_id, date, status) VALUES (?, ?, ?)",
        attendance,
    )

    leave_requests = []
    for _ in range(N_LEAVE_REQUESTS):
        employee_id = random.randint(1, N_EMPLOYEES)
        leave_type = random.choice(LEAVE_TYPES)
        start_date = today - timedelta(days=random.randint(0, 365))
        end_date = start_date + timedelta(days=random.randint(1, 14))
        status = random.choice(LEAVE_STATUSES)
        leave_requests.append((employee_id, leave_type, start_date.isoformat(), end_date.isoformat(), status))
    cur.executemany(
        "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, status) "
        "VALUES (?, ?, ?, ?, ?)",
        leave_requests,
    )

    payroll = []
    for _ in range(N_PAYROLL):
        employee_id = random.randint(1, N_EMPLOYEES)
        month = (today - timedelta(days=random.randint(0, 365))).strftime("%Y-%m")
        base_salary = round(random.uniform(30000, 180000) / 12, 2)
        bonus = round(random.uniform(0, 5000), 2)
        deductions = round(random.uniform(0, 3000), 2)
        net_pay = round(base_salary + bonus - deductions, 2)
        payroll.append((employee_id, month, base_salary, bonus, deductions, net_pay))
    cur.executemany(
        "INSERT INTO payroll (employee_id, month, base_salary, bonus, deductions, net_pay) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        payroll,
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
