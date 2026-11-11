FROM ghcr.io/developmentseed/titiler:0.22.4
COPY app.py /app/geoportal_titiler.py
WORKDIR /app
ENV PYTHONPATH=/app
CMD ["uvicorn", "geoportal_titiler:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--root-path", "/tiles/r"]
