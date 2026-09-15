"""Five-minute defense deck. Run with: make streamlit"""

from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st

from weather_mlops.api.http import tls_verify
from weather_mlops.config.settings import settings
from weather_mlops.demo.slides import SLIDES

STYLES = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
DEFAULT_API_URL = os.environ.get("DEMO_API_URL", "https://nginx")
API_AUTH = (
    os.environ.get("API_AUTH_USER") or "",
    os.environ.get("API_AUTH_PASSWORD") or "",
)


def _inject_css() -> None:
    st.markdown(f"<style>{STYLES}</style>", unsafe_allow_html=True)


def _clamp(index: int) -> int:
    return max(0, min(index, len(SLIDES) - 1))


def _bootstrap_slide() -> None:
    if "slide" in st.session_state:
        return
    raw = st.query_params.get("slide")
    try:
        st.session_state.slide = _clamp(int(raw)) if raw is not None else 0
    except ValueError:
        st.session_state.slide = 0


def _set_slide(index: int) -> None:
    st.session_state.slide = _clamp(index)


def _render_architecture() -> None:
    st.markdown(
        """
        <div class="pipe">
          <div class="node">Open-Meteo</div>
          <div class="node">Ingest</div>
          <div class="node">Preprocess</div>
          <div class="node">FastAPI</div>
          <div class="node">Nginx</div>
        </div>
        <p class="lede">Train is a POST to the API, not a container that starts training.</p>
        """,
        unsafe_allow_html=True,
    )


def _render_stores() -> None:
    st.markdown(
        """
        <div class="store-grid">
          <div>
            <h2>Storage</h2>
            <p><code>s3://weather-mlops-dvc</code><br>raw and processed snapshots</p>
            <p><code>s3://weather-mlops-mlflow</code><br>model artifacts</p>
          </div>
          <div>
            <h2>Postgres</h2>
            <p><code>dataset_versions</code> catalog<br>
            <code>weather_observations</code> rows<br>
            <code>model_versions</code> / <code>predictions</code></p>
            <p>Secrets sit in Vault, not in this app.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_live(api_url: str) -> None:
    st.caption(f"Talking to {api_url}")
    try:
        health = requests.get(
            f"{api_url}/health",
            timeout=3,
            verify=tls_verify(api_url),
        )
        health.raise_for_status()
        body = health.json()
        st.success(body.get("status", "API up"))
    except requests.RequestException as exc:
        st.error("Gateway is down. From the repo root run `make api` or `make up`.")
        st.caption(str(exc))
        return

    locations_path = settings.weather_locations_path
    locations = ["Sydney"]
    if locations_path.exists():
        locations = [
            line.split(",")[0]
            for line in locations_path.read_text(encoding="utf-8").splitlines()[1:]
            if line.strip()
        ]
    sydney_index = locations.index("Sydney") if "Sydney" in locations else 0
    location = st.selectbox("Station", locations, index=sydney_index)
    if st.button("Predict from live weather", type="primary"):
        try:
            response = requests.post(
                f"{api_url}/predict/live_data",
                json={"location": location},
                auth=API_AUTH if all(API_AUTH) else None,
                timeout=40,
                verify=tls_verify(api_url),
            )
            _show_prediction(response)
        except requests.RequestException as exc:
            st.error(str(exc))


def _show_prediction(response: requests.Response) -> None:
    if response.status_code == 401:
        st.warning(
            "API returned 401. Restart `make streamlit` so it hydrates basic auth from Vault."
        )
        return
    if response.status_code == 503:
        st.warning("API basic auth is not configured on the server.")
        return
    if not response.ok:
        st.error(response.text)
        return
    payload = response.json()
    rain = "Rain" if payload.get("rain_tomorrow") else "No rain"
    probability = float(payload.get("probability", 0))
    st.markdown(
        f'<div class="forecast"><strong>{rain}</strong><span>{probability:.0%}</span></div>',
        unsafe_allow_html=True,
    )
    model = payload.get("model") or {}
    if model.get("alias") and model.get("version"):
        st.caption(f"Served by {model['name']}@{model['alias']} v{model['version']}")
    elif model.get("source"):
        st.caption(f"Served by {model['source']}")


def main() -> None:
    st.set_page_config(
        page_title="Weather MLOps",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_css()
    _bootstrap_slide()
    st.radio(
        "Screen",
        options=list(range(len(SLIDES))),
        format_func=lambda i: SLIDES[i].kicker,
        key="slide",
        horizontal=True,
        label_visibility="collapsed",
    )
    current = _clamp(int(st.session_state.slide))
    slide = SLIDES[current]
    st.markdown(
        f'<p class="kicker">{current + 1} / {len(SLIDES)}</p><h1>{slide.title}</h1>',
        unsafe_allow_html=True,
    )

    if slide.id == "architecture":
        _render_architecture()
    elif slide.id == "stores":
        _render_stores()
    else:
        _render_live(DEFAULT_API_URL.rstrip("/"))

    if slide.notes:
        items = "".join(f"<li>{note}</li>" for note in slide.notes)
        st.markdown(f'<ul class="talk-notes">{items}</ul>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
