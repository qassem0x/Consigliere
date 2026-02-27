FROM python:3.12-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Ensure required runtime directories exist
RUN mkdir -p /code/data /code/static/plots

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /code
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]