# The official datasetteproject/datasette image is amd64-only; ampere is arm64.
FROM python:3.12-slim

RUN pip install --no-cache-dir datasette==0.65.5

COPY metadata.yml /config/metadata.yml

EXPOSE 8001
CMD ["datasette", "serve", "/data/grades.db", \
     "--host", "0.0.0.0", "--port", "8001", \
     "--metadata", "/config/metadata.yml", \
     "--setting", "sql_time_limit_ms", "5000"]
