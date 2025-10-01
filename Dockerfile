FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

# Установка всех необходимых зависимостей для PyMuPDF
RUN apk add --no-cache \
    gcc g++ make \
    python3-dev \
    musl-dev \
    linux-headers \
    clang-dev \
    llvm-dev \
    mupdf-dev \
    freetype-dev \
    harfbuzz-dev \
    openjpeg-dev \
    jbig2dec-dev \
    libjpeg-turbo-dev \
    tesseract-ocr \
    tesseract-ocr-data-rus \
    tesseract-ocr-data-eng \
    netcat-openbsd \
    rust \
    cargo

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
RUN rm -rf ./*