#!/usr/bin/env python3
'''生成宇宙像素风 README 所需的手绘 SVG（仅标准库，输出确定）。

用法: python scripts/build_assets.py [输出目录]
'''
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
    W, H = 900, 300
    rng = random.Random(20261102)
    title, sub, status = 'CXSUNFLOWER', 'BEGINNER PROGRAMMER // CODING', 'STATUS: ONLINE'
    tx, sx, ux = (W - text_w(title, 8)) // 2, (W - text_w(sub, 3)) // 2, (W - text_w(status, 2)) // 2
    t_svg, t_css = typed(title, tx, 64, 8, 'url(#gt)', 'a', 0.6, 0.2, 14, 12.6, shadow='#2a1a6e')
    s_svg, s_css = typed(sub, sx, 142, 3, CYAN, 'b', 3.4, 0.07, 14, 12.6)
    u_svg, u_css = typed(status, ux, 182, 2, PINK, 'c', 5.8, 0.05, 14, 12.6)
    defs = ("<linearGradient id='gt' gradientUnits='userSpaceOnUse' x1='%d' y1='0' x2='%d' y2='0'>"
            "<stop offset='0' stop-color='%s'/><stop offset='.5' stop-color='#c9a6ff'/><stop offset='1' stop-color='%s'/>"
            "</linearGradient>" % (tx, tx + text_w(title, 8), CYAN, PINK))
    body = [nebula(rng, 150, 200, PURPLE, 26), nebula(rng, 700, 230, PINK, 22), nebula(rng, 520, 40, CYAN, 16),
            starfield(rng, W, H, 110, 46)]
    for x, y, dur, delay in [(760, 10, 9, 0.5), (520, 0, 11, 4), (880, 70, 13, 7), (300, 0, 8, 9.5)]:
        body.append(meteor(x, y, dur, delay))
    body.append("<g transform='translate(790 96)'><g class='bob'>%s%s%s</g></g>"
                % (path([(-72, -6, 144, 6)], mix(PINK, -0.35)), ''.join(disc_paths(5, 6, PURPLE)),
                   path([(-54, 6, 108, 6)], PINK)))
    body.append("<g transform='translate(95 215)'><g class='bob' style='animation-delay:-1.5s'>%s</g></g>"
                % ''.join(disc_paths(3, 4, CYAN)))
    body += [t_svg, s_svg, u_svg]
    body.append("<rect class='cur' x='%d' y='142' width='9' height='21' fill='%s'/>" % (sx + text_w(sub, 3) + 6, CYAN))
    body.append(ship_group(238, 24, 7))
    body.append(frame(W, H))
    return svg_doc(W, H, 'cxsunflower space pixel banner', ''.join(body), t_css + s_css + u_css, defs)


LANGS = [('Kotlin', '#a66bff'), ('Java', '#ff9a5c'), ('TypeScript', '#4aa8ff'),
         ('Python', '#ffd86b'), ('Vue', '#3ee08f'), ('Flutter', '#2ee6d6')]

ORBIT_CSS = (
    '.ox,.oy{animation-timing-function:cubic-bezier(.37,0,.63,1);animation-iteration-count:infinite;animation-direction:alternate}'
    '.ox{animation-name:ox}.oy{animation-name:oy}'
    '@keyframes ox{from{transform:translateX(calc(var(--rx) * -1))}to{transform:translateX(var(--rx))}}'
    '@keyframes oy{from{transform:translateY(calc(var(--ry) * -1))}to{transform:translateY(var(--ry))}}'
    '.halo{animation:halo 2s steps(2,end) infinite}@keyframes halo{50%{opacity:.25}}'
)


def build_stack():
    W, H = 900, 320
    cx, cy = 450, 140
    rng = random.Random(77)
    body = [starfield(rng, W, H, 70, 24), path(text_rects('TECH GALAXY', 24, 20, 3), CYAN)]
    for i in range(len(LANGS)):
        body.append("<ellipse cx='%d' cy='%d' rx='%d' ry='%d' fill='none' stroke='%s' stroke-width='2' stroke-dasharray='6 6'/>"
                    % (cx, cy, 100 + i * 56, 28 + i * 17, DIM))
    body.append("<g transform='translate(%d %d)'><rect class='halo' x='-34' y='-34' width='68' height='68' fill='none' stroke='%s' stroke-width='2'/>%s</g>"
                % (cx, cy, PINK, ''.join(disc_paths(5, 4, YELLOW))))
    for i, (name, color) in enumerate(LANGS):
        rx, ry = 100 + i * 56, 28 + i * 17
        d = (14 + i * 6) / 2.0
        off = i * 3.7
        body.append("<g transform='translate(%d %d)'><g class='ox' style='--rx:%dpx;animation-duration:%ss;animation-delay:-%ss'>"
                    "<g class='oy' style='--ry:%dpx;animation-duration:%ss;animation-delay:-%ss'>%s</g></g></g>"
                    % (cx, cy, rx, n(d), n(round(off, 2)), ry, n(d), n(round(off + d / 2, 2)),
                       ''.join(disc_paths(4 if i % 2 == 0 else 3, 3, color))))
    for i, (name, color) in enumerate(LANGS):
        x = 14 + i * 148
        body.append("<g transform='translate(%d 291)'>%s</g>" % (x + 7, ''.join(disc_paths(3, 2, color))))
        body.append(path(text_rects(name.upper(), x + 22, 284, 2), WHITE))
    body.append(frame(W, H))
    return svg_doc(W, H, 'Tech galaxy: Kotlin Java TypeScript Python Vue Flutter', ''.join(body), ORBIT_CSS)


def build_divider():
    W, H = 900, 36
    cols = [PURPLE, CYAN, PINK]
    parts = []
    for i in range(45):
        if 20 <= i <= 24:
            continue
        parts.append("<rect class='dv' style='animation-delay:%ss' x='%d' y='15' width='6' height='6' fill='%s'/>"
                     % (n(round(i * 0.1, 1)), 10 + i * 20, cols[i % 3]))
    star = [(447, 15, 6, 6), (441, 15, 6, 6), (453, 15, 6, 6), (447, 9, 6, 6), (447, 21, 6, 6), (435, 15, 6, 6), (459, 15, 6, 6)]
    parts.append("<g class='halo'>%s</g>" % path(star, WHITE))
    css = ORBIT_CSS + '.dv{animation:dv 4.4s ease-in-out infinite}@keyframes dv{0%,100%{opacity:.25}12%{opacity:1}30%{opacity:.25}}'
    return svg_doc(W, H, 'pixel star divider', ''.join(parts), css)


def build_footer():
    W, H = 900, 90
    rng = random.Random(4242)
    msg = 'END OF TRANSMISSION // SEE YOU IN SPACE'
    mx = (W - text_w(msg, 2)) // 2
    body = [starfield(rng, W, H, 40, 14), ship_group(10, 16, 4),
            path(text_rects(msg, mx, 54, 2), '#8f86e8'),
            "<rect class='cur' x='%d' y='54' width='6' height='14' fill='%s'/>" % (mx + text_w(msg, 2) + 6, PINK),
            frame(W, H)]
    return svg_doc(W, H, 'end of transmission', ''.join(body))


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in [('hero.svg', build_hero()), ('divider.svg', build_divider()),
                      ('stack.svg', build_stack()), ('footer.svg', build_footer())]:
        with open(out / name, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(svg)
        print('%s %d bytes' % (out / name, len(svg.encode('utf-8'))))


if __name__ == '__main__':
    main(sys.argv)