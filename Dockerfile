# One image: the dashboard is built to static files and served by the API.

FROM node:22-alpine AS dashboard
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/fenrix ./fenrix
COPY --from=dashboard /web/out ./web
RUN useradd --create-home fenrix && mkdir -p /data && chown fenrix /data
USER fenrix

ENV FENRIX_DATABASE_URL=sqlite:////data/fenrix.db \
    FENRIX_STATIC_DIR=/app/web
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "fenrix.main:app", "--host", "0.0.0.0", "--port", "8000"]
