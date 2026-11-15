FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system certificates and curl for network operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a cached layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create non-root user and prepare writable persistence directories
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data /app/reports \
    && chown -R appuser:appuser /app

USER appuser

# Persistence mount points for SQLite DB and generated reports
VOLUME ["/app/data", "/app/reports"]

CMD ["python", "main.py"]

