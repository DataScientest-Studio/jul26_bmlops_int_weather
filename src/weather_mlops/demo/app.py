"""Defense deck and the two-screen demo. Run with: make streamlit"""

from __future__ import annotations

import os
import time
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
import streamlit as st

from weather_mlops.api.http import tls_verify
from weather_mlops.config.settings import settings
from weather_mlops.demo.deck import render_slide, slide_label
from weather_mlops.demo.observability import (
    DagTask,
    ModelTelemetry,
    load_dag_run_state,
    load_model_telemetry,
    load_task_states,
    trigger_dag_run,
)
from weather_mlops.demo.presentation import all_slides
from weather_mlops.demo.slides import SLIDES, slide_index

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
GRAFANA_EMBED_ENABLED = os.environ.get("GRAFANA_EMBED_ENABLED", "true").lower() == "true"
AIRFLOW_API_URL = os.environ.get("AIRFLOW_API_URL", "http://airflow-webserver:8080")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
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
    query.update({"panelId": str(panel_id), "from": "now-5m", "to": "now", "refresh": "5s"})
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
    st.caption(
        "Request rate and latency for the last 5 minutes. Make a forecast and watch "
        "the request appear; these panels refresh every 5 seconds."
    )
    _render_grafana_panels(GRAFANA_API_URL, (1, 3))


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


def _load_model_health_telemetry() -> ModelTelemetry | None:
    """Read the same metrics as Grafana without making a monitoring change."""

    try:
        return load_model_telemetry(PROMETHEUS_URL, timeout=0.75)
    except (requests.RequestException, ValueError):
        return None


def _model_health_replay_markup(
    telemetry: ModelTelemetry | None,
    *,
    revealed: bool,
) -> str:
    """Build the two-state outcome replay shown during the defense."""

    recall = telemetry.delayed_recall if telemetry else None
    roc_auc = telemetry.delayed_roc_auc if telemetry else None
    has_quality = recall is not None and roc_auc is not None
    retraining_requested = bool(
        telemetry and telemetry.retrain_requested and telemetry.retrain_requested >= 1
    )

    if revealed:
        outcome_title = "Outcomes reconciled"
        outcome_detail = "Next-day observations are now available"
        decision_title = "Retraining requested" if retraining_requested else "No retraining"
        decision_detail = (
            "The delayed quality gate failed"
            if retraining_requested
            else "The serving model stays unchanged"
        )
        decision_tone = "warning" if retraining_requested else "complete"
    else:
        outcome_title = "Waiting for next-day labels"
        outcome_detail = "Production quality is still unknown"
        decision_title = "Quality gate waiting"
        decision_detail = "No model decision yet"
        decision_tone = "pending"

    steps = (
        ("01", "Predictions stored", "Forecast window captured", "complete"),
        ("02", outcome_title, outcome_detail, "complete" if revealed else "pending"),
        ("03", decision_title, decision_detail, decision_tone),
    )
    rail = "".join(
        (
            f'<div class="health-replay__step health-replay__step--{tone}">'
            f'<span class="health-replay__number">{number}</span>'
            f"<strong>{escape(title)}</strong>"
            f"<small>{escape(detail)}</small>"
            "</div>"
            + (
                '<span class="health-replay__connector" aria-hidden="true"></span>'
                if number != "03"
                else ""
            )
        )
        for number, title, detail, tone in steps
    )

    result = ""
    if revealed:
        if has_quality:
            metrics = f"<span>Recall {recall:.3f}</span><span>ROC-AUC {roc_auc:.3f}</span>"
        else:
            metrics = "<span>Quality metrics unavailable</span>"
        drift_context = (
            f" Feature drift is {telemetry.drift_share:.0%}, but labelled performance "
            "makes the retraining decision."
            if telemetry and telemetry.drift_share is not None
            else " Labelled performance makes the retraining decision."
        )
        result = (
            f'<div class="health-replay__result health-replay__result--{decision_tone}">'
            f"<strong>{escape(decision_title)}</strong>"
            f'<div class="health-replay__metrics">{metrics}</div>'
            f"<p>{escape(drift_context.strip())}</p>"
            "</div>"
        )

    state_class = "is-revealed" if revealed else "is-waiting"
    return (
        f'<section class="health-replay {state_class}" aria-label="Next-day outcome replay">'
        f'<div class="health-replay__rail">{rail}</div>'
        f"{result}"
        "</section>"
    )


def _toggle_model_health_replay() -> None:
    """Switch the outcome replay before Streamlit redraws the page."""

    st.session_state.model_health_revealed = not bool(
        st.session_state.get("model_health_revealed", False)
    )


def _render_model_health() -> None:
    """Replay the arrival of delayed labels without starting a live workflow."""

    st.markdown(
        '<p class="lede">A forecast becomes measurable when tomorrow arrives. Reveal the '
        "next-day outcomes, then watch the quality gate decide.</p>",
        unsafe_allow_html=True,
    )
    telemetry = _load_model_health_telemetry()
    revealed = bool(st.session_state.get("model_health_revealed", False))
    st.markdown(
        _model_health_replay_markup(telemetry, revealed=revealed),
        unsafe_allow_html=True,
    )
    st.button(
        "Reset replay" if revealed else "Reveal next-day outcomes",
        type="primary",
        use_container_width=True,
        on_click=_toggle_model_health_replay,
    )

    if revealed:
        st.markdown("<h2>Grafana confirms the decision</h2>", unsafe_allow_html=True)
        st.caption(
            "These are the real delayed-quality and retraining panels. The replay does not "
            "start Airflow, train a model, or change the serving champion."
        )
        _render_grafana_panels(GRAFANA_MODEL_URL, (16, 14), height=250)


def _request_model_training(
    api_url: str,
    *,
    auth: tuple[str, str],
    post=requests.post,
) -> dict:
    """Train through the same authenticated API boundary used by other clients."""

    response = post(
        f"{api_url}/train",
        json={"track_run": False},
        auth=auth if all(auth) else None,
        timeout=120,
        verify=tls_verify(api_url),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("validation"), dict):
        raise ValueError("Training response did not contain validation metrics.")
    return payload


def _prepare_training_split():
    """Rebuild the processed split when DVC raw data is newer than that split."""

    from weather_mlops.config.settings import PROJECT_ROOT
    from weather_mlops.data.split_status import (
        ensure_fresh_split,
        incremental_pointer_md5,
        load_dvc_lock,
    )

    pointer = settings.raw_incremental_dir.with_suffix(".dvc")
    return ensure_fresh_split(
        lock=load_dvc_lock(PROJECT_ROOT / "dvc.lock"),
        incremental_md5=incremental_pointer_md5(pointer),
        processed_dir=settings.processed_data_dir,
    )


def _split_training_note(preparation) -> str:
    if preparation.rebuilt:
        return (
            "DVC raw data was newer than the split. Merged the raw files, "
            "rebuilt the split, then trained."
        )
    return "The processed split matches the newest DVC raw data. Trained on that split."


def _training_result_markup(
    payload: dict,
    *,
    elapsed_seconds: float,
    split_note: str = "",
) -> str:
    """Turn the returned validation metrics into one projection-friendly result."""

    train = payload["train"]
    validation = payload["validation"]
    metrics = (
        ("Validation recall", validation["recall"]),
        ("Validation ROC-AUC", validation["roc_auc"]),
        ("Validation accuracy", validation["accuracy"]),
    )
    metric_markup = "".join(
        '<article class="training-result__metric">'
        f"<span>{label}</span><strong>{float(value):.1%}</strong>"
        "</article>"
        for label, value in metrics
    )
    return (
        '<section class="training-result" aria-label="Model training result">'
        '<div class="training-result__summary"><span aria-hidden="true">&#10003;</span>'
        "<div><strong>Training complete</strong>"
        f"<small>POST /train finished in {elapsed_seconds:.1f} seconds</small></div></div>"
        f'<div class="training-result__metrics">{metric_markup}</div>'
        '<p class="training-result__comparison">Training ROC-AUC '
        f"{float(train['roc_auc']):.1%} &rarr; validation ROC-AUC "
        f"{float(validation['roc_auc']):.1%}</p>"
        + (f'<p class="training-result__comparison">{escape(split_note)}</p>' if split_note else "")
        + "</section>"
    )


def _render_model_training(api_url: str) -> None:
    """Run one real training call and show the returned validation evidence."""

    st.markdown(
        '<p class="lede">One API call fits the model and returns the metrics we use to '
        "judge it.</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Checks the DVC raw pointer. Rebuilds the split when it is stale, "
        "then POST /train → fit XGBoost → validate → return metrics."
    )

    action = st.empty()
    result_panel = st.empty()
    st.markdown(
        '<h2 class="section-title">API traffic while training runs</h2>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Requests per endpoint and average serving call time for the last 5 minutes. "
        "The training call appears in request traffic when it completes; its own duration "
        "is shown with the result."
    )
    _render_grafana_panels(GRAFANA_API_URL, (1, 3), height=190)

    result = st.session_state.get("training_result")
    if action.button("Train model now", type="primary", use_container_width=True):
        started = time.perf_counter()
        try:
            with st.spinner("Checking the DVC split, then training…"):
                preparation = _prepare_training_split()
                payload = _request_model_training(api_url, auth=API_AUTH)
            result = {
                "payload": payload,
                "elapsed_seconds": time.perf_counter() - started,
                "split_note": _split_training_note(preparation),
            }
            st.session_state["training_result"] = result
        except (requests.RequestException, OSError, KeyError, TypeError, ValueError) as exc:
            st.error(f"Training failed: {exc}")
            result = None

    if result:
        result_panel.markdown(
            _training_result_markup(
                result["payload"],
                elapsed_seconds=float(result["elapsed_seconds"]),
                split_note=str(result.get("split_note", "")),
            ),
            unsafe_allow_html=True,
        )


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

    if slide.id == "train":
        _render_model_training(DEFAULT_API_URL.rstrip("/"))
    elif slide.id == "live":
        _render_live(DEFAULT_API_URL.rstrip("/"))
    else:
        st.caption("This screen has no live panel.")


def _menu_navigation_state(menu: str) -> dict[str, int]:
    """Choose the correct continuation point when changing presentation surfaces."""

    if menu == "Demo":
        return {"slide": slide_index("live")}
    live_demo_index = next(
        index for index, (_, slide) in enumerate(all_slides()) if slide["id"] == "demo"
    )
    return {"deck": live_demo_index, "cue": -1}


def _apply_menu_navigation(state) -> None:
    menu = str(state["menu"])
    for key, value in _menu_navigation_state(menu).items():
        state[key] = value
    if menu == "Demo":
        state.pop("training_result", None)


def _sync_menu_navigation() -> None:
    _apply_menu_navigation(st.session_state)


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
    menu = st.segmented_control(
        "Menu",
        MENU,
        default=MENU[0],
        key="menu",
        on_change=_sync_menu_navigation,
    )
    if menu == "Demo":
        _render_demo()
    else:
        _render_presentation()


if __name__ == "__main__":
    main()
