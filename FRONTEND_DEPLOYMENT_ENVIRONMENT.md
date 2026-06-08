# Frontend Deployment Environment Contract

This contract specifies the configuration and execution parameters for the MandiSense AI Next.js frontend application deployed to platforms like Vercel or hosted inside Docker containers.

---

## 1. Environment Variables

### Required Variables
* **`NEXT_PUBLIC_API_URL`**
  - **Type**: URL (String)
  - **Description**: The absolute base HTTP/HTTPS URL of the running FastAPI backend.
  - **Default**: `http://localhost:8000` (Localhost development)
  - **Production Example**: `https://mandisense-api.onrender.com`

### Dynamic WebSocket Derivation
WebSockets connect to the same host specified in `NEXT_PUBLIC_API_URL`. The application dynamically translates protocol schemas:
- `http://...` ➔ `ws://...`
- `https://...` ➔ `wss://...`

No independent WebSocket variables are required during deployment.

---

## 2. Compilation & Build Instructions

### Prerequisites
- Node.js: `^18.0.0` or `^20.0.0`
- Package manager: `npm`

### Local Development Instructions
1. Navigate to the `frontend/` subdirectory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Access the interface at `http://localhost:3000`.

### Production Build & Deployment (Vercel / Netlify / Static)
1. **Set Environment Variables**: Configure `NEXT_PUBLIC_API_URL` in the hosting dashboard (e.g., Vercel environment settings).
2. **Build Commands**:
   - Install command: `npm install`
   - Build command: `npm run build`
   - Output directory: `.next` or default compilation output
3. **Execution**: Next.js automatically packages static optimization components and handles routing during startup.
