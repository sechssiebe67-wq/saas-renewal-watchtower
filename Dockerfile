# Focus Flow — static container image.
#
# Serves the app/ directory with nginx. The image is based on the unprivileged
# nginx variant so the container does not run as root. The listen port is
# configurable through the PORT environment variable (default 8080).
FROM nginxinc/nginx-unprivileged:1.27-alpine

ENV PORT=8080

COPY app/ /usr/share/nginx/html/
COPY docker/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O - "http://127.0.0.1:${PORT}/healthz" || exit 1

LABEL org.opencontainers.image.title="Focus Flow" \
      org.opencontainers.image.description="Distraction-free, offline-capable focus timer." \
      org.opencontainers.image.licenses="MIT"
