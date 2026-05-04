# Base image: Use a slim version for smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system-level dependencies
# - libgomp1: Required by LightGBM/XGBoost for multi-threading
# - curl: Required for Docker Compose healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize Caching: Copy only dependency files first
# This prevents re-installing all packages when only source code changes
COPY pyproject.toml README.md /app/

# Install dependencies using pip
# --no-cache-dir: Prevents bloating the image with installation artifacts
RUN pip install --no-cache-dir .

# Copy the rest of the application code
# .dockerignore handles excluding unnecessary files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP__ENVIRONMENT=production

# Expose port 8000 for FastAPI
EXPOSE 8000

# Production runtime command
# Uses 2 workers for basic concurrency within the container
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]


