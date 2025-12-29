# Dockerfile for Railway deployment
# This is an alternative if Nixpacks continues to have issues

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads temp_calendars

# Expose port (Railway will map this to PORT env var)
EXPOSE 5000

# Run gunicorn (PORT is set by Railway as environment variable)
# Use shell form CMD to allow variable expansion
CMD sh -c "python -m gunicorn src.app:app --bind 0.0.0.0:${PORT:-5000}"

