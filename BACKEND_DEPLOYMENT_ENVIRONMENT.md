# Backend Deployment Environment Contract

This contract specifies the configuration and execution parameters for the MandiSense AI FastAPI backend application deployed to public cloud services (such as Render) or hosted in Docker containers.

---

## 1. Environment Variables Configuration

### Required Variables
* **`DATABASE_URL`**
  - **Type**: Connection URI (String)
  - **Description**: The PostgreSQL connection string. Must target a database using v15 or higher.
  - **Production Requirement**: If `APP__ENVIRONMENT` is set to `production` and this is missing, the application will fail-fast with a `ValueError`.
  - **Example**: `postgresql://postgres:password@render-pg-host:5432/mandisense_production`

* **`REDIS_URL`** (or **`REDIS_HOST`**)
  - **Type**: Connection URL / Hostname
  - **Description**: Target host parameters for the Redis caching network.
  - **Production Requirement**: At least one of these must be supplied in a `production` environment, or startup fails.
  - **Example**: `redis://red-hash:6379/0`

* **`NEWS_API_KEY`**
  - **Type**: String (Secret Token)
  - **Description**: External factors API key required to extract real-time news for agent calculations.
  - **Production Requirement**: Required to run external factors model forecasts.

### Optional Variables
* **`APP__ENVIRONMENT`**
  - **Type**: Choice (`development`, `production`, `test`)
  - **Description**: Dictates runtime safety checks. Set to `production` in hosting environments.
  - **Default**: `development`

* **`PORT`**
  - **Type**: Integer
  - **Description**: Port the FastAPI server listens on.
  - **Default**: `8000` (Render sets this dynamically at runtime)

* **`LOGGING__LEVEL`**
  - **Type**: Choice (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
  - **Description**: Logger verbosity control.
  - **Default**: `INFO`

* **`CORS_ALLOWED_ORIGINS`**
  - **Type**: Comma-separated list of origins
  - **Description**: Configures cross-origin restrictions on the API.
  - **Example**: `https://mandisense.vercel.app,http://localhost:3000`

---

## 2. Deployment Instructions

### Local Execution (No Docker)
1. Set up dependencies:
   ```bash
   pip install -r pyproject.toml
   ```
2. Set environment variables locally (or write a `.env` file).
3. Run uvicorn:
   ```bash
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

### Docker Deployment
1. Build the image using the root `Dockerfile`:
   ```bash
   docker build -t mandisense-backend:latest .
   ```
2. Start container with environment mapping:
   ```bash
   docker run -p 8000:8000 --env-file .env mandisense-backend:latest
   ```

### Render Deployment Web Service
1. **Service Type**: Web Service
2. **Environment**: Python
3. **Build Command**: `pip install -e .` (or using Docker environment option targeting the root `Dockerfile`)
4. **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. **Environment Configuration**: Set all required variables in the Render Dashboard environment section.
