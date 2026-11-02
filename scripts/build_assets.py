#!/usr/bin/env python3
'''生成宇宙像素风 README 所需的手绘 SVG（仅标准库，输出确定）。

用法: python scripts/build_assets.py [输出目录]
'''
import json
import random
import sys
from pathlib import Path

BG = '#0b0a1f'
PURPLE = '#a66bff'
CYAN = '#2ee6d6'
PINK = '#ff5ccf'
YELLOW = '#ffd86b'
WHITE = '#e8e6ff'
DIM = '#2a2560'
FRAME = '#3b2f8f'

# 5x7 点阵字体：字符 + 7 行十六进制（bit4 为最左列）
_FONT_SRC = '''
A 0E 11 11 1F 11 11 11
B 1E 11 11 1E 11 11 1E
C 0E 11 10 10 10 11 0E
D 1E 11 11 11 11 11 1E
E 1F 10 10 1E 10 10 1F
F 1F 10 10 1E 10 10 10
G 0E 11 10 17 11 11 0F
H 11 11 11 1F 11 11 11
I 0E 04 04 04 04 04 0E
J 07 02 02 02 02 12 0C
K 11 12 14 18 14 12 11
L 10 10 10 10 10 10 1F
M 11 1B 15 15 11 11 11
N 11 11 19 15 13 11 11
O 0E 11 11 11 11 11 0E
P 1E 11 11 1E 10 10 10
Q 0E 11 11 11 15 12 0D
R 1E 11 11 1E 14 12 11
S 0F 10 10 0E 01 01 1E
T 1F 04 04 04 04 04 04
U 11 11 11 11 11 11 0E
V 11 11 11 11 11 0A 04
W 11 11 11 15 15 1B 11
X 11 11 0A 04 0A 11 11
Y 11 11 0A 04 04 04 04
Z 1F 01 02 04 08 10 1F
0 0E 11 13 15 19 11 0E
1 04 0C 04 04 04 04 0E
2 0E 11 01 02 04 08 1F
3 1F 02 04 02 01 11 0E
4 02 06 0A 12 1F 02 02
5 1F 10 1E 01 01 11 0E
6 06 08 10 1E 11 11 0E
7 1F 01 02 04 08 08 08
8 0E 11 11 0E 11 11 0E
9 0E 11 11 0F 01 02 0C
/ 01 01 02 04 08 10 10
- 00 00 00 1F 00 00 00
. 00 00 00 00 00 0C 0C
: 00 0C 0C 00 0C 0C 00
% 18 19 02 04 08 13 03
_ 00 00 00 00 00 00 1F
> 08 04 02 01 02 04 08
< 02 04 08 10 08 04 02
+ 00 04 04 1F 04 04 00
! 04 04 04 04 04 00 04
? 0E 11 01 02 04 00 04
* 00 0A 04 1F 04 0A 00
'''
FONT = {' ': (0,) * 7}
for _line in _FONT_SRC.strip().splitlines():
    _p = _line.split()
    FONT[_p[0]] = tuple(int(v, 16) for v in _p[1:])

SHIP = [
    '...KK........',
    '..PPPP...CC..',
    'YYPPPPPPPCCCW',
    'YYPPPPPPPCCCW',
    '..PPPP...CC..',
    '...KK........',
]
SHIP_COLORS = {'P': PURPLE, 'K': PINK, 'C': CYAN, 'W': WHITE, 'Y': YELLOW}

BASE_CSS = (
    '.t0{animation:tw 2.4s ease-in-out infinite}'
    '.t1{animation:tw 3.7s ease-in-out infinite}'
    '.t2{animation:tw 5.3s ease-in-out infinite}'
    '@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}'
    '.neb{animation:neb 9s ease-in-out infinite}'
    '@keyframes neb{0%,100%{opacity:.06}50%{opacity:.15}}'
    '.cur{animation:blink 1s steps(1,end) infinite}'
    '@keyframes blink{50%{opacity:0}}'
    '.fl{animation:fl .3s steps(1,end) infinite}'
    '@keyframes fl{50%{opacity:.2}}'
    '.mt{opacity:0;animation:mt 9s linear infinite}'
    '@keyframes mt{0%{transform:translate(0,0);opacity:0}2%{opacity:1}'
    '20%{transform:translate(-320px,320px);opacity:0}'
    '100%{transform:translate(-320px,320px);opacity:0}}'
    '.ship{animation:fly 24s linear infinite}'
    '@keyframes fly{from{transform:translateX(-80px)}to{transform:translateX(980px)}}'
    '.bob{animation:bob 3s ease-in-out infinite alternate}'
    '@keyframes bob{from{transform:translateY(0)}to{transform:translateY(6px)}}'
)
REDUCED_CSS = ('@media (prefers-reduced-motion:reduce){*{animation:none!important}'
               '.ox{transform:translateX(var(--rx))}.mt{opacity:0}}')


def n(v):
    if float(v).is_integer():
        return str(int(v))
    return ('%.2f' % v).rstrip('0').rstrip('.')


def d_rects(rects):
    return ''.join('M%s %sh%sv%sh-%sz' % (n(x), n(y), n(w), n(h), n(w)) for x, y, w, h in rects)


def path(rects, fill, extra=''):
    return "<path fill='%s'%s d='%s'/>" % (fill, extra, d_rects(rects))


def merge_h(rects):
    out = []
    for x, y, w, h in rects:
        if out and out[-1][1] == y and out[-1][3] == h and abs(out[-1][0] + out[-1][2] - x) < 1e-6:
            px, py, pw, ph = out[-1]
            out[-1] = (px, py, pw + w, ph)
        else:
            out.append((x, y, w, h))
    return out


def glyph_rects(ch, x, y, s):
    rows = FONT.get(ch.upper(), FONT['?'])
    out = []
    for r, bits in enumerate(rows):
        c = 0
        while c < 5:
            if bits & (0x10 >> c):
                st = c
                while c < 5 and bits & (0x10 >> c):
                    c += 1
                out.append((x + st * s, y + r * s, (c - st) * s, s))
            else:
                c += 1
    return out


def text_w(text, s):
    return len(text) * 6 * s - s


def text_rects(text, x, y, s):
    out = []
    for i, ch in enumerate(text):
        if ch != ' ':
            out += glyph_rects(ch, x + i * 6 * s, y, s)
    return out


def typed(text, x, y, s, fill, prefix, start, step, total, hold, shadow=None):
    '''逐字出现并循环的打字机文字，返回 (svg, css)。'''
    svg, css = [], []
    for i, ch in enumerate(text):
        if ch == ' ':
            continue
        cx = x + i * 6 * s
        g = ''
        if shadow:
            off = max(2, s // 2)
            g += path(glyph_rects(ch, cx + off, y + off, s), shadow)
        g += path(glyph_rects(ch, cx, y, s), fill)
        name = '%s%d' % (prefix, i)
        a = (start + step * i) / total * 100
        b = hold / total * 100
        svg.append("<g class='%s'>%s</g>" % (name, g))
        css.append('@keyframes %s{0%%{opacity:0}%.2f%%{opacity:1}%.2f%%{opacity:0}100%%{opacity:0}}.%s{animation:%s %ss steps(1,end) infinite}'
                   % (name, a, b, name, name, n(total)))
    return ''.join(svg), ''.join(css)


def grid_rects(grid, cell, x, y):
    by = {}
    for r, row in enumerate(grid):
        c = 0
        while c < len(row):
            k = row[c]
            if k == '.':
                c += 1
                continue
            st = c
            while c < len(row) and row[c] == k:
                c += 1
            by.setdefault(k, []).append((x + st * cell, y + r * cell, (c - st) * cell, cell))
    return by


def sprite(grid, cell, colors, x=0, y=0):
    out = []
    for k, rs in grid_rects(grid, cell, x, y).items():
        if k == 'Y':
            out.append("<g class='fl'>%s</g>" % path(rs, colors[k]))
        else:
            out.append(path(rs, colors[k]))
    return ''.join(out)


def mix(c, t):
    '''t>0 向白色混合，t<0 向黑色混合。'''
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    if t >= 0:
        f = lambda v: int(v + (255 - v) * t)
    else:
        f = lambda v: int(v * (1 + t))
    return '#%02x%02x%02x' % (f(r), f(g), f(b))


def disc_paths(r, cell, base):
    '''以 (0,0) 为中心的像素行星，返回 path 字符串列表。'''
    light, dark = mix(base, 0.45), mix(base, -0.45)
    by = {}
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + r * 0.6:
                t = (dx + dy) / (2.0 * r)
                col = light if t < -0.5 else dark if t > 0.4 else base
                if col == base and (dx * 7 + dy * 13) % 11 == 0 and t > -0.2:
                    col = dark
                by.setdefault(col, []).append((dx, dy))
    out = []
    for col, cells in by.items():
        rs = [(dx * cell - cell / 2.0, dy * cell - cell / 2.0, cell, cell)
              for dx, dy in sorted(cells, key=lambda p: (p[1], p[0]))]
        out.append(path(merge_h(rs), col))
    return out


def starfield(rng, w, h, n_static, n_twinkle):
    d = []
    for _ in range(n_static):
        x = rng.randrange(6, w - 6, 2)
        y = rng.randrange(6, h - 6, 2)
        s = rng.choice([2, 2, 2, 4])
        d.append('M%d %dh%dv%dh-%dz' % (x, y, s, s, s))
    out = ["<path fill='#6f6aa8' opacity='.75' d='%s'/>" % ''.join(d)]
    colors = [WHITE, WHITE, CYAN, PINK, PURPLE, YELLOW]
    for _ in range(n_twinkle):
        x = rng.randrange(8, w - 8, 2)
        y = rng.randrange(8, h - 8, 2)
        c = rng.choice(colors)
        cls = 't%d' % rng.randrange(3)
        delay = round(rng.uniform(0, 6), 1)
        if rng.random() < 0.35:
            rs = [(x, y, 2, 2), (x - 2, y, 2, 2), (x + 2, y, 2, 2), (x, y - 2, 2, 2), (x, y + 2, 2, 2)]
        else:
            rs = [(x, y, 2, 2)]
        out.append("<path class='%s' style='animation-delay:-%ss' fill='%s' d='%s'/>" % (cls, delay, c, d_rects(rs)))
    return ''.join(out)


def nebula(rng, cx, cy, color, cells, size=16):
    pos = {(0, 0)}
    cur = (0, 0)
    for _ in range(cells):
        dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        cur = (cur[0] + dx, cur[1] + dy)
        pos.add(cur)
    rs = [(cx + px * size, cy + py * size, size, size) for px, py in sorted(pos, key=lambda p: (p[1], p[0]))]
    return "<path class='neb' fill='%s' opacity='.1' d='%s'/>" % (color, d_rects(merge_h(rs)))


def meteor(x, y, dur, delay):
    trail = []
    for k in range(1, 8):
        trail.append(path([(4 * k, -4 * k, 4, 4)], CYAN if k < 4 else PURPLE,
                          " opacity='%s'" % n(round(1 - k / 8.0, 2))))
    return ("<g transform='translate(%d %d)'><g class='mt' style='animation-duration:%ss;animation-delay:%ss'>%s%s</g></g>"
            % (x, y, dur, delay, path([(0, 0, 4, 4)], WHITE), ''.join(trail)))


def frame(w, h):
    corners = [(0, 0), (w - 10, 0), (0, h - 10), (w - 10, h - 10)]
    return ("<rect x='2' y='2' width='%d' height='%d' fill='none' stroke='%s' stroke-width='4'/>%s"
            % (w - 4, h - 4, FRAME, path([(x, y, 10, 10) for x, y in corners], PINK)))


def side_frame(w, h):
    return path([(2, 0, 2, h), (w - 4, 0, 2, h)], FRAME)


ICONS = {
    'package': (('..KKKK..', '.KYYYYK.', 'KYYOYYYK', 'KYYYYYYK', 'KYYYYYYK', '.KYYYYK.', '..KKKK..'),
                {'K': '#241b50', 'Y': YELLOW, 'O': '#ff9a5c'}),
    'star': (('...Y...', '..YYY..', 'YYYYYYY', '.YYYYY.', '..YYY..', '.YY.YY.', 'Y.....Y'),
             {'Y': YELLOW}),
    'snake': (('..GGG.....', '.GG.GGG...', '.G...GG...', '.GGG.GG...', '...G.G....', '...GGG....'),
              {'G': '#3ee08f'}),
    'crew': (('..C...C...', '.CCC.CCC..', '.CCC.CCC..', '..C...C...', '.PPP.PPP..', '.PPP.PPP..'),
             {'C': CYAN, 'P': PINK}),
    'clock': (('..CCCC..', '.C....C.', 'C..WW..C', 'C..W...C', 'C..W...C', 'C..WW..C', '.C....C.', '..CCCC..'),
              {'C': CYAN, 'W': WHITE}),
    'signal': (('C.......', 'CC......', 'CCC.....', 'CCCC....', 'CCCCC...', 'CCCCCC..', 'CCCCCCC.'),
               {'C': CYAN}),
    'astronaut': (('..WWWW..', '.WKWWKW.', 'WWKWWKWW', 'WWCCCCWW', '.WCCCCW.', '..WWWW..', '..W..W..', '..W..W..'),
                  {'W': WHITE, 'K': '#241b50', 'C': CYAN}),
}


def icon(name, x, y, cell):
    aliases = {'package': 'box', 'crew': 'users'}
    key = aliases.get(name, name)
    if key in PIXEL_ICONS:
        color = {'star': YELLOW, 'package': YELLOW, 'crew': CYAN,
                 'clock': CYAN, 'signal': PINK}.get(name, CYAN)
        shapes = ''.join("<path d='%s'/>" % d for d in PIXEL_ICONS[key])
        return "<g transform='translate(%s %s) scale(%s)' fill='%s'>%s</g>" % (n(x), n(y), n(cell / 3), color, shapes)
    grid, colors = ICONS[name]
    return sprite(grid, cell, colors, x, y)


PIXEL_ICONS = json.loads((Path(__file__).with_name('pixelarticons.json')).read_text(encoding='utf-8'))


def svg_doc(w, h, label, body, css='', defs=''):
    defs_xml = '<defs>%s</defs>' % defs if defs else ''
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' "
            "shape-rendering='crispEdges' role='img' aria-label='%s'>\n"
            "<title>%s</title>\n%s<style>%s%s%s</style>\n"
            "<rect width='%d' height='%d' fill='%s'/>\n%s\n</svg>\n"
            % (w, h, w, h, label, label, defs_xml, BASE_CSS, css, REDUCED_CSS, w, h, BG, body))


def ship_group(y, dur, delay):
    return ("<g transform='translate(0 %d)'><g class='ship' style='animation-duration:%ss;animation-delay:-%ss'>"
            "<g class='bob' style='animation-duration:1s'>%s</g></g></g>"
            % (y, dur, delay, sprite(SHIP, 4, SHIP_COLORS)))


def build_hero():
    W, H = 900, 220
    rng = random.Random(20261102)
    title = 'CXSUNFLOWER'
    t_svg, t_css = typed(title, 40, 72, 8, 'url(#gt)', 'a', .2, .08, 18, 17, shadow='#2a1a6e')
    defs = ("<linearGradient id='gt' x1='0' y1='0' x2='1' y2='0'>"
            "<stop offset='0' stop-color='%s'/><stop offset='.5' stop-color='#c9a6ff'/>"
            "<stop offset='1' stop-color='%s'/></linearGradient>" % (CYAN, PINK))
    body = [nebula(rng, 760, 116, PURPLE, 18), starfield(rng, W, H, 38, 20),
            path(text_rects('SPACE LOG // 001', 40, 28, 2), '#8f86e8'), t_svg,
            path(text_rects('BEGINNER PROGRAMMER / EXPLORING CODE', 40, 150, 2), CYAN),
            "<rect class='cur' x='454' y='150' width='6' height='14' fill='%s'/>" % CYAN,
            meteor(800, 0, 11, -3), meteor(540, 0, 13, -8)]
    body.append("<g transform='translate(758 100)'><g class='bob'>%s%s%s</g></g>"
                % (path([(-72, -6, 144, 6)], mix(PINK, -0.35)), ''.join(disc_paths(6, 6, PURPLE)),
                   path([(-60, 6, 120, 6)], PINK)))
    body += [ship_group(184, 24, 17), side_frame(W, H),
             path([(2, 0, W - 4, 4)], FRAME), path([(0, 0, 10, 10), (W - 10, 0, 10, 10)], PINK)]
    return svg_doc(W, H, 'cxsunflower - space pixel poster', ''.join(body), t_css, defs)


LANGS = [('Kotlin', '#a66bff'), ('Java', '#ff9a5c'), ('TypeScript', '#4aa8ff'),
         ('Python', '#ffd86b'), ('Vue', '#3ee08f'), ('Flutter', '#2ee6d6')]

ORBIT_CSS = (
    '.ox,.oy{animation-timing-function:cubic-bezier(.37,0,.63,1);animation-iteration-count:infinite;animation-direction:alternate}'
    '.ox{animation-name:ox}.oy{animation-name:oy}'
    '@keyframes ox{from{transform:translateX(calc(var(--rx) * -1))}to{transform:translateX(var(--rx))}}'
    '@keyframes oy{from{transform:translateY(calc(var(--ry) * -1))}to{transform:translateY(var(--ry))}}'
    '.halo{animation:halo 2s steps(2,end) infinite}@keyframes halo{50%{opacity:.25}}'
)


def build_panel():
    W, H = 900, 276
    cx, cy = 684, 128
    rng = random.Random(2027)
    body = [starfield(rng, W, H, 22, 10), icon('code', 32, 22, 3),
            path(text_rects('PLAYER NOTES', 68, 24, 3), CYAN),
            icon('star', 526, 22, 3), path(text_rects('TECH GALAXY', 562, 24, 3), PINK),
            path([(486, 24, 2, 224)], FRAME)]
    for i, line in enumerate(['LEARN. BUILD. EXPLORE.', 'OPEN SOURCE / SIDE QUESTS', 'ONE PIXEL AT A TIME.']):
        body.append(path(text_rects(line, 32, 80 + i * 36, 2), WHITE if i == 0 else '#aaa2d6'))
    body += [icon('astronaut', 32, 210, 4),
             path(text_rects('PLAYER 01 / CXSUNFLOWER', 80, 222, 2), '#8f86e8')]
    for i in range(len(LANGS)):
        body.append("<ellipse cx='%d' cy='%d' rx='%d' ry='%d' fill='none' stroke='%s' stroke-width='2' stroke-dasharray='4 8'/>"
                    % (cx, cy, 64 + i * 20, 16 + i * 7, DIM))
    body.append("<g transform='translate(%d %d)'>%s</g>" % (cx, cy, ''.join(disc_paths(4, 3, YELLOW))))
    for i, (name, color) in enumerate(LANGS):
        rx, ry, dur, off = 64 + i * 20, 16 + i * 7, 6 + i * 2, i * 2.9
        body.append("<g transform='translate(%d %d)'><g class='ox' style='--rx:%dpx;animation-duration:%ss;animation-delay:-%ss'>"
                    "<g class='oy' style='--ry:%dpx;animation-duration:%ss;animation-delay:-%ss'>%s</g></g></g>"
                    % (cx, cy, rx, n(dur), n(off), ry, n(dur), n(off + dur / 2), ''.join(disc_paths(3, 2, color))))
    for i, (name, color) in enumerate(LANGS):
        col, row = i % 2, i // 2
        x, y = 534 + col * 174, 202 + row * 22
        body.append(path([(x, y + 3, 8, 8)], color))
        body.append(path(text_rects(name.upper(), x + 18, y, 2), WHITE))
    body.append(side_frame(W, H))
    return svg_doc(W, H, 'Player notes and tech galaxy - two panels', ''.join(body), ORBIT_CSS)


def build_button(text, color, icon_name, stars=3):
    W, H = 450, 80
    left = icon_name == 'package'
    body = [icon(icon_name, 32, 28, 3), path(text_rects(text, 72, 32, 2), WHITE),
            icon('chevron-right', 394, 28, 3),
            path([(2 if left else W - 4, 0, 2, H)], FRAME)]
    return svg_doc(W, H, text, ''.join(body))


def build_label(text, color, icon_name):
    W, H = 900, 80
    body = [icon(icon_name, 32, 28, 3), path(text_rects(text, 72, 30, 3), color),
            path(text_rects('CONTRIBUTIONS', 708, 34, 2), '#8f86e8'), side_frame(W, H)]
    return svg_doc(W, H, text, ''.join(body))


def build_footer():
    W, H = 900, 80
    rng = random.Random(4242)
    msg = 'SEE YOU IN SPACE'
    body = [starfield(rng, W, H, 16, 6), ship_group(12, 20, 15),
            path(text_rects(msg, 32, 28, 2), '#8f86e8'), side_frame(W, H),
            path([(2, H - 4, W - 4, 4)], FRAME),
            path([(0, H - 10, 10, 10), (W - 10, H - 10, 10, 10)], PINK)]
    return svg_doc(W, H, 'See you in space', ''.join(body))


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in [('hero.svg', build_hero()), ('panel.svg', build_panel()),
                      ('btn-aur.svg', build_button('ARCH LINUX AUR', YELLOW, 'package')),
                      ('btn-stars.svg', build_button('STARRED PROJECTS', PURPLE, 'star')),
                      ('label-activity.svg', build_label('ACTIVITY // SNAKE', PINK, 'snake')),
                      ('footer.svg', build_footer())]:
        with open(out / name, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(svg)
        print('%s %d bytes' % (out / name, len(svg.encode('utf-8'))))


if __name__ == '__main__':
    main(sys.argv)
