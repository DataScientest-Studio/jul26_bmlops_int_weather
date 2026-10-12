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
                "title": "Data lineage: two sources, one schema, one hash",
                "layout": "flow",
                "stages": ["data", "versioning"],
                "figure": None,
                "lanes": [
                    {
                        "name": "From source to training run",
                        "steps": [
                            "Kaggle + Open-Meteo",
                            "Rolling split",
                            "sha256 manifest",
                            "DVC snapshot",
                            "MLflow run",
                        ],
                    },
                ],
                "points": [
                    "Kaggle WeatherAUS: 145,460 daily station rows, 2007 to June 2017.",
                    "Open-Meteo: same 23 columns.",
                    "Split by date",
                ],
                "facts": [
                    ["DVC snapshot, 2 Oct", "185,150 rows, 49 stations"],
                    ["Train, 5 years", "Mar 2014 to Mar 2019"],
                    ["Validation, 90 days", "Mar to Jun 2019"],
                    ["Test, 90 days", "Jun to Sep 2019"],
                    ["Open-Meteo share: train, val, test", "35%, 100%, 100%"],
                ],
                "links": [
                    ["DVC pipeline", "dvc.yaml"],
                    ["Rolling split", "src/weather_mlops/data/preprocess.py"],
                    ["Manifest", "src/weather_mlops/data/manifest.py"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["point-0"],
                    ["point-1"],
                    ["lane-0", "point-2", "fact-1", "fact-2", "fact-3"],
                    ["lane-0", "fact-0"],
                    ["fact-4"],
                ],
                "notes": [
                    "[TITLE] Thank you, Gabriel. Every model we serve must lead back to the exact "
                    "data that trained it, so I start with the data.",
                    "[KAGGLE (bullet 1)] Our labelled history is the Kaggle WeatherAUS file: a "
                    "hundred and forty-five thousand daily rows from forty-nine stations, up to "
                    "June 2017.",
                    "[OPEN-METEO (bullet 2)] To go further, we call the "
                    "Open-Meteo archive API at each station's coordinates and convert the answer "
                    "into the same twenty-three columns. Our resumable backfill reaches September "
                    "2019 so far; the seven years after that are not filled yet.",
                    "[LANE + ROLLING SPLIT (bullet 3) + TABLE: windows] Both sources are merged "
                    "and split by date, never at random, so no future weather leaks into training. "
                    "The windows count the days we actually have, and our data stops in September "
                    "2019. So today we train on March 2014 to March 2019, validate on the next "
                    "ninety days, and test on the ninety days up to September 2019.",
                    "[MANIFEST, DVC, MLFLOW + TABLE: snapshot] Each split gets a manifest with the "
                    "SHA-256 of every file, its raw parent's hash and the git commit, and training "
                    "refuses files that do not match it. DVC, in no-Git mode as the brief asks, "
                    "stores the snapshots, and the same hash goes into Postgres and into every "
                    "MLflow run.",
                    "[TABLE: Open-Meteo share] Keep one number in mind: validation and test are "
                    "one hundred percent Open-Meteo, while training is still two-thirds station "
                    "data. And Open-Meteo is a weather model's estimate, not the station's own "
                    "instruments.",
                ],
            },
            {
                "id": "tracking",
                "title": "Experiment tracking: every model and every day on record",
                "layout": "tracking",
                "stages": ["tracking"],
                "figure": None,
                "lanes": [],
                # champion metrics: the baseline's settings on 90 unseen validation days, from
                # the 12-trial search run, before the refit on all Kaggle rows
                "rows": [
                    {
                        "name": "Each training run, from make train, POST /train or Airflow",
                        "cards": [
                            {
                                "name": "Parameters",
                                "ask": "How was it trained?",
                                "points": [
                                    "XGBoost settings: trees, depth, learning rate",
                                    "Training rows and class weight",
                                ],
                            },
                            {
                                "name": "Metrics",
                                "ask": "How good is it?",
                                "points": [
                                    "Champion ROC-AUC 0.866",
                                    "Recall 0.776",
                                    "Precision 0.512",
                                ],
                            },
                            {
                                "name": "Tags",
                                "ask": "Which data and code?",
                                "points": [
                                    "<code>dataset_sha256</code>: the DVC snapshot",
                                    "<code>git_commit</code>: the code",
                                ],
                            },
                            {
                                "name": "Artifacts",
                                "ask": "Can we reload it?",
                                "points": [
                                    "The model itself",
                                    "Dataset manifest",
                                    "<code>release.json</code> ties them together",
                                ],
                            },
                        ],
                    },
                    {
                        "name": "Each evening, the Evidently job on the latest predictions",
                        "cards": [
                            {
                                "name": "Drift",
                                "ask": "Did inputs change?",
                                "points": [
                                    "PSI per feature against the training data",
                                    "Share of drifted features",
                                ],
                            },
                            {
                                "name": "Real performance",
                                "ask": "Was it right?",
                                "points": [
                                    "Recall on predictions whose outcome is known",
                                    "Retrain request below 0.75",
                                ],
                            },
                            {
                                "name": "Tags",
                                "ask": "Which model?",
                                "points": [
                                    "Version holding <code>@champion</code>",
                                    "Hash of its training data",
                                ],
                            },
                            {
                                "name": "Artifacts",
                                "ask": "Can we read it?",
                                "points": [
                                    "Full Evidently HTML report, on S3",
                                    "<code>summary.json</code>",
                                ],
                            },
                        ],
                    },
                ],
                "points": [],
                "links": [
                    ["Tracking", "src/weather_mlops/models/tracking.py"],
                    ["Evidently runs", "src/weather_mlops/monitoring/drift.py"],
                    ["MLflow server", "docker-compose.yml"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["row-0", "card-0-0", "card-0-1", "card-0-2", "card-0-3"],
                    ["card-0-0"],
                    ["card-0-1"],
                    ["card-0-2"],
                    ["card-0-3"],
                    ["row-1", "card-1-0", "card-1-1", "card-1-2", "card-1-3"],
                    ["card-1-0"],
                    ["card-1-1"],
                    ["card-1-2"],
                    ["card-1-3"],
                ],
                "notes": [
                    "[TITLE] Once a dataset has a hash, every model needs a record of how it was "
                    "made, and so does every day it serves. MLflow keeps both.",
                    "[ROW 1 LABEL] First, training. Whoever starts it, a developer with make "
                    "train, a client calling POST /train or Airflow, the same function writes "
                    "the record.",
                    "[PARAMETERS] It records how the model was trained: the XGBoost settings, the "
                    "training rows and the class weight.",
                    "[METRICS] And how good it is. For our current champion, the baseline, "
                    "measured on ninety days it had never seen: ROC-AUC zero point eight seven, "
                    "recall zero point seven eight, precision zero point five one. That zero point "
                    "eight seven is the bar our Grafana alert watches.",
                    "[TAGS] Every run is tagged with the hash of its DVC snapshot and the git "
                    "commit of its code. From any model, we can go back to its exact data and its "
                    "exact code.",
                    "[ARTIFACTS] The model itself, the dataset manifest, and a release file that "
                    "ties them together. MLflow can reload any version at any time.",
                    "[ROW 2 LABEL] Second, and just as important: every evening, after new weather "
                    "comes in, our Evidently job also writes a run to MLflow, in its own "
                    "experiment.",
                    "[DRIFT] Did the inputs change? It computes the drift score, PSI, for each "
                    "feature against the training data, and the share of features that drifted.",
                    "[REAL PERFORMANCE] Was the model right? Once the real weather is known, it "
                    "computes the real recall of our past predictions. Below zero point seven "
                    "five, it requests a retrain.",
                    "[TAGS] Each report is tagged with the champion version it watched and the "
                    "hash of that model's training data. So drift is always measured against the "
                    "right reference.",
                    "[ARTIFACTS] The full Evidently report is stored as HTML on S3, so we can open "
                    "the report for any past day. The numbers also go to Grafana, as Thomas will "
                    "show.",
                ],
            },
            {
                "id": "registry",
                "title": "Model registry: only the gate moves @champion",
                "layout": "registry",
                "stages": ["registry"],
                "figure": None,
                "lanes": [],
                # recall of the latest candidate, as in the deck's other numbers: DVC snapshot of
                # 2 Oct 2026, code of commit 32ea7ea
                "versions": {
                    "name": "Versions of one registered model, oldest to newest",
                    "steps": [
                        {"label": "Older versions", "note": "", "state": "older", "alias": ""},
                        {
                            "label": "Baseline",
                            "note": "served today",
                            "state": "champion",
                            "alias": "@champion",
                        },
                        {
                            "label": "Candidate",
                            "note": "recall 0.673, rejected",
                            "state": "rejected",
                            "alias": "",
                        },
                        {
                            "label": "Newest",
                            "note": "waits for the gate",
                            "state": "candidate",
                            "alias": "@candidate",
                        },
                    ],
                },
                "gate": "The gate moves @champion only if all three hold",
                "points": [
                    "The release is complete: clean git commit, version matches its run, all "
                    "files in MLflow.",
                    "Validation recall is at least 0.75.",
                    "Validation ROC-AUC beats the champion.",
                ],
                "hub": {
                    "name": "FastAPI asks for a name, not a file",
                    "uri": "models:/weather-rainfall-classifier@champion",
                    "note": "It checks the alias on every prediction and reloads only when the "
                    "version changes. Rollback: point the alias back.",
                },
                "links": [
                    ["Promotion rule", "src/weather_mlops/models/comparison.py"],
                    ["Release check", "src/weather_mlops/models/release.py"],
                    ["Model loading", "src/weather_mlops/models/predict.py"],
                ],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["version-0", "version-1", "version-2", "version-3"],
                    ["version-1"],
                    ["version-3"],
                    ["point-0"],
                    ["point-1", "version-2"],
                    ["point-2"],
                    ["hub"],
                    ["hub"],
                    [],
                ],
                "notes": [
                    "[TITLE] Tracking tells us what each model is. The registry decides which "
                    "model our users get.",
                    "[VERSION LANE] Every training run registers a new version of one model, "
                    "weather-rainfall-classifier. A version never changes once it's written; only "
                    "the aliases move. They work like named bookmarks.",
                    "[@CHAMPION: BASELINE] The champion alias marks the version we serve. Our "
                    "first champion is the baseline: a twelve-trial random search on Kaggle data, "
                    "then retrained on all Kaggle rows. It could become champion directly only "
                    "because no champion existed yet. That shortcut works once.",
                    "[@CANDIDATE: NEWEST] Every new version automatically gets the candidate "
                    "alias, and waits for the gate.",
                    "[GATE (point 1)] Only the gate moves the champion, and all three conditions "
                    "must hold. First, the release must be complete: clean git commit, the version "
                    "really belongs to its run, and all its files are in MLflow. A model trained "
                    "from uncommitted code is refused.",
                    "[GATE (point 2) + REJECTED CANDIDATE] Second, validation recall of at least "
                    "zero point seven five, because a missed rainy day costs more than a false "
                    "alarm. Our latest candidate reached zero point six seven, so the gate "
                    "rejected it and the champion stayed.",
                    "[GATE (point 3)] Third, its validation ROC-AUC must beat the champion's. "
                    "Known limit: the champion's zero point eight nine was measured on days it had "
                    "already seen in training, and on an older window. That's a high bar. "
                    "Re-scoring the champion on the candidate's window is our next fix.",
                    "[FASTAPI BOX] The API never loads a file path. It asks MLflow for "
                    '"champion" by name. It checks the alias on every prediction and reloads '
                    "only when the version changes, so a promotion goes live without a restart. If "
                    "MLflow is down, it serves a local copy of the model.",
                    "[ROLLBACK] That also gives us rollback: we point the alias back at the "
                    "previous version, and the next prediction uses it.",
                    "[NEXT: THOMAS] So the gate decides which model our users get. Thomas will now "
                    "show how we serve it.",
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
                    "Every prediction is also logged to Supabase with its features, result, "
                    "latency and model. A day later we know the real weather, so we can "
                    "measure how good the model really was. More on that in monitoring.",
                    "The API checks the champion alias on each prediction, so a promotion "
                    "or rollback takes effect without a restart.",
                ],
            },
            {
                "id": "orchestration",
                "title": "Two DAGs: watch daily, retrain on demand",
                "layout": "flow",
                "stages": ["orchestration"],
                "figure": None,
                "lanes": [
                    {
                        "name": "weather_pipeline, daily at 18:00 Berlin",
                        "steps": ["Ingest", "Preprocess", "Add outcomes", "Evidently"],
                    },
                    {
                        "name": "weather_retrain, on Grafana alert",
                        "steps": ["Train", "Validate", "Compare"],
                    },
                ],
                "points": [
                    "Each task runs one of our Docker images.",
                    "We check the model every day, but train only when it got worse.",
                    "Training goes through the gateway, like any client.",
                ],
                "facts": [
                    ["DAGs", "2"],
                    ["Schedule", "daily, 18:00 Berlin"],
                    ["Retrain trigger", "Grafana webhook, max 1/day"],
                    ["Missed days", "caught up automatically"],
                ],
                "links": [
                    ["Airflow DAGs", "airflow/dags/weather_dag.py"],
                ],
                "notes": [
                    "About 1.5 minutes.",
                    "Two DAGs. weather_pipeline runs every day at 18:00 Berlin time, which "
                    "is 16:00 UTC now. It fetches new weather, cleans it, adds the real "
                    "outcome to past predictions, and runs the Evidently monitoring job.",
                    "weather_retrain has no schedule. It trains, validates and compares with "
                    "the champion. Grafana starts it through the Airflow REST API when the "
                    "real recall drops. For this the Airflow web server joins our Docker "
                    "network.",
                    "Why split them: checking is cheap, training is not. And retraining on "
                    "a fixed schedule would train even when nothing is wrong.",
                    "Each task is a DockerOperator that runs one of our images "
                    "and containers are removed after each task.",
                    "The train task calls POST /train through Nginx like any client, so the "
                    "stack must be up.",
                    "Airflow reaches Docker through a socket proxy that allows containers, "
                    "images and POST calls, and denies network management.",
                    "Each task retries up to 3 times, one minute apart.",
                    "If Airflow was down, it catches up every missed day, one run at a "
                    "time, and each run fetches the weather of its own day. For the days "
                    "that were already missing, we ran a one-time backfill.",
                    "A retrained model only becomes champion if it "
                    "passes the recall gate and beats the current champion.",
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
                    ["Tests", "229 (6 live gateway)"],
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
                    "The first line is our continuous integration. "
                    "CI runs on every push and pull request to master, in two jobs.",
                    "Job one: ruff lint and format check, then the unit tests.",
                    "Job two, in Docker: build all seven images, start the API and Nginx, "
                    "and run the live gateway tests against them.",
                    "The second line is our release. "
                    "Every time code lands on master, GitHub builds our ingestion, "
                    "preprocess and API images and uploads them to the GitHub Container "
                    "Registry. Any server can then download and start them without building "
                    "them itself.",
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
                        "name": "Live, every 15 s",
                        "steps": ["API", "/metrics", "Prometheus", "Grafana"],
                    },
                    {
                        "name": "Daily, once the real weather is known",
                        "steps": ["Evidently", "Pushgateway", "Recall alert", "weather_retrain"],
                    },
                ],
                "points": [
                    "The API reports traffic, errors, latency and every prediction.",
                    "Evidently checks drift and the real recall once a day.",
                    "Retraining starts only when the real recall drops, at most once a day.",
                ],
                "facts": [
                    ["Scrape interval", "15 s"],
                    ["Dashboards", "2"],
                    ["Alerts", "7 (3 API, 4 model)"],
                    ["Max retraining", "1/day"],
                ],
                "links": [
                    ["API metrics", "src/weather_mlops/api/metrics.py"],
                    ["Evidently job", "src/weather_mlops/monitoring/drift.py"],
                    ["Grafana", "docker/grafana/"],
                ],
                "notes": [
                    "About 1.5 minutes. Then hand over to Ziad.",
                    "Two kinds of monitoring: live from the API, and a daily batch check.",
                    "Live: the API measures itself. Every request is counted by endpoint and "
                    "status and is timed. On top, live predictions record station, rain or no "
                    "rain, probability and the model that answered; training records the "
                    "validation metrics.",
                    "All of it is on /metrics. Nginx blocks it from outside, Prometheus "
                    "reads it inside the Docker network every 15 seconds.",
                    "Once a day, when the real weather is known, an Evidently job runs two checks.",
                    "First, it checks whether the inputs have changed compared to the "
                    "training data. We call this feature drift. It only raises a warning, "
                    "because changed inputs do not prove the model got worse.",
                    "Second, it checks whether the model was actually right. As soon as at "
                    "least 30 predictions have a known outcome, it computes the real recall. "
                    "If recall is below 0.75, it requests a retrain.",
                    "Evidently is a batch job that ends after a few seconds, so Prometheus "
                    "cannot scrape it. It pushes its numbers to a Pushgateway instead, and "
                    "Prometheus reads them from there.",
                    "Grafana turns the retrain request into an alert and calls Airflow "
                    "through a webhook, at most once a day. That starts weather_retrain.",
                    "Seven alerts. API: down, more than 10 percent server errors, average "
                    "latency above 5 seconds. Model: retrain request, last training below "
                    "ROC-AUC 0.866 or recall 0.75, and an unusual rain rate.",
                    "Only the retrain request starts training. The others are warnings for "
                    "a person, for now visible in Grafana only.",
                    "Our dashboards and alerts are not clicked together by hand. "
                    "They are stored as files in Git, so anyone on the team can rebuild "
                    "the same monitoring with one command. ",
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
                    "3. The caption names the champion that answered, as Jonathan explained. "
                    "If it says rain_classifier.joblib, MLflow is not reachable and the API "
                    "fell back to its local copy.",
                    "4. MLflow on port 8080: experiment weather-rainfall-classifier, open "
                    "the latest run, show params, metrics and the dataset_sha256 and "
                    "git_commit tags. Then Models: the versions and the champion and "
                    "candidate aliases.",
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
