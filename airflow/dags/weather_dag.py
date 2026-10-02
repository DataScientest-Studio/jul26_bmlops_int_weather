import os
from datetime import datetime, timedelta

import pendulum
from airflow.operators.docker_operator import DockerOperator
from docker.types import Mount

from airflow import DAG

path = os.environ.get("HOST_PROJECT_PATH")
local_tz = pendulum.timezone("Europe/Berlin")

with DAG(
    dag_id="weather_pipeline",
    tags=["docker", "weather_ingestion"],
    default_args={
        "owner": "airflow",
        "start_date": datetime(2026, 9, 1, tzinfo=local_tz),
        "retries": 3,
        "retry_delay": timedelta(minutes=1),
    },
    schedule_interval="0 18 * * *",
    catchup=False,
) as dag:
    ingestion = DockerOperator(
        task_id="ingestion",
        image="weather-ingestion:latest",
        mounts=[Mount(source=path + "/data", target="/app/data", type="bind")],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        mount_tmp_dir=False,
    )
    preprocessing = DockerOperator(
        task_id="preprocess",
        image="weather-preprocess:latest",
        mounts=[Mount(source=path + "/data", target="/app/data", type="bind")],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        mount_tmp_dir=False,
    )
    reconcile_outcomes = DockerOperator(
        task_id="reconcile_outcomes",
        image="weather-api:latest",
        mounts=[
            Mount(source=path + "/data", target="/app/data", type="bind", read_only=True),
        ],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        command="python3 -m weather_mlops.data.outcomes",
        environment={
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
        },
        mount_tmp_dir=False,
    )
    evidently_monitor = DockerOperator(
        task_id="evidently_monitor",
        image="weather-api:latest",
        mounts=[
            Mount(source=path + "/data", target="/app/data", type="bind", read_only=True),
            Mount(source=path + "/models", target="/app/models", type="bind"),
            Mount(source=path + "/reports", target="/app/reports", type="bind"),
        ],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        command="python3 -m weather_mlops.monitoring.drift",
        environment={
            "MLFLOW_TRACKING_URI": "http://mlflow:8080",
            "PUSHGATEWAY_URL": "http://pushgateway:9091",
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
        },
        mount_tmp_dir=False,
    )
    ingestion >> preprocessing >> reconcile_outcomes >> evidently_monitor

with DAG(
    dag_id="weather_retrain",
    tags=["docker", "weather_retraining"],
    default_args={
        "owner": "airflow",
        "start_date": datetime(2026, 9, 1, tzinfo=local_tz),
        "retries": 3,
        "retry_delay": timedelta(minutes=1),
    },
    schedule_interval=None,
    catchup=False,
) as retrain_dag:
    training = DockerOperator(
        task_id="train",
        image="weather-api:latest",
        mounts=[
            Mount(source=path + "/data", target="/app/data", type="bind", read_only=True),
            Mount(source=path + "/models", target="/app/models", type="bind"),
            Mount(source=path + "/reports", target="/app/reports", type="bind"),
        ],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        command="python3 scripts/train_via_api.py",
        environment={
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
        },
        mount_tmp_dir=False,
    )
    evaluation = DockerOperator(
        task_id="evaluation",
        image="weather-api:latest",
        mounts=[
            Mount(source=path + "/data", target="/app/data", type="bind", read_only=True),
            Mount(source=path + "/models", target="/app/models", type="bind"),
            Mount(source=path + "/reports", target="/app/reports", type="bind"),
        ],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        command=(
            "python3 -m weather_mlops.models.evaluation "
            "--x-data data/processed/X_validation.csv "
            "--y-data data/processed/y_validation.csv "
            "--metrics-output reports/metrics/validation.json "
            "--split-name validation"
        ),
        environment={"MLFLOW_TRACKING_URI": "http://mlflow:8080"},
        mount_tmp_dir=False,
    )
    compare = DockerOperator(
        task_id="compare",
        image="weather-api:latest",
        mounts=[
            Mount(source=path + "/data", target="/app/data", type="bind", read_only=True),
            Mount(source=path + "/models", target="/app/models", type="bind"),
            Mount(source=path + "/reports", target="/app/reports", type="bind"),
        ],
        docker_url="tcp://docker-socket-proxy:2375",
        network_mode="jul26_bmlops_int_weather_weather_network",
        auto_remove=True,
        command="python3 -m weather_mlops.models.comparison",
        environment={"MLFLOW_TRACKING_URI": "http://mlflow:8080"},
        mount_tmp_dir=False,
    )
    training >> evaluation >> compare
