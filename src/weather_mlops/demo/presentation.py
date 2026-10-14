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
                    "Good morning. We're Gabriel, Jonathan, Thomas and Ziad.",
                    "We started with a simple question: will it rain tomorrow at a weather "
                    "station in Australia?",
                    "Training a model for that is the easy part, so today we want to show you "
                    "everything around it.",
                    "I'll cover the architecture, the problem, drift and our gateway. After me, "
                    "Jonathan and Thomas take you through the rest, and Ziad ends with a live "
                    "demo.",
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
                            ["Supabase", "Prediction logged"],
                            ["Open-Meteo", "Real outcome arrives"],
                            ["Evidently", "Drift and recall check"],
                            ["Grafana", "Grafana alert"],
                            ["Airflow", "Airflow retrains"],
                            ["MLflow", "Gate moves @champion"],
                        ],
                    },
                ],
                "caption": "Docker Compose: 11 services — 8 built from our 7 Dockerfiles "
                "(api and baseline share one), 3 public images. "
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
                    "Let's start with the big picture. The whole system runs in Docker Compose.",
                    "It all begins with data: Kaggle's Australian weather history, plus new days "
                    "from the Open-Meteo API, in the same format.",
                    "To keep this running on its own, Airflow runs two pipelines: a daily one, "
                    "and one that retrains the model.",
                    "Every day, the new data, the real outcomes and the drift results go into "
                    "Supabase Postgres. Dataset snapshots go to storage, and our secrets stay in "
                    "Supabase Vault.",
                    "When we retrain, MLflow keeps track of every model, and a new one only "
                    "becomes champion if it passes our quality gate (a recall of at least 0.75 on"
                    " validation, and a better ROC AUC than the current champion).",
                    "Users reach the champion through Nginx and FastAPI, and every prediction "
                    "they get is saved in Postgres.",
                    "Once it's live, we keep an eye on it: Prometheus and Grafana watch the API, "
                    "and Evidently checks for drift every day.",
                    "And that closes the loop. When the real weather comes in and recall falls "
                    "below 0.75, Grafana triggers a retrain.",
                    "So why do we need all this? Because the problem is harder than it looks.",
                ],
            },
            {
                "id": "problem",
                "title": "Class imbalance: why accuracy is the wrong metric",
                "layout": "hero",
                "stages": [],
                "figure": ["77.1%", "test accuracy of the majority-class baseline (always no)"],
                # share of test days, from the facts below
                "split": [["No rain", 77.1], ["Rain", 22.9]],
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
                    "For each prediction, we take one station on one day, with 20 weather "
                    "measurements, and return the chance of rain tomorrow.",
                    "The tricky part is that only 23% of days are rainy. In other words, a "
                    "model that always says no is 77% accurate, and never catches a rainy day.",
                    "So we don't judge on accuracy. We pick models on ROC AUC, and ours scores "
                    "0.87.",
                    "Recall also has to stay above 0.75, because missing a rainy day hurts more"
                    " than a false alarm.",
                ],
            },
            {
                "id": "drift",
                "title": "Distribution shift: Australia to Singapore",
                "layout": "hero",
                "stages": [],
                "figure": ["0.87 to 0.70", "ROC-AUC, Australian test set vs all Singapore days"],
                # the facts are ROC-AUC scores, drawn as bars
                "chart": "bars",
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
                    ["fact-0", "fact-1", "fact-2", "fact-3", "chart-note"],
                    ["point-2"],
                ],
                "notes": [
                    "Then we asked: what happens when the weather changes? So we took the model"
                    " to Singapore, which is much rainier but has the same data format.",
                    "It rains there on 83% of days, and Evidently flags all five features we "
                    "monitor.",
                    "And the model suffers: ROC AUC drops from 0.87 to 0.70.",
                    "Retraining on Singapore data helps, from 0.64 up to 0.70.",
                    "But it only wins back part of the loss, and that's why we keep monitoring.",
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
                            ["Nginx", "TLS 1.2/1.3 on 443"],
                            ["Nginx", "limit_req per IP"],
                            ["FastAPI", "Basic auth (FastAPI)"],
                            ["FastAPI", "FastAPI"],
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
                    "Now let's talk about security. Nginx is our only entry point, and every "
                    "other service can only be reached from inside the machine.",
                    "Every request passes three checks. Nginx encrypts it with TLS, then limits "
                    "each IP to 10 requests per second, or 1 on train, because training is "
                    "expensive. Then FastAPI asks for a login.",
                    "Six live tests in our CI check these layers.",
                    "And with that, I'll hand over to Jonathan, who'll show you how we version "
                    "the data and the model.",
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
                            ["Kaggle", "Kaggle + Open-Meteo"],
                            "Rolling split",
                            "sha256 manifest",
                            ["DVC", "DVC snapshot"],
                            ["MLflow", "MLflow run"],
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
                "title": "Experiment tracking: every model and every day",
                "layout": "tracking",
                "stages": ["tracking"],
                "figure": None,
                "lanes": [],
                # champion metrics: the baseline's settings on 90 unseen validation days, from
                # the 12-trial search run, before the refit on all Kaggle rows
                "rows": [
                    {
                        "name": "Each training run, from make train, POST /train or Airflow",
                        "tool": "MLflow",
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
                        "tool": "Evidently",
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
                    "tool": "MLflow",
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
                "layout": "sequence",
                "stages": ["serving"],
                "figure": None,
                "lanes": [],
                # one prediction, as in the wiki (Architecture, "Request path")
                "sequence": {
                    "participants": [
                        ["Streamlit", "Client"],
                        ["Nginx", "Nginx"],
                        ["FastAPI", "FastAPI"],
                        ["MLflow", "MLflow"],
                        ["Supabase", "Postgres"],
                    ],
                    # [from, to, message, "call" or "reply"]
                    "messages": [
                        ["Client", "Nginx", "POST /predict, HTTPS", "call"],
                        ["Nginx", "Nginx", "TLS, rate limit per IP", "call"],
                        ["Nginx", "FastAPI", "proxy", "call"],
                        ["FastAPI", "FastAPI", "Basic auth, validate input", "call"],
                        ["FastAPI", "MLflow", "which version is @champion?", "call"],
                        ["MLflow", "FastAPI", "champion version", "reply"],
                        ["FastAPI", "FastAPI", "reload only if the version changed", "call"],
                        ["FastAPI", "Postgres", "log prediction", "call"],
                        ["FastAPI", "Client", "rain probability + model version", "reply"],
                    ],
                },
                "points": [
                    "Five public endpoints, plus /metrics for Prometheus only.",
                    "Out-of-range values and unknown stations are rejected.",
                    "Every answer names the model that produced it.",
                ],
                "facts": [
                    ["Endpoints", "5 + /metrics"],
                    ["Rainfall bounds", "0 to 500 mm"],
                    ["Stations accepted", "49"],
                ],
                "links": [
                    ["API", "src/weather_mlops/api/main.py"],
                    ["Model loading", "src/weather_mlops/models/predict.py"],
                ],
                "notes": [
                    "About 1 minute 15 seconds.",
                    "Let's follow one prediction through the system.",
                    "The request comes in over HTTPS to Nginx, which handles the encryption and "
                    "the rate limit, and then hands it to FastAPI.",
                    "FastAPI checks the login and the input. For example, rainfall has to be "
                    "between 0 and 500 mm, and an unknown station is rejected, with a suggestion "
                    "if it looks like a typo.",
                    "Then it asks MLflow which version is the champion. It only reloads the model"
                    " when that version changes, so a promotion or a rollback goes live without a"
                    " restart. And if MLflow is down, it falls back to a local copy of the model.",
                    "Every prediction is saved in Postgres. A day later we know the real weather,"
                    " so we can check how good the model really was.",
                    "And the answer comes back with the chance of rain and the exact model that "
                    "produced it.",
                    "Besides predict, there are four other public endpoints: health, live "
                    "predict, which fetches today's weather from Open-Meteo, train, and the drift"
                    " simulator we use in the demo.",
                    "There's also /metrics, but that one is only for Prometheus. From outside, "
                    "Nginx returns a 404.",
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
                        "tool": "Airflow",
                        "steps": [
                            ["Open-Meteo", "Ingest"],
                            "Preprocess",
                            ["Supabase", "Add outcomes"],
                            ["Evidently", "Evidently"],
                        ],
                    },
                    {
                        "name": "weather_retrain, on Grafana alert",
                        "tool": "Airflow",
                        "steps": [
                            ["XGBoost", "Train"],
                            "Validate",
                            ["MLflow", "Compare"],
                        ],
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
                        "tool": "GitHub Actions",
                        "steps": [
                            ["Ruff", "Lint"],
                            ["pytest", "Unit tests"],
                            ["Docker", "Build images"],
                            ["Nginx", "Live gateway tests"],
                        ],
                    },
                    {
                        "name": "Release, on master",
                        "tool": "GitHub Actions",
                        "steps": [
                            ["Docker", "Build"],
                            ["GitHub", "Push to ghcr.io"],
                        ],
                    },
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
                        "tool": "Prometheus",
                        "steps": [
                            ["FastAPI", "API"],
                            "/metrics",
                            ["Prometheus", "Prometheus"],
                            ["Grafana", "Grafana"],
                        ],
                    },
                    {
                        "name": "Daily, once the real weather is known",
                        "tool": "Evidently",
                        "steps": [
                            ["Evidently", "Evidently"],
                            ["Prometheus", "Pushgateway"],
                            ["Grafana", "Recall alert"],
                            ["Airflow", "weather_retrain"],
                        ],
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
        "minutes": 7,
        "slides": [
            {
                "id": "demo",
                "title": "Live demo",
                "layout": "demo-hero",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [],
                "links": [
                    ["Streamlit app", "src/weather_mlops/demo/app.py"],
                ],
                "notes": [
                    "[0:00-0:20] About 5 minutes. I will now leave the slides and show two "
                    "real API actions: one prediction and one model-training run.",
                    "[0:20-1:35] Pick Sydney in Live prediction and click Predict from live "
                    "weather. Point first to rain or no rain, then to the probability. This "
                    "is the result a user receives from the serving API.",
                    "[1:35-2:10] Keep the embedded Grafana panels in view just long enough to "
                    "show that the API request happened and that its latency was recorded. "
                    "Do not tour the full dashboard.",
                    "[2:10-2:30] Switch to Model training. This screen keeps the story to one "
                    "action, two compact operational signals, and one result.",
                    "[2:30-3:35] Click Train model now. While the live POST /train request "
                    "runs, point to request rate and average serving call time. Then let the "
                    "training result become the payoff.",
                    "[3:35-4:25] When Training complete appears, point to validation Recall, "
                    "ROC-AUC, Accuracy, and the elapsed time. These values came back from the "
                    "training endpoint; they are not prepared slide numbers.",
                    "[4:25-5:00] Return to Presentations. It resumes on this Live demo slide; "
                    "press Next once for Future work. If a service is unavailable, say so once "
                    "and continue rather than troubleshooting on stage.",
                ],
            },
            {
                "id": "next-steps",
                "title": "Future work",
                "layout": "future",
                "stages": [],
                "figure": None,
                "lanes": [],
                "points": [],
                "cards": [
                    {
                        "icon": "kubernetes",
                        "title": "Scale on Kubernetes",
                        "text": (
                            "Run resilient API replicas and increase capacity as live traffic "
                            "grows."
                        ),
                    },
                    {
                        "icon": "models",
                        "title": "Jev and transformers",
                        "text": (
                            "Compare Jev and transformer models with the current XGBoost baseline."
                        ),
                    },
                    {
                        "icon": "canary",
                        "title": "Canary release",
                        "text": (
                            "Route ten percent of live traffic to the candidate. "
                            "Promote it only when real recall holds."
                        ),
                    },
                    {
                        "icon": "rollback",
                        "title": "Shadow evaluation and rollback",
                        "text": (
                            "Score candidates beside the champion. Monitor real recall and restore "
                            "the previous champion when it drops."
                        ),
                    },
                ],
                "links": [],
                # elements lit on the slide while each note is read
                "focus": [
                    ["title"],
                    ["card-0"],
                    ["card-1"],
                    ["card-2"],
                    ["card-3"],
                    [],
                ],
                "notes": [
                    "[TITLE] About 1 minute. To close, we built a solid MLOps base for weather "
                    "prediction. These four additions would make it more useful beyond a "
                    "laptop demo.",
                    "[1. KUBERNETES] First, move beyond local Docker. Kubernetes can restart a "
                    "failed API replica and add capacity as traffic grows, making the system more "
                    "robust at production scale.",
                    "[2. JEV AND TRANSFORMERS] Second, XGBoost is a strong baseline, but we should "
                    "compare it with Jev, other System One approaches, and transformer models. "
                    "These alternatives can add inference cost, so we need to test whether "
                    "improved forecast quality earns that cost.",
                    "[3. CANARY] Third, when newer data leads to a retrained or fine-tuned "
                    "candidate, we should not replace the production model in one step. A canary "
                    "release sends "
                    "a small fraction of real traffic to it and checks its observed quality.",
                    "[4. SHADOW EVALUATION AND ROLLBACK] In parallel, shadow evaluation scores a "
                    "candidate without returning its prediction to users. Continuous monitoring "
                    "gives us evidence before promotion; if quality falls, the champion alias "
                    "moves back to the previous version.",
                    "[NEXT: QUESTIONS] These are the steps that turn a solid base into a scalable, "
                    "safe production system. Thank you. We are happy to take your questions.",
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
                    "[QUESTIONS] About 15 seconds. Thank you. We built a solid MLOps base for "
                    "weather prediction. "
                    "The next steps are scaling, model evaluation, and safe monitored rollouts. "
                    "We are happy to take your questions.",
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
