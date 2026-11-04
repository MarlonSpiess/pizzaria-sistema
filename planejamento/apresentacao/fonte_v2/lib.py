import math

DARK = '#1E1A17'
CREAM = '#FAF6EF'
RED = '#B5361F'
GOLD = '#D9A441'
TAN = '#F1E7D8'
LINE = '#E6DCCD'
GREY = '#5E534A'
INK = '#2B2420'
SLATE = '#6F8FA3'
GREEN = '#7A9A6B'


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def wrap(text, maxchars):
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= maxchars:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(cx, cy, text, fs, fill, weight=500, maxw=None, anchor='middle', lh=1.22, family='dm'):
    maxw = maxw or 300
    maxchars = max(6, int(maxw / ((0.43 if family == 'os' else 0.52) * fs)))
    lines = wrap(text, maxchars)
    total = len(lines) * fs * lh
    y0 = cy - total / 2 + fs * 0.9
    out = []
    for i, l in enumerate(lines):
        out.append(f'<text x="{cx}" y="{y0 + i * fs * lh:.1f}" font-size="{fs}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" class="{family}">{esc(l)}</text>')
    return ''.join(out)


def box(x, y, w, h, text, fill=CREAM, stroke=RED, color=INK, fs=22, weight=500, rx=14, sw=2.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
    s += text_block(x + w / 2, y + h / 2, text, fs, color, weight, w - 28)
    return s


def title_box(x, y, w, h, title, sub, fill, color='#fff', subcolor=None, fs=26, fs2=19):
    subcolor = subcolor or color
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}"/>'
    s += text_block(x + w / 2, y + h * 0.33, title, fs, color, 700, w - 24, family='os')
    s += text_block(x + w / 2, y + h * 0.7, sub, fs2, subcolor, 500, w - 24)
    return s


def diamond(cx, cy, w, h, text, fill=GOLD, stroke=DARK, color=DARK, fs=20):
    pts = f'{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}'
    s = f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>'
    s += text_block(cx, cy, text, fs, color, 700, w * 0.62)
    return s


def arrow(x1, y1, x2, y2, color=INK, dash=None, sw=3, label=None, lx=None, ly=None, lcolor=None, fs=18, lw=220, bg=CREAM, mid=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    if mid:
        pts = [(x1, y1)] + mid + [(x2, y2)]
        path = 'M ' + ' L '.join(f'{px},{py}' for px, py in pts)
    else:
        path = f'M {x1},{y1} L {x2},{y2}'
    s = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{sw}"{d} marker-end="url(#ah-{color.strip("#")})"/>'
    if label:
        lx = lx if lx is not None else (x1 + x2) / 2
        ly = ly if ly is not None else (y1 + y2) / 2
        lcolor = lcolor or color
        chars = len(label)
        tw = min(lw, chars * fs * 0.53 + 16)
        s += f'<rect x="{lx - tw / 2:.1f}" y="{ly - fs * 0.9:.1f}" width="{tw:.1f}" height="{fs * 1.5:.1f}" rx="6" fill="{bg}" opacity="0.94"/>'
        s += f'<text x="{lx}" y="{ly + fs * 0.35:.1f}" font-size="{fs}" fill="{lcolor}" font-weight="600" text-anchor="middle" class="dm">{esc(label)}</text>'
    return s


def markers(colors):
    out = '<defs>'
    for c in colors:
        out += f'<marker id="ah-{c.strip("#")}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    out += '</defs>'
    return out


def svg(w, h, body, extra_markers=()):
    cols = [INK, RED, GOLD, CREAM, SLATE, GREEN, GREY, '#FAF6EF'] + list(extra_markers)
    cols = list(dict.fromkeys(cols))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{markers(cols)}{body}</svg>'


def pizza(cx, cy, r, labels=True, bg=DARK, numbers=True):
    groups = [SLATE, SLATE, RED, SLATE, GREEN, RED, RED, RED, GREEN]
    s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#C98F2E"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r - 16}" fill="{GOLD}"/>'
    rin = r - 34
    for i in range(9):
        a0 = math.radians(-90 + i * 40 + 1.6)
        a1 = math.radians(-90 + (i + 1) * 40 - 1.6)
        x0, y0 = cx + rin * math.cos(a0), cy + rin * math.sin(a0)
        x1, y1 = cx + rin * math.cos(a1), cy + rin * math.sin(a1)
        s += f'<path d="M {cx},{cy} L {x0:.1f},{y0:.1f} A {rin},{rin} 0 0 1 {x1:.1f},{y1:.1f} Z" fill="{groups[i]}"/>'
        am = math.radians(-90 + i * 40 + 20)
        if numbers:
            s += f'<text x="{cx + rin * 0.66 * math.cos(am):.1f}" y="{cy + rin * 0.66 * math.sin(am) + 14:.1f}" font-size="{int(r * 0.15)}" fill="#fff" font-weight="700" text-anchor="middle" class="os">{i + 1}</text>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r * 0.2}" fill="{DARK}" stroke="{GOLD}" stroke-width="4"/>'
    s += f'<text x="{cx}" y="{cy + r * 0.045:.1f}" font-size="{int(r * 0.085)}" fill="{GOLD}" font-weight="700" text-anchor="middle" class="os">NÚCLEO</text>'
    return s
