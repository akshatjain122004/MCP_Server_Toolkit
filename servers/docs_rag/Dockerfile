FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .

RUN uv sync --frozen
RUN uv run servers/docs_rag/build_index.py

EXPOSE 8002
CMD ["uv", "run", "servers/docs_rag/server.py", "--http"]
