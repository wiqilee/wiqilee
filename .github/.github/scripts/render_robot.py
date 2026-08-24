"""Render an original flying-robot animation over the GitHub contribution grid.

Usage:
    python render_robot.py --user wiqilee --out assets
    python render_robot.py --preview          # mock data, no network
"""
import argparse, json, os, random, urllib.request

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD_X, PAD_TOP, PAD_BOT = 14, 30, 30
CYCLE = 14.0
SWEEP_END = 82.0
RESTORE_A, RESTORE_B = 93.0, 97.0

THEMES = {
    'dark': {
        'levels': ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'],
        'body': '#e6edf3', 'accent': '#1d9e75',
        'visor': '#0d1117', 'flame': '#f0883e',
    },
    'light': {
        'levels': ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'],
        'body': '#ffffff', 'accent': '#1a7f5a',
        'visor': '#24292f', 'flame': '#e36209',
    },
}

QUERY = ("query($login:String!){user(login:$login){contributionsCollection"
         "{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}")


def fetch(login, token):
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': login}}).encode(),
        headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if 'errors' in payload:
        raise SystemExit('GraphQL error: ' + json.dumps(payload['errors']))
    weeks = payload['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    return [[d['contributionCount'] for d in w['contributionDays']] for w in weeks]


def mock():
    rnd = random.Random(3)
    return [[rnd.choice([0, 0, 0, 1, 2, 5, 9, 14]) for _ in range(7)] for _ in range(53)]


def to_levels(weeks):
    peak = max((c for w in weeks for c in w), default=0)
    out = []
    for w in weeks:
        col = []
        for c in w:
            if c == 0 or peak == 0:
                col.append(0)
            else:
                col.append(min(4, int(c / peak * 4) + 1))
        out.append(col)
    return out


def robot_parts(t):
    """Original robot sprite, drawn around its own origin, facing +x."""
    return [
        ('poly', [(-7, 3), (-25, 7), (-7, 11)], t['flame'], 'flame'),
        ('rrect', -11, 2, 5, 8, 2.5, t['accent'], None),
        ('rrect', -7, 0, 14, 13, 5, t['accent'], None),
        ('rrect', 6, 2, 5, 8, 2.5, t['accent'], None),
        ('rrect', -6, 12, 5, 4, 1.5, t['accent'], None),
        ('rrect', 1, 12, 5, 4, 1.5, t['accent'], None),
        ('circle', 0, -9, 9, t['body'], None),
        ('rrect', -6, -12, 12, 6, 3, t['visor'], None),
        ('circle', -3, -9, 1.7, t['accent'], None),
        ('circle', 3, -9, 1.7, t['accent'], None),
        ('line', 0, -18, 0, -23, t['accent'], None),
        ('circle', 0, -24, 2.2, t['accent'], None),
    ]


def emit(part):
    kind = part[0]
    cls = ' class="flame"' if part[-1] == 'flame' else ''
    if kind == 'circle':
        _, cx, cy, r, fill, _ = part
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{cls}/>'
    if kind == 'rrect':
        _, x, y, w, h, r, fill, _ = part
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{cls}/>'
    if kind == 'poly':
        _, pts, fill, _ = part
        p = ' '.join(f'{x},{y}' for x, y in pts)
        return f'<polygon points="{p}" fill="{fill}"{cls}/>'
    _, x1, y1, x2, y2, stroke, _ = part
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="2"{cls}/>'


def render(levels, theme_name):
    t = THEMES[theme_name]
    n = len(levels)
    W = PAD_X * 2 + n * STEP - GAP
    H = PAD_TOP + 7 * STEP - GAP + PAD_BOT
    mid_y = PAD_TOP + 3.5 * STEP - GAP / 2

    css = [
        f'@keyframes fly{{0%{{transform:translateX(-38px)}}'
        f'{SWEEP_END}%,100%{{transform:translateX({W + 38}px)}}}}',
        '@keyframes bob{0%,100%{transform:translateY(-7px)}50%{transform:translateY(7px)}}',
        '@keyframes flick{0%,100%{opacity:.95;transform:scaleX(1)}'
        '50%{opacity:.55;transform:scaleX(.6)}}',
        '.flame{transform-origin:-7px 7px;animation:flick .16s linear infinite}',
    ]

    cells, overlays = [], []
    for c, col in enumerate(levels):
        x = PAD_X + c * STEP
        p = 3.0 + (c / max(n - 1, 1)) * (SWEEP_END - 6.0)
        css.append(
            '@keyframes q%d{0%%,%.2f%%{opacity:1}%.2f%%,%.1f%%{opacity:0}%.1f%%,100%%{opacity:1}}'
            % (c, p, p + 1.4, RESTORE_A, RESTORE_B)
        )
        for r, lvl in enumerate(col):
            y = PAD_TOP + r * STEP
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{t["levels"][0]}"/>'
            )
            if lvl:
                overlays.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                    f'fill="{t["levels"][lvl]}" '
                    f'style="animation:q{c} {CYCLE}s linear infinite"/>'
                )

    sprite = ''.join(emit(p) for p in robot_parts(t))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="A robot flying across the contribution grid">'
        f'<style>{"".join(css)}</style>'
        f'{"".join(cells)}{"".join(overlays)}'
        f'<g style="animation:fly {CYCLE}s linear infinite">'
        f'<g style="animation:bob 2.3s ease-in-out infinite">'
        f'<g transform="translate(0,{mid_y:.1f}) rotate(6)">{sprite}</g>'
        f'</g></g></svg>'
    )


def preview(theme_name, path):
    """Rasterise the sprite with PIL so the design can be eyeballed offline."""
    from PIL import Image, ImageDraw
    t = THEMES[theme_name]
    S, box = 6, 90
    img = Image.new('RGB', (box * S, box * S),
                    (13, 17, 23) if theme_name == 'dark' else (255, 255, 255))
    d = ImageDraw.Draw(img)
    ox = oy = box // 2

    def hx(c):
        c = c.lstrip('#')[:6]
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

    for p in robot_parts(t):
        k = p[0]
        if k == 'circle':
            _, cx, cy, r, fill, _ = p
            d.ellipse([(ox + cx - r) * S, (oy + cy - r) * S,
                       (ox + cx + r) * S, (oy + cy + r) * S], fill=hx(fill))
        elif k == 'rrect':
            _, x, y, w, h, r, fill, _ = p
            d.rounded_rectangle([(ox + x) * S, (oy + y) * S,
                                 (ox + x + w) * S, (oy + y + h) * S],
                                r * S, fill=hx(fill))
        elif k == 'poly':
            _, pts, fill, _ = p
            d.polygon([((ox + a) * S, (oy + b) * S) for a, b in pts], fill=hx(fill))
        else:
            _, x1, y1, x2, y2, stroke, _ = p
            d.line([(ox + x1) * S, (oy + y1) * S, (ox + x2) * S, (oy + y2) * S],
                   fill=hx(stroke), width=2 * S)
    img.resize((box * 3, box * 3)).save(path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', default='wiqilee')
    ap.add_argument('--out', default='assets')
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()

    if a.preview:
        weeks = mock()
    else:
        tok = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not tok:
            raise SystemExit('GH_TOKEN belum diset')
        weeks = fetch(a.user, tok)

    levels = to_levels(weeks)
    os.makedirs(a.out, exist_ok=True)
    for name in THEMES:
        path = os.path.join(a.out, f'robot-{name}.svg')
        with open(path, 'w') as f:
            f.write(render(levels, name))
        print('wrote', path)
        if a.preview:
            preview(name, os.path.join(a.out, f'_sprite-{name}.png'))
