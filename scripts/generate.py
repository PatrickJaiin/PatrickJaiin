"""Render dark_mode.svg and light_mode.svg: binary portrait + neofetch-style card.

Stdlib only so it runs anywhere (including the daily GitHub Action).
Live stats need a token in GH_TOKEN / GITHUB_TOKEN; without one, the
fallback numbers below are used.

    python scripts/generate.py
"""
import json
import os
import urllib.request
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

USER = "PatrickJaiin"
JOINED = date(2016, 8, 9)
ROOT = Path(__file__).resolve().parent.parent
ART = json.loads((Path(__file__).parent / "art.json").read_text())

FALLBACK = {"repos": 55, "contributed": 5, "stars": 21, "commits": 348, "followers": 14}

# --- layout --------------------------------------------------------------
FONT_SIZE = 12.5
CHAR_W = 7.53  # advance width of a 12.5px monospace glyph
LINE_H = 17.0
ART_FONT_SIZE = 9.5  # portrait uses a smaller font for more resolution
ART_CHAR_W = 5.72
ART_LINE_H = 11.0
PAD = 26
INFO_W = 62  # characters per info line
GAP = 30  # px between art and info

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", art="#e6edf3", text="#c9d1d9",
                 key="#ffa657", value="#a5d6ff", dots="#484f58", add="#3fb950"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", art="#1f2328", text="#24292f",
                  key="#953800", value="#0a3069", dots="#afb8c1", add="#1a7f37"),
}


# --- data ----------------------------------------------------------------
def gh_graphql(query, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("no token, using fallback stats")
        return FALLBACK
    years = range(JOINED.year, date.today().year + 1)
    per_year = " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z")'
        f" {{ totalCommitContributions restrictedContributionsCount }}"
        for y in years
    )
    q = f"""{{ user(login: "{USER}") {{
        followers {{ totalCount }}
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {{ totalCount }}
        repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {{
            totalCount nodes {{ stargazerCount }} }}
        {per_year}
    }} }}"""
    try:
        u = gh_graphql(q, token)["user"]
    except Exception as e:  # keep the card rendering even if the API hiccups
        print("stats fetch failed, using fallback:", e)
        return FALLBACK
    return {
        "repos": u["repositories"]["totalCount"],
        "contributed": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "commits": sum(u[f"y{y}"]["totalCommitContributions"]
                       + u[f"y{y}"]["restrictedContributionsCount"] for y in years),
        "followers": u["followers"]["totalCount"],
    }


def uptime(start, today):
    y, m, d = today.year - start.year, today.month - start.month, today.day - start.day
    if d < 0:
        m -= 1
        prev_month = (today.month - 2) % 12 + 1
        d += [31, 29 if today.year % 4 == 0 else 28, 31, 30, 31, 30,
              31, 31, 30, 31, 30, 31][prev_month - 1]
    if m < 0:
        y, m = y - 1, m + 12
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"


# --- info lines: each line is a list of (css class, text) segments --------
def kv(key, value, width=INFO_W):
    """'. Key: ........ value' padded to width."""
    dots = width - len(key) - len(value) - 5
    return [("dots", ". "), ("key", key), ("text", ":"),
            ("dots", " " + "." * max(1, dots) + " "), ("value", value)]


def header(title):
    """Section title; the rule after it is drawn as an SVG line."""
    return [("text", f"- {title} "), ("rule", "")]


def two_kv(k1, v1, k2, v2, width=INFO_W):
    half = 34
    left, right = kv(k1, v1, half), kv(k2, v2, width - half + 2 - 3)
    return left + [("text", " | ")] + right[1:]  # drop the second leading '. '


def info_lines(s):
    today = datetime.now(timezone.utc).date()
    return [
        [("text", "shiv"), ("key", "@"), ("text", "gupta "), ("rule", "")],
        kv("OS", "macOS (Apple Silicon), Linux"),
        kv("Uptime.GitHub", uptime(JOINED, today)),
        kv("Host", "Carnegie Mellon University"),
        kv("Kernel", "M.S. AI & Innovation (May '27)"),
        kv("Location", "Pittsburgh, PA"),
        kv("IDE", "Claude Code, VS Code"),
        [],
        kv("Languages.Programming", "Python, TypeScript, C++, Java"),
        kv("Languages.ML", "PyTorch, TensorFlow, CUDA"),
        kv("Languages.Web", "React, Next.js, Tailwind, Flask"),
        kv("Languages.Real", "English, Hindi"),
        [],
        kv("Interests.AI", "LLM Context, Token Efficiency, Safety"),
        kv("Interests.Builds", "Poker Bots, Drones, Trading Tools"),
        kv("Interests.Hobbies", "Gaming on Mac via CrossOver"),
        [],
        header("Contact"),
        kv("Email.School", "shivg@andrew.cmu.edu"),
        kv("Website", "shivgupta.in"),
        kv("LinkedIn", "shivvguptaa"),
        kv("Medium", "@shiv_"),
        [],
        header("GitHub Stats"),
        two_kv("Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}", "Stars", f"{s['stars']:,}"),
        two_kv("Commits", f"{s['commits']:,}", "Followers", f"{s['followers']:,}"),
    ]


# --- svg -----------------------------------------------------------------
def render(theme, stats):
    c = THEMES[theme]
    art_cols = len(ART[0])
    info_x = PAD + art_cols * ART_CHAR_W + GAP
    info_right = info_x + INFO_W * CHAR_W
    width = round(info_right + PAD)
    lines = info_lines(stats)
    art_h = len(ART) * ART_LINE_H
    height = round(PAD * 2 + max(art_h, len(lines) * LINE_H))
    art_top = (height - art_h) / 2
    info_top = (height - len(lines) * LINE_H) / 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, '
        f'Consolas, \'Liberation Mono\', monospace" font-size="{FONT_SIZE}px">',
        "<style>",
        f".art{{fill:{c['art']}}}",
        *(f".l{i}{{fill-opacity:{0.12 + 0.88 * (i / 7) ** 1.4:.2f}}}" for i in range(8)),
        f".text{{fill:{c['text']}}} .key{{fill:{c['key']}}} .value{{fill:{c['value']}}} "
        f".dots{{fill:{c['dots']}}} .add{{fill:{c['add']}}}",
        "text{white-space:pre}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>',
    ]

    # portrait: group runs of the same brightness level into one tspan.
    # On a light background ink means dark, so flip levels and digits there.
    flip = theme == "light"
    art = [[[{"0": "1", "1": "0"}.get(ch, ch) if flip else ch, 7 - lvl if flip else lvl]
            for ch, lvl in row] for row in ART]
    out.append(f'<text class="art" font-size="{ART_FONT_SIZE}px" xml:space="preserve">')
    for r, row in enumerate(art):
        y = art_top + (r + 0.8) * ART_LINE_H
        spans, run, lvl = [], "", None
        for ch, level in row + [[None, None]]:
            if ch is not None and level == lvl:
                run += ch
                continue
            if run:
                spans.append(f'<tspan class="l{lvl}">{run}</tspan>' if run.strip() else run)
            run, lvl = (ch or ""), level
        out.append(f'<tspan x="{PAD}" y="{y:.1f}">{"".join(spans)}</tspan>')
    out.append("</text>")

    rules = []
    out.append('<text xml:space="preserve">')
    for i, segs in enumerate(lines):
        if not segs:
            continue
        y = info_top + (i + 0.8) * LINE_H
        body = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for cls, t in segs if cls != "rule")
        out.append(f'<tspan x="{info_x:.1f}" y="{y:.1f}">{body}</tspan>')
        if segs[-1][0] == "rule":
            x0 = info_x + sum(len(t) for _, t in segs) * CHAR_W + 2
            ry = y - FONT_SIZE * 0.32
            rules.append(f'<line x1="{x0:.1f}" y1="{ry:.1f}" x2="{info_right:.1f}" y2="{ry:.1f}" '
                         f'stroke="{c["dots"]}" stroke-width="1"/>')
    out.append("</text>")
    out.extend(rules)
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    stats = fetch_stats()
    print(stats)
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats))
