FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fenrix ./fenrix
RUN useradd --create-home fenrix && mkdir -p /data && chown fenrix /data
USER fenrix

ENV FENRIX_DATABASE_URL=sqlite:////data/fenrix.db
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "fenrix.main:app", "--host", "0.0.0.0", "--port", "8000"]
