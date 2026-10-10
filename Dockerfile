FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=tesseract
ENV TESSERACT_LANG=eng
ENV DATABASE_PATH=/data/users.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data uploads

CMD gunicorn app:app --workers 1 --bind 0.0.0.0:${PORT:-8000}
