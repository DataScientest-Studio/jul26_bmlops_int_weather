FROM python:3.13-slim

WORKDIR /app

COPY docker/ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY references/ ./references/
COPY docker/ingestion/entrypoint.sh .

# the project root inside the container is /app
ENV PYTHONPATH=/app/src

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
