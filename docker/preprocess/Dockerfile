FROM python:3.13-slim

WORKDIR /app

COPY docker/preprocess/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY docker/preprocess/entrypoint.sh .

ENV PYTHONPATH=/app/src

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
