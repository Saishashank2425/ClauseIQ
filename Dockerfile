# Build the Vite frontend first; the production UI is served by FastAPI.
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
WORKDIR /app

# Install the Tesseract executable used by the optional scanned-PDF OCR path.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini .
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 10000
CMD ["sh", "-c", "if [ -n \"${DATABASE_URL:-}\" ]; then echo \"Applying ClauseIQ database migrations\"; alembic upgrade head; fi; exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
