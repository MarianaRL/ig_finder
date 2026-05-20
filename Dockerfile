# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install runtime deps first for better layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the rest of the project
COPY . .

EXPOSE 8000

# Drop privileges
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
    sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
