# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="SaaS Renewal Watchtower" \
      org.opencontainers.image.description="Extracts SaaS renewal deadlines from invoices and recommends an action."

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WATCHTOWER_HOST=0.0.0.0 \
    WATCHTOWER_PORT=8080 \
    WATCHTOWER_DB=/data/watchtower.db

WORKDIR /app

COPY watchtower ./watchtower

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin watchtower \
    && mkdir -p /data \
    && chown -R watchtower:watchtower /data /app

USER 10001

EXPOSE 8080
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).status == 200 else 1)"

ENTRYPOINT ["python", "-m", "watchtower"]
CMD ["serve"]
