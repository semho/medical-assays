FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libpq5 \
    netcat-openbsd \
    gcc g++ python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY .python-version pyproject.toml uv.lock ./

# Устанавливаем пакеты БЕЗ создания .venv
RUN uv pip install --system -r pyproject.toml

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000