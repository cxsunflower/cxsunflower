#!/usr/bin/env python3
'''像素海报共享工具：调色板、点阵字体、精灵、动画样式与 SVG 封装。

只依赖标准库；随机数由调用方传入带种子的 random.Random，保证输出确定。
'''
import html
import json
import math
from pathlib import Path

W = 846  # GitHub 桌面端 README 内容宽度，按 1:1 绘制时像素不会被缩放糊掉

INK = '#07061a'
BG = '#0b0a1f'
BG2 = '#100d2a'
PANEL = '#141134'
PANEL2 = '#1b1745'
LINE = '#2a2560'
FRAME = '#3b2f8f'
FRAME2 = '#5a48c8'
MUTED = '#8f86e8'
SOFT = '#b4aee0'
WHITE = '#e8e6ff'
SNOW = '#ffffff'
PURPLE = '#a66bff'
PURPLE2 = '#6b3fd4'
PURPLE3 = '#3a2a8c'
PINK = '#ff5ccf'
PINK2 = '#c2389e'
PINK3 = '#5c1f63'
CYAN = '#2ee6d6'
CYAN2 = '#17a3b8'
CYAN3 = '#0f4a63'
BLUE = '#4aa8ff'
BLUE2 = '#2a6fd6'
GREEN = '#3ee08f'
GREEN2 = '#1f9e63'
LEAF = '#92cf50'
LEAF2 = '#5fa83a'
LEAF3 = '#2f6b25'
SUN_L = '#fff6b0'
SUN = '#ffe86b'
SUN2 = '#f5c443'
SUN3 = '#c98a1f'
ORANGE = '#ff9a5c'
ORANGE2 = '#e0662e'
FACE = '#d48a1d'
FACE_L = '#eaa940'
FACE_D = '#9a5a14'
RED = '#ff5c7a'
BLUSH = '#ff8fa3'

# 5x9 点阵：字符 + 每行十六进制（bit4 为最左列）；大写占 0-6 行，小写下伸部分到 8 行
_FONT_SRC = r'''
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
a 00 00 0E 01 0F 11 0F
b 10 10 16 19 11 11 1E
c 00 00 0E 10 10 11 0E
d 01 01 0D 13 11 11 0F
e 00 00 0E 11 1F 10 0E
f 06 09 08 1C 08 08 08
g 00 00 0F 11 11 11 0F 01 0E
h 10 10 16 19 11 11 11
i 04 00 0C 04 04 04 0E
j 02 00 06 02 02 02 02 12 0C
k 10 10 12 14 18 14 12
l 0C 04 04 04 04 04 0E
m 00 00 1A 15 15 11 11
n 00 00 16 19 11 11 11
o 00 00 0E 11 11 11 0E
p 00 00 1E 11 11 11 1E 10 10
q 00 00 0F 11 11 11 0F 01 01
r 00 00 16 19 10 10 10
s 00 00 0F 10 0E 01 1E
t 08 08 1C 08 08 09 06
u 00 00 11 11 11 13 0D
v 00 00 11 11 11 0A 04
w 00 00 11 11 15 15 0A
x 00 00 11 0A 04 0A 11
y 00 00 11 11 11 11 0F 01 0E
z 00 00 1F 02 04 08 1F
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
\ 10 10 08 04 02 01 01
- 00 00 00 1F 00 00 00
. 00 00 00 00 00 0C 0C
, 00 00 00 00 00 0C 0C 04 08
: 00 0C 0C 00 0C 0C 00
; 00 0C 0C 00 0C 0C 04 08
% 18 19 02 04 08 13 03
_ 00 00 00 00 00 00 1F
> 08 04 02 01 02 04 08
< 02 04 08 10 08 04 02
+ 00 04 04 1F 04 04 00
! 04 04 04 04 04 00 04
? 0E 11 01 02 04 00 04
* 00 0A 04 1F 04 0A 00
' 0C 04 08 00 00 00 00
" 0A 0A 00 00 00 00 00
( 02 04 08 08 08 04 02
) 08 04 02 02 02 04 08
[ 0E 08 08 08 08 08 0E
] 0E 02 02 02 02 02 0E
= 00 00 1F 00 1F 00 00
@ 0E 11 17 15 17 10 0F
# 0A 0A 1F 0A 1F 0A 0A
& 0C 12 14 08 15 12 0D
~ 00 00 08 15 02 00 00
$ 04 0F 14 0E 05 1E 04
| 04 04 04 04 04 04 04
^ 04 0A 11 00 00 00 00
· 00 00 00 0C 0C 00 00
• 00 00 0E 0E 0E 00 00
★ 04 04 1F 0E 0E 1B 11
♥ 00 0A 1F 1F 0E 04 00
▶ 10 18 1C 1E 1C 18 10
◀ 01 03 07 0F 07 03 01
→ 00 04 02 1F 02 04 00
↑ 04 0E 15 04 04 04 04
✓ 00 01 01 02 12 0C 04
× 00 11 0A 04 0A 11 00
█ 1F 1F 1F 1F 1F 1F 1F
… 00 00 00 00 00 00 15
'''
FONT = {}
for _line in _FONT_SRC.strip().splitlines():
    _key, *_vals = _line.split()
    _rows = [int(v, 16) for v in _vals]
    FONT[_key] = tuple(_rows + [0] * (9 - len(_rows)))

# 标题专用的粗体字形（笔画两格粗）
TITLE_GLYPHS = {
    'C': ('.####.', '######', '##..##', '##....', '##....', '##..##', '######', '.####.'),
    'X': ('##..##', '##..##', '.####.', '..##..', '..##..', '.####.', '##..##', '##..##'),
    'S': ('.#####', '######', '##....', '#####.', '.#####', '....##', '######', '#####.'),
    'U': ('##..##',) * 6 + ('######', '.####.'),
    'N': ('##..##', '###.##', '###.##', '######', '######', '##.###', '##.###', '##..##'),
    'F': ('######', '######', '##....', '#####.', '#####.', '##....', '##....', '##....'),
    'L': ('##....',) * 6 + ('######', '######'),
    'O': ('.####.', '######', '##..##', '##..##', '##..##', '##..##', '######', '.####.'),
    'W': ('##...##', '##...##', '##...##', '##.#.##', '##.#.##', '#######', '###.###', '##...##'),
    'E': ('######', '######', '##....', '#####.', '#####.', '##....', '######', '######'),
    'R': ('#####.', '######', '##..##', '######', '#####.', '##.##.', '##..##', '##..##'),
}

_GLYPHS = {}


def glyph(ch, style='r'):
    '''返回 (宽度, 行位图)；style: r 常规 5 列，b 粗体 6 列，t 标题粗体。'''
    key = (ch, style)
    if key not in _GLYPHS:
        if style == 't' and ch.upper() in TITLE_GLYPHS:
            rows = TITLE_GLYPHS[ch.upper()]
            _GLYPHS[key] = (len(rows[0]), [int(r.replace('#', '1').replace('.', '0'), 2) for r in rows])
        elif style == 't':
            w, b = glyph(ch.upper(), 'b')
            _GLYPHS[key] = (w, [b[i] | (b[i - 1] if i else 0) for i in range(8)])
        else:
            rows = FONT.get(ch) or FONT.get(ch.upper()) or FONT['?']
            if style == 'b':
                _GLYPHS[key] = (6, [((r << 1) | r) & 0x3F for r in rows])
            else:
                _GLYPHS[key] = (5, list(rows))
    return _GLYPHS[key]


def advance(ch, style='r'):
    if ch == ' ':
        return {'r': 6, 'b': 7, 't': 5}[style]
    return glyph(ch, style)[0] + 1


def text_w(text, s, style='r'):
    return sum(advance(ch, style) for ch in text) * s - s if text else 0


def n(v):
    if float(v).is_integer():
        return str(int(v))
    return ('%.2f' % v).rstrip('0').rstrip('.')


def merge_v(rects):
    by = {}
    for x, y, w, h in rects:
        by.setdefault((x, w), []).append((y, h))
    out = []
    for (x, w), spans in by.items():
        spans.sort()
        cy, ch = spans[0]
        for y, h in spans[1:]:
            if abs(y - (cy + ch)) < 1e-6:
                ch += h
            else:
                out.append((x, cy, w, ch))
                cy, ch = y, h
        out.append((x, cy, w, ch))
    out.sort(key=lambda r: (r[1], r[0]))
    return out


def merge_h(rects):
    by = {}
    for x, y, w, h in rects:
        by.setdefault((y, h), []).append((x, w))
    out = []
    for (y, h), spans in by.items():
        spans.sort()
        cx, cw = spans[0]
        for x, w in spans[1:]:
            if abs(x - (cx + cw)) < 1e-6:
                cw += w
            else:
                out.append((cx, y, cw, h))
                cx, cw = x, w
        out.append((cx, y, cw, h))
    return out


def merge(rects):
    return merge_v(merge_h(rects))


def cells_rects(cells, c, x=0, y=0):
    '''格子坐标集合 -> 合并后的矩形。'''
    return merge([(x + i * c, y + j * c, c, c) for i, j in cells])


def d_rects(rects):
    return ''.join('M%s %sh%sv%sh-%sz' % (n(x), n(y), n(w), n(h), n(w)) for x, y, w, h in rects)


def path(rects, fill, extra=''):
    if not rects:
        return ''
    return "<path fill='%s'%s d='%s'/>" % (fill, extra, d_rects(rects))


def text_rects(text, x, y, s, style='r', rows=None):
    '''点阵文字矩形；rows 只取指定字形行（双色字用）。'''
    out = []
    cx = x
    for ch in text:
        if ch != ' ':
            w, bits = glyph(ch, style)
            for r, b in enumerate(bits):
                if not b or (rows is not None and r not in rows):
                    continue
                c = 0
                while c < w:
                    if b >> (w - 1 - c) & 1:
                        st = c
                        while c < w and b >> (w - 1 - c) & 1:
                            c += 1
                        out.append((cx + st * s, y + r * s, (c - st) * s, s))
                    else:
                        c += 1
        cx += advance(ch, style) * s
    return merge_v(out)


def text(t, x, y, s, fill, style='r', shadow=None, extra=''):
    '''单色点阵文字，可选右下 1 格阴影。'''
    out = ''
    if shadow:
        out += path(text_rects(t, x + s, y + s, s, style), shadow)
    return out + path(text_rects(t, x, y, s, style), fill, extra)


def text2(t, x, y, s, top, bottom, style='b', split=4, shadow=INK, extra=''):
    '''上下双色的标题字（像素风渐变），默认带阴影。'''
    out = path(text_rects(t, x + s, y + s, s, style), shadow) if shadow else ''
    out += path(text_rects(t, x, y, s, style, rows=range(split)), top, extra)
    out += path(text_rects(t, x, y, s, style, rows=range(split, 9)), bottom, extra)
    return out


def cx_text(t, s, style='r', x0=0, x1=W):
    return (x0 + x1 - text_w(t, s, style)) // 2


def fit(t, s, width, style='r'):
    '''按像素宽度截断，超出时以 … 结尾。'''
    if text_w(t, s, style) <= width:
        return t
    while t and text_w(t + '…', s, style) > width:
        t = t[:-1]
    return t.rstrip() + '…'


def ascii_only(t):
    return all(ch == ' ' or ch in FONT for ch in t)


def grid_rects(rows, cell, x=0, y=0):
    by = {}
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            k = row[c]
            if k in '. ':
                c += 1
                continue
            st = c
            while c < len(row) and row[c] == k:
                c += 1
            by.setdefault(k, []).append((x + st * cell, y + r * cell, (c - st) * cell, cell))
    return {k: merge_v(v) for k, v in by.items()}


def sprite(rows, colors, cell, x=0, y=0, extra=''):
    '''按调色板绘制格子精灵；不在 colors 里的键会被跳过。'''
    return ''.join(path(rs, colors[k], extra) for k, rs in sorted(grid_rects(rows, cell, x, y).items()) if k in colors)


def raster(w, h, fn):
    return [''.join(fn(x, y) or '.' for x in range(w)) for y in range(h)]


def outline(rows, key='K', pad=0):
    '''给精灵加 4 邻域描边；pad 先在四周留出空白。'''
    if pad:
        wd = max(len(r) for r in rows) + 2 * pad
        rows = ['.' * wd] * pad + ['.' * pad + r.ljust(wd - 2 * pad, '.') + '.' * pad for r in rows] + ['.' * wd] * pad
    h, w = len(rows), max(len(r) for r in rows)
    g = [list(r.ljust(w, '.')) for r in rows]
    out = [row[:] for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] != '.':
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] != '.':
                    out[y][x] = key
                    break
    return [''.join(r) for r in out]


def stamp(rows, cells):
    '''在 rows 上覆盖 {(x, y): key}。'''
    g = [list(r) for r in rows]
    for (x, y), k in cells.items():
        if 0 <= y < len(g) and 0 <= x < len(g[y]):
            g[y][x] = k
    return [''.join(r) for r in g]


REDUCED = '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'


class Svg:
    '''收集 defs 与 CSS 规则（自动去重），最后输出完整 SVG。'''

    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.defs, self.rules = [], []
        self._seen = set()
        self._n = 0

    def css(self, *rules):
        for r in rules:
            if r and r not in self._seen:
                self._seen.add(r)
                self.rules.append(r)

    def uid(self, prefix='i'):
        self._n += 1
        return '%s%d' % (prefix, self._n)

    def add_def(self, xml, key=None):
        if key:
            if ('def', key) in self._seen:
                return
            self._seen.add(('def', key))
        self.defs.append(xml)

    def render(self, body, bg=BG):
        if not isinstance(body, str):
            body = ''.join(body)
        defs = '<defs>%s</defs>\n' % ''.join(self.defs) if self.defs else ''
        label = html.escape(self.label, quote=True)
        return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' "
                "shape-rendering='crispEdges' role='img' aria-label='{l}'>\n<title>{l}</title>\n{d}"
                "<style>{c}</style>\n<rect width='{w}' height='{h}' fill='{bg}'/>\n{b}\n</svg>\n").format(
            w=self.w, h=self.h, l=label, d=defs, c=''.join(self.rules) + REDUCED, bg=bg, b=body)


def pc(v):
    return '%.2f%%' % min(100.0, max(0.0, v))


def window_cls(svg, t_on, t_off, cycle):
    '''元素只在 [t_on, t_off) 秒可见；关闭动画时保持可见。'''
    name = 'v%x_%x_%x' % (int(round(t_on * 100)), int(round(t_off * 100)), int(round(cycle * 100)))
    a, b = t_on / cycle * 100, min(t_off, cycle) / cycle * 100
    if a <= 0:
        frames = '0%{opacity:1}' + ('%s{opacity:0}' % pc(b) if b < 100 else '')
    else:
        frames = '0%%{opacity:0}%s{opacity:1}' % pc(a) + ('%s{opacity:0}' % pc(b) if b < 100 else '')
    svg.css('@keyframes %s{%s}.%s{animation:%s %ss steps(1,end) infinite}' % (name, frames, name, name, n(cycle)))
    return name


def reveal(svg, x, y, w, h, t0, dur, cycle, steps, t_off=None):
    '''打字机式逐格出现的 clip-path 属性；关闭动画时完整显示。'''
    cid = svg.uid('rv')
    a, b = t0 / cycle * 100, (t0 + dur) / cycle * 100
    frames = '0%%,%s{transform:translateX(-%spx)}%s{transform:translateX(0)}' % (pc(a), n(w), pc(b))
    if t_off is not None and t_off < cycle:
        c = t_off / cycle * 100
        frames += '%s{transform:translateX(0)}%s{transform:translateX(-%spx)}' % (pc(c), pc(c + 0.01), n(w))
    svg.css('@keyframes %s{%s}.%s{animation:%s %ss steps(%d,end) infinite}' % (cid, frames, cid, cid, n(cycle), steps))
    svg.add_def("<clipPath id='%s'><rect class='%s' x='%s' y='%s' width='%s' height='%s'/></clipPath>"
                % (cid, cid, n(x), n(y), n(w), n(h)))
    return " clip-path='url(#%s)'" % cid


def typing_cursor(svg, x, y, w, h, color, t0, dur, cycle, steps, travel, t_hide=None):
    '''跟随打字位置移动的方块光标。'''
    cid = svg.uid('tc')
    a, b = t0 / cycle * 100, (t0 + dur) / cycle * 100
    frames = '0%%,%s{transform:translateX(0)}%s{transform:translateX(%spx)}' % (pc(a), pc(b), n(travel))
    svg.css('@keyframes %s{%s}.%s{animation:%s %ss steps(%d,end) infinite}' % (cid, frames, cid, cid, n(cycle), steps))
    inner = "<rect class='%s' x='%s' y='%s' width='%s' height='%s' fill='%s'/>" % (cid, n(x), n(y), n(w), n(h), color)
    if t_hide is not None:
        return "<g class='%s'>%s</g>" % (window_cls(svg, 0, t_hide, cycle), inner)
    return inner


def odometer(svg, value, x, y, s, color, t0, dur, cycle, style='b', shadow=INK):
    '''数字从 0 转一整圈后停在目标值；关闭动画时直接显示终值。'''
    out, cx = [], x
    adv, lh = advance('0', style) * s, 9 * s
    for ch in value:
        if not ch.isdigit():
            out.append(text(ch, cx, y, s, color, style, shadow))
            cx += advance(ch, style) * s
            continue
        d = int(ch)
        cid = svg.uid('od')
        end = (10 + d) * lh
        svg.add_def("<clipPath id='%s'><rect x='%s' y='%s' width='%s' height='%s'/></clipPath>" % (cid, n(cx), n(y - s), n(adv + s), n(9 * s)))
        svg.css('@keyframes %s{0%%,%s{transform:translateY(0)}%s,100%%{transform:translateY(-%dpx)}}'
                '.%s{animation:%s %ss cubic-bezier(.15,.7,.25,1) infinite}'
                % (cid, pc(t0 / cycle * 100), pc((t0 + dur) / cycle * 100), end, cid, cid, n(cycle)))
        strip = ''.join(text(str(k % 10), cx, y + k * lh, s, color, style, shadow) for k in range(11 + d))
        out.append("<g clip-path='url(#%s)'><g class='%s' style='transform:translateY(-%dpx)'>%s</g></g>" % (cid, cid, end, strip))
        cx += adv
    return ''.join(out)


BLINK_CSS = '.blk{animation:blk 1s steps(1,end) infinite}@keyframes blk{50%{opacity:0}}'
TWINKLE_CSS = '.tw{animation:tw 3s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.2}50%{opacity:1}}'
SPARKLE_CSS = ('.sp0,.sp1,.sp2{animation:4s steps(1,end) infinite}'
               '.sp0{animation-name:sp0}.sp1{animation-name:sp1}.sp2{animation-name:sp2}'
               '@keyframes sp0{0%{opacity:0}66%{opacity:1}70%{opacity:0}90%{opacity:1}94%{opacity:0}}'
               '@keyframes sp1{0%{opacity:0}70%{opacity:1}75%{opacity:0}85%{opacity:1}90%{opacity:0}}'
               '@keyframes sp2{0%{opacity:0}75%{opacity:1}85%{opacity:0}}')
BOB_CSS = ('.bob{animation:bob 2.4s steps(2,end) infinite}'
           '@keyframes bob{0%{transform:translateY(0)}50%{transform:translateY(-4px)}}')


def sparkle(svg, x, y, color, c=2, delay=0.0):
    svg.css(SPARKLE_CSS)
    frames = ([(x, y, c, c)],
              [(x - c, y, 3 * c, c), (x, y - c, c, 3 * c)],
              [(x - 2 * c, y, 5 * c, c), (x, y - 2 * c, c, 5 * c), (x - c, y - c, 3 * c, 3 * c)])
    st = " style='animation-delay:-%ss'" % n(delay) if delay else ''
    return ''.join("<path class='sp%d'%s fill='%s' d='%s'/>" % (i, st, color, d_rects(merge_v(f)))
                   for i, f in enumerate(frames))


def starfield(svg, rng, box, n_static=40, n_twinkle=14, n_sparkle=3,
              colors=(WHITE, WHITE, CYAN, PINK, PURPLE, SUN)):
    x0, y0, x1, y1 = box
    svg.css(TWINKLE_CSS)
    far = [(rng.randrange(x0, x1, 2), rng.randrange(y0, y1, 2), 2, 2) for _ in range(n_static)]
    mid = [(rng.randrange(x0, x1, 2), rng.randrange(y0, y1, 2), 2, 2) for _ in range(n_static // 3)]
    out = [path(far, '#35307a'), path(mid, '#6f6aa8')]
    for _ in range(n_twinkle):
        x, y = rng.randrange(x0 + 2, x1 - 2, 2), rng.randrange(y0 + 2, y1 - 2, 2)
        rs = [(x, y, 2, 2)]
        if rng.random() < 0.3:
            rs = [(x - 2, y, 6, 2), (x, y - 2, 2, 6)]
        out.append("<path class='tw' style='animation-duration:%ss;animation-delay:-%ss' fill='%s' d='%s'/>"
                   % (n(round(rng.uniform(2.2, 5.5), 1)), n(round(rng.uniform(0, 5), 1)),
                      rng.choice(colors), d_rects(merge_v(rs))))
    for _ in range(n_sparkle):
        out.append(sparkle(svg, rng.randrange(x0 + 6, x1 - 6, 2), rng.randrange(y0 + 6, y1 - 6, 2),
                           rng.choice((WHITE, SUN, CYAN, PINK)), 2, round(rng.uniform(0, 4), 1)))
    return ''.join(out)


def shooting_star(svg, x, y, dist, dur, delay, direction=-1, color=WHITE, tail=7, c=2):
    '''45° 划过的流星；direction=-1 向左下，1 向右下。关闭动画时不显示。'''
    name = svg.uid('ss')
    dx, dy = direction * dist, dist
    svg.css('.%s{opacity:0;animation:%s %ss linear infinite;animation-delay:-%ss}'
            '@keyframes %s{0%%{opacity:0;transform:translate(0,0)}1%%{opacity:1}11%%{opacity:1}'
            '14%%{opacity:0;transform:translate(%spx,%spx)}100%%{opacity:0;transform:translate(%spx,%spx)}}'
            % (name, name, n(dur), n(delay), name, n(dx * 14 / 11.0), n(dy * 14 / 11.0), n(dx), n(dy)))
    parts = [path([(0, 0, c, c)], color)]
    shades = [SNOW, WHITE, CYAN, CYAN, PURPLE, PURPLE, PURPLE3, PURPLE3]
    for k in range(1, tail + 1):
        op = n(round(1 - k / (tail + 1.0), 2))
        parts.append(path([(-direction * k * c, -k * c, c, c)], shades[min(k, len(shades) - 1)], " opacity='%s'" % op))
    return "<g transform='translate(%s %s)'><g class='%s'>%s</g></g>" % (n(x), n(y), name, ''.join(parts))


def dither(svg, color, level):
    '''2 像素颗粒的有序抖动图案，level 1/2/3 对应 25%/50%/75% 覆盖。'''
    pid = 'd%d%s' % (level, color[1:])
    cells = {1: [(0, 0)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (2, 2), (2, 0)]}[level]
    svg.add_def("<pattern id='%s' width='4' height='4' patternUnits='userSpaceOnUse'>%s</pattern>"
                % (pid, path([(x, y, 2, 2) for x, y in cells], color)), key=pid)
    return 'url(#%s)' % pid


def bands(svg, x, w, stops, tz=4):
    '''竖直色带：stops=[(y, color), ..., (y_end, None)]，相邻色带用抖动过渡。'''
    out = []
    for (y0, c), (y1, _) in zip(stops, stops[1:]):
        out.append(path([(x, y0, w, y1 - y0)], c))
    for (_, c0), (yb, c1), _ in zip(stops, stops[1:], stops[2:]):
        out.append("<rect x='%s' y='%s' width='%s' height='%s' fill='%s'/>" % (n(x), n(yb - 2 * tz), n(w), tz, dither(svg, c1, 1)))
        out.append("<rect x='%s' y='%s' width='%s' height='%s' fill='%s'/>" % (n(x), n(yb - tz), n(w), tz, dither(svg, c1, 2)))
        out.append("<rect x='%s' y='%s' width='%s' height='%s' fill='%s'/>" % (n(x), n(yb), n(w), tz, dither(svg, c0, 1)))
    return ''.join(out)


def scanlines(svg, x, y, w, h, color=INK, opacity=0.35, gap=4):
    pid = 'sl%d%s' % (gap, color[1:])
    svg.add_def("<pattern id='%s' width='4' height='%d' patternUnits='userSpaceOnUse'><rect width='4' height='1' fill='%s'/></pattern>"
                % (pid, gap, color), key=pid)
    return "<rect x='%s' y='%s' width='%s' height='%s' fill='url(#%s)' opacity='%s'/>" % (n(x), n(y), n(w), n(h), pid, n(opacity))


def side_frame(w, h):
    return path([(2, 0, 2, h), (w - 4, 0, 2, h)], FRAME)


def cap_frame(w, h, top=True):
    '''海报首尾的横边与角饰。'''
    y = 0 if top else h - 4
    cy = 0 if top else h - 10
    return (path([(2, y, w - 4, 4)], FRAME) +
            path([(0, cy, 10, 10), (w - 10, cy, 10, 10)], PINK) +
            path([(4, cy + 4, 2, 2), (w - 6, cy + 4, 2, 2)], SUN))


def bevel(x, y, w, h, face, light, dark, edge=INK, b=2):
    '''带高光与阴影的像素凸起面板（四角切掉一格形成圆角）。'''
    return (path([(x + b, y, w - 2 * b, b), (x + b, y + h - b, w - 2 * b, b), (x, y + b, b, h - 2 * b),
                  (x + w - b, y + b, b, h - 2 * b)], edge) +
            path([(x + b, y + b, w - 2 * b, h - 2 * b)], face) +
            path([(x + b, y + b, w - 2 * b, b), (x + b, y + 2 * b, b, h - 4 * b)], light) +
            path([(x + b, y + h - 2 * b, w - 2 * b, b), (x + w - 2 * b, y + 2 * b, b, h - 4 * b)], dark))


def brackets(x, y, w, h, color, size=10, t=2):
    '''HUD 风格的四角括号。'''
    rs = []
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        hx = cx if sx > 0 else cx - size
        vy = cy if sy > 0 else cy - size
        rs.append((hx, cy if sy > 0 else cy - t, size, t))
        rs.append((cx if sx > 0 else cx - t, vy, t, size))
    return path(rs, color)


def window(svg, x, y, w, h, title, bar=PURPLE2, body=PANEL, title_color=SNOW, icon_name=None):
    '''复古操作系统窗口：标题栏 + 三个按钮 + 凸起边框。返回 (svg, 内容区 y)。'''
    out = [path([(x + 4, y + 4, w, h)], INK)]
    out.append(bevel(x, y, w, h, body, PANEL2, BG2))
    out.append(path([(x + 4, y + 4, w - 8, 22)], bar))
    out.append(path([(x + 4, y + 4, w - 8, 2)], mix(bar, 0.35)))
    out.append(path([(x + 4, y + 24, w - 8, 2)], mix(bar, -0.45)))
    for i in range(3):
        out.append(path([(x + 4 + 6 + i * 4, y + 10, 2, 10)], mix(bar, 0.2)))
    tx = x + 26
    if icon_name:
        out.append(icon(icon_name, tx, y + 5, 20, title_color))
        tx += 26
    out.append(text(title, tx, y + 10, 2, title_color, 'b', shadow=mix(bar, -0.5)))
    bx = x + w - 4 - 8 - 3 * 20
    for i, glyph_rows in enumerate((('......', '......', '......', '......', '######', '######'),
                                    ('######', '#....#', '#....#', '#....#', '#....#', '######'),
                                    ('##..##', '.####.', '..##..', '..##..', '.####.', '##..##'))):
        bxx = bx + i * 20
        out.append(bevel(bxx, y + 7, 16, 16, mix(bar, 0.15), mix(bar, 0.45), mix(bar, -0.4), INK))
        out.append(sprite(glyph_rows, {'#': SNOW}, 1, bxx + 5, y + 12))
    return ''.join(out), y + 30


def mix(c, t):
    '''t>0 向白色混合，t<0 向黑色混合。'''
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    if t >= 0:
        f = lambda v: int(v + (255 - v) * t)
    else:
        f = lambda v: int(v * (1 + t))
    return '#%02x%02x%02x' % (f(r), f(g), f(b))


PIXEL_ICONS = json.loads((Path(__file__).with_name('pixelarticons.json')).read_text(encoding='utf-8'))


def icon(name, x, y, size, color, extra=''):
    '''Pixelarticons 24x24 图标；size 取 24 的倍数时像素最清晰。'''
    shapes = ''.join("<path d='%s'/>" % d for d in PIXEL_ICONS[name])
    return "<g transform='translate(%s %s) scale(%s)' fill='%s'%s>%s</g>" % (n(x), n(y), n(size / 24.0), color, extra, shapes)


def _kotlin():
    rows = raster(16, 16, lambda x, y: ('P' if x - y > 3 else 'M' if x - y > -5 else 'R')
                  if x + 0.5 < 8.5 + abs(y + 0.5 - 8) else None)
    return rows, {'P': '#7f52ff', 'M': '#c711e1', 'R': '#e44857'}


def _vue():
    def f(x, y):
        if y < 1 or y > 14:
            return None
        yy = y - 1
        wo = 8 - yy * 8 / 14.0
        d = abs(x + 0.5 - 8)
        if wo - 3.2 < d <= wo:
            return 'G'
        if wo - 6 < d <= wo - 3.2:
            return 'D'
        return None
    return raster(16, 16, f), {'G': '#41b883', 'D': '#35495e'}


def _flutter():
    def f(x, y):
        if 11 <= x + y <= 13 and y <= 9 and x >= 2:
            return 'L'
        if 19 <= x + y <= 21 and 6 <= y <= 10:
            return 'L'
        if -3 <= x - y <= -1 and y >= 10 and x + y >= 19:
            return 'D'
        return None
    return raster(16, 16, f), {'L': '#47c5fb', 'D': '#00569e'}


def _arch(size=16):
    def f(x, y):
        hw = 0.4 + (y + 0.5) * (size / 2.0 - 0.4) / size
        d = x + 0.5 - size / 2.0
        if abs(d) > hw:
            return None
        top = size * 0.56
        if y + 0.5 > top:
            hole = (y + 0.5 - top) / (size - top) * size * 0.2 + 0.5
            if abs(d) < hole and not (y + 0.5 > size - 1 and abs(d) < hole - 1):
                return None
        if y + 0.5 > size * 0.42 and d > 0 and abs((d - (y + 0.5 - size * 0.42) * 0.55) - size * 0.08) < 0.55:
            return None
        return 'a' if d < -hw * 0.25 else 'A'
    return raster(size, size, f), {'A': '#1793d1', 'a': '#57b9eb'}


LOGOS = {
    'kotlin': _kotlin(),
    'java': ((
        '................', '................', '................', '................', '................',
        '..BBBBBBBBBB....',
        '..BCCCCCCCCB....',
        '..BBBBBBBBBBBB..',
        '..BBBBBBBBBB..B.',
        '..BBBBBBBBBB..B.',
        '...BBBBBBBBBBB..',
        '....BBBBBBBB....',
        '................',
        '..SSSSSSSSSSSS..',
        '...SSSSSSSSSS...',
        '................'), {'B': '#5382a1', 'C': '#e76f00', 'S': '#3a6a8a'}),
    'typescript': ((
        '.TTTTTTTTTTTTTT.', 'TTTTTTTTTTTTTTTT', 'TTTTTTTTTTTTTTTT', 'TTTTTTTTTTTTTTTT', 'TTTTTTTTTTTTTTTT',
        'TTTTTTTTTTTTTTTT', 'TTTTTTTTTTTTTTTT', 'TTTTTTTTTTTTTTTT',
        'TTTTWWWWWTTWWWTT',
        'TTTTTTWTTTWTTTTT',
        'TTTTTTWTTTWTTTTT',
        'TTTTTTWTTTTWWTTT',
        'TTTTTTWTTTTTTWTT',
        'TTTTTTWTTTTTTWTT',
        'TTTTTTWTTTWWWTTT',
        '.TTTTTTTTTTTTTT.'), {'T': '#3178c6', 'W': SNOW}),
    'python': ((
        '....BBBBBB......',
        '...BBBBBBBB.....',
        '...BWBBBBBB.....',
        '...BBBBBBBB.....',
        '.......BBBB.....',
        '.BBBBBBBBBB.YYY.',
        'BBBBBBBBBBB.YYYY',
        'BBBBBBBBBB..YYYY',
        'BBBB..YYYYYYYYYY',
        'BBBB.YYYYYYYYYYY',
        '.BBB.YYYYYYYYYY.',
        '.....YYYY.......',
        '.....YYYYYYYY...',
        '.....YYYYYYWY...',
        '.....YYYYYYYY...',
        '......YYYYYY....'), {'B': '#3776ab', 'Y': '#ffd43b', 'W': SNOW}),
    'vue': _vue(),
    'flutter': _flutter(),
    'cpp': ((
        '.......HH.......',
        '.....hHHHHkk....',
        '...hhhHHHHHkkk..',
        '.hhhhhHHHHHHkkk.',
        'hhhhhhHHHHHHkkkk',
        'hhWWWWHHHHHHkkkk',
        'hWhhhhHHWHHHkWkk',
        'hWhhhhHWWWHkWWWk',
        'hWhhhhHHWHHHkWkk',
        'hWhhhhHHHHHHkkkk',
        'hhWWWWHHHHHHkkkk',
        'hhhhhhHHHHHHkkkk',
        '.hhhhhHHHHHHkkk.',
        '...hhhHHHHHkkk..',
        '.....hHHHHkk....',
        '.......HH.......'), {'h': '#659ad2', 'H': '#00599c', 'k': '#004482', 'W': SNOW}),
    'arch': _arch(16),
    'arch_big': _arch(32),
}

JAVA_STEAM = (
    ['.....O..O.......', '......O..O......', '.....O..O.......', '......O..O......'],
    ['......O..O......', '.....O..O.......', '......O..O......', '.....O..O.......'],
)


def logo(name, x, y, cell):
    rows, colors = LOGOS[name]
    return sprite(rows, colors, cell, x, y)


def flower_rows(face_r, petals, ring, pa, pb, w, h, cx, cy, offset=0.0, face=True):
    '''程序化生成向日葵头部（花瓣 + 脸盘），返回未描边的格子行；offset 为花瓣旋转弧度。'''
    def f(x, y):
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy <= face_r * face_r:
            if not face:
                return None
            t = dx + dy
            return 'H' if t < -face_r * 0.85 else 'D' if t > face_r * 0.75 else 'O'
        best = None
        for k in range(petals):
            a = (k + 0.5) * 2 * math.pi / petals + offset
            u = dx * math.cos(a) + dy * math.sin(a) - ring
            v = -dx * math.sin(a) + dy * math.cos(a)
            q = (u / pa) ** 2 + (v / pb) ** 2
            if q <= 1 and (best is None or q < best[0]):
                best = (q, k, u)
        if best:
            _, k, u = best
            if u < -pa * 0.5:
                return 'g'
            return ('Y' if k % 2 == 0 else 'G') if u < pa * 0.45 else ('L' if k % 2 == 0 else 'Y')
        return None
    return raster(w, h, f)


def ellipse_cells(cx, cy, a, b, angle, keys=('F', 'f')):
    out = {}
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    r = int(max(a, b)) + 2
    for y in range(int(cy) - r, int(cy) + r + 1):
        for x in range(int(cx) - r, int(cx) + r + 1):
            u = (x - cx) * ca + (y - cy) * sa
            v = -(x - cx) * sa + (y - cy) * ca
            if (u / a) ** 2 + (v / b) ** 2 <= 1:
                out[(x, y)] = keys[0] if v < 0 else keys[1]
    return out


FLOWER_COLORS = {'K': '#24120a', 'Y': SUN, 'G': SUN2, 'L': SUN_L, 'g': SUN3, 'O': FACE, 'H': FACE_L, 'D': FACE_D,
                 'E': '#1a0d05', 'W': SNOW, 'M': '#5a2c08', 'B': BLUSH, 'S': LEAF2, 's': LEAF3, 'F': LEAF, 'f': LEAF2}


def mascot_parts():
    '''吉祥物向日葵：返回 (宽, 高, 头部行, 身体行, 睁眼格, 闭眼格)。'''
    w, h, cx, cy = 27, 34, 13, 11
    head = outline(flower_rows(6.3, 12, 9.0, 3.4, 2.25, w, 22, cx, cy))
    body = ['.' * w for _ in range(h)]
    cells = {}
    for y in range(16, h - 3):
        cells[(cx - 1, y)] = 'S'
        cells[(cx, y)] = 's'
    cells.update(ellipse_cells(cx - 5.2, 24.5, 4.6, 1.9, -28))
    cells.update(ellipse_cells(cx + 5.2, 26.5, 4.6, 1.9, 28))
    cells.update(ellipse_cells(cx, h - 3.6, 8.2, 2.1, 0))
    cells.update(ellipse_cells(cx - 8.5, h - 4.6, 2.6, 1.3, -20))
    cells.update(ellipse_cells(cx + 8.5, h - 4.6, 2.6, 1.3, 20))
    body = outline(stamp(body, cells))
    eyes_open = {}
    for ex in (cx - 3, cx + 2):
        for dy in (-2, -1, 0):
            for dx in (0, 1):
                eyes_open[(ex + dx, cy + dy)] = 'E'
        eyes_open[(ex, cy - 2)] = 'W'
    eyes_closed = {(cx - 3, cy - 1): 'E', (cx - 2, cy - 1): 'E', (cx + 2, cy - 1): 'E', (cx + 3, cy - 1): 'E',
                   (cx - 4, cy - 2): 'E', (cx + 4, cy - 2): 'E'}
    mouth = {(cx - 3, cy + 2): 'M', (cx + 3, cy + 2): 'M'}
    for x in range(cx - 2, cx + 3):
        mouth[(x, cy + 3)] = 'M'
    mouth.update({(cx - 5, cy + 1): 'B', (cx - 4, cy + 1): 'B', (cx + 4, cy + 1): 'B', (cx + 5, cy + 1): 'B'})
    head = stamp(head, mouth)
    return w, h, head, body, eyes_open, eyes_closed


def mascot(svg, x, y, cell, delay=0.0, blink=4.0):
    '''会摇头、眨眼的向日葵；cell 为每个像素格的大小。'''
    w, h, head, body, eyes_open, eyes_closed = mascot_parts()
    name = 'mh%d' % cell
    svg.css('.%s{animation:%s 1.6s steps(1,end) infinite}'
            '@keyframes %s{0%%{transform:translate(0,0)}25%%{transform:translate(-%dpx,-%dpx)}'
            '50%%{transform:translate(0,0)}75%%{transform:translate(%dpx,-%dpx)}}'
            % (name, name, name, cell, cell, cell, cell))
    open_cls = window_cls(svg, 0, blink - 0.18, blink)
    shut_cls = window_cls(svg, blink - 0.18, blink, blink)
    eo = sprite(stamp(['.' * w] * 22, eyes_open), FLOWER_COLORS, cell)
    ec = sprite(stamp(['.' * w] * 22, eyes_closed), FLOWER_COLORS, cell)
    st = " style='animation-delay:-%ss'" % n(delay) if delay else ''
    return ("<g transform='translate(%s %s)'>%s<g class='%s'%s>%s<g class='%s'>%s</g>"
            "<g class='%s' opacity='0'>%s</g></g></g>"
            % (n(x), n(y), sprite(body, FLOWER_COLORS, cell), name, st, sprite(head, FLOWER_COLORS, cell),
               open_cls, eo, shut_cls, ec))


def mini_flower(cell, x, y, stem=6, face=True):
    '''小向日葵（花田用），返回 SVG 片段与尺寸。'''
    w, cy = 13, 6
    head = flower_rows(2.7, 10, 4.3, 1.9, 1.35, w, 12, 6, cy)
    if face:
        head = stamp(head, {(5, 5): 'E', (7, 5): 'E', (5, 7): 'M', (6, 7): 'M', (7, 7): 'M'})
    head = outline(head)
    cells = {}
    for yy in range(11, 11 + stem):
        cells[(6, yy)] = 'S'
    cells.update(ellipse_cells(3.6, 11 + stem * 0.55, 2.4, 1.0, -25))
    cells.update(ellipse_cells(8.4, 11 + stem * 0.7, 2.4, 1.0, 25))
    body = outline(stamp(['.' * w for _ in range(12 + stem)], cells))
    return sprite(body, FLOWER_COLORS, cell, x, y), sprite(head, FLOWER_COLORS, cell, x, y), w, 12 + stem


def bubble(x, y, w, h, msg, s=2, fill=SNOW, ink=INK, color=None, tail='left'):
    '''像素对话气泡。'''
    out = [path([(x + 2, y, w - 4, h), (x, y + 2, w, h - 4)], ink),
           path([(x + 2, y + 2, w - 4, h - 4)], fill)]
    tx = x + 10 if tail == 'left' else x + w - 16
    out.append(path([(tx, y + h, 6, 2), (tx + (0 if tail == 'left' else 2), y + h + 2, 4, 2),
                     (tx + (0 if tail == 'left' else 4), y + h + 4, 2, 2)], ink))
    out.append(path([(tx + 2, y + h - 2, 2, 2), (tx + 2, y + h, 2, 2)], fill))
    out.append(text(msg, x + (w - text_w(msg, s, 'b')) // 2, y + (h - 7 * s) // 2, s, color or ink, 'b'))
    return ''.join(out)
