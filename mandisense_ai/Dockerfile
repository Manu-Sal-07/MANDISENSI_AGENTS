FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    redis>=5.0.0 \
    && pip install --no-cache-dir -e .

# Application code
COPY . .

# Create required directories
RUN mkdir -p logs data/ensemble models/meta_ensemble

EXPOSE 8000

# Default: run the API server
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
