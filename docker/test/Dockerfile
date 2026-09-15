FROM python:3.13-slim

WORKDIR /app

COPY docker/api/requirements.txt docker/api/requirements.txt
COPY docker/test/requirements.txt docker/test/requirements.txt
RUN pip install --no-cache-dir -r docker/api/requirements.txt -r docker/test/requirements.txt

ENV PYTHONPATH=/app/src

CMD ["pytest", "-q"]
