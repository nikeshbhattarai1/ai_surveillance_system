# Stage 1: Python deps
FROM python:3.11-slim AS python-deps

WORKDIR /app

# System deps for opencv + psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Stage 2: Frontend build
FROM node:20-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent

COPY frontend/ .
RUN npm run build
# Output: /frontend/dist

# Stage 3: Final image (FastAPI app)
FROM python:3.11-slim AS final

WORKDIR /app

# System deps needed at runtime (opencv + psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin
# COPY --from=python-deps /app/src ./src

# Frontend build output
COPY --from=frontend-build /frontend/dist ./static/

# Storage dirs
RUN mkdir -p storage/uploads storage/frames logs models

# Non-root user for security — never run containers as root
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "ai_surveillance_system.main:app", \
    "--host", "0.0.0.0", "--port", "8000", \
    "--workers", "1"]

# Stage 4: Nginx serving the built frontend
FROM nginx:alpine AS nginx-final

COPY --from=frontend-build /frontend/dist /usr/share/nginx/html