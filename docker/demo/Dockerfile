FROM python:3.13-slim

WORKDIR /app

COPY docker/demo/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY references/ ./references/
COPY .streamlit/ ./.streamlit/

ENV PYTHONPATH=/app/src
ENV STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

CMD ["streamlit", "run", "src/weather_mlops/demo/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
