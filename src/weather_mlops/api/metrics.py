from prometheus_client import Counter, Gauge, Histogram

model_training_total = Counter(
    "model_training_total",
    "Number of times the model was trained.",
)
model_predictions_total = Counter(
    "model_predictions_total",
    "Number of model predictions.",
    ["location", "rain_tomorrow"],
)

model_probability_distribution = Histogram(
    "model_probability_distribution",
    "Probability distribution of predictions.",
    ["location"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
)

model_training_duration_seconds = Histogram(
    "model_training_duration_seconds",
    "Training duration of a model.",
    buckets=[5, 10, 15, 20, 30, 60, 120, 300],
)

model_info = Gauge(
    "model_info",
    "Currently served model",
    ["name", "version", "source"],
)

model_performance = Gauge(
    "model_performance",
    "Validation-set performance of the last trained model",
    ["metric"],
)
