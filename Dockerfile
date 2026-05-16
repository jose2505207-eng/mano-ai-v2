# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# Stage 2: Production backend
FROM python:3.12-slim

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxext6 libxi6 libxtst6 \
    fonts-liberation fonts-noto-color-emoji curl \
    && rm -rf /var/lib/apt/lists/*

# Set up Python app
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install Playwright chromium (headless)
RUN playwright install chromium

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build output
COPY --from=frontend-build /build/frontend/out ./frontend/out

# Copy data directory
COPY data/ ./data/

# Environment
ENV BROWSER_HEADLESS=true
ENV PORT=8000
ENV PYTHONPATH=/app/backend

EXPOSE 8000 8080

# Health check (use same PORT as the app)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Run from backend directory — use PORT env var set by Zeabur
WORKDIR /app/backend
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
