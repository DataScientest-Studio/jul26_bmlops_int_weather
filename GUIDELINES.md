# Project Guidelines

## Overview

This document summarizes the guidelines provided by the mentor for the **MLOps project (Weather)**. Evaluation focuses on MLOps proficiency, not model performance — spend 1–2 days max on a working model, then focus on the architecture.

- **Mentor contact**: Nicolas Fradin (Slack channel)
- **Project repo**: https://github.com/DataScientest-Studio/jul26_bmlops_int_weather
- **Communication**: Slack is the primary channel; meetings are recorded and shared.

---

## Project Plan & Deadlines

### Phase 0: Kick-off — Deadline: Before Aug 28
- Q&A meeting (15 min)

### Internal Meeting — Mon Aug 31, 10:00 AM CET
- Team kick-off (internal).

### Phase 1: Foundations — Deadline: Sep 4
- Define project objectives and key metrics.
- Set up a reproducible development environment.
- Collect and preprocess data:
  - Create a database (SQL or NoSQL).
  - Store the data with a one-time-run Python script.
- Build and evaluate a baseline ML model:
  - Create 2 Python scripts: `training.py` and `predict.py`.
- Implement a basic inference API:
  - Create 2 endpoints: `training/` and `predict/`.

### Phase 2: Microservices, Tracking & Versioning — Deadline: Sep 20
- Set up experiment tracking with **MLflow**:
  - Add MLflow logging to the training script.
  - Implement data and model versioning using the MLflow Model Registry.
  - Compare performance after each run and tag the best model in MLflow.
  - At the end of the training script (or later via Airflow), load the previous version and compare it with the newly trained model.
- Split the application into Docker-based microservices with simple orchestration using `docker-compose`.
- Develop automatic model and component updates:
  - Scheduled training: cron script, Jenkins, or Airflow (recommended but more complex).
- Use **DVC** (without Git) to version datasets and store their hashes in MLflow.
- **(OPTIONAL)** Implement unit tests.
- **(OPTIONAL)** CI/CD pipeline with GitHub Actions:
  - `ci.yaml` (always): Linter + Unit tests + Build Docker images.
  - `release.yaml` (only on master): Linter + Unit tests + Build & deploy images to Docker Hub.
- **(OPTIONAL)** Optimize and secure the API (basic auth or OAuth2).
- **(OPTIONAL)** Implement scalability with Kubernetes.

### Phase 4: Monitoring & Maintenance — Deadline: Oct 2
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

| Concern | Tool |
|---|---|
| Database | SQL or NoSQL (local) |
| API framework | FastAPI (`predict/` and `training/` endpoints) |
| Experiment tracking | MLflow (logging + Model Registry) |
| Data versioning | DVC (without Git) + hashes in MLflow |
| Orchestration | Airflow, Jenkins, or cron |
| Drift detection | Evidently |
| Monitoring | Prometheus + Grafana |
| Frontend | Streamlit |
| Microservices | Docker + docker-compose |
| CI/CD (optional) | GitHub Actions |
| Scaling (optional) | Kubernetes |

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

**Next meeting**: Sep 4 at 5:00 PM.
