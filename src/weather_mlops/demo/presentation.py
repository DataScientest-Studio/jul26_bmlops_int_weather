"""content of the defense deck. speaker notes are only shown in the notes window."""

REPO_URL = "https://github.com/DataScientest-Studio/jul26_bmlops_int_weather"
# links point to this commit, so the jury sees the code we present
COMMIT = "32ea7eab3118fa25a312f03c347e1293fe15f58f"

STAGES = [
    {"id": "data", "label": "Data", "built": True},
    {"id": "versioning", "label": "Versioning", "built": True},
    {"id": "tracking", "label": "Tracking", "built": True},
    {"id": "registry", "label": "Registry", "built": True},
    {"id": "serving", "label": "Serving", "built": True},
    {"id": "security", "label": "Security", "built": True},
    {"id": "orchestration", "label": "Orchestration", "built": True},
    {"id": "cicd", "label": "CI/CD", "built": True},
    {"id": "monitoring", "label": "Monitoring", "built": True},
]

TEAM = ["Gabriel", "Jonathan", "Thomas", "Ziad"]

# rounded values from reports/metrics/*.json (make pipeline, 25 Sep 2026)
METRICS = {
    "ROC-AUC": {"Train": 0.893, "Validation": 0.871, "Test": 0.866},
    "Recall": {"Train": 0.8, "Validation": 0.726, "Test": 0.762},
    "Precision": {"Train": 0.56, "Validation": 0.535, "Test": 0.543},
}
RECALL_GATE = 0.75

# roc curve of the model on the test set: [false positive rate, true positive rate]
ROC_POINTS = [
    [0.0, 0.0],
    [0.004, 0.162],
    [0.008, 0.246],
    [0.013, 0.294],
    [0.019, 0.332],
    [0.024, 0.365],
    [0.03, 0.405],
    [0.037, 0.434],
    [0.044, 0.464],
    [0.05, 0.489],
    [0.058, 0.515],
    [0.066, 0.541],
    [0.075, 0.564],
    [0.084, 0.587],
    [0.093, 0.606],
    [0.102, 0.626],
    [0.113, 0.645],
    [0.123, 0.662],
    [0.136, 0.683],
    [0.148, 0.7],
    [0.162, 0.719],
    [0.176, 0.738],
    [0.188, 0.756],
    [0.202, 0.773],
    [0.217, 0.789],
    [0.234, 0.806],
    [0.252, 0.821],
    [0.274, 0.836],
    [0.297, 0.85],
    [0.322, 0.865],
    [0.353, 0.879],
    [0.379, 0.894],
    [0.415, 0.907],
    [0.458, 0.92],
    [0.5, 0.934],
    [0.545, 0.947],
    [0.596, 0.96],
    [0.669, 0.974],
    [0.768, 0.987],
    [1.0, 1.0],
]
ROC_AUC = 0.866
# cut-off, share of rainy days caught, share of dry days flagged as rain
CUTOFFS = [
    [0.3, 0.910, 0.427],
    [0.5, 0.762, 0.191],
    [0.7, 0.565, 0.075],
]

SECTIONS = [
    {
        "presenter": "Gabriel",
        "title": "Problem, architecture, drift and gateway",
        "minutes": 5,
        "slides": [
            {
                "id": "cover",
                "title": "Will it rain tomorrow?",
                "layout": "cover",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [],
                "links": [],
                # elements lit on the slide while each note is read
                "focus": [
                    ["team"],
                    ["title"],
                    ["lede"],
                    ["team"],
                ],
                "notes": [
                    "[TEAM NAMES] Good morning. We are Gabriel, Jonathan, Thomas and Ziad.",
                    "[TITLE] Our task is a binary classification: will it rain tomorrow at a "
                    "given Australian weather station?",
                    "[SUBTITLE] The model is the small part. Today we show the system around it.",
                    "[TEAM NAMES] I start with the architecture, the problem, drift and our "
                    "gateway. Then Jonathan presents data and model, Thomas serving and "
                    "operations, and Ziad the live demo.",
                ],
            },
            {
                "id": "architecture",
                "title": "Overall software architecture",
                "layout": "system",
                "stages": [],
                "figure": None,
                "lanes": [
                    {
                        "name": "Closed loop: from prediction to new champion",
                        "steps": [
                            "Prediction logged",
                            "Real outcome arrives",
                            "Drift and recall check",
                            "Grafana alert",
                            "Airflow retrains",
                            "Gate moves @champion",
                        ],
                    },
                ],
                "zones": [
                    {
                        "name": "Data sources",
                        "tools": ["Kaggle", "Open-Meteo"],
                        "points": [
                            "WeatherAUS seed, 2007 to 2017",
                            "Open-Meteo archive API for new days",
                            "Same schema, 49 stations",
                        ],
                    },
                    {
                        "name": "Orchestration",
                        "tools": ["Airflow"],
                        "points": [
                            "Daily DAG: ingest, preprocess, Evidently",
                            "Retrain DAG: train, evaluate, compare",
                            "Each task runs in its own container",
                        ],
                    },
                    {
                        "name": "Storage and lineage",
                        "tools": ["Supabase", "DVC", "Vault"],
                        "points": [
                            "Postgres: data, catalog, predictions",
                            "S3: dataset snapshots, model artifacts",
                            "Supabase Vault: app secrets",
                        ],
                    },
                    {
                        "name": "Training and registry",
                        "tools": ["MLflow", "XGBoost"],
                        "points": [
                            "Every run tracked with data hash and commit",
                            "New model gets @candidate",
                            "Only the gate moves @champion",
                        ],
                    },
                    {
                        "name": "Serving",
                        "tools": ["Nginx", "FastAPI", "Streamlit"],
                        "points": [
                            "Nginx: TLS, rate limits",
                            "FastAPI: login, serves @champion",
                            "New champion live without restart",
                        ],
                    },
                    {
                        "name": "Monitoring",
                        "tools": ["Prometheus", "Grafana", "Evidently"],
                        "points": [
                            "API metrics every 15 s",
                            "Daily job: drift and real recall",
                            "Grafana: 2 dashboards, 7 alerts",
                        ],
                    },
                ],
                "caption": "Docker Compose: 11 services, 7 built from our own Dockerfiles. "
                "Airflow 2.8.1 runs as a separate stack.",
                "points": [],
                "links": [
                    ["Compose file", "docker-compose.yml"],
                    ["Airflow DAGs", "airflow/dags/weather_dag.py"],
                    ["Alerts", "docker/grafana/provisioning/alerting/alerts.yml"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    [],
                    ["zone-0"],
                    ["zone-1"],
                    ["zone-2"],
                    ["zone-3"],
                    ["zone-4"],
                    ["zone-5"],
                    ["lane-0"],
                    [],
                ],
                "notes": [
                    "[WHOLE SLIDE] This is our overall software architecture. Everything runs "
                    "in Docker Compose, and Airflow runs as a separate stack.",
                    "[DATA SOURCES] We use the WeatherAUS dataset from Kaggle as our labelled "
                    "history, and we extend it with the Open-Meteo archive API in the same "
                    "schema.",
                    "[ORCHESTRATION] Airflow runs two DAGs. Every evening, weather_pipeline "
                    "fetches new weather, cleans it, fills in the real outcome of past "
                    "predictions, then runs our monitoring job. weather_retrain trains, "
                    "evaluates, and compares with the champion.",
                    "[STORAGE AND LINEAGE] We keep our data in Supabase Postgres, dataset "
                    "snapshots in DVC, and secrets in Supabase Vault.",
                    "[TRAINING AND REGISTRY] We track every training run in MLflow, with its "
                    "dataset hash and git commit. A new model gets the candidate alias; only "
                    "our promotion gate moves the champion alias.",
                    "[SERVING] Nginx is the single entry point. FastAPI always serves the "
                    "current champion, so a promotion goes live without a restart.",
                    "[MONITORING] Prometheus and Grafana watch the API, and Evidently checks "
                    "feature drift.",
                    "[CLOSED LOOP STRIP] The bottom line is our closed loop. A few days after "
                    "each prediction, we learn the real outcome and compute the real recall. "
                    "If it falls below zero point seven five, Grafana triggers "
                    "weather_retrain. We retrain on real recall, not on drift alone, because "
                    "drift does not prove the model got worse.",
                    "[NEXT SLIDE] So, why is this problem harder than it looks?",
                ],
            },
            {
                "id": "problem",
                "title": "Class imbalance: why accuracy is the wrong metric",
                "layout": "hero",
                "stages": [],
                "figure": ["77.1%", "test accuracy of the majority-class baseline (always no)"],
                "lanes": [],
                "points": [
                    "Target: RainTomorrow, binary. One XGBoost model for 49 stations.",
                    "Promotion metric: validation ROC-AUC.",
                    "Guardrail: validation recall of at least 0.75.",
                ],
                "facts": [
                    ["Test rows", "24,808"],
                    ["Positive class (rain)", "5,689 (22.9%)"],
                    ["Baseline recall", "0.000"],
                    ["Candidate run: recall / precision", "0.762 / 0.543"],
                    ["Candidate run: ROC-AUC", "0.866"],
                ],
                "links": [
                    ["Evaluation", "src/weather_mlops/models/evaluation.py"],
                    ["Settings", "src/weather_mlops/config/settings.py"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["point-0"],
                    ["hero", "fact-1", "fact-2"],
                    ["point-1", "fact-4"],
                    ["point-2"],
                ],
                "notes": [
                    "[TARGET (bullet 1)] The input is one row of the CSV: one day at one "
                    "station, with twenty weather columns, like minimum temperature, "
                    "humidity at three p.m., pressure, wind, and whether it rained today. "
                    "The output is the probability of rain tomorrow.",
                    "[77.1% + TABLE: Positive class, Baseline recall] Only twenty-three "
                    "percent of test days are rainy. So the baseline that always says no "
                    "reaches seventy-seven percent accuracy, with a recall of zero. Our "
                    "candidate run reaches about eighty percent. Accuracy cannot tell a "
                    "useful model from a useless one.",
                    "[PROMOTION METRIC (bullet 2) + TABLE: Candidate ROC-AUC] So we promote "
                    "on validation ROC-AUC, which measures ranking and does not depend on a "
                    "threshold. The constant baseline scores zero point five; this run scores "
                    "zero point eight seven on the test set.",
                    "[GUARDRAIL (bullet 3)] And we add a guardrail: validation recall of at "
                    "least zero point seven five, because a missed rainy day costs more than "
                    "a false alarm.",
                ],
            },
            {
                "id": "drift",
                "title": "Distribution shift: Australia to Singapore",
                "layout": "hero",
                "stages": [],
                "figure": ["0.87 to 0.70", "ROC-AUC, Australian test set vs all Singapore days"],
                "lanes": [],
                "points": [
                    "Label shift: rain tomorrow on 82.6% of Singapore days, 21.9% in Australia.",
                    "Covariate shift: Evidently (PSI) flags all 5 monitored features.",
                    "Retraining recovers only part of the loss.",
                ],
                "facts": [
                    ["AU model, Singapore 2022-24", "0.641"],
                    ["Retrained on Singapore 2014-21", "0.703"],
                    ["Retrained on AU + Singapore", "0.708"],
                    ["AU + Singapore, AU test set", "0.867"],
                ],
                "links": [
                    ["Merge Singapore", "scripts/merge_singapore.py"],
                    ["Score and retrain", "scripts/score_drift.py"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["point-0", "point-1"],
                    ["hero"],
                    ["fact-0", "fact-1", "fact-2", "fact-3"],
                    ["point-2"],
                ],
                "notes": [
                    "[TITLE] To test drift on real data, we took a much rainier place with "
                    "the same schema: Singapore, eleven years from Open-Meteo.",
                    "[LABEL SHIFT + COVARIATE SHIFT (bullets 1-2)] Two shifts at once. It "
                    "rains the next day on eighty-three percent of Singapore days, against "
                    "twenty-two percent in Australia. And Evidently flags all five monitored "
                    "features.",
                    "[0.87 TO 0.70] The ROC-AUC falls from zero point eight seven to zero "
                    "point seven.",
                    "[TABLE: 0.641, 0.703, 0.708, 0.867] On a temporal split, retraining with "
                    "Singapore lifts its score from zero point six four to zero point seven, "
                    "and Australia stays at zero point eight seven.",
                    "[RETRAINING RECOVERS (bullet 3)] So retraining recovers only part of the "
                    "loss. This was an offline experiment; the served model stays Australian.",
                ],
            },
            {
                "id": "gateway",
                "title": "Single ingress: the Nginx gateway",
                "layout": "flow",
                "stages": ["security"],
                "figure": None,
                "lanes": [
                    {
                        "name": "Every external request",
                        "steps": [
                            "TLS 1.2/1.3 on 443",
                            "limit_req per IP",
                            "Basic auth (FastAPI)",
                            "FastAPI",
                        ],
                    },
                ],
                "points": [
                    "Only Nginx is public. All other tools bind to localhost.",
                    "Excess requests get 429 before they reach Python.",
                    "6 live tests in CI: redirect, TLS, HSTS, health, 401, 429.",
                ],
                "facts": [
                    ["Public ports", "80 (301), 443"],
                    ["API limit", "10 r/s per IP, burst 20"],
                    ["/train limit", "1 r/s per IP, burst 3"],
                    ["Body cap, timeouts", "2 MB, 15 s"],
                    ["/metrics from outside", "404"],
                ],
                "links": [
                    ["Nginx config", "docker/nginx/nginx.conf"],
                    ["Auth", "src/weather_mlops/api/main.py"],
                    ["Live tests", "tests/integration/test_nginx_live.py"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["point-0", "fact-0"],
                    ["lane-0", "fact-1", "fact-2"],
                    ["point-2"],
                    [],
                ],
                "notes": [
                    "[ONLY NGINX IS PUBLIC (bullet 1) + TABLE: Public ports] Our system has a "
                    "single entry point: Nginx, on ports 80 and 443. All other tools bind to "
                    "localhost.",
                    "[LANE: Every external request + TABLE: limits] Every request passes three "
                    "layers. First, TLS: only versions 1.2 and 1.3, and plain HTTP is redirected. "
                    "Second, "
                    "per-IP rate limiting: ten requests per second, and one per second on "
                    "training, because training is expensive. Third, HTTP Basic "
                    "authentication in FastAPI, with credentials loaded from Supabase Vault.",
                    "[6 LIVE TESTS (bullet 3)] Six live tests in CI check these layers. Known "
                    "limits: a self-signed certificate and one shared credential.",
                    "[NEXT: JONATHAN] Now Jonathan will show you how we version the data and "
                    "the model.",
                ],
            },
        ],
    },
    {
        "presenter": "Jonathan",
        "title": "Data and model",
        "minutes": 5,
        "slides": [
            {
                "id": "lineage",
                "title": "Data and lineage",
                "layout": "flow",
                "stages": ["data", "versioning"],
                "figure": None,
                "lanes": [
                    {
                        "name": "From source to training run",
                        "steps": [
                            "WeatherAUS and Open-Meteo",
                            "Merge",
                            "Preprocess",
                            "sha256 manifest",
                            "MLflow run",
                        ],
                    },
                ],
                "points": [
                    "145,509 daily rows from 49 stations.",
                    "WeatherAUS covers 2007 to 2017. Open-Meteo adds new days.",
                    "DVC stores snapshots. A make target registers them in Postgres.",
                ],
                "facts": [
                    ["Train rows", "93,076"],
                    ["Validation rows", "24,358"],
                    ["Test rows", "24,808"],
                    ["Stations", "49"],
                ],
                "links": [
                    ["DVC pipeline", "dvc.yaml"],
                    ["Manifest", "src/weather_mlops/data/manifest.py"],
                    ["Schema", "supabase/schema.sql"],
                ],
                "notes": [
                    "About 2.5 minutes.",
                    "Seed: the WeatherAUS CSV, 145,460 daily rows from 49 stations, 1 Nov "
                    "2007 to 25 Jun 2017.",
                    "Ingestion calls the Open-Meteo archive API for each station's "
                    "coordinates and converts the answer to the WeatherAUS columns. So far "
                    "it has added one day, 1 Sep 2026: 49 rows, for 145,509 in total. Be "
                    "upfront about the nine-year gap.",
                    "merge_raw joins the seed and every Open-Meteo file, drops duplicates "
                    "on date and station keeping the newest, and sorts. version_raw then "
                    "writes the sha256 of the merged file.",
                    "Preprocess drops rows without a date or label and maps Yes/No to 1/0. "
                    "The split is temporal, 70/15/15 by date, so the test set is the most "
                    "recent period and no future weather leaks into training.",
                    "Imputation, scaling and one-hot encoding live inside the model "
                    "pipeline, not in the CSVs. So serving applies exactly the "
                    "preprocessing used in training.",
                    "Each processed set gets a manifest: its sha256, the parent raw sha256, "
                    "the preprocessing version, the git commit and the split fractions. "
                    "Training refuses to start if the manifest is missing or does not match "
                    "the files.",
                    "DVC describes six stages in dvc.yaml and stores the files in the "
                    "weather-mlops-dvc bucket on Supabase Storage. make dvc-pull restores "
                    "the team's baseline on any laptop.",
                    "make register-dataset records a snapshot in the Postgres "
                    "dataset_versions table.",
                    "If asked whether the nightly data can be rebuilt: the nightly job "
                    "hashes the data but does not push it. Pushing is manual, with make "
                    "dvc-push.",
                ],
            },
            {
                "id": "promotion",
                "title": "Tracking and the promotion gate",
                "layout": "metrics",
                "stages": ["tracking", "registry"],
                "figure": None,
                "lanes": [],
                "points": [
                    "Each training run registers a candidate.",
                    "Promote only if ROC-AUC beats the champion and recall is at least 0.75.",
                    "Latest run: validation recall 0.726, so compare rejected it.",
                ],
                "links": [
                    ["Promotion rule", "src/weather_mlops/models/comparison.py"],
                    ["Tracking", "src/weather_mlops/models/tracking.py"],
                ],
                "notes": [
                    "About 2 minutes.",
                    "Model: XGBoost with 250 trees, depth 4, learning rate 0.05, subsample "
                    "and column sample 0.9. The class weight is the ratio of dry to rainy "
                    "days in the training set: 3.38 in the latest run.",
                    "Every run logs to MLflow: the parameters including row and class "
                    "counts, the training metrics, the metrics file, the model file, the "
                    "dataset manifest, and the whole preprocessing-plus-model pipeline.",
                    "Each run is tagged with the dataset sha256, the parent sha256, the git "
                    "commit and the preprocessing version, so any model traces back to its "
                    "exact data and code.",
                    "Every run registers a new version of weather-rainfall-classifier and "
                    "moves the candidate alias to it. Only compare can move the champion "
                    "alias.",
                    "Compare first checks that the validation metrics, the model file and "
                    "the dataset hash belong to the same run. Then it promotes only if "
                    "validation ROC-AUC beats the champion and recall is at least 0.75.",
                    "Three outcomes: promoted, kept_previous, rejected_recall. On promotion "
                    "it moves the champion alias, tags the version champion, and copies the "
                    "model to best_model.joblib.",
                    "Read the chart: ROC-AUC is 0.893 on train, 0.871 on validation and "
                    "0.866 on test. The small drop suggests little overfitting.",
                    "Say the precision out loud: 0.54. We accept more false alarms to catch rain.",
                    "The gate worked on our own model: run 4d5c45cd reached validation "
                    "ROC-AUC 0.871 but recall 0.726, so it stayed a candidate. The Airflow "
                    "run on 25 Sep made the same decision.",
                    "So there is no champion yet. A possible next step is a recall-targeted "
                    "decision threshold; it is not built.",
                    "The MLflow server keeps runs in SQLite and artifacts in the "
                    "weather-mlops-mlflow bucket.",
                ],
            },
            {
                "id": "roc",
                "title": "ROC curve: how well the model ranks days",
                "layout": "roc",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [
                    "Each point is one cut-off between rain and no rain.",
                    "The area under the curve is ROC-AUC: 0.866. Always no gets 0.5.",
                    "We serve the 0.5 cut-off: 76.2% of rainy days caught.",
                ],
                "links": [
                    ["Evaluation", "src/weather_mlops/models/evaluation.py"],
                ],
                "notes": [
                    "About 1 minute. Then hand over to Thomas.",
                    "ROC stands for Receiver Operating Characteristic, AUC for Area Under "
                    "the Curve. The curve is computed on the 24,808 test rows.",
                    "Up means more rainy days caught. Right means more dry days wrongly "
                    "flagged as rain.",
                    "The dots are three cut-offs: 0.3 catches 91.0% of rainy days but flags "
                    "42.7% of dry days; 0.5, the one we serve, catches 76.2% and flags "
                    "19.1%; 0.7 catches 56.5% and flags 7.5%.",
                    "The dashed diagonal is a model with no skill, area 0.5. Always "
                    "answering no is its bottom-left corner.",
                    "Accuracy would prefer the 0.7 cut-off, 84.2% accuracy, while missing "
                    "2,472 rainy days instead of 1,355. The recall guardrail stops that.",
                ],
            },
        ],
    },
    {
        "presenter": "Thomas",
        "title": "Serving and operations",
        "minutes": 5,
        "slides": [
            {
                "id": "serving",
                "title": "Serving the champion",
                "layout": "flow",
                "stages": ["serving"],
                "figure": None,
                "lanes": [
                    {
                        "name": "One prediction",
                        "steps": [
                            "Validate input",
                            "Load champion",
                            "Predict",
                            "Answer with model",
                            "Record metrics",
                        ],
                    },
                ],
                "points": [
                    "Four public endpoints, plus /metrics for Prometheus only.",
                    "Out-of-range values and unknown stations are rejected.",
                    "Every answer names the model that produced it.",
                ],
                "facts": [
                    ["Endpoints", "5"],
                    ["Rainfall bounds", "0 to 500 mm"],
                    ["Live weather timeout", "30 s"],
                    ["Stations accepted", "49"],
                ],
                "links": [
                    ["API", "src/weather_mlops/api/main.py"],
                    ["Model loading", "src/weather_mlops/models/predict.py"],
                ],
                "notes": [
                    "About 1 minute 15 seconds.",
                    "At startup the API loads its Basic-auth credentials from Supabase Vault.",
                    "Four public endpoints. Health is open. Predict takes one day of "
                    "measurements. Live predict takes only a station name. Train retrains.",
                    "A fifth endpoint, /metrics, is for Prometheus only. Nginx answers 404 "
                    "from outside; more on that in the monitoring slide.",
                    "Inputs have bounds, for example rainfall between 0 and 500 mm. Unknown "
                    "stations are rejected with a suggestion for likely typos.",
                    "Live predict looks up the station's coordinates, fetches today's "
                    "weather from Open-Meteo with a 30-second timeout, and returns 502 if "
                    "the data is not available yet.",
                    "Train accepts five hyperparameters with bounds, for example depth up "
                    "to 15. It returns metrics on the training and on the validation data, "
                    "and clears the prediction cache.",
                    "Every answer includes the model that served it: name, alias, version, source.",
                    "The API checks the champion alias on each prediction, so a promotion "
                    "or rollback takes effect without a restart.",
                ],
            },
            {
                "id": "orchestration",
                "title": "Scheduled retraining with Airflow",
                "layout": "flow",
                "stages": ["orchestration"],
                "figure": None,
                "lanes": [
                    {
                        "name": "Scheduled daily at 18:00 CEST, or on drift alert",
                        "steps": ["Ingest", "Preprocess", "Train", "Validate", "Compare"],
                    },
                ],
                "points": [
                    "Each task runs one of our Docker images.",
                    "Training goes through the gateway, like any client.",
                    "DAG can be triggered via Grafana-Webhook",
                ],
                "facts": [
                    ["Schedule", "daily, 18:00 CEST"],
                    ["Tasks", "5"],
                    ["Retries", "3, one minute apart"],
                    ["Verified run", "25 Sep: 5 of 5 in 44 s"],
                ],
                "links": [
                    ["Airflow DAG", "airflow/dags/weather_dag.py"],
                ],
                "notes": [
                    "About 1.5 minutes.",
                    "Airflow 2.8.1 runs as its own Compose stack: a Postgres 13 metadata "
                    "database, the web server, the scheduler, and a LocalExecutor.",
                    "The DAG weather_pipeline has five tasks: ingestion, preprocess, train, "
                    "evaluation, compare. It runs daily at 18:00 Berlin time. No "
                    "catch-up: after downtime only the latest missed run is executed.",
                    "Second trigger: when the drift alert fires, Grafana starts the DAG "
                    "through the Airflow REST API. For this the Airflow web server also "
                    "joins our Docker network.",
                    "Each task is a DockerOperator that runs one of our images, so Airflow "
                    "runs the same code as Compose. Containers are removed after each task.",
                    "Ingestion and preprocess can write the data folder. Train, evaluation "
                    "and compare mount it read-only and write only models and reports.",
                    "The train task calls POST /train through Nginx like any client, so the "
                    "stack must be up (make up).",
                    "Airflow reaches Docker through a socket proxy that allows containers, "
                    "images and POST calls, and denies network management.",
                    "Each task retries up to 3 times, one minute apart. The DAG runs "
                    "validation only; the test-set evaluation is make pipeline.",
                    "Verified 25 Sep 2026: a scheduled run succeeded. All five tasks passed "
                    "on the first try, in 44 seconds. It fetched 49 new rows, retrained, "
                    "and compare rejected the model on recall (0.726), the same decision "
                    "as make pipeline.",
                    "Verified 28 Sep 2026: the Grafana webhook started a run, visible in "
                    "Airflow with the run config triggered_by grafana.",
                    "The run history is in the Airflow UI at localhost:8081. The DAG starts "
                    "paused (Airflow setting) and stays paused until unpaused.",
                ],
            },
            {
                "id": "cicd",
                "title": "Continuous integration and delivery",
                "layout": "flow",
                "stages": ["cicd"],
                "figure": None,
                "lanes": [
                    {
                        "name": "CI, on pushes and pull requests to master",
                        "steps": ["Lint", "Unit tests", "Build images", "Live gateway tests"],
                    },
                    {"name": "Release, on master", "steps": ["Build", "Push to ghcr.io"]},
                ],
                "points": [],
                "facts": [
                    ["CI jobs", "2"],
                    ["Tests", "160 (6 live gateway)"],
                    ["Images built", "7"],
                    ["Images on ghcr.io", "3"],
                ],
                "links": [
                    ["CI workflow", ".github/workflows/ci.yml"],
                    ["Release workflow", ".github/workflows/release.yml"],
                    ["Tests", "tests/"],
                ],
                "notes": [
                    "About 45 seconds. Keep it short, the lanes say most of it.",
                    "CI runs on every push and pull request to master, in two jobs.",
                    "Job one: ruff lint and format check, then the unit tests.",
                    "Job two, in Docker: build all seven images, start the API and Nginx, "
                    "and run the live gateway tests against them: redirect, TLS, 401 "
                    "without credentials, and 429 on a burst.",
                    "Release, on push to master: push the ingestion, preprocess and API "
                    "images to ghcr.io.",
                    "If asked: release runs in parallel with CI and tags only latest. "
                    "Gating it on CI and tagging by commit is the next step.",
                    "If asked about details, the full CI setup was built by the team; "
                    "the workflow files are linked below.",
                ],
            },
            {
                "id": "monitoring",
                "title": "Monitoring with Prometheus and Grafana",
                "layout": "flow",
                "stages": ["monitoring"],
                "figure": None,
                "lanes": [
                    {
                        "name": "Prometheus scrapes every 15 sec",
                        "steps": ["API endpoints", "/metrics", "Prometheus", "Grafana"],
                    },
                    {
                        "name": "On drift alert",
                        "steps": ["Alert", "Webhook", "Airflow", "New model"],
                    },
                ],
                "points": [
                    "Live predictions and training report model metrics",
                    "Drift proxy via alert based on the rain prediction distribution",
                    "If the alert is firing -> DAG run via Grafana Webhook",
                ],
                "facts": [
                    ["Scrape interval", "15 s"],
                    ["Dashboards", "2"],
                    ["Alerts", "6 (3 API, 3 model)"],
                    ["Max retraining", "1/day"],
                ],
                "links": [
                    ["Metrics", "src/weather_mlops/api/metrics.py"],
                    ["Prometheus", "docker/prometheus/"],
                    ["Grafana", "docker/grafana/"],
                ],
                "notes": [
                    "About 1.5 minutes. Then hand over to Ziad.",
                    "The API measures itself. A library counts every request by endpoint, "
                    "method and status, and times it.",
                    "On top come our own model metrics. Live predictions record the "
                    "station, rain or no rain, the probability and the model that answered. "
                    "Train records how often and how long we train, and the validation "
                    "metrics.",
                    "All of it is exposed on /metrics. Nginx blocks it from outside, "
                    "Prometheus reads it inside the Docker network every 15 seconds and "
                    "keeps the history.",
                    "Grafana shows two dashboards: Weather API for requests, errors and "
                    "latency, Weather model for rain rate, probabilities, active model and "
                    "performance.",
                    "Everything in Grafana is code in docker/grafana: data source, "
                    "dashboards and alerts. After git pull and make monitoring everyone has "
                    "the same setup.",
                    "Six alerts. API: down, more than 10 percent server errors, average "
                    "latency above 5 seconds. Model: ROC-AUC below 0.866, recall below "
                    "0.75, unusual rain rate.",
                    "Performance alerts go to a person, not to retraining: retraining on "
                    "the same data would produce the same model.",
                    "The rain-rate alert is our drift signal: if under 5 or over 60 percent "
                    "of the last 24 hours' predictions say rain, with at least 20 "
                    "predictions, Grafana calls Airflow through a webhook, at most once a "
                    "day.",
                    "This is a proxy. Real drift detection compares the input "
                    "data with the training data; that is the Evidently part.",
                    "For now alerts are only visible in Grafana, no Slack, to avoid noise "
                    "while we test.",
                    "If asked about latency: the library's default buckets stop at 1 "
                    "second, so we alert on average latency instead of the 95th percentile.",
                ],
            },
        ],
    },
    {
        "presenter": "Ziad",
        "title": "Demo and next steps",
        "minutes": 5,
        "slides": [
            {
                "id": "demo",
                "title": "Live demo",
                "layout": "script",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [
                    "Pick a station.",
                    "Get tomorrow's forecast and the model that served it.",
                    "Show the training run in MLflow.",
                    "Show the nightly DAG in Airflow.",
                ],
                "links": [
                    ["Streamlit app", "src/weather_mlops/demo/app.py"],
                ],
                "notes": [
                    "About 4 minutes, leaving 1 minute for next steps.",
                    "Before the defense: make up, make streamlit and make airflow-up. On "
                    "Gabriel's Mac, first stop Tailscale (it holds port 443) and Homebrew "
                    "httpd (it holds 8080).",
                    "Present the deck from the Streamlit container at 127.0.0.1:8501. The "
                    "demo panel calls https://nginx, which only resolves inside Docker; a "
                    "deck started with uv run on the Mac shows Gateway is down.",
                    "1. The green line under this slide comes from /health through Nginx.",
                    "2. Pick Sydney, click Predict from live weather. The API fetches "
                    "today's weather and answers Rain or No rain with a probability.",
                    "3. The caption says Served by rain_classifier.joblib: no champion "
                    "exists yet, as Jonathan explained.",
                    "4. MLflow on port 8080: experiment weather-rainfall-classifier, open "
                    "the latest run, show params, metrics and the dataset_sha256 and "
                    "git_commit tags. Then Models: the versions and the candidate alias.",
                    "5. Airflow on port 8081, user admin, password in airflow/.env: open "
                    "weather_pipeline and show the successful run executed on 25 Sep "
                    "(Airflow names it scheduled__2026-09-23) in the graph view.",
                    "If the network fails, say so and continue on the slides. Do not retry "
                    "for more than 30 seconds.",
                ],
            },
            {
                "id": "next-steps",
                "title": "Next steps: from laptop to production",
                "layout": "script",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [
                    "Cloud hosting with Kubernetes: API replicas that restart on failure.",
                    "Canary release: Nginx sends 10% of traffic to the new model first.",
                    "Decision threshold tuned on validation to reach recall 0.75.",
                    "Tomorrow's Open-Meteo forecast as new model features.",
                    "Paid API: one key per client, Stripe billing per call.",
                ],
                "links": [],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["point-0"],
                    ["point-1"],
                    ["point-2"],
                    ["point-3"],
                    ["point-4"],
                    [],
                ],
                "notes": [
                    "[TITLE] Before your questions, five next steps.",
                    "[1. KUBERNETES] One: leave the laptop. We host the system in the cloud, "
                    "for example on AWS, with Kubernetes running several API replicas.",
                    "[2. CANARY] Two: a canary release. Nginx sends ten percent of real "
                    "traffic to the new champion first, and we keep it only if its real "
                    "recall holds.",
                    "[3. THRESHOLD] Three: today we cut at zero point five. We would tune the "
                    "threshold on validation to reach recall zero point seven five.",
                    "[4. FORECAST FEATURES] Four: our model only sees today's weather. "
                    "Open-Meteo also forecasts tomorrow; adding that forecast as features "
                    "should be our biggest gain.",
                    "[5. PAID API] Five: one API key per client, and Stripe billing per "
                    "prediction call.",
                    "[NEXT: QUESTIONS] Thank you. We are happy to take your questions.",
                ],
            },
            {
                "id": "questions",
                "title": "Questions",
                "layout": "closing",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [],
                "links": [],
                "notes": [
                    "Likely questions: the 2017 to 2026 gap, recall below the gate, "
                    "rollback with only a latest tag, the self-signed certificate.",
                    "Rollback: point the champion alias at the previous version in MLflow. "
                    "The API picks it up on the next prediction.",
                    "Everyone answers questions on their own part.",
                ],
            },
        ],
    },
]


def all_slides():
    # every slide in talk order, with the section it belongs to
    result = []
    for section in SECTIONS:
        for slide in section["slides"]:
            result.append((section, slide))
    return result


def total_minutes():
    total = 0
    for section in SECTIONS:
        total = total + section["minutes"]
    return total


def source_url(path):
    if path.endswith("/"):
        return REPO_URL + "/tree/" + COMMIT + "/" + path.rstrip("/")
    return REPO_URL + "/blob/" + COMMIT + "/" + path
