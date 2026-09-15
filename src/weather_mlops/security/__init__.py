"""Server-side secrets helpers. Never import this from Streamlit."""

from weather_mlops.security.vault import hydrate_runtime_secrets

__all__ = ["hydrate_runtime_secrets"]
