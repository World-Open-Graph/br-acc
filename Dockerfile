# Multi-stage Dockerfile (root). Prefer per-service Dockerfiles: api/Dockerfile, frontend/Dockerfile, etl/Dockerfile.
FROM python:3.12-slim AS api

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY api/src ./src
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "bracc.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM node:22-slim AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine AS frontend
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]


FROM python:3.12-slim AS etl

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace/etl

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY etl/pyproject.toml etl/uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY etl/src ./src
RUN uv sync --no-dev

WORKDIR /workspace
CMD ["bash"]
