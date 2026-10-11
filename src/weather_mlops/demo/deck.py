"""build the html of each slide of the defense deck."""

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


def make_lane(lane, number=0):
    html = (
        f'<div class="lane" data-focus="lane-{number}">'
        f'<p class="lane-name">{lane["name"]}</p><ol class="lane-steps">'
    )
    for step in lane["steps"]:
        html = html + f"<li>{step}</li>"
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


def make_hero(slide):
    value = slide["figure"][0]
    label = slide["figure"][1]
    return (
        make_title(slide)
        + f'<div class="hero" data-focus="hero"><p class="hero-value">{value}</p>'
        + f'<p class="hero-label">{label}</p></div>'
        + make_points_and_facts(slide)
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


# brand colour of each tool, shown as a dot before its name
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
}


def make_zone(zone, number):
    tools = ""
    for tool in zone["tools"]:
        color = TOOL_COLORS.get(tool, "#5B6B78")
        tools = tools + f'<li><span class="tool-dot" style="background:{color}"></span>{tool}</li>'
    points = ""
    for point in zone["points"]:
        points = points + f"<li>{point}</li>"
    return (
        f'<div class="zone" data-focus="zone-{number}">'
        f'<p class="zone-name">{zone["name"]}</p>'
        f'<ul class="zone-tools">{tools}</ul>'
        f'<ul class="zone-points">{points}</ul>'
        "</div>"
    )


def make_system(slide):
    zones = ""
    for number, zone in enumerate(slide["zones"]):
        zones = zones + make_zone(zone, number)
    return (
        make_title(slide)
        + f'<div class="zones">{zones}</div>'
        + f'<div class="lanes">{make_lane(slide["lanes"][0])}</div>'
        + f'<p class="system-caption" data-focus="caption">{slide["caption"]}</p>'
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
            + f'<p class="lane-name" data-focus="row-{row_number}">{row["name"]}</p>'
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
        + f'<p class="hub-name">{hub["name"]}</p>'
        + f'<p class="hub-note"><code>{hub["uri"]}</code></p>'
        + f'<p class="hub-note">{hub["note"]}</p>'
        + "</div></div>"
    )


def make_closing(slide):
    return (
        '<div class="cover">'
        f'<h2 class="cover-title">{slide["title"]}</h2>'
        '<p class="cover-lede">All nine lifecycle stages are in place.</p>'
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
    elif layout == "tracking":
        return make_tracking(slide)
    elif layout == "registry":
        return make_registry(slide)
    elif layout == "script":
        return make_title(slide) + make_points(slide, tag="ol")
    elif layout == "closing":
        return make_closing(slide)
    else:
        return make_title(slide) + make_points_and_facts(slide)


def focus_style(slide, cue):
    # cue is the index of the speaker note being read, -1 when nothing is pointed at
    if cue < 0 or cue >= len(slide.get("focus", [])) or len(slide["focus"][cue]) == 0:
        return ""
    lit = ""
    for target in slide["focus"][cue]:
        lit = lit + f', .slide [data-focus="{target}"]'
    return (
        "<style>.slide [data-focus] { opacity: 0.25; }"
        f"{lit[2:]} {{ opacity: 1; outline: 3px solid #F5B700; outline-offset: 4px; }}</style>"
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
