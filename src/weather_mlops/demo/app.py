"""Defense deck and the three-screen demo. Run with: make streamlit"""

from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st

from weather_mlops.api.http import tls_verify
from weather_mlops.config.settings import settings
from weather_mlops.demo.deck import render_slide, slide_label
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
)
# keys: n or right arrow = next, p or left arrow = previous, s = speaker notes
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
    if (key === "s") {
      window.open(window.location.pathname + "?view=notes", "weather-speaker-notes");
    }
  });
}
</script>
"""
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


@st.cache_resource
def _live_position():
    # shared by all browser windows, so the notes window follows the deck
    return {"index": 0}


def _step_deck(step):
    last = len(all_slides()) - 1
    new_index = st.session_state.deck + step
    if new_index < 0:
        new_index = 0
    if new_index > last:
        new_index = last
    st.session_state.deck = new_index


def _render_presentation():
    st.markdown(f"<style>{DECK_STYLES}{DECK_WIDTH}</style>", unsafe_allow_html=True)
    st.html(DECK_SHORTCUTS, unsafe_allow_javascript=True)
    slides = all_slides()
    if "deck" not in st.session_state:
        st.session_state.deck = 0
    index = st.session_state.deck
    _live_position()["index"] = index
    st.markdown(render_slide(index), unsafe_allow_html=True)
    section, slide = slides[index]
    if slide["id"] == "demo":
        _render_live(DEFAULT_API_URL.rstrip("/"))

    col1, col2, col3 = st.columns([1, 4, 1], vertical_alignment="center")
    col1.button("Previous", on_click=_step_deck, args=(-1,), disabled=index == 0)
    col2.selectbox(
        "Go to slide",
        options=list(range(len(slides))),
        format_func=slide_label,
        key="deck",
        label_visibility="collapsed",
    )
    col3.button("Next", on_click=_step_deck, args=(1,), disabled=index == len(slides) - 1)


@st.fragment(run_every=1)
def _follow_deck():
    slides = all_slides()
    index = _live_position()["index"]
    section, slide = slides[index]
    st.markdown(
        f'<p class="kicker">Slide {index + 1} of {len(slides)}, '
        f"{section['presenter']} ({section['minutes']} min section)</p>"
        f"<h1>{slide['title']}</h1>",
        unsafe_allow_html=True,
    )
    notes = ""
    for note in slide["notes"]:
        notes = notes + f"<li>{note}</li>"
    st.markdown(f'<ul class="speaker-notes">{notes}</ul>', unsafe_allow_html=True)
    if index + 1 < len(slides):
        next_section, next_slide = slides[index + 1]
        text = f"Next: {next_slide['title']}."
        if next_section["presenter"] != section["presenter"]:
            text = text + f" Hand over to {next_section['presenter']}."
        st.caption(text)
    st.caption("Keys on the deck window: N or → next, P or ← previous, S reopens these notes.")


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
