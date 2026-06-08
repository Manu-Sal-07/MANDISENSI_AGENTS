# Base image: Use a slim version for smaller footprint
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system-level dependencies
# - libgomp1: Required by LightGBM/XGBoost for multi-threading
# - curl: Required for Docker Compose healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY mandisense_ai /app/mandisense_ai
COPY api /app/api
COPY run_agents.py /app/

RUN pip install --no-cache-dir .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP__ENVIRONMENT=production

# Expose port 8000 for FastAPI
EXPOSE 8000

# Production runtime command.
# Keep a single worker because the cognition stream uses in-memory WebSocket state.
CMD ["sh", "-c", "python scripts/init_db.py && python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]



