# Django + Gunicorn (production-style image)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Pillow / psycopg wheels usually pull binary deps; minimal libs for edge cases
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x deploy/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
