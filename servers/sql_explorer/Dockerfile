FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .

RUN uv sync --frozen
RUN uv run scripts/seed_db.py && uv run scripts/seed_inventory.py && uv run scripts/seed_hr.py

EXPOSE 8000
CMD ["uv", "run", "servers/sql_explorer/server.py", "--http"]
