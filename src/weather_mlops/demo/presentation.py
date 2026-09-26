"""content of the defense deck. speaker notes are only shown in the notes window."""

REPO_URL = "https://github.com/DataScientest-Studio/jul26_bmlops_int_weather"
# links point to this commit, so the jury sees the code we present
COMMIT = "4f7419c5f8a78635e19d3e22844c76d416b8316e"

STAGES = [
    {"id": "data", "label": "Data", "built": True},
    {"id": "versioning", "label": "Versioning", "built": True},
    {"id": "tracking", "label": "Tracking", "built": True},
    {"id": "registry", "label": "Registry", "built": True},
    {"id": "serving", "label": "Serving", "built": True},
    {"id": "security", "label": "Security", "built": True},
    {"id": "orchestration", "label": "Orchestration", "built": True},
    {"id": "cicd", "label": "CI/CD", "built": True},
    {"id": "monitoring", "label": "Monitoring", "built": False},
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
        "title": "Problem, architecture and gateway",
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
                "notes": [
                    "About 20 seconds.",
                    "We are Gabriel, Jonathan, Thomas and Ziad.",
                    "Our question: will it rain tomorrow at a given Australian weather "
                    "station? The model is the small part. The talk is about the machinery "
                    "around it: data, versioning, tracking, serving, security, "
                    "orchestration and CI/CD.",
                    "I cover the problem, the architecture and the gateway. Then Jonathan "
                    "on data and model, Thomas on serving and operations, and Ziad with the "
                    "live demo.",
                ],
            },
            {
                "id": "problem",
                "title": "Why we do not grade on accuracy",
                "layout": "hero",
                "stages": [],
                "figure": ["77.1%", "test accuracy of a model that always answers no"],
                "lanes": [],
                "points": [
                    "Target: rain tomorrow, one model for 49 stations.",
                    "Promotion metric: ROC-AUC.",
                    "Guardrail: recall of at least 0.75.",
                ],
                "facts": [
                    ["Test rows", "24,808"],
                    ["Rainy days", "5,689 (22.9%)"],
                    ["Caught by always no", "0"],
                    ["Caught by our model", "4,334 (76.2%)"],
                ],
                "links": [
                    ["Evaluation", "src/weather_mlops/models/evaluation.py"],
                    ["Settings", "src/weather_mlops/config/settings.py"],
                ],
                "notes": [
                    "About 1 minute.",
                    "Input: the station name plus 20 measurements from one day: "
                    "temperature, rainfall, humidity, pressure, wind, cloud, sunshine. "
                    "Output: rain tomorrow, yes or no, with a probability.",
                    "Only 22.9% of test days are rainy, so answering no every time already "
                    "scores 77.1%.",
                    "Our model scores 79.8% accuracy. The gap looks tiny, which is why "
                    "accuracy is the wrong metric here.",
                    "ROC-AUC scores the ranking over all thresholds; always answering no "
                    "gets only 0.5.",
                    "Recall guardrail: a missed rainy day costs more than a false alarm.",
                ],
            },
            {
                "id": "architecture",
                "title": "Two pipelines, one registry",
                "layout": "architecture",
                "stages": [],
                "figure": None,
                "lanes": [
                    {
                        "name": "Training, scheduled daily",
                        "steps": ["Airflow", "Ingest", "Preprocess", "Train"],
                    },
                    {"name": "Prediction, on request", "steps": ["Client", "Nginx", "FastAPI"]},
                ],
                "points": [],
                "links": [
                    ["Compose file", "docker-compose.yml"],
                    ["Airflow DAG", "airflow/dags/weather_dag.py"],
                ],
                "notes": [
                    "About 1.5 minutes.",
                    "Training writes a candidate to the MLflow registry. Prediction loads "
                    "the version holding the champion alias, or the local model file when "
                    "there is none.",
                    "Seven Dockerfiles, one per service: ingestion, preprocess, API, Nginx, "
                    "MLflow, the Streamlit demo and the test runner.",
                    "Ingestion and preprocess are jobs that exit; the API stays up. Compose "
                    "starts preprocess only after ingestion exits with code 0.",
                    "The API mounts the data read-only. It writes only models and reports, "
                    "because POST /train saves the new model there.",
                    "Team decision on 10 Sep: no container trains on startup. Training is a "
                    "POST /train call, so a restart never retrains silently.",
                    "Also decided on 10 Sep: one requirements file per image, to keep images lean.",
                    "Postgres on Supabase holds observations and the dataset catalog; the "
                    "DVC remote holds dataset snapshots.",
                ],
            },
            {
                "id": "gateway",
                "title": "One door in: the Nginx gateway",
                "layout": "flow",
                "stages": ["security"],
                "figure": None,
                "lanes": [
                    {
                        "name": "Every request from outside",
                        "steps": ["HTTPS on 443", "Rate limit per IP", "Basic auth", "FastAPI"],
                    },
                ],
                "points": [
                    "Only Nginx listens publicly. The API port is not published.",
                    "10 requests/s per IP, 1/s on training. Above that: 429.",
                    "TLS 1.2 or 1.3 only. Plain HTTP is redirected.",
                ],
                "facts": [
                    ["Public ports", "80, 443"],
                    ["API limit", "10 req/s per IP, burst 20"],
                    ["/train limit", "1 req/s per IP, burst 3"],
                    ["Max request body", "2 MB"],
                ],
                "links": [
                    ["Nginx config", "docker/nginx/nginx.conf"],
                    ["Auth", "src/weather_mlops/api/main.py"],
                    ["Live tests", "tests/integration/test_nginx_live.py"],
                ],
                "notes": [
                    "About 2 minutes. Then hand over to Jonathan.",
                    "Why a gateway: the API container has no published port. Nginx is the "
                    "only service on ports 80 and 443. MLflow and Streamlit bind to "
                    "127.0.0.1 only, so they are not reachable from the network.",
                    "Encryption: port 80 answers with a 301 redirect to HTTPS. Only TLS 1.2 "
                    "and 1.3 are accepted. HSTS tells browsers to stay on HTTPS for a year.",
                    "Flooding and brute force: Nginx limits each client IP to 10 requests "
                    "per second with a burst of 20, and /train to 1 per second with a burst "
                    "of 3, because training is expensive. Excess requests get 429 before "
                    "they reach Python.",
                    "Slow or oversized requests: bodies above 2 MB are refused, and Nginx "
                    "drops a client that goes silent for 15 seconds while sending headers "
                    "or body. That limits attacks that hold connections open.",
                    "Authentication: predict, live predict and train need HTTP Basic auth. "
                    "The API compares credentials in constant time, so response time does "
                    "not leak how much of a guess was right. Credentials come from Supabase "
                    "Vault at startup, never from the repo.",
                    "Less exposure: server_tokens off hides the Nginx version. Headers "
                    "block framing, MIME sniffing and referrer leaks.",
                    "Proof: live tests in CI check the redirect, TLS version, HSTS, 401 "
                    "without credentials, and a burst that must return 429.",
                    "Limitations. The certificate is self-signed for localhost, so our own "
                    "clients skip verification for local hosts only; production needs a CA "
                    "certificate.",
                    "Limits are per IP: they do not stop an attack from many IPs, and "
                    "behind another proxy all clients would share one IP, since no real-IP "
                    "setting is configured.",
                    "One shared Basic auth user, with no lockout: at 10 requests per second "
                    "one IP can still try 864,000 passwords a day. Rotating a Vault secret "
                    "needs an API restart.",
                    "/health has no login and no rate limit, and /docs and /openapi.json "
                    "are public, rate-limited, and show the API schema.",
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
                        ],
                    },
                ],
                "points": [
                    "Four endpoints: health, predict, live predict, train.",
                    "Out-of-range values and unknown stations are rejected.",
                    "Every answer names the model that produced it.",
                ],
                "facts": [
                    ["Endpoints", "4"],
                    ["Rainfall bounds", "0 to 500 mm"],
                    ["Live weather timeout", "30 s"],
                    ["Stations accepted", "49"],
                ],
                "links": [
                    ["API", "src/weather_mlops/api/main.py"],
                    ["Model loading", "src/weather_mlops/models/predict.py"],
                ],
                "notes": [
                    "About 1.5 minutes.",
                    "At startup the API loads its Basic-auth credentials from Supabase Vault.",
                    "Four endpoints. Health is open. Predict takes one day of measurements. "
                    "Live predict takes only a station name. Train retrains.",
                    "Inputs have bounds, for example rainfall between 0 and 500 mm. Unknown "
                    "stations are rejected with a suggestion for likely typos.",
                    "Live predict looks up the station's coordinates, fetches today's "
                    "weather from Open-Meteo with a 30-second timeout, and returns 502 if "
                    "the data is not available yet.",
                    "Train accepts five hyperparameters with bounds, for example depth up "
                    "to 15. It returns the training metrics and clears the prediction "
                    "cache.",
                    "Every answer includes the model that served it: name, alias, version, source.",
                    "The API checks the champion alias on each prediction, so a promotion "
                    "or rollback takes effect without a restart.",
                    "No champion exists yet, so the API serves the local model file. Say "
                    "this before the demo rather than being caught by it.",
                    "Gabriel covered the gateway in front of this; do not repeat it.",
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
                        "name": "Scheduled daily at 22:00",
                        "steps": ["Ingest", "Preprocess", "Train", "Validate", "Compare"],
                    },
                ],
                "points": [
                    "Each task runs one of our Docker images.",
                    "Training goes through the gateway, like any client.",
                    "Three retries per task.",
                ],
                "facts": [
                    ["Schedule", "daily, 22:00"],
                    ["Tasks", "5"],
                    ["Retries", "3, one minute apart"],
                    ["Verified run", "25 Sep: 5 of 5 in 44 s"],
                ],
                "links": [
                    ["Airflow DAG", "airflow/dags/weather_dag.py"],
                ],
                "notes": [
                    "About 2 minutes.",
                    "Airflow 2.8.1 runs as its own Compose stack: a Postgres 13 metadata "
                    "database, the web server, the scheduler, and a LocalExecutor.",
                    "The DAG weather_pipeline has five tasks: ingestion, preprocess, train, "
                    "evaluation, compare. It is scheduled daily at 22:00, from 1 Sep 2026, "
                    "without catch-up.",
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
                    "Verified 25 Sep 2026: the scheduled run for the 24 Sep 22:00 UTC slot "
                    "succeeded. All five tasks passed on the first try, in 44 seconds.",
                    "That run fetched 49 new rows, retrained, and compare rejected the "
                    "model on recall (0.726), the same decision as make pipeline.",
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
                    ["Tests", "122 (6 live gateway)"],
                    ["Images built", "7"],
                    ["Images on ghcr.io", "3"],
                ],
                "links": [
                    ["CI workflow", ".github/workflows/ci.yml"],
                    ["Release workflow", ".github/workflows/release.yml"],
                    ["Tests", "tests/"],
                ],
                "notes": [
                    "About 1.5 minutes. Then hand over to Ziad.",
                    "CI runs on pushes and pull requests to master, in two jobs.",
                    "Job one, on the runner: install from the locked uv environment, ruff "
                    "lint, ruff format check, then pytest without the live gateway tests.",
                    "Job two, in Docker: build every image across the four Compose "
                    "profiles, start the API and Nginx, and run the test image against "
                    "https://nginx, so the live gateway tests run too.",
                    "The live tests check the HTTP redirect, the TLS version, HSTS, 401 "
                    "without credentials, and a burst that must return 429.",
                    "The committed suite collects 122 tests, 6 of them live gateway tests.",
                    "Release, on push to master: log in to ghcr.io with the workflow token "
                    "and push the ingestion, preprocess and API images, approved by Nicolas "
                    "on 10 Sep.",
                    "If asked: release runs in parallel with CI and tags only latest. "
                    "Gating it on CI and tagging by commit is the next step.",
                ],
            },
        ],
    },
    {
        "presenter": "Ziad",
        "title": "Demo and limits",
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
                    "About 4 minutes, leaving 1 minute for limits.",
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
                "id": "limits",
                "title": "What we have not built yet",
                "layout": "limits",
                "stages": ["monitoring"],
                "figure": None,
                "lanes": [],
                "points": [
                    "Drift detection with Evidently.",
                    "Storing each prediction with its features.",
                    "Metrics and alerts with Prometheus and Grafana.",
                ],
                "facts": [
                    ["Tables ready", "predictions, drift_reports"],
                    ["Lifecycle stages built", "8 of 9"],
                ],
                "links": [
                    ["Schema", "supabase/schema.sql"],
                ],
                "notes": [
                    "About 1 minute.",
                    "Monitoring is the one stage of the lifecycle we have not built.",
                    "The schema is ready. predictions stores each request's features, "
                    "class, probability, latency and model version. drift_reports stores "
                    "whether drift was detected, the metrics, the report path and the "
                    "MLflow run.",
                    "Next steps in order: log every prediction, run Evidently in the DAG to "
                    "compare recent features with the training data, then alert and retrain "
                    "on drift.",
                    "Prometheus and Grafana would add API latency and error alerts.",
                    "Close with: eight of nine lifecycle stages are in place.",
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
