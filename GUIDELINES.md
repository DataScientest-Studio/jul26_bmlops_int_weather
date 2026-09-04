# Project Guidelines

## Overview

This document summarizes the guidelines provided by the mentor for the **MLOps project (Weather)**. Evaluation focuses on MLOps proficiency, not model performance — spend 1–2 days max on a working model, then focus on the architecture.

- **Mentor contact**: Nicolas Fradin (Slack channel)
- **Project repo**: https://github.com/DataScientest-Studio/jul26_bmlops_int_weather
- **Communication**: Slack is the primary channel; meetings are recorded and shared.

---

## Project Objectives and Key Metrics

### What we are building

A system that predicts whether it will rain tomorrow at a given weather station in Australia,
and serves that prediction through an API. The point of the project is not the prediction
itself — it is the machinery around it: getting the data in, training, versioning, serving,
watching for drift, and retraining when needed.

### The data

- **Source**: WeatherAUS, extended with fresh daily data from Open-Meteo.
- **Size**: 145,509 daily observations from 49 weather stations.
- **Period**: 2007-11-01 to 2026-09-01.
- **Input**: the station name plus 20 weather measurements taken that day
  (temperature, rainfall, humidity, pressure, wind, cloud, sunshine).
- **Target**: `RainTomorrow` — Yes or No.

The data is unbalanced: it rains on about 1 day in 4 (31,890 Yes against 110,352 No).
3,267 rows have no label and are dropped.

### The prediction task

Binary classification. Given one day of weather at one station, say whether it will rain there
the next day, and how confident we are.

### Baseline model

XGBoost, trained on a temporal split (70% train / 15% validation / 15% test — the test set is
the most recent period, so we are always predicting forward in time).

### Our target metrics

- **Primary metric: ROC-AUC.** The baseline is **0.866** on the test set. A retrained model has
  to beat this number to replace the one in production.
- **Guardrail: recall.** Currently **0.771**. Missing a rainy day costs more than a false alarm,
  so we do not accept a model that raises accuracy by dropping recall below **0.75**.
- **We deliberately do not use accuracy as the main metric.** Since it only rains 1 day in 4,
  a model that always answers "No" would already score 77.6% accuracy — almost the same as our
  79.0%. Accuracy would make a useless model look good.

### What is out of scope for now

- Beating the state of the art. The mentor's rule stands: 1–2 days on the model, the rest on the architecture.
- Forecasting more than one day ahead, or predicting how much rain.
- A separate model per station — one model covers all 49.

---

## Project Plan & Deadlines

### Phase 0: Kick-off — Deadline: Before Aug 28

- Q&A meeting (15 min)

### Internal Meeting — Mon Aug 31, 10:00 AM CET

- Team kick-off (internal).

### Phase 1: Foundations — Deadline: Sep 4

- ✅ Define project objectives and key metrics. // Jonathan
  - See chapter [**Project Objectives and Key Metrics**](#project-objectives-and-key-metrics)
- ✅ Set up a reproducible development environment. // Ziad — DONE 2026-08-31
- Collect and preprocess data:
  - ✅ Create a database (SQL or NoSQL). // Supabase - Gabriel — DONE 2026-08-31
    - Supabase project: `fgxgenjxslytnqygpefk` (eu-west-1), Postgres 17
    - DB host: `db.fgxgenjxslytnqygpefk.supabase.co:5432`
    - Schema: WeatherAUS-compatible `public.weather_observations`, `public.dataset_versions`, future `public.predictions`, `public.model_versions`, `public.drift_reports`, and the `weather-mlops-dvc` Storage bucket (see `supabase/schema.sql`)
    - Access: invite users via Supabase Auth (`Authentication → Users`); `service_role` key for server-side only
    - Migrations tracked in `supabase/migrations/`; apply via `supabase db push` after `supabase link`
  - ✅ Store the data with a one-time-run Python script. // Update the scripts to store in the DB - Ziad — DONE 2026-08-31
- Build and evaluate a baseline ML model:
  - ✅ Create 2 Python scripts: `training.py` and `predict.py`. // XGBoost - Ziad — DONE 2026-08-31
- Implement a basic inference API:
  - Create 2 endpoints: `training/` and `predict/`. // Gabriel + Thomas — IN REVIEW 2026-09-03
    - Branch `feature/inference-api`, not merged. Works; needs input validation, `/train` fixes,
      CI and a rebase before merging.

### Phase 2: Microservices, Tracking & Versioning — Deadline: Sep 20

- Set up experiment tracking with **MLflow**: // Jonathan
  - Add MLflow logging to the training script.
  - Implement data and model versioning using the MLflow Model Registry.
  - Compare performance after each run and tag the best model in MLflow.
  - At the end of the training script (or later via Airflow), load the previous version and compare it with the newly trained model.
- Split the application into Docker-based microservices with simple orchestration using `docker-compose`. // Gabriel
- Develop automatic model and component updates: // Gabriel + Ziad
  - Scheduled training: cron script, Jenkins, or Airflow (recommended but more complex). // Thomas - Airflow
- ✅ Use **DVC** (without Git) to version datasets. // Ziad — DONE 2026-08-31; MLflow hash logging deferred to the later MLflow stage
- **(OPTIONAL)** Implement unit tests.
- **(OPTIONAL)** CI/CD pipeline with GitHub Actions: (Recommendation: only master branch)
  - `ci.yaml` (always): Linter + Unit tests + Build Docker images.
  - `release.yaml` (only on master): Linter + Unit tests + Build & deploy images to Docker Hub.
- **(OPTIONAL)** Optimize and secure the API (basic auth or OAuth2). // Gabriel + Ziad = [NGINX] - Sprint 1 API security module - review the slides from master class - check optional course
- **(OPTIONAL)** Implement scalability with Kubernetes. // Thomas

### Phase 3: Monitoring & Maintenance — Deadline: Oct 2

- Implement drift detection with **Evidently** in the Airflow pipeline:
  - **Training**:
    - Reference dataset: historical dataset.
    - Current dataset: recent dataset.
    - Track generated report and metrics in MLflow.
    - Retrain the model if necessary.
  - **Prediction**:
    - Store each prediction along with its features in the database.
    - Add an automated DAG to check for data drift.
    - Track generated report and metrics in MLflow.
    - Trigger the training DAG if needed.
- API performance monitoring with **Prometheus / Grafana**:
  - Define alerts.
  - Training trigger via built-in Grafana webhook.
- Create a simple **Streamlit** application to interact with the API and make predictions.
- Finish the repo's technical documentation.

### Final Presentation (Defense) — Oct 13

- 15-minute presentation: explain project progress and chosen architecture.
- 5-minute demonstration: show the application is functional.
- 10-minute Q&A with the jury.
- The full presentation may be delivered on the Streamlit application instead of slides.
- Every member must talk during the presentation.

---

## Key Rules

- **MLOps > model performance**: Spend 1–2 days on a working baseline model, then focus on the MLOps architecture.
- **Deadlines are flexible** if needed — but you manage your own time.
- **Final README is critical**: must include visuals, be well-structured, and free of spelling errors. No formal report to submit.
- **Every team member must speak** during the defense.

---

## Recommended Stack

| Concern             | Tool                                           |
| ------------------- | ---------------------------------------------- |
| Database            | SQL or NoSQL (local)                           |
| API framework       | FastAPI (`predict/` and `training/` endpoints) |
| Experiment tracking | MLflow (logging + Model Registry)              |
| Data versioning     | DVC (without Git) + hashes in MLflow           |
| Orchestration       | Airflow, Jenkins, or cron                      |
| Drift detection     | Evidently                                      |
| Monitoring          | Prometheus + Grafana                           |
| Frontend            | Streamlit                                      |
| Microservices       | Docker + docker-compose                        |
| CI/CD (optional)    | GitHub Actions                                 |
| Scaling (optional)  | Kubernetes                                     |

---

## Additional Resources

- Sprint planning: https://docs.google.com/spreadsheets/d/1Df0VZLkBNmhFG_GJbhoyYVYF38xRdtlSqvua67g3r4w/edit?gid=1397140348
- Project guidelines (slides): https://docs.google.com/presentation/d/1qIjvUaZMwHl6vvmQfJErMwcwCs4BbyHja6v9Lk4RBWQ/edit
- MLOps model canvas: https://docs.google.com/document/d/1MbIGVPfpu8y1DVvhnzCnkgwRmWArD4Wenz14g6r6AEk/edit
- Report guidelines: https://docs.google.com/document/d/1sbgOhiBA4hIYgkO-wrEDZrAejmoz9Ezr5EEwDqsdGMw/edit
- Defense guidelines: https://docs.google.com/document/d/1bF9K4yBjaeWvBRdnNCIpwHDLqdZUHX1VRiEpQOQPY0A/edit

### Similar Projects for Inspiration

- Pompiers (June 2023): https://github.com/DataScientest-Studio/juin23_continu_mlops_pompiers/tree/master
- Bird Image Recognition (AVR24CMLOPS): https://github.com/DataScientest-Studio/AVR24CMLOPS_Bird-Image-Recognition
- Streamlit gallery: https://streamlit.io/gallery
- Reports archive: https://drive.google.com/drive/folders/1vJ89jQHGb5xNvXiomliUbVGiM77GZDQk
- Slides / Streamlit archive: https://drive.google.com/drive/folders/1q3fFLqENeoFD66BD6UP5eIJYcnJsag23

### Architecture Goals

- **Training pipeline** (chart n°1): Automated/scheduled batch process — Airflow, Jenkins, or a simple cron job.
- **Prediction pipeline** (chart n°2): Real-time process.

---

## Next Steps (from Aug 26 meeting)

- Align on project structure, organization, and chosen technologies.
- Explore the given dataset (or pick another from the internet).
- Define a problem to solve and identify useful data.
- Collect data into a SQL or NoSQL database locally (one-time Python script).
- Build a first baseline ML model:
  - `training.py` script.
  - `predict.py` script.
- Create a **FastAPI** with two endpoints (`predict/` and `training/`) using the above scripts.

**Next meeting**: Sep 4 at 5:30 PM.

Suggestion from Nicolas: https://github.com/minio/minio as local S3 bucket.
