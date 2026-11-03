FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .

RUN uv sync --frozen

EXPOSE 8001
CMD ["uv", "run", "servers/github_analyzer/server.py", "--http"]
