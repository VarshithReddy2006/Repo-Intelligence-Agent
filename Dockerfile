# Stage 1: Build the Astro Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.11-slim AS backend-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc g++ libc-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Production Image
FROM python:3.11-slim AS production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy python packages
COPY --from=backend-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend source code
COPY backend/ ./backend
COPY core/ ./core
COPY services/ ./services
COPY models/ ./models
COPY storage/ ./storage
COPY agents/ ./agents
COPY memory/ ./memory

# Copy built frontend code to be served by the backend static file mount
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8001
ENV APP_ENV=production
ENV LOG_FORMAT=json

# Startup command running the FastAPI backend via uvicorn
CMD ["python", "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8001"]
