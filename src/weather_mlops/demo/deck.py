"""build the html of each slide of the defense deck."""

import base64
from pathlib import Path

from weather_mlops.demo.presentation import (
    STAGES,
    TEAM,
    all_slides,
    source_url,
)


def make_rail(current_stages):
    html = '<ol class="rail">'
    for stage in STAGES:
        css = "stop"
        if stage["id"] in current_stages:
            css = css + " is-current"
        if not stage["built"]:
            css = css + " is-gap"
        html = html + f'<li class="{css}"><span>{stage["label"]}</span></li>'
    return html + "</ol>"


def make_links(slide):
    html = '<span class="code-links">'
    for label, path in slide["links"]:
        html = html + f'<a href="{source_url(path)}" target="_blank">{label}</a>'
    return html + "</span>"


def make_footer(slide, presenter, number, count):
    return (
        '<div class="slide-foot">'
        f"<span>{presenter}</span>"
        f"{make_links(slide)}"
        f"<span>{number} / {count}</span>"
        "</div>"
    )


def make_points(slide, tag="ul"):
    if len(slide["points"]) == 0:
        return ""
    html = f'<{tag} class="points">'
    for number, point in enumerate(slide["points"]):
        html = html + f'<li data-focus="point-{number}">{point}</li>'
    return html + f"</{tag}>"


def make_facts(slide):
    if len(slide.get("facts", [])) == 0:
        return ""
    html = '<table class="facts">'
    for number, (label, value) in enumerate(slide["facts"]):
        html = html + f'<tr data-focus="fact-{number}"><th>{label}</th><td>{value}</td></tr>'
    return html + "</table>"


def make_points_and_facts(slide):
    # points on the left, key figures on the right
    facts = make_facts(slide)
    if facts == "":
        return make_points(slide)
    return f'<div class="split">{make_points(slide)}{facts}</div>'


def make_step(step):
    # a step is its text, or a [tool, text] pair to show the tool logo first
    if isinstance(step, str):
        return f"<li>{step}</li>"
    return f"<li>{tool_logo(step[0])}{step[1]}</li>"


def name_logo(item):
    # lanes, rows and the registry can name the tool that runs them
    if "tool" not in item:
        return ""
    return tool_logo(item["tool"])


def make_lane(lane, number=0):
    html = (
        f'<div class="lane" data-focus="lane-{number}">'
        f'<p class="lane-name">{name_logo(lane)}{lane["name"]}</p><ol class="lane-steps">'
    )
    for step in lane["steps"]:
        html = html + make_step(step)
    return html + "</ol></div>"


def make_title(slide):
    return f'<h2 class="slide-title" data-focus="title">{slide["title"]}</h2>'


def make_cover(slide):
    team = ""
    for name in TEAM:
        team = team + f"<li>{name}</li>"
    return (
        '<div class="cover">'
        f'<h2 class="cover-title" data-focus="title">{slide["title"]}</h2>'
        '<p class="cover-lede" data-focus="lede">Next-day rain for 49 Australian weather stations, '
        "trained, versioned and served as an MLOps pipeline.</p>"
        f'<ul class="team" data-focus="team">{team}</ul>'
        '<p class="cover-meta">DataScientest MLOps defense, 15 October 2026</p>'
        "</div>"
    )


def make_split_bar(parts):
    # one bar cut into its shares, each share labelled with its name and percent
    html = '<div class="split-bar">'
    for name, share in parts:
        html = (
            html
            + f'<div class="split-part" style="flex: {share}">'
            + f'<span class="split-label">{name}: {share}%</span></div>'
        )
    return html + "</div>"


def make_bars(slide):
    # the facts as a bar chart from 0 to 1, with the 0.5 of a random guess marked
    html = '<div class="bars">'
    for number, (label, value) in enumerate(slide["facts"]):
        html = (
            html
            + f'<div class="bar-row" data-focus="fact-{number}">'
            + f'<span class="bar-label">{label}</span>'
            + f'<span class="bar-track"><span class="bar" style="width: {float(value) * 100}%">'
            + f'<span class="bar-value">{value}</span></span></span></div>'
        )
    return (
        html
        + '<p class="bar-guess" data-focus="chart-note">dashed line: 0.5, a random guess</p></div>'
    )


def make_hero(slide):
    value = slide["figure"][0]
    label = slide["figure"][1]
    chart = ""
    if "split" in slide:
        chart = make_split_bar(slide["split"])
    body = make_points_and_facts(slide)
    if slide.get("chart") == "bars":
        body = f'<div class="split">{make_points(slide)}{make_bars(slide)}</div>'
    return (
        make_title(slide)
        + f'<div class="hero" data-focus="hero"><p class="hero-value">{value}</p>'
        + f'<p class="hero-label">{label}</p>{chart}</div>'
        + body
    )


def make_architecture(slide):
    training = slide["lanes"][0]
    prediction = slide["lanes"][1]
    return (
        make_title(slide)
        + '<div class="arch">'
        + f'<div class="arch-train">{make_lane(training)}</div>'
        + '<div class="arch-hub"><p class="hub-name">MLflow registry</p>'
        + '<p class="hub-note">Training registers a candidate. '
        + "The champion alias marks the version we serve.</p></div>"
        + f'<div class="arch-predict">{make_lane(prediction, 1)}</div>'
        + '<div class="arch-stores">'
        + "<span>Supabase Postgres: observations and dataset catalog</span>"
        + "<span>DVC remote: dataset snapshots</span>"
        + "</div></div>"
    )


IMAGE_DIR = Path(__file__).with_name("images")

# brand colour of each tool, used to paint its logo
TOOL_COLORS = {
    "Kaggle": "#20BEFF",
    "Open-Meteo": "#FF8800",
    "Airflow": "#017CEE",
    "Supabase": "#3ECF8E",
    "DVC": "#945DD6",
    "Vault": "#10263A",
    "MLflow": "#0194E2",
    "XGBoost": "#189FDD",
    "Nginx": "#009639",
    "FastAPI": "#009688",
    "Streamlit": "#FF4B4B",
    "Prometheus": "#E6522C",
    "Grafana": "#F46800",
    "Evidently": "#ED0400",
    "Docker": "#2496ED",
    "GitHub Actions": "#2088FF",
    "GitHub": "#181717",
    "pytest": "#0A9EDC",
    "Ruff": "#261230",
}

# Logos from Simple Icons (simpleicons.org, CC0). Open-Meteo, Vault, XGBoost
# and Evidently have none there, and Kaggle's is a wordmark too small to read,
# so they get their first letter instead.
TOOL_LOGOS = {
    "Airflow": "apacheairflow.svg",
    "Supabase": "supabase.svg",
    "DVC": "dvc.svg",
    "MLflow": "mlflow.svg",
    "Nginx": "nginx.svg",
    "FastAPI": "fastapi.svg",
    "Streamlit": "streamlit.svg",
    "Prometheus": "prometheus.svg",
    "Grafana": "grafana.svg",
    "Docker": "docker.svg",
    "GitHub Actions": "githubactions.svg",
    "GitHub": "github.svg",
    "pytest": "pytest.svg",
    "Ruff": "ruff.svg",
}


def logo_uri(tool):
    svg = (IMAGE_DIR / "logos" / TOOL_LOGOS[tool]).read_text(encoding="utf-8")
    svg = svg.replace("<svg ", f'<svg fill="{TOOL_COLORS[tool]}" ', 1)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def tool_logo(tool):
    color = TOOL_COLORS.get(tool, "#5B6B78")
    if tool not in TOOL_LOGOS:
        return f'<span class="tool-logo tool-mark" style="background:{color}">{tool[0]}</span>'
    return f'<img class="tool-logo" alt="{tool}" src="{logo_uri(tool)}">'


def svg_logo(tool, x, y, size=18):
    # the same logo inside a diagram: an image, or the first letter on the brand colour
    if tool in TOOL_LOGOS:
        return f'<image href="{logo_uri(tool)}" x="{x}" y="{y}" width="{size}" height="{size}"/>'
    color = TOOL_COLORS.get(tool, "#5B6B78")
    return (
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{color}"/>'
        f'<text x="{x + size / 2}" y="{y + size / 2}" class="d-mark">{tool[0]}</text>'
    )


def svg_box(x, y, w, h, tool, text, sub=""):
    html = f'<rect class="d-node" x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/>'
    left = x + 10
    if tool != "":
        html = html + svg_logo(tool, x + 10, y + (h - 18) / 2)
        left = x + 36
    if sub == "":
        return html + f'<text class="d-text" x="{left}" y="{y + h / 2}">{text}</text>'
    return (
        html
        + f'<text class="d-text" x="{left}" y="{y + h / 2 - 9}">{text}</text>'
        + f'<text class="d-sub" x="{left}" y="{y + h / 2 + 10}">{sub}</text>'
    )


def svg_arrow(points, label="", label_x=0, label_y=0, anchor="middle", dashed=False):
    css = "d-edge is-dashed" if dashed else "d-edge"
    path = f'<polyline class="{css}" points="{points}" marker-end="url(#d-head)"/>'
    if label == "":
        return path
    return (
        path
        + f'<text class="d-label" x="{label_x}" y="{label_y}" text-anchor="{anchor}">{label}</text>'
    )


def svg_head():
    return (
        '<defs><marker id="d-head" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" class="d-head"/></marker></defs>'
    )


# The whole system, as in the wiki (Architecture, "Whole system"). Each group is
# [focus, name, x, y, width, height, boxes] and each box is [x, y, w, h, tool, text, sub].
SYSTEM_GROUPS = [
    [
        "zone-0",
        "Data sources",
        0,
        0,
        200,
        122,
        [
            [12, 30, 176, 36, "Kaggle", "Kaggle WeatherAUS", ""],
            [12, 74, 176, 36, "Open-Meteo", "Open-Meteo API", ""],
        ],
    ],
    [
        "zone-1",
        "Airflow",
        280,
        0,
        400,
        122,
        [
            [292, 30, 376, 36, "Airflow", "weather_pipeline, daily", ""],
            [292, 74, 376, 36, "Airflow", "weather_retrain, on alert", ""],
        ],
    ],
    [
        "zone-2",
        "Supabase",
        760,
        0,
        340,
        122,
        [
            [772, 30, 154, 36, "Supabase", "S3 storage", ""],
            [934, 30, 154, 36, "Vault", "Vault secrets", ""],
            [772, 74, 316, 36, "Supabase", "Postgres: data, predictions", ""],
        ],
    ],
    [
        "zone-3",
        "",
        400,
        156,
        180,
        40,
        [
            [400, 156, 180, 40, "MLflow", "MLflow registry", ""],
        ],
    ],
    [
        "zone-4",
        "Serving",
        420,
        230,
        320,
        110,
        [
            [432, 258, 128, 70, "FastAPI", "FastAPI", "auth, @champion"],
            [600, 258, 128, 70, "Nginx", "Nginx", "TLS, rate limit"],
            [800, 262, 170, 46, "Streamlit", "Streamlit, users", ""],
        ],
    ],
    [
        "zone-5",
        "Monitoring",
        0,
        230,
        330,
        110,
        [
            [12, 258, 148, 32, "Evidently", "Evidently", ""],
            [170, 258, 148, 32, "Grafana", "Grafana", ""],
            [12, 298, 148, 32, "Prometheus", "Pushgateway", ""],
            [170, 298, 148, 32, "Prometheus", "Prometheus", ""],
        ],
    ],
]

# [points, label, label x, label y, anchor]; the routes never cross
SYSTEM_EDGES = [
    ["200,61 280,61", "new days", 240, 53, "middle"],
    ["668,48 720,48 720,92 772,92", "outcomes, drift", 706, 40, "middle"],
    ["650,110 650,258", "POST /train", 658, 190, "start"],
    ["247,258 247,92 292,92", "recall alert", 255, 190, "start"],
    ["490,110 490,156", "moves @champion", 498, 142, "start"],
    ["490,258 490,196", "loads @champion", 498, 222, "start"],
    ["500,328 500,352 1060,352 1060,110", "log prediction", 900, 345, "middle"],
    ["318,314 432,314", "scrape", 375, 306, "middle"],
    ["600,293 560,293", "", 0, 0, "middle"],
    ["800,285 728,285", "HTTPS", 764, 277, "middle"],
]


def make_system_diagram():
    html = '<svg class="diagram" viewBox="-2 -2 1104 360" role="img">' + svg_head()
    for focus, name, x, y, w, h, boxes in SYSTEM_GROUPS:
        html = html + f'<g data-focus="{focus}">'
        if name != "":
            html = (
                html
                + f'<rect class="d-group" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
                + f'<text class="d-group-name" x="{x + 12}" y="{y + 17}">{name.upper()}</text>'
            )
        for box in boxes:
            html = html + svg_box(*box)
        html = html + "</g>"
    for points, label, label_x, label_y, anchor in SYSTEM_EDGES:
        html = html + svg_arrow(points, label, label_x, label_y, anchor)
    return html + "</svg>"


def make_system(slide):
    return (
        make_title(slide)
        + make_system_diagram()
        + f'<div class="lanes">{make_lane(slide["lanes"][0])}</div>'
        + f'<p class="system-caption" data-focus="caption">{slide["caption"]}</p>'
    )


def make_sequence_diagram(sequence):
    # one column per participant, one row per message, as in the wiki (Request path)
    count = len(sequence["participants"])
    step = 1100 / count
    centers = {}
    html = ""
    for number, (tool, name) in enumerate(sequence["participants"]):
        center = step * number + step / 2
        centers[name] = center
        html = html + svg_box(center - 80, 0, 160, 34, tool, name)
    height = 46 + 30 * len(sequence["messages"])
    lifelines = ""
    for center in centers.values():
        lifelines = lifelines + (
            f'<line class="d-life" x1="{center}" y1="34" x2="{center}" y2="{height}"/>'
        )
    y = 60
    for sender, receiver, text, kind in sequence["messages"]:
        start = centers[sender]
        if sender == receiver:
            points = (
                f"{start},{y - 6} {start + 28},{y - 6} {start + 28},{y + 6} {start + 4},{y + 6}"
            )
            html = html + svg_arrow(points, text, start + 36, y + 4, "start")
        else:
            end = centers[receiver]
            if end > start:
                end = end - 4
            else:
                end = end + 4
            html = html + svg_arrow(
                f"{start},{y} {end},{y}", text, (start + end) / 2, y - 6, "middle", kind == "reply"
            )
        y = y + 30
    return (
        f'<svg class="diagram is-sequence" data-focus="lane-0" viewBox="-2 -2 1104 {height}" '
        f'role="img">{svg_head()}{lifelines}{html}</svg>'
    )


def make_sequence(slide):
    return (
        make_title(slide) + make_sequence_diagram(slide["sequence"]) + make_points_and_facts(slide)
    )


def make_flow(slide):
    lanes = ""
    for number, lane in enumerate(slide["lanes"]):
        lanes = lanes + make_lane(lane, number)
    return make_title(slide) + f'<div class="lanes">{lanes}</div>' + make_points_and_facts(slide)


def make_card(card, focus):
    points = ""
    for point in card["points"]:
        points = points + f"<li>{point}</li>"
    return (
        f'<div class="zone" data-focus="{focus}">'
        f'<p class="zone-name">{card["name"]}</p>'
        f'<p class="zone-ask">{card["ask"]}</p>'
        f'<ul class="zone-points">{points}</ul>'
        "</div>"
    )


def make_tracking(slide):
    # one row of cards for what a training run records, one for a daily Evidently run
    rows = ""
    for row_number, row in enumerate(slide["rows"]):
        cards = ""
        for number, card in enumerate(row["cards"]):
            cards = cards + make_card(card, f"card-{row_number}-{number}")
        css = "zones run-zones"
        if row_number > 0:
            css = css + " is-monitoring"
        rows = (
            rows
            + f'<p class="lane-name" data-focus="row-{row_number}">'
            + f"{name_logo(row)}{row['name']}</p>"
            + f'<div class="{css}">{cards}</div>'
        )
    return make_title(slide) + rows


def make_version(step, number):
    css = f"is-{step['state']}"
    alias = ""
    if step["alias"] != "":
        alias = f'<span class="alias">{step["alias"]}</span>'
    note = ""
    if step["note"] != "":
        note = f'<span class="step-note">{step["note"]}</span>'
    return f'<li class="{css}" data-focus="version-{number}">{alias}{step["label"]}{note}</li>'


def make_registry(slide):
    steps = ""
    for number, step in enumerate(slide["versions"]["steps"]):
        steps = steps + make_version(step, number)
    hub = slide["hub"]
    return (
        make_title(slide)
        + '<div class="lanes"><div class="lane versions">'
        + f'<p class="lane-name">{slide["versions"]["name"]}</p>'
        + f'<ol class="lane-steps">{steps}</ol></div></div>'
        + '<div class="split">'
        + f'<div><p class="gate-name">{slide["gate"]}</p>{make_points(slide, tag="ol")}</div>'
        + '<div class="arch-hub" data-focus="hub">'
        + f'<p class="hub-name">{name_logo(hub)}{hub["name"]}</p>'
        + f'<p class="hub-note"><code>{hub["uri"]}</code></p>'
        + f'<p class="hub-note">{hub["note"]}</p>'
        + "</div></div>"
    )


# Photographs and official marks. Credits stay with the files:
# kubernetes.svg is the CNCF Kubernetes icon.
# jev.png is the TypeSafe mark from typesafe.ai.
# canary.jpg, forecast.jpg and shadow.jpg are Wikimedia Commons, CC0.
# threshold.jpg is Wikimedia Commons, File:Pressure Gauge.jpg,
# by In Transit, CC BY-SA 4.0.
CARD_IMAGES = {
    "kubernetes": ("kubernetes.svg", "Kubernetes", "logo", "center"),
    "models": ("jev.png", "Jev", "logo", "center"),
    "canary": ("canary.jpg", "Canary", "photo", "center"),
    "forecast": ("forecast.jpg", "Clouds", "photo", "center 28%"),
    "threshold": ("threshold.jpg", "Pressure gauge", "photo", "center 32%"),
    "rollback": ("shadow.jpg", "Shadows on a pavement", "photo", "center 70%"),
}


def image_data_uri(filename):
    path = IMAGE_DIR / filename
    if path.suffix == ".svg":
        mime = "image/svg+xml"
    elif path.suffix == ".png":
        mime = "image/png"
    else:
        mime = "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def card_image(key):
    filename, alt, kind, position = CARD_IMAGES[key]
    return (
        f'<img class="future-photo is-{kind}" alt="{alt}" '
        f'style="object-position: {position}" '
        f'src="{image_data_uri(filename)}">'
    )


def make_demo_hero(slide):
    return (
        '<div class="demo-hero">'
        '<img class="demo-hero-image" alt="Weather forecast dashboard illustration" '
        'data-asset="live_demo_hero.png" '
        f'src="{image_data_uri("live_demo_hero.png")}">'
        '<div class="demo-hero-overlay">'
        f'<h2 class="demo-hero-title" data-focus="title">{slide["title"]}</h2>'
        "</div></div>"
    )


def make_future(slide):
    cards = ""
    for number, card in enumerate(slide["cards"]):
        is_lead = number < 2
        card_class = "future-card is-lead" if is_lead else "future-card is-compact"
        index = f'<span class="future-index" aria-hidden="true">0{number + 1}</span>'
        visual = f"{index}{card_image(card['icon'])}" if is_lead else index
        cards = cards + (
            f'<article class="{card_class}" data-focus="card-{number}">'
            f"{visual}"
            f'<p class="future-name">{card["title"]}</p>'
            f'<p class="future-text">{card["text"]}</p>'
            "</article>"
        )
    return make_title(slide) + f'<div class="future-grid">{cards}</div>'


def make_closing(slide):
    return (
        '<div class="questions-closing">'
        '<div class="questions-copy">'
        '<p class="questions-kicker">Weather MLOps</p>'
        f'<h2 class="questions-title" data-focus="title">{slide["title"]}</h2>'
        '<p class="questions-thanks">Thank you</p>'
        "</div>"
        '<span class="questions-mark" aria-hidden="true">?</span>'
        "</div>"
    )


def make_body(slide):
    layout = slide["layout"]
    if layout == "cover":
        return make_cover(slide)
    elif layout == "hero":
        return make_hero(slide)
    elif layout == "architecture":
        return make_architecture(slide)
    elif layout == "system":
        return make_system(slide)
    elif layout == "flow":
        return make_flow(slide)
    elif layout == "sequence":
        return make_sequence(slide)
    elif layout == "tracking":
        return make_tracking(slide)
    elif layout == "registry":
        return make_registry(slide)
    elif layout == "demo-hero":
        return make_demo_hero(slide)
    elif layout == "script":
        return make_title(slide) + make_points(slide, tag="ol")
    elif layout == "future":
        return make_future(slide)
    elif layout == "closing":
        return make_closing(slide)
    else:
        return make_title(slide) + make_points_and_facts(slide)


def focus_style(slide, cue):
    # cue is the index of the speaker note being read, -1 when nothing is pointed at
    if cue < 0 or cue >= len(slide.get("focus", [])) or len(slide["focus"][cue]) == 0:
        return ""
    lit = ""
    # svg groups take no outline, so their boxes get the yellow border instead
    boxes = ""
    for target in slide["focus"][cue]:
        lit = lit + f', .slide [data-focus="{target}"]'
        boxes = boxes + f', .slide g[data-focus="{target}"] rect:first-child'
    return (
        "<style>.slide [data-focus], .slide .d-edge, .slide .d-label { opacity: 0.25; }"
        f"{lit[2:]} {{ opacity: 1; outline: 3px solid #F5B700; outline-offset: 4px; }}"
        f"{boxes[2:]} {{ stroke: #F5B700; stroke-width: 3px; }}</style>"
    )


def render_slide(index, cue=-1):
    slides = all_slides()
    section, slide = slides[index]
    rail = ""
    if len(slide["stages"]) > 0:
        rail = make_rail(slide["stages"])
    return (
        focus_style(slide, cue)
        + f'<section class="slide layout-{slide["layout"]}">'
        + rail
        + f'<div class="slide-body">{make_body(slide)}</div>'
        + make_footer(slide, section["presenter"], index + 1, len(slides))
        + "</section>"
    )


def slide_label(index):
    section, slide = all_slides()[index]
    return f"{index + 1}. {slide['title']}"
