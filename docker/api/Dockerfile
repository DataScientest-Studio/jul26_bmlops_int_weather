FROM python:3.13-slim

WORKDIR /app

COPY docker/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY references/ ./references/

ARG GIT_COMMIT=
ENV GIT_COMMIT=$GIT_COMMIT
ENV PYTHONPATH=/app/src

EXPOSE 8000

# 0.0.0.0 so the port also works from outside the container
CMD ["uvicorn", "weather_mlops.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
