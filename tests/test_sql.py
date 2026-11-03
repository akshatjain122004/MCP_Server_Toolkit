import pytest
from mcp.server.mcpserver.exceptions import ToolError

from servers.sql_explorer.server import (
    describe_table,
    list_databases,
    list_tables,
    run_readonly_query,
    sales_report,
    schema_hr,
    schema_inventory,
    schema_shop,
)


def test_list_databases_returns_all_three():
    assert set(list_databases()) == {"shop", "inventory", "hr"}


def test_list_tables_rejects_unknown_database():
    with pytest.raises(ToolError):
        list_tables(database="nope")


def test_list_tables_returns_the_three_tables():
    assert set(list_tables()) == {"customers", "products", "orders"}


def test_list_tables_defaults_to_shop_but_accepts_other_databases():
    assert set(list_tables(database="inventory")) == {
        "warehouses", "suppliers", "categories", "items", "stock_levels", "shipments",
    }
    assert set(list_tables(database="hr")) == {
        "departments", "employees", "projects", "attendance", "leave_requests", "payroll",
    }


def test_describe_table_includes_city_column():
    columns = describe_table("customers")
    assert {"name": "city", "type": "TEXT"} in columns


def test_describe_table_rejects_unknown_table_name():
    with pytest.raises(ToolError):
        describe_table("users; --")


def test_valid_select_returns_rows():
    rows = run_readonly_query("SELECT * FROM products")
    assert len(rows) > 0


def test_with_query_works():
    rows = run_readonly_query(
        "WITH cheap AS (SELECT * FROM products WHERE price < 50) SELECT * FROM cheap"
    )
    assert all(row["price"] < 50 for row in rows)


def test_row_cap_limits_to_max_rows():
    rows = run_readonly_query("SELECT * FROM orders", limit=5000)
    assert len(rows) <= 100


def test_keyword_named_column_still_works():
    rows = run_readonly_query("SELECT created_at FROM customers")
    assert len(rows) > 0
    assert "created_at" in rows[0]


def test_run_readonly_query_against_other_databases():
    rows = run_readonly_query("SELECT * FROM warehouses", database="inventory")
    assert len(rows) > 0

    rows = run_readonly_query("SELECT * FROM employees", database="hr")
    assert len(rows) > 0


def test_run_readonly_query_rejects_unknown_database():
    with pytest.raises(ToolError):
        run_readonly_query("SELECT 1", database="nope")


@pytest.mark.parametrize(
    "attack_sql",
    [
        "DROP TABLE customers",
        "DELETE FROM orders",
        "SELECT 1; DROP TABLE customers",
        "select * from customers; update orders set total=0",
        "PRAGMA table_info(customers)",
        "ATTACH DATABASE 'x.db' AS x",
    ],
)
def test_attack_queries_are_rejected(attack_sql):
    with pytest.raises(ToolError):
        run_readonly_query(attack_sql)


def test_schema_shop_resource_lists_every_table_with_columns():
    result = schema_shop()
    assert "customers(" in result
    assert "products(" in result
    assert "orders(" in result
    assert "city TEXT" in result


def test_schema_inventory_resource_lists_every_table():
    result = schema_inventory()
    for table in ("warehouses", "suppliers", "categories", "items", "stock_levels", "shipments"):
        assert f"{table}(" in result


def test_schema_hr_resource_lists_every_table():
    result = schema_hr()
    for table in ("departments", "employees", "projects", "attendance", "leave_requests", "payroll"):
        assert f"{table}(" in result


def test_sales_report_prompt_mentions_the_month_and_asks():
    result = sales_report("2026-03")
    assert "2026-03" in result
    assert "revenue" in result.lower()
    assert "top 5 products" in result.lower()
    assert "top 5 customers" in result.lower()
