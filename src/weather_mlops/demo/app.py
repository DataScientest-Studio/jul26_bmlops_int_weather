"""Defense deck and the two-screen demo. Run with: make streamlit"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
import streamlit as st

from weather_mlops.api.http import tls_verify
from weather_mlops.config.settings import settings
from weather_mlops.demo.deck import render_slide, slide_label
from weather_mlops.demo.observability import (
    PIPELINE_TASKS,
    RETRAIN_TASKS,
    DagTask,
    load_dag_run_state,
    load_task_states,
    trigger_dag_run,
)
from weather_mlops.demo.presentation import all_slides
from weather_mlops.demo.slides import SLIDES

MENU = ("Presentations", "Demo")
STYLES = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
DECK_STYLES = Path(__file__).with_name("deck.css").read_text(encoding="utf-8")
DECK_WIDTH = ".block-container { max-width: 1280px; }"
NOTES_STYLES = (
    ".speaker-notes { font-family: 'IBM Plex Sans', sans-serif; font-size: 1.35rem;"
    " line-height: 1.55; color: #E8EEF2; max-width: 60ch; }"
    " .speaker-notes li { margin-bottom: 0.8rem; }"
    " .note-cue { display: block; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em;"
    " color: #F5B700; }"
    " .speaker-notes li.is-active { border-left: 4px solid #F5B700; padding-left: 0.6rem; }"
)
# the point buttons only exist for the keyboard, the audience does not see them
HIDDEN_BUTTONS = ".st-key-cue_back, .st-key-cue_next { display: none; }"
# keys: n or right arrow = next, p or left arrow = previous, s = speaker notes,
# j or down arrow = highlight the next point, k or up arrow = the previous point
DECK_SHORTCUTS = """
<script>
if (!window.__deckShortcuts) {
  window.__deckShortcuts = true;
  const clickButton = (label) => {
    const button = [...document.querySelectorAll("button")]
      .find((element) => element.innerText.trim() === label);
    if (button && !button.disabled) button.click();
  };
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const fields = ["INPUT", "TEXTAREA", "SELECT"];
    const typing = target.isContentEditable || fields.includes(target.tagName);
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === "n" || key === "arrowright") clickButton("Next");
    if (key === "p" || key === "arrowleft") clickButton("Previous");
    if (key === "j" || key === "arrowdown") {
      event.preventDefault();
      clickButton("Next point");
    }
    if (key === "k" || key === "arrowup") {
      event.preventDefault();
      clickButton("Previous point");
    }
    if (key === "s") {
      window.open(window.location.pathname + "?view=notes", "weather-speaker-notes");
    }
  });
}
</script>
"""
DEFAULT_API_URL = os.environ.get("DEMO_API_URL", "https://nginx")
GRAFANA_API_URL = os.environ.get(
    "GRAFANA_API_URL", "http://127.0.0.1:3000/d/weather-api/weather-api"
)
GRAFANA_MODEL_URL = os.environ.get(
    "GRAFANA_MODEL_URL", "http://127.0.0.1:3000/d/weather-model/weather-model"
)
MLFLOW_URL = os.environ.get("MLFLOW_URL", "http://127.0.0.1:8082")
GRAFANA_EMBED_ENABLED = os.environ.get("GRAFANA_EMBED_ENABLED", "true").lower() == "true"
AIRFLOW_URL = os.environ.get("AIRFLOW_URL", "http://127.0.0.1:8081/dags/weather_retrain/grid")
AIRFLOW_API_URL = os.environ.get("AIRFLOW_API_URL", "http://airflow-webserver:8080")
API_AUTH = (
    os.environ.get("API_AUTH_USER") or "",
    os.environ.get("API_AUTH_PASSWORD") or "",
)
AIRFLOW_AUTH = (
    os.environ.get("AIRFLOW_API_USER") or "",
    os.environ.get("AIRFLOW_API_PASSWORD") or "",
)
_TASK_STATE_CLASS = {
    "success": "success",
    "running": "running",
    "queued": "queued",
    "scheduled": "queued",
    "failed": "failed",
    "upstream_failed": "failed",
}


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


def _render_live(api_url: str) -> None:
    try:
        health = requests.get(
            f"{api_url}/health",
            timeout=3,
            verify=tls_verify(api_url),
        )
        health.raise_for_status()
        health.json()
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
    selector_column, action_column = st.columns((3, 1.5), gap="medium")
    with selector_column:
        location = st.selectbox("Station", locations, index=sydney_index)
    with action_column:
        st.markdown('<div class="prediction-action-spacer"></div>', unsafe_allow_html=True)
        predict = st.button("Predict live weather", type="primary", use_container_width=True)
    if predict:
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
    _render_prediction_result()
    _render_live_activity()


def _grafana_embed_url(dashboard_url: str) -> str:
    """Use Grafana's compact chrome while preserving configured query parameters."""

    parsed = urlsplit(dashboard_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"kiosk": "", "theme": "dark"})
    return urlunsplit(parsed._replace(query=urlencode(query)))


def _grafana_panel_url(dashboard_url: str, panel_id: int) -> str:
    """Return a kiosk-mode Grafana solo panel for a short live demo window."""

    parsed = urlsplit(_grafana_embed_url(dashboard_url))
    if not parsed.path.startswith("/d/"):
        raise ValueError("Grafana dashboard URLs must use the /d/ route")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"panelId": str(panel_id), "from": "now-5m", "to": "now"})
    return urlunsplit(
        parsed._replace(
            path=parsed.path.replace("/d/", "/d-solo/", 1),
            query=urlencode(query),
        )
    )


def _render_grafana_panels(
    dashboard_url: str, panel_ids: tuple[int, ...], *, height: int = 220
) -> None:
    """Embed a small set of real Grafana panels, not a Streamlit reimplementation."""

    if not GRAFANA_EMBED_ENABLED:
        st.info("Grafana embedding is disabled for this environment.")
        return
    columns = st.columns(len(panel_ids), gap="small")
    for column, panel_id in zip(columns, panel_ids, strict=True):
        with column:
            st.iframe(_grafana_panel_url(dashboard_url, panel_id), height=height)


def _render_live_activity() -> None:
    st.markdown("<h2>Live API activity</h2>", unsafe_allow_html=True)
    st.caption("These are the live Grafana panels; make a forecast and watch the request appear.")
    _render_grafana_panels(GRAFANA_API_URL, (1, 2, 3))


def _dag_markup(tasks: tuple[DagTask, ...], states: dict[str, str]) -> str:
    """Draw the ordered Airflow tasks as a connected, status-coloured DAG."""

    flow = []
    for index, task in enumerate(tasks):
        state = states.get(task.task_id, "")
        css = _TASK_STATE_CLASS.get(state, "pending")
        flow.append(
            '<div class="dag__node '
            f'{css}"><span class="dag__marker">{index + 1:02d}</span>'
            f'<span class="dag__label">{escape(task.label)}</span></div>'
        )
        if index < len(tasks) - 1:
            flow.append(f'<span class="dag__edge {css}" aria-hidden="true"></span>')
    return f'<div class="dag" role="img" aria-label="Airflow task graph">{"".join(flow)}</div>'


def _task_states(dag_id: str, run_id: str | None = None) -> dict[str, str]:
    if not all(AIRFLOW_AUTH):
        return {}
    return load_task_states(AIRFLOW_API_URL, dag_id, run_id=run_id, auth=AIRFLOW_AUTH)


def _run_state(dag_id: str, run_id: str) -> str | None:
    if not all(AIRFLOW_AUTH):
        return None
    return load_dag_run_state(AIRFLOW_API_URL, dag_id, run_id, auth=AIRFLOW_AUTH)


def _trigger_dag(
    dag_id: str,
    session_key: str,
    *,
    conf: dict[str, str],
) -> None:
    """Start a named Airflow run and keep its id stable while the UI refreshes."""

    try:
        with st.spinner("Starting the Airflow run"):
            st.session_state[session_key] = trigger_dag_run(
                AIRFLOW_API_URL,
                dag_id,
                conf=conf,
                auth=AIRFLOW_AUTH,
            )
    except requests.RequestException as exc:
        st.error("Airflow did not accept the requested run.")
        st.caption(str(exc))


@st.fragment(run_every=15)
def _render_airflow(
    dag_id: str,
    tasks: tuple[DagTask, ...],
    run_id: str | None,
) -> None:
    """Show one chosen Airflow run so scheduled runs cannot replace the demo state."""

    task_states: dict[str, str] = {}
    airflow_error = None
    run_state = None
    try:
        if run_id:
            run_state = _run_state(dag_id, run_id)
            task_states = _task_states(dag_id, run_id)
    except (requests.RequestException, ValueError) as exc:
        airflow_error = str(exc)

    st.markdown(_dag_markup(tasks, task_states), unsafe_allow_html=True)
    if airflow_error:
        st.caption("Airflow is not reachable from this app yet. The graph is the task order.")
        st.caption(airflow_error)
    elif not all(AIRFLOW_AUTH):
        st.caption("Airflow credentials are not in this app, so the boxes stay uncolored.")
    elif not run_id:
        st.caption("Start this workflow to see its individual task states here.")
    else:
        st.caption(
            f"Airflow run {run_id} is {run_state}. Teal is success, gold is running, "
            "coral is failed. This refreshes every 15 seconds."
        )


def _render_model_health() -> None:
    """Present the real data lineage, monitoring evidence, and guarded candidate lifecycle."""

    st.markdown(
        '<p class="lede">Refresh the prepared weather batch, preserve its immutable dataset '
        "version, inspect drift evidence, then train a candidate only when you choose to.</p>",
        unsafe_allow_html=True,
    )
    configured = all(AIRFLOW_AUTH)
    if not configured:
        st.warning("Restart `make streamlit` so Airflow credentials are hydrated from Vault.")

    st.markdown("<h2>1. Refresh and version the data</h2>", unsafe_allow_html=True)
    st.caption(
        "Airflow ingests and merges the prepared batch, preprocesses the splits, uploads immutable "
        "raw and processed snapshots to Supabase Storage, and records their hashes in "
        "dataset_versions."
    )
    if st.button(
        "Refresh prepared data",
        type="primary",
        use_container_width=True,
        disabled=not configured,
    ):
        _trigger_dag(
            "weather_pipeline",
            "pipeline_run_id",
            conf={"triggered_by": "streamlit-demo", "purpose": "prepared-data-refresh"},
        )
        st.session_state.pop("retrain_run_id", None)
    pipeline_run_id = st.session_state.get("pipeline_run_id")
    _render_airflow("weather_pipeline", PIPELINE_TASKS, pipeline_run_id)

    st.markdown("<h2>2. Inspect live model-health evidence</h2>", unsafe_allow_html=True)
    st.caption(
        "These real Grafana trends show Evidently's drift share, delayed-outcome quality, and "
        "whether the performance gate has requested retraining."
    )
    _render_grafana_panels(GRAFANA_MODEL_URL, (15, 16, 14), height=250)

    st.markdown("<h2>3. Train and compare a candidate</h2>", unsafe_allow_html=True)
    pipeline_state = None
    if pipeline_run_id and configured:
        try:
            pipeline_state = _run_state("weather_pipeline", pipeline_run_id)
        except (requests.RequestException, ValueError) as exc:
            st.caption(f"Unable to confirm the data-refresh state: {exc}")
    refresh_is_running = pipeline_state in {"queued", "running", "scheduled"}
    can_retrain = configured
    if pipeline_state == "success":
        st.caption(
            "This candidate will use the dataset version created by the completed refresh above."
        )
    elif refresh_is_running:
        st.caption(
            "The data refresh is still running. You can train now on the last completed "
            "registered version, or wait to use the refreshed version."
        )
    elif not pipeline_run_id:
        st.caption(
            "No refresh is selected, so this runs deliberately on the latest registered dataset "
            "version. No-drift runs do not block a manual retrain."
        )
    else:
        st.caption(
            "The selected refresh did not complete. A manual retrain uses the latest registered "
            "dataset version instead."
        )
    if st.button(
        "Train candidate and compare",
        use_container_width=True,
        disabled=not can_retrain,
    ):
        _trigger_dag(
            "weather_retrain",
            "retrain_run_id",
            conf={
                "triggered_by": "streamlit-demo",
                "source_pipeline_run_id": str(pipeline_run_id or "latest_registered"),
            },
        )
    _render_airflow("weather_retrain", RETRAIN_TASKS, st.session_state.get("retrain_run_id"))
    st.caption(
        "Training logs the candidate run and model in MLflow. Compare evaluates the same immutable "
        "dataset version and promotes it only when the validation guards beat the champion."
    )
    st.caption(
        "Automatic retraining remains separate: Grafana only calls Airflow after delayed "
        "performance fails its gate, not from feature drift alone."
    )
    st.link_button("Open MLflow model registry", MLFLOW_URL, use_container_width=True)


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
    st.session_state.live_prediction = payload


def _render_prediction_result() -> None:
    """Keep the latest live result visible while the presenter talks."""

    payload = st.session_state.get("live_prediction")
    if not payload:
        st.markdown(
            '<section class="forecast forecast--ready"><span class="forecast__icon">☁️</span>'
            "<strong>Ready for a forecast</strong>"
            "<span>Choose a station, then use the live weather feed.</span></section>",
            unsafe_allow_html=True,
        )
        return

    rain = bool(payload.get("rain_tomorrow"))
    probability = float(payload.get("probability", 0))
    outcome = "YES" if rain else "NO"
    label = "Rain is expected tomorrow" if rain else "No rain is expected tomorrow"
    icon = "🌧️" if rain else "☀️"
    variant = "rain" if rain else "dry"
    st.markdown(
        f'<section class="forecast forecast--{variant}"><span class="forecast__icon">{icon}</span>'
        f'<strong>{outcome}</strong><span class="forecast__label">{label}</span>'
        f'<span class="forecast__probability">{probability:.0%}</span>'
        '<span class="forecast__detail">chance of rain tomorrow</span></section>',
        unsafe_allow_html=True,
    )


@st.cache_resource
def _live_position():
    # shared by all browser windows, so the notes window follows the deck
    return {"index": 0, "cue": -1}


def _step_deck(step):
    last = len(all_slides()) - 1
    new_index = st.session_state.deck + step
    if new_index < 0:
        new_index = 0
    if new_index > last:
        new_index = last
    st.session_state.deck = new_index
    st.session_state.cue = -1


def _reset_cue():
    st.session_state.cue = -1


def _step_cue(step):
    section, slide = all_slides()[st.session_state.deck]
    last = len(slide["notes"]) - 1
    new_cue = st.session_state.cue + step
    if new_cue < -1:
        new_cue = -1
    if new_cue > last:
        new_cue = last
    st.session_state.cue = new_cue


def _render_presentation():
    st.markdown(f"<style>{DECK_STYLES}{DECK_WIDTH}{HIDDEN_BUTTONS}</style>", unsafe_allow_html=True)
    st.html(DECK_SHORTCUTS, unsafe_allow_javascript=True)
    slides = all_slides()
    if "deck" not in st.session_state:
        st.session_state.deck = 0
    if "cue" not in st.session_state:
        st.session_state.cue = -1
    index = st.session_state.deck
    cue = st.session_state.cue
    _live_position()["index"] = index
    _live_position()["cue"] = cue
    st.markdown(render_slide(index, cue), unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1], vertical_alignment="center")
    col1.button("Previous", on_click=_step_deck, args=(-1,), disabled=index == 0)
    col2.selectbox(
        "Go to slide",
        options=list(range(len(slides))),
        format_func=slide_label,
        key="deck",
        on_change=_reset_cue,
        label_visibility="collapsed",
    )
    col3.button("Next", on_click=_step_deck, args=(1,), disabled=index == len(slides) - 1)
    st.button("Previous point", key="cue_back", on_click=_step_cue, args=(-1,))
    st.button("Next point", key="cue_next", on_click=_step_cue, args=(1,))


@st.fragment(run_every=1)
def _follow_deck():
    slides = all_slides()
    index = _live_position()["index"]
    cue = _live_position()["cue"]
    section, slide = slides[index]
    st.markdown(
        f'<p class="kicker">Slide {index + 1} of {len(slides)}, '
        f"{section['presenter']} ({section['minutes']} min section)</p>"
        f"<h1>{slide['title']}</h1>",
        unsafe_allow_html=True,
    )
    notes = ""
    for number, note in enumerate(slide["notes"]):
        # "[DATA SOURCES] text": the label names the part of the slide to point at
        if note.startswith("["):
            label, note = note[1:].split("] ", 1)
            note = f'<span class="note-cue">{label}</span>{note}'
        css = ""
        if number == cue:
            css = ' class="is-active"'
        notes = notes + f"<li{css}>{note}</li>"
    st.markdown(f'<ul class="speaker-notes">{notes}</ul>', unsafe_allow_html=True)
    if index + 1 < len(slides):
        next_section, next_slide = slides[index + 1]
        text = f"Next: {next_slide['title']}."
        if next_section["presenter"] != section["presenter"]:
            text = text + f" Hand over to {next_section['presenter']}."
        st.caption(text)
    st.caption(
        "Keys on the deck window: N or → next, P or ← previous, "
        "J or ↓ highlight the next point, K or ↑ the previous one, S reopens these notes."
    )


def _render_notes():
    # open ?view=notes in a window you do not share
    st.markdown(f"<style>{NOTES_STYLES}</style>", unsafe_allow_html=True)
    _follow_deck()


def _render_demo() -> None:
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
    if slide.id != "live":
        st.markdown(f"<h1>{slide.title}</h1>", unsafe_allow_html=True)

    if slide.id == "health":
        _render_model_health()
    elif slide.id == "live":
        _render_live(DEFAULT_API_URL.rstrip("/"))
    else:
        st.caption("This screen has no live panel.")


def main() -> None:
    st.set_page_config(
        page_title="Weather MLOps",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_css()
    if st.query_params.get("view") == "notes":
        _render_notes()
        return
    menu = st.segmented_control("Menu", MENU, default=MENU[0], key="menu")
    if menu == "Demo":
        _render_demo()
    else:
        _render_presentation()


if __name__ == "__main__":
    main()
