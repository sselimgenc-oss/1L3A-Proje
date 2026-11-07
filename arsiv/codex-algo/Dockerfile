FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CODEX_ALGO_HOSTED=1 \
    CODEX_ALGO_RUNTIME_DIR=/app/runtime \
    PORT=8501

WORKDIR /app
COPY pyproject.toml README.md app.py ./
COPY config ./config
COPY src ./src
RUN pip install --no-cache-dir .
RUN mkdir -p /app/runtime/state /app/runtime/data/cache

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8501')+'/_stcore/health', timeout=3)"

CMD ["codex-algo-hosted"]
