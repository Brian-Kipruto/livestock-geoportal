FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN echo "Acquire::ForceIPv4 \"true\";" > /etc/apt/apt.conf.d/99force-ipv4 \
 && apt-get update \
 && apt-get install -y --no-install-recommends gdal-bin libgdal32 libgeos-c1v5 libproj25 binutils curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ARG INSTALL_DEV=0
COPY requirements/ requirements/
RUN pip install -r requirements/processing.txt \
 && if [ "$INSTALL_DEV" = "1" ]; then pip install -r requirements/dev.txt; fi

COPY . .
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["web"]
