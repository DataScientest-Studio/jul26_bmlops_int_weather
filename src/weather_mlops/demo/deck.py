"""build the html of each slide of the defense deck."""

from weather_mlops.demo.presentation import (
    METRICS,
    RECALL_GATE,
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
    for point in slide["points"]:
        html = html + f"<li>{point}</li>"
    return html + f"</{tag}>"


def make_lane(lane):
    html = f'<div class="lane"><p class="lane-name">{lane["name"]}</p><ol class="lane-steps">'
    for step in lane["steps"]:
        html = html + f"<li>{step}</li>"
    return html + "</ol></div>"


def make_title(slide):
    return f'<h2 class="slide-title">{slide["title"]}</h2>'


def make_cover(slide):
    team = ""
    for name in TEAM:
        team = team + f"<li>{name}</li>"
    return (
        '<div class="cover">'
        f'<h2 class="cover-title">{slide["title"]}</h2>'
        '<p class="cover-lede">Next-day rain for 49 Australian weather stations, '
        "trained, versioned and served as an MLOps pipeline.</p>"
        f'<ul class="team">{team}</ul>'
        '<p class="cover-meta">DataScientest MLOps defense, 15 October 2026</p>'
        "</div>"
    )


def make_hero(slide):
    value = slide["figure"][0]
    label = slide["figure"][1]
    return (
        make_title(slide)
        + f'<div class="hero"><p class="hero-value">{value}</p>'
        + f'<p class="hero-label">{label}</p></div>'
        + make_points(slide)
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
        + f'<div class="arch-predict">{make_lane(prediction)}</div>'
        + '<div class="arch-stores">'
        + "<span>Supabase Postgres: observations and dataset catalog</span>"
        + "<span>DVC remote: dataset snapshots</span>"
        + "</div></div>"
    )


def make_flow(slide):
    lanes = ""
    for lane in slide["lanes"]:
        lanes = lanes + make_lane(lane)
    return make_title(slide) + f'<div class="lanes">{lanes}</div>' + make_points(slide)


def make_bar(split, value, gate):
    css = "bar"
    if gate is not None and value < gate:
        css = "bar is-below"
    tick = ""
    if gate is not None:
        tick = f'<span class="gate" style="left:{gate * 100:.1f}%"></span>'
    return (
        '<div class="bar-row">'
        f'<span class="bar-split">{split}</span>'
        f'<span class="bar-track"><span class="{css}" style="width:{value * 100:.1f}%"></span>'
        f"{tick}</span>"
        f'<span class="bar-value">{value:.3f}</span>'
        "</div>"
    )


def make_metrics(slide):
    chart = ""
    for metric, splits in METRICS.items():
        gate = None
        name = metric
        # only recall has a promotion gate
        if metric == "Recall":
            gate = RECALL_GATE
            name = name + f' <span class="gate-label">dashed line: gate at {gate:.2f}</span>'
        bars = ""
        for split, value in splits.items():
            bars = bars + make_bar(split, value, gate)
        chart = chart + f'<div class="bar-group"><p class="bar-metric">{name}</p>{bars}</div>'
    return (
        make_title(slide)
        + f'<div class="split"><div class="chart">{chart}</div>{make_points(slide)}</div>'
    )


def make_closing(slide):
    return (
        '<div class="cover">'
        f'<h2 class="cover-title">{slide["title"]}</h2>'
        '<p class="cover-lede">Eight of nine lifecycle stages are in place. '
        "Monitoring is next.</p>"
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
    elif layout == "flow":
        return make_flow(slide)
    elif layout == "metrics":
        return make_metrics(slide)
    elif layout == "script":
        return make_title(slide) + make_points(slide, tag="ol")
    elif layout == "closing":
        return make_closing(slide)
    else:
        return make_title(slide) + make_points(slide)


def render_slide(index):
    slides = all_slides()
    section, slide = slides[index]
    rail = ""
    if len(slide["stages"]) > 0:
        rail = make_rail(slide["stages"])
    return (
        f'<section class="slide layout-{slide["layout"]}">'
        + rail
        + f'<div class="slide-body">{make_body(slide)}</div>'
        + make_footer(slide, section["presenter"], index + 1, len(slides))
        + "</section>"
    )


def slide_label(index):
    section, slide = all_slides()[index]
    return f"{index + 1}. {slide['title']}"
