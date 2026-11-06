#!/usr/bin/env python3
'''生成主页的静态像素海报：标题屏、玩家卡、背包、按钮、街机标题与页脚（仅标准库，输出确定）。

用法: python scripts/build_assets.py [输出目录]
'''
import math
import random
import sys
from pathlib import Path

import pixelkit as pk
from pixelkit import W, d_rects, n, path, pc


def nebula(svg, rng, cx, cy, rx, ry, color, core, cell=4, dur=11, delay=0):
    '''抖动像素星云：带噪声的椭圆分三档密度，核心换色。'''
    waves = [(rng.uniform(0.15, 0.5), rng.uniform(0.15, 0.5), rng.uniform(0, 6.3), rng.uniform(0.08, 0.2)) for _ in range(4)]
    levels = {1: [], 2: [], 3: []}
    for j in range(-ry - 2, ry + 3):
        for i in range(-rx - 2, rx + 3):
            v = 1 - (i / float(rx)) ** 2 - (j / float(ry)) ** 2
            v += sum(a * math.sin(i * fx + j * fy + ph) for fx, fy, ph, a in waves)
            if v > 0.62:
                levels[3].append((i, j))
            elif v > 0.32:
                levels[2].append((i, j))
            elif v > 0:
                levels[1].append((i, j))
    svg.css('.neb{animation:neb 11s ease-in-out infinite}@keyframes neb{0%,100%{opacity:.55}50%{opacity:1}}')
    body = ''.join("<path fill='%s' d='%s'/>" % (pk.dither(svg, col, lv), d_rects(pk.cells_rects(levels[lv], cell, cx, cy)))
                   for lv, col in ((1, color), (2, color), (3, core)) if levels[lv])
    return "<g class='neb' style='animation-duration:%ss;animation-delay:-%ss'>%s</g>" % (dur, delay, body)


def disc(r):
    return [(i, j) for j in range(-r, r) for i in range(-r, r) if (i + .5) ** 2 + (j + .5) ** 2 <= r * r]


def planet(svg, cx, cy, r, c, palette, dur=18):
    '''带环的气态行星：表面条纹在圆形裁剪内循环平移，形成自转。'''
    pid = svg.uid('pl')
    cells = disc(r)
    svg.add_def("<clipPath id='%s'><path d='%s'/></clipPath>" % (pid, d_rects(pk.cells_rects(cells, c, cx, cy))))
    period = 2 * r
    tex = {}
    for j in range(-r, r):
        for i in range(-r, -r + 2 * period):
            wob = math.sin((i % period) / float(period) * 2 * math.pi) * 1.3
            band = int(math.floor((j + r + wob) / (2.0 * r) * 7))
            tex.setdefault(palette[band % len(palette)], []).append((i, j))
    svg.css('.%s{animation:%s %ss linear infinite}@keyframes %s{to{transform:translateX(-%dpx)}}'
            % (pid, pid, dur, pid, period * c))
    surf = ''.join(path(pk.cells_rects(v, c, cx, cy), k) for k, v in sorted(tex.items()))
    shade = [(i, j) for i, j in cells if i + j + 1 > r * 0.6 or (i + j + 1 > r * 0.25 and (i + j) % 2 == 0)]
    light = [(i, j) for i, j in cells if i + j + 1 < -r * 1.05]
    ra, rb = r * 1.85, r * 0.5
    ring = {}
    for j in range(-int(rb) - 2, int(rb) + 3):
        for i in range(-int(ra) - 2, int(ra) + 3):
            q = ((i + .5) / ra) ** 2 + ((j + .5) / rb) ** 2
            if 0.62 <= q <= 1.0:
                ring[(i, j)] = '#ffd9a8' if q > 0.8 else '#c97a5a'
    back = {p: v for p, v in ring.items() if p[1] < 0}
    front = {p: v for p, v in ring.items() if p[1] >= 0}

    def ring_svg(part):
        by = {}
        for p, v in part.items():
            by.setdefault(v, []).append(p)
        return ''.join(path(pk.cells_rects(v, c, cx, cy), k) for k, v in sorted(by.items()))
    return (ring_svg(back) + "<g clip-path='url(#%s)'><g class='%s'>%s</g></g>" % (pid, pid, surf) +
            path(pk.cells_rects(shade, c, cx, cy), pk.INK, " opacity='.45'") +
            path(pk.cells_rects(light, c, cx, cy), pk.SNOW, " opacity='.3'") + ring_svg(front))


def moon(svg, cx, cy, r, c):
    cells = [(i, j) for i, j in disc(r) if (i + .5 - r * 0.45) ** 2 + (j + .5 + r * 0.25) ** 2 > (r * 0.85) ** 2]
    glow = [(i, j) for i, j in disc(r + 3) if (i + .5) ** 2 + (j + .5) ** 2 > (r + 0.5) ** 2]
    craters = [(i, j) for i, j in cells if (i * 7 + j * 3) % 11 == 0 and i < -1]
    dark = [(i, j) for i, j in cells if i + j > -1]
    svg.css('.mglow{animation:mglow 6s ease-in-out infinite}@keyframes mglow{0%,100%{opacity:.35}50%{opacity:.8}}')
    return ("<g class='mglow'>%s</g>" % "<path fill='%s' d='%s'/>" % (pk.dither(svg, '#6f5fd0', 1), d_rects(pk.cells_rects(glow, c, cx, cy))) +
            path(pk.cells_rects(cells, c, cx, cy), '#f3ecff') +
            path(pk.cells_rects(dark, c, cx, cy), '#c9bdf5') +
            path(pk.cells_rects(craters, c, cx, cy), '#a99ce6'))


SHIP = ('.......KKKK.........',
        '......KWPPPK........',
        '....KKPPPPPPKKKKK...',
        '....KPPPPPPPPPCCCKK.',
        '....KpPPPPPPPCCWWCCK',
        '....KppppppppppppppK',
        '....KKpppppKKKKKKKK.',
        '......KpppK.........',
        '.......KKKK.........')
SHIP_COLORS = {'K': pk.INK, 'P': pk.PURPLE, 'p': pk.PURPLE2, 'W': pk.SNOW, 'C': pk.CYAN,
               'O': pk.ORANGE, 'S': pk.SUN_L, 'R': pk.PINK}
FLAMES = (('', '', '', '..RO', '.SSO', '..RO'), ('', '', '', '.ROO', 'SSSO', '.ROO'))


def ship(svg, y, cycle, delay, cell=2, travel=None):
    svg.css(pk.BLINK_CSS)
    travel = travel or W + 140
    name = svg.uid('fly')
    svg.css('.%s{animation:%s %ss linear infinite;animation-delay:-%ss}'
            '@keyframes %s{0%%{transform:translateX(-80px)}45%%,100%%{transform:translateX(%dpx)}}'
            % (name, name, cycle, delay, name, travel))
    svg.css('.fl0{animation:fl .24s steps(1,end) infinite}.fl1{animation:fl .24s steps(1,end) infinite reverse}'
            '@keyframes fl{0%{opacity:1}50%{opacity:0}}')
    flames = ''.join("<g class='fl%d'>%s</g>" % (i, pk.sprite(list(f), SHIP_COLORS, cell)) for i, f in enumerate(FLAMES))
    svg.css(pk.BOB_CSS)
    return ("<g transform='translate(0 %d)'><g class='%s'><g class='bob' style='animation-duration:1.2s'>%s%s</g></g></g>"
            % (y, name, flames, pk.sprite(SHIP, SHIP_COLORS, cell)))


def sunflower_sun(svg, cx, hz, R, c):
    '''地平线上升起的向日葵太阳：渐变日轮 + 移动的合成波条纹 + 逐帧转动的花瓣。'''
    sid = svg.uid('sun')
    rows = [pk.SUN_L, pk.SUN, pk.SUN2, pk.ORANGE, pk.PINK]
    body = {}
    for i, j in disc(R):
        if j >= 0:
            continue
        t = (j + R) / float(R) * len(rows)
        k = min(len(rows) - 1, int(t))
        if t - k < 0.25 and k and (i + j) % 2 == 0:
            k -= 1
        body.setdefault(rows[k], []).append((i, j))
    gap, top = 3 * c, hz - R * c * 0.55
    stripes = [(cx - R * c, int(top + y), 2 * R * c, c) for y in range(-gap, int(hz - top) + gap, gap)]
    svg.css('.%s{animation:%s 1.4s linear infinite}@keyframes %s{to{transform:translateY(%dpx)}}' % (sid, sid, sid, gap))
    svg.add_def("<clipPath id='%sc'><rect x='%d' y='%d' width='%d' height='%d'/></clipPath>"
                "<mask id='%sm'><rect x='0' y='0' width='%d' height='%d' fill='#fff'/>"
                "<g clip-path='url(#%sc)'><g class='%s'><path fill='#000' d='%s'/></g></g></mask>"
                % (sid, cx - R * c, int(top), 2 * R * c, int(hz - top), sid, W, hz, sid, sid, d_rects(stripes)))
    disc_svg = ''.join(path(pk.cells_rects(v, c, cx, hz), k) for k, v in body.items())
    frames = []
    count = 20
    step = 2 * math.pi / count
    layers = ((R + 4.8, 5.4, 2.3, step / 2, pk.SUN3, pk.SUN2), (R + 4.0, 4.8, 2.0, 0.0, pk.SUN, pk.SUN_L))

    def petal_hit(dx, dy, off, ring, pa, pb, extra, base, tip):
        for k in range(count):
            a = off + extra + k * step
            u = dx * math.cos(a) + dy * math.sin(a) - ring
            v = -dx * math.sin(a) + dy * math.cos(a)
            if (u / pa) ** 2 + (v / pb) ** 2 <= 1:
                return tip if u > pa * 0.45 else base
        return None
    for f in range(4):
        off = f / 4.0 * step
        petals = {}
        for j in range(-R - 12, 0):
            for i in range(-R - 12, R + 12):
                dx, dy = i + .5, j + .5
                if dx * dx + dy * dy <= (R + .3) ** 2:
                    continue
                hit = None
                for layer in layers:
                    hit = petal_hit(dx, dy, off, *layer) or hit
                if hit:
                    petals[(i, j)] = hit
        by = {}
        rim = []
        for (i, j), v in petals.items():
            by.setdefault(v, []).append((i, j))
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (i + di, j + dj)
                if q not in petals and (q[0] + .5) ** 2 + (q[1] + .5) ** 2 > (R + .3) ** 2 and q[1] < 0:
                    rim.append(q)
        g = path(pk.cells_rects(set(rim), c, cx, hz), '#7a4510') + ''.join(
            path(pk.cells_rects(v, c, cx, hz), k) for k, v in sorted(by.items()))
        cls = pk.window_cls(svg, f * 0.5, (f + 1) * 0.5, 2.0)
        frames.append("<g class='%s'%s>%s</g>" % (cls, '' if f == 0 else " style='opacity:0'", g))
    halo = [(i, j) for i, j in disc(R + 16) if j < 0 and (i + .5) ** 2 + (j + .5) ** 2 > (R + 11) ** 2]
    svg.css('.halo{animation:halo 3s ease-in-out infinite}@keyframes halo{0%,100%{opacity:.3}50%{opacity:.9}}')
    return ("<path class='halo' fill='%s' d='%s'/>" % (pk.dither(svg, pk.PINK, 1), d_rects(pk.cells_rects(halo, c, cx, hz))) +
            ''.join(frames) + "<g mask='url(#%sm)'>%s</g>" % (sid, disc_svg))


def mountains(rng, x0, x1, base, peaks, color, rim, step=4):
    tops = []
    for x in range(x0, x1, step):
        h = max(ph - abs(x - px) * sl for px, ph, sl in peaks)
        h = max(4, int(h + rng.choice((-2, 0, 0, 2))) // 2 * 2)
        tops.append((x, h))
    body = [(x, base - h, step, h) for x, h in tops]
    lit = [(x, base - h, step, 2) for (x, h), (_, hn) in zip(tops, tops[1:] + tops[-1:]) if hn >= h]
    return path(pk.merge(body), color) + path(pk.merge(lit), rim)


def floor(svg, hz, H, vx, dur=1.1):
    out = [pk.bands(svg, 0, W, [(hz, '#2a1252'), (hz + 14, '#1d0d40'), (hz + 34, '#150a32'), (H - 16, '#0e0a26'), (H, None)])]
    yv, lines = hz - 34, []
    for i in range(-15, 16):
        xb = vx + i * 64
        xh = vx + (xb - vx) * (hz - yv) / float(H + 40 - yv)
        xe = vx + (xb - vx) * (H - yv) / float(H + 40 - yv)
        lines.append("<line x1='%s' y1='%d' x2='%s' y2='%d'/>" % (n(round(xh)), hz, n(round(xe)), H))
    out.append("<g stroke='%s' stroke-width='2' opacity='.55'>%s</g>" % (pk.PINK2, ''.join(lines)))
    span, dz = H - hz, 0.55
    for k in range(10):
        z0 = 1 + k * dz
        y0 = hz + span / z0
        frames = []
        for f in range(7):
            z = max(0.8, z0 - f / 6.0 * dz)
            y = hz + span / z
            op = max(0.15, min(1.0, (y - hz) / 46.0)) * (1 if y < H - 8 else 0.4)
            frames.append('%s{transform:translateY(%spx);opacity:%s}' % (pc(f / 6.0 * 100), n(round(y - y0, 1)), n(round(op, 2))))
        name = 'gl%d' % k
        svg.css('@keyframes %s{%s}.%s{animation:%s %ss linear infinite}' % (name, ''.join(frames), name, name, dur))
        out.append("<rect class='%s' x='0' y='%s' width='%d' height='2' fill='%s'/>" % (name, n(round(y0)), W, pk.PINK))
    out.append(path([(0, hz, W, 2)], pk.SUN_L) + path([(0, hz + 2, W, 2)], pk.PINK))
    return ''.join(out)


def hero_title(svg, title, y, s):
    x = pk.cx_text(title, s, 't')
    tw = pk.text_w(title, s, 't')
    th = 8 * s
    svg.css('.wv{animation:wv 5s cubic-bezier(.3,0,.3,1) infinite}'
            '@keyframes wv{0%,13%,100%{transform:translateY(0)}5%{transform:translateY(-10px)}9%{transform:translateY(2px)}}')
    band = []
    for r in range(-4, th + 6, 2):
        bx = x - 70 + (th - r) // 2 // 2 * 2
        band.append((bx, y + r, 8, 2))
        band.append((bx + 12, y + r, 4, 2))
    svg.add_def("<path id='shine' fill='%s' opacity='.8' d='%s'/>" % (pk.SNOW, d_rects(band)))
    svg.css('.shn{animation:shn 5s linear infinite}'
            '@keyframes shn{0%%,30%%{transform:translateX(0)}52%%,100%%{transform:translateX(%dpx)}}' % (tw + 150))
    out, cx = [], x
    fills = ((range(0, 2), pk.SUN_L), (range(2, 4), pk.SUN), (range(4, 6), pk.ORANGE), (range(6, 8), pk.PINK))
    for i, ch in enumerate(title):
        main = pk.text_rects(ch, cx, y, s, 't')
        deep = [(a, b + 9, c, d) for a, b, c, d in main]
        mid = [(a, b + 5, c, d) for a, b, c, d in main]
        edge = [(a - 4, b - 4, c + 8, d + 8) for a, b, c, d in main + deep]
        clip = svg.uid('tl')
        svg.add_def("<clipPath id='%s'><path d='%s'/></clipPath>" % (clip, d_rects(main)))
        g = (path(edge, pk.INK) + path(deep, pk.PURPLE3) + path(mid, pk.PURPLE2) +
             ''.join(path(pk.text_rects(ch, cx, y, s, 't', rows=r), col) for r, col in fills) +
             "<g clip-path='url(#%s)'><use class='shn' href='#shine'/></g>" % clip)
        out.append("<g class='wv' style='animation-delay:%ss'>%s</g>" % (n(round(i * 0.07, 2)), g))
        cx += pk.advance(ch, 't') * s
    return ''.join(out)


def typed_cycle(svg, lines, y, s, color, prefix='▶ ', type_dt=0.07, hold=2.8, erase_dt=0.03, gap=0.45):
    '''多条标语轮流打字、停留、退格；关闭动画时只显示第一条。'''
    spans, t = [], 0.0
    for line in lines:
        t1 = t + len(line) * type_dt
        t2 = t1 + hold
        t3 = t2 + len(line) * erase_dt
        spans.append((t, t1, t2, t3))
        t = t3 + gap
    cycle = t
    svg.css(pk.BLINK_CSS)
    adv = pk.advance('A', 'b') * s
    out = []
    for k, (line, (t0, t1, t2, t3)) in enumerate(zip(lines, spans)):
        pw = len(prefix) * adv
        full = len(line) * adv
        x = (W - pw - full) // 2
        tx = x + pw
        cid, kid = svg.uid('ty'), svg.uid('tk')
        a, b, c, d = (v / cycle * 100 for v in (t0, t1, t2, t3))
        svg.css('@keyframes %s{0%%,%s{transform:translateX(-%dpx)}%s,%s{transform:translateX(0)}%s,100%%{transform:translateX(-%dpx)}}'
                '.%s{animation:%s %ss steps(%d,end) infinite}'
                % (cid, pc(a), full, pc(b), pc(c), pc(d), full, cid, cid, n(round(cycle, 2)), len(line)))
        svg.css('@keyframes %s{0%%,%s{transform:translateX(0)}%s,%s{transform:translateX(%dpx)}%s,100%%{transform:translateX(0)}}'
                '.%s{animation:%s %ss steps(%d,end) infinite}'
                % (kid, pc(a), pc(b), pc(c), full, pc(d), kid, kid, n(round(cycle, 2)), len(line)))
        svg.add_def("<clipPath id='%s'><rect class='%s' x='%d' y='%d' width='%d' height='%d'/></clipPath>"
                    % (cid, cid, tx, y - 2, full, 9 * s + 4))
        vis = pk.window_cls(svg, t0, t3 + gap * 0.6, round(cycle, 2))
        body = (pk.text(prefix.strip(), x, y, s, pk.PINK, 'b', shadow=pk.INK) +
                "<g clip-path='url(#%s)'>%s</g>" % (cid, pk.text(line, tx, y, s, color, 'b', shadow=pk.INK)) +
                "<g class='blk'><rect class='%s' style='transform:translateX(%dpx)' x='%d' y='%d' width='%d' height='%d' fill='%s'/></g>"
                % (kid, full, tx, y, 2 * s, 7 * s, color))
        out.append("<g class='%s'%s>%s</g>" % (vis, '' if k == 0 else " style='opacity:0'", body))
    return ''.join(out)


def build_hero():
    H, HZ = 300, 222
    svg = pk.Svg(W, H, 'cxsunflower - pixel title screen: beginning programmer, Arch Linux user')
    rng = random.Random(20261106)
    b = [pk.bands(svg, 0, W, [(0, pk.BG), (62, '#100c2c'), (110, '#170f3a'), (148, '#221246'),
                               (178, '#331552'), (202, '#48195c'), (HZ, None)]),
         nebula(svg, rng, 150, 150, 30, 7, pk.PURPLE2, pk.PINK2), nebula(svg, rng, 640, 136, 26, 6, pk.PURPLE2, pk.PURPLE, delay=4),
         pk.starfield(svg, rng, (6, 6, W - 6, 190), 80, 24, 6),
         moon(svg, 78, 50, 8, 3),
         planet(svg, 768, 62, 12, 3, ('#ffb26b', '#ff8a5c', '#ffd27a', '#e0662e', '#ff9a5c', '#c2389e', '#ffc58a')),
         pk.shooting_star(svg, 560, 8, 150, 9, 2), pk.shooting_star(svg, 300, 20, 120, 13, 8),
         pk.shooting_star(svg, 120, 10, 110, 11, 5, direction=1),
         ship(svg, 150, 20, 4),
         sunflower_sun(svg, W // 2, HZ, 21, 3)]
    b.append(mountains(rng, 0, W, HZ, [(40, 46, .5), (190, 34, .45), (300, 52, .55), (560, 44, .5), (700, 58, .5), (830, 40, .6)],
                       '#2b1858', '#6b3fd4'))
    b.append(mountains(rng, 0, W, HZ, [(0, 24, .3), (150, 30, .4), (330, 16, .35), (520, 18, .35), (660, 30, .4), (800, 26, .3)],
                       '#1b0f3d', pk.PINK2))
    b.append(floor(svg, HZ, H, W // 2))
    b.append(hero_title(svg, 'CXSUNFLOWER', 34, 7))
    b.append(typed_cycle(svg, ['BEGINNING PROGRAMMER', 'ARCH LINUX USER', 'LEARN. BUILD. EXPLORE.', 'ONE PIXEL AT A TIME'],
                         114, 2, pk.CYAN))
    press = 'PRESS START'
    px = pk.cx_text(press, 2, 'b')
    svg.css('.nudge{animation:nudge .8s steps(2,end) infinite}@keyframes nudge{50%{transform:translateX(4px)}}'
            '.nudgel{animation:nudgel .8s steps(2,end) infinite}@keyframes nudgel{50%{transform:translateX(-4px)}}')
    b.append("<g class='blk' style='animation-duration:1.6s'>%s</g>" % pk.text(press, px, 266, 2, pk.SUN, 'b', shadow=pk.INK))
    b.append("<g class='nudge'>%s</g><g class='nudgel'>%s</g>"
             % (pk.text('▶', px - 24, 266, 2, pk.PINK, shadow=pk.INK), pk.text('◀', px + pk.text_w(press, 2, 'b') + 14, 266, 2, pk.PINK, shadow=pk.INK)))
    b.append(pk.mascot(svg, 34, 194, 3))
    b.append("<g class='%s' style='opacity:0'>%s</g>" % (pk.window_cls(svg, 1.2, 4.2, 9), pk.bubble(108, 168, 84, 24, 'HELLO!', color=pk.PURPLE2)))
    b.append(pk.scanlines(svg, 0, 0, W, H, opacity=0.18))
    b.append(pk.side_frame(W, H) + pk.cap_frame(W, H, top=True))
    return svg.render(b)


def checkbox(x, y, checked, color):
    out = pk.bevel(x, y, 16, 16, pk.BG2, pk.LINE, pk.INK)
    if checked:
        out += pk.sprite(('......#', '.....##', '#...##.', '##.##..', '.###...', '..#....'), {'#': color}, 2, x + 1, y + 2)
    return out


def seg_bar(x, y, segs, color, dim, seg_w=14, seg_h=10, gap=2):
    out = [path([(x - 2, y - 2, segs * (seg_w + gap) + 2, seg_h + 4)], pk.INK)]
    for i in range(segs):
        out.append(path([(x + i * (seg_w + gap), y, seg_w, seg_h)], dim))
    return ''.join(out), [(x + i * (seg_w + gap), y, seg_w, seg_h) for i in range(segs)]


def lit_seg(rect, color):
    x, y, w, h = rect
    return path([rect], color) + path([(x, y, w, 2)], pk.mix(color, 0.45)) + path([(x, y + h - 2, w, 2)], pk.mix(color, -0.3))


def build_profile():
    H = 252
    svg = pk.Svg(W, H, 'Player card - beginning programmer, Arch Linux user, graduated, based in Shanghai')
    rng = random.Random(77)
    b = [pk.starfield(svg, rng, (6, 2, W - 6, H - 2), 30, 10, 2)]
    win, top = pk.window(svg, 24, 10, 798, 230, 'PLAYER 1 - STATUS', icon_name='user')
    b.append(win)
    px, py, pw, ph = 40, top + 10, 150, 178
    b.append(pk.bevel(px, py, pw, ph, '#1d1450', pk.FRAME2, pk.INK))
    b.append(pk.bands(svg, px + 4, pw - 8, [(py + 4, '#24185e'), (py + 60, '#33186a'), (py + 112, '#4a1d6e'), (py + ph - 26, None)], tz=4))
    b.append(pk.starfield(svg, random.Random(9), (px + 8, py + 8, px + pw - 8, py + 90), 14, 5, 1, colors=(pk.WHITE, pk.SUN, pk.CYAN)))
    b.append(path([(px + 4, py + ph - 26, pw - 8, 22)], '#1f3a2a') + path([(px + 4, py + ph - 26, pw - 8, 2)], pk.LEAF2) +
             path([(px + 4 + i * 12, py + ph - 24, 4, 2) for i in range(12)], pk.LEAF3))
    b.append(pk.mascot(svg, px + (pw - 108) // 2, py + ph - 4 - 138, 4, delay=0.4, blink=5.2))
    b.append(pk.bevel(px + 6, py + 6, 30, 18, pk.PINK2, pk.PINK, pk.PINK3) + pk.text('P1', px + 13, py + 9, 2, pk.SNOW, 'b'))
    b.append(pk.bevel(px + pw - 72, py + 6, 66, 18, pk.PURPLE2, pk.PURPLE, pk.PURPLE3) + pk.text('LV.1', px + pw - 66, py + 9, 2, pk.SNOW, 'b'))
    ix = 206
    b.append(pk.text2('CXSUNFLOWER', ix, top + 14, 3, pk.SUN_L, pk.ORANGE))
    facts = (('user', pk.CYAN, 'Beginning programmer'), ('terminal', pk.BLUE, 'Arch Linux user'),
             ('book-open', pk.SUN, 'Graduated'), ('map-pin', pk.PINK, 'Shanghai'))
    for i, (ic, col, line) in enumerate(facts):
        y = top + 58 + i * 30
        b.append(pk.icon(ic, ix, y - 5, 24, col))
        b.append(pk.text(line, ix + 30, y, 2, pk.WHITE, shadow=pk.INK))
    b.append(path([(484, y0, 2, 2) for y0 in range(top + 12, top + 188, 6)], pk.LINE))
    rx = 498
    b.append(pk.icon('flag', rx, top + 10, 24, pk.CYAN) + pk.text('QUEST LOG', rx + 32, top + 15, 2, pk.CYAN, 'b', shadow=pk.INK))
    quests = (('Learn. Build. Explore.', True), ('Open source side quests', True), ('One pixel at a time', False))
    cycle = 4.5
    for i, (q, done) in enumerate(quests):
        y = top + 44 + i * 26
        b.append(checkbox(rx + 16, y - 2, done, pk.GREEN))
        if not done:
            b.append("<g class='blk'>%s</g>" % path([(rx + 21, y + 4, 6, 6)], pk.SUN))
        b.append(pk.text(q, rx + 38, y + 1, 2, pk.WHITE if done else pk.SUN, shadow=pk.INK))
        cls = pk.window_cls(svg, i * 1.5, (i + 1) * 1.5, cycle)
        b.append("<g class='%s'%s>%s</g>" % (cls, '' if i == 0 else " style='opacity:0'", pk.text('▶', rx, y + 1, 2, pk.PINK)))
    bars = (('HP', pk.RED, 10, 'MAX'), ('MP', pk.CYAN, 7, '7/10'), ('XP', pk.SUN, 3, ''))
    for i, (label, col, lit, note) in enumerate(bars):
        y = top + 132 + i * 20
        b.append(pk.text(label, rx, y, 2, col, 'b', shadow=pk.INK))
        frame_svg, segs = seg_bar(rx + 38, y + 1, 10, col, pk.LINE, seg_w=12)
        b.append(frame_svg)
        if label != 'XP':
            b.append(''.join(lit_seg(r, col) for r in segs[:lit]))
            b.append(pk.text(note, rx + 190, y, 2, pk.SOFT))
            continue
        xp_cycle = 8.0
        for k, r in enumerate(segs):
            on = 0.4 + k * 0.45
            cls = pk.window_cls(svg, 0 if k < lit else on, 7.2, xp_cycle)
            b.append("<g class='%s'%s>%s</g>" % (cls, '' if k < lit else " style='opacity:0'", lit_seg(r, col)))
        lv = pk.window_cls(svg, 0.4 + 9 * 0.45 + 0.3, 7.2, xp_cycle)
        b.append("<g class='%s' style='opacity:0'><g class='blk' style='animation-duration:.4s'>%s</g></g>"
                 % (lv, pk.text('LEVEL UP!', rx + 190, y, 2, pk.SUN, 'b', shadow=pk.INK)))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


ITEMS = (('kotlin', 'KOTLIN', 'LANGUAGE', 'Main weapon. Concise and null-safe.', '#b48cff'),
         ('java', 'JAVA', 'LANGUAGE', 'Trusty classic that runs everywhere.', '#f8a64a'),
         ('typescript', 'TYPESCRIPT', 'LANGUAGE', 'Typed scrolls for the web.', '#5aa2ff'),
         ('python', 'PYTHON', 'LANGUAGE', 'Swiss-army snake for scripts.', '#ffd43b'),
         ('vue', 'VUE', 'FRAMEWORK', 'Crafts reactive web interfaces.', '#41d391'),
         ('flutter', 'FLUTTER', 'FRAMEWORK', 'One codebase, many screens.', '#47c5fb'),
         ('cpp', 'C++', 'LANGUAGE', 'Heavy hammer. Handle with care.', '#7fb0ea'),
         ('arch', 'ARCH LINUX', 'OPERATING SYSTEM', 'Home base. I use Arch, btw.', '#38a8e8'))


def build_inventory():
    H = 214
    svg = pk.Svg(W, H, 'Inventory - Kotlin, Java, TypeScript, Python, Vue, Flutter, C++, Arch Linux')
    rng = random.Random(31)
    b = [pk.starfield(svg, rng, (6, 2, W - 6, H - 2), 26, 8, 1)]
    b.append(path([(28, 30, 798, 176)], pk.INK))
    b.append(pk.bevel(24, 26, 798, 176, pk.PANEL, pk.PANEL2, pk.BG2))
    b.append(pk.bevel(40, 10, 172, 28, pk.PURPLE2, pk.PURPLE, pk.PURPLE3))
    b.append(pk.icon('briefcase', 48, 12, 24, pk.SUN_L) + pk.text('INVENTORY', 80, 17, 2, pk.SNOW, 'b', shadow=pk.PURPLE3))
    count = 'ITEMS %d/12' % len(ITEMS)
    b.append(pk.text(count, 806 - pk.text_w(count, 2, 'b'), 40, 2, pk.MUTED, 'b'))
    slot, gap, sy = 56, 8, 58
    sx = 24 + (798 - (12 * slot + 11 * gap)) // 2
    step = 2.5
    cycle = step * len(ITEMS)
    svg.css('.steam0{animation:fl .9s steps(1,end) infinite}.steam1{animation:fl .9s steps(1,end) infinite reverse}'
            '@keyframes fl{0%{opacity:1}50%{opacity:0}}')
    for i in range(12):
        x = sx + i * (slot + gap)
        b.append(pk.bevel(x, sy, slot, slot, '#0f0c26', pk.INK, pk.LINE, pk.INK))
        if i >= len(ITEMS):
            b.append(pk.icon('lock', x + 16, sy + 16, 24, pk.LINE))
            continue
        name = ITEMS[i][0]
        a, bb = i * step / cycle * 100, (i * step + 0.3) / cycle * 100
        hop = svg.uid('hop')
        svg.css('@keyframes %s{0%%,%s{transform:translateY(0)}%s{transform:translateY(-6px)}%s,100%%{transform:translateY(0)}}'
                '.%s{animation:%s %ss steps(1,end) infinite}' % (hop, pc(a), pc(a + 0.01), pc(bb), hop, hop, n(cycle)))
        g = pk.logo(name, x + 4, sy + 4, 3)
        if name == 'java':
            g += ''.join("<g class='steam%d'>%s</g>" % (k, pk.sprite(f, {'O': '#f89820'}, 3, x + 4, sy + 4))
                         for k, f in enumerate(pk.JAVA_STEAM))
        b.append("<g class='%s'>%s</g>" % (hop, g))
    cur = svg.uid('cur')
    stops = ''.join('%s{transform:translateX(%dpx)}' % (pc(i * step / cycle * 100), i * (slot + gap)) for i in range(len(ITEMS)))
    svg.css('@keyframes %s{%s}.%s{animation:%s %ss steps(1,end) infinite}' % (cur, stops, cur, cur, n(cycle)))
    corners = pk.brackets(sx - 5, sy - 5, slot + 10, slot + 10, pk.SUN, 12, 4)
    arrow = pk.sprite(('#######', '.#####.', '..###..', '...#...'), {'#': pk.PINK}, 2, sx + slot // 2 - 7, sy - 18)
    svg.css('.arrow{animation:arrow .6s steps(2,end) infinite}@keyframes arrow{50%{transform:translateY(3px)}}')
    b.append("<g class='%s'>%s<g class='arrow'>%s</g></g>" % (cur, corners, arrow))
    dx, dy, dw, dh = 40, 128, 766, 64
    b.append(pk.bevel(dx, dy, dw, dh, '#0f0c26', pk.INK, pk.LINE, pk.INK))
    for i, (name, title, kind, desc, color) in enumerate(ITEMS):
        g = (pk.logo(name, dx + 12, dy + 8, 3) +
             pk.text2(title, dx + 76, dy + 10, 3, pk.mix(color, 0.35), color) +
             pk.text(desc, dx + 76, dy + 40, 2, pk.SOFT))
        tag_x = dx + 76 + pk.text_w(title, 3, 'b') + 16
        g += pk.bevel(tag_x, dy + 12, pk.text_w(kind, 2) + 16, 20, pk.PANEL2, pk.LINE, pk.INK) + pk.text(kind, tag_x + 8, dy + 16, 2, pk.MUTED)
        cls = pk.window_cls(svg, i * step, (i + 1) * step, cycle)
        b.append("<g class='%s'%s>%s</g>" % (cls, '' if i == 0 else " style='opacity:0'", g))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


STAR_ICON = ('.....##.....', '....####....', '....####....', '############', '.##########.', '..########..',
             '...######...', '...######...', '..###..###..', '..##....##..', '.##......##.')
BOOK_ICON = ('.##########.', '#WWWWWWWWWW#', '#W#######WW#', '#WWWWWWWWWW#', '#W#####WWWW#', '#WWWWWWWWWW#',
             '#W######WWW#', '#WWWWWWWWWW#', '#WWWWWWWWWW#', '############', '#C#C#C#C#C##')


def build_button(label, kind, face, light, dark, ink, side):
    Wb, H = W // 2, 96
    svg = pk.Svg(Wb, H, label)
    rng = random.Random(len(label) * 13)
    b = [pk.starfield(svg, rng, (6, 2, Wb - 6, H - 2), 10, 4, 0)]
    bx, by, bw, bh = 20, 16, Wb - 40, 60
    b.append(path([(bx + 4, by + 6, bw, bh)], pk.INK))
    press = svg.uid('pr')
    svg.css('@keyframes %s{0%%,86%%{transform:translateY(0)}88%%,94%%{transform:translateY(3px)}96%%,100%%{transform:translateY(0)}}'
            '.%s{animation:%s 4s steps(1,end) infinite;animation-delay:-%ss}' % (press, press, press, n(1.5 if kind == 'star' else 0)))
    clip = svg.uid('bc')
    svg.add_def("<clipPath id='%s'><rect x='%d' y='%d' width='%d' height='%d'/></clipPath>" % (clip, bx + 4, by + 4, bw - 8, bh - 8))
    glint = []
    for r in range(0, bh, 2):
        glint.append((bx - 40 + (bh - r) // 2 // 2 * 2, by + r, 10, 2))
        glint.append((bx - 24 + (bh - r) // 2 // 2 * 2, by + r, 4, 2))
    svg.css('.gl{animation:gl 4s linear infinite}@keyframes gl{0%%,40%%{transform:translateX(0)}62%%,100%%{transform:translateX(%dpx)}}' % (bw + 90))
    if kind == 'star':
        ic = pk.outline(STAR_ICON, 'K', pad=1)
        icon_svg = pk.sprite(ic, {'K': pk.INK, '#': pk.SUN_L}, 3)
        spin = 'spin'
        svg.css('.spin{transform-box:fill-box;transform-origin:center;animation:spin 2.4s steps(1,end) infinite}'
                '@keyframes spin{0%{transform:scaleX(1)}10%{transform:scaleX(.66)}20%{transform:scaleX(.33)}'
                '30%{transform:scaleX(-.33)}40%{transform:scaleX(-.66)}50%{transform:scaleX(-1)}60%{transform:scaleX(-.66)}'
                '70%{transform:scaleX(-.33)}80%{transform:scaleX(.33)}90%{transform:scaleX(.66)}}')
    else:
        ic = pk.outline(BOOK_ICON, 'K', pad=1)
        icon_svg = pk.sprite(ic, {'K': pk.INK, '#': pk.CYAN3, 'W': pk.SNOW, 'C': pk.SUN}, 3)
        spin = 'bob'
        svg.css(pk.BOB_CSS)
    tx = bx + 70
    face_svg = (pk.bevel(bx, by, bw, bh, face, light, dark) +
                "<g transform='translate(%d %d)'><g class='%s'>%s</g></g>" % (bx + 14, by + 10, spin, icon_svg) +
                pk.text(label, tx + 2, by + 22, 3, dark, 'b') + pk.text(label, tx, by + 20, 3, ink, 'b') +
                "<g class='nudge'>%s</g>" % pk.text('▶', bx + bw - 34, by + 22, 3, ink) +
                "<g clip-path='url(#%s)'><path class='gl' fill='%s' opacity='.45' d='%s'/></g>" % (clip, pk.SNOW, d_rects(glint)))
    svg.css('.nudge{animation:nudge .8s steps(2,end) infinite}@keyframes nudge{50%{transform:translateX(4px)}}')
    b.append("<g class='%s'>%s</g>" % (press, face_svg))
    b.append(path([(2, 0, 2, H)] if side == 'left' else [(Wb - 4, 0, 2, H)], pk.FRAME))
    return svg.render(b)


SNAKE_ICON = ('...GGGG.....', '..GGGGGG....', '..GWGGWG....', '..GGGGGG.RR.', '...GGGG..R..', '....GG......',
              '.GGGGG......', 'GGGGG..GGG..', 'GG....GGGGG.', 'GGGGGGGG.GG.', '.GGGGGG..GG.', '.........G..')


def build_arcade():
    H = 118
    svg = pk.Svg(W, H, 'Arcade cabinet - contribution snake')
    rng = random.Random(55)
    b = [pk.starfield(svg, rng, (6, 2, W - 6, 40), 14, 5, 0)]
    x, y, w, h = 24, 8, 798, 92
    b.append(path([(x + 4, y + 4, w, h)], pk.INK))
    b.append(pk.bevel(x, y, w, h, '#1d0f3f', pk.PURPLE2, pk.INK))
    b.append(pk.bands(svg, x + 4, w - 8, [(y + 4, '#2a1056'), (y + 30, '#22104a'), (y + 64, '#1a0d3c'), (y + h - 4, None)]))
    bulbs = []
    for bx in range(x + 12, x + w - 12, 16):
        bulbs += [(bx, y + 8), (bx, y + h - 12)]
    for by in range(y + 24, y + h - 20, 16):
        bulbs += [(x + 8, by), (x + w - 12, by)]
    groups = [[], [], []]
    for i, p in enumerate(sorted(bulbs)):
        groups[i % 3].append(p)
    svg.css('.bl0,.bl1,.bl2{animation:bl .9s steps(1,end) infinite}.bl1{animation-delay:-.3s}.bl2{animation-delay:-.6s}'
            '@keyframes bl{0%{opacity:1}33%{opacity:.25}}')
    b.append(path([(px, py, 4, 4) for px, py in bulbs], pk.SUN3))
    for k, g in enumerate(groups):
        b.append("<g class='bl%d'>%s%s</g>" % (k, path([(px, py, 4, 4) for px, py in g], pk.SUN),
                                               path([(px, py, 2, 2) for px, py in g], pk.SNOW)))
    title = 'CONTRIBUTION SNAKE'
    b.append(pk.text2(title, pk.cx_text(title, 3, 'b'), y + 24, 3, pk.SUN_L, pk.ORANGE))
    sub = 'Eat every commit. One square a day.'
    b.append(pk.text(sub, pk.cx_text(sub, 2), y + 58, 2, pk.SOFT, shadow=pk.INK))
    svg.css('.tongue{animation:fl .5s steps(1,end) infinite}@keyframes fl{0%{opacity:1}50%{opacity:0}}')
    ic = pk.outline(SNAKE_ICON, 'K', pad=1)
    b.append(pk.sprite([r.replace('R', '.') for r in ic], {'K': pk.INK, 'G': pk.LEAF, 'W': pk.SNOW}, 3, x + 30, y + 18))
    b.append("<g class='tongue'>%s</g>" % pk.sprite(ic, {'R': pk.RED}, 3, x + 30, y + 18))
    b.append(pk.text('1P', x + w - 120, y + 26, 2, pk.CYAN, 'b', shadow=pk.INK))
    svg.css(pk.BLINK_CSS)
    b.append("<g class='blk' style='animation-duration:1.4s'>%s</g>" % pk.text('INSERT', x + w - 120, y + 46, 2, pk.PINK, 'b', shadow=pk.INK))
    b.append("<g class='blk' style='animation-duration:1.4s'>%s</g>" % pk.text('COIN', x + w - 120, y + 64, 2, pk.PINK, 'b', shadow=pk.INK))
    b.append(path([(x, y + h + 2, w, 8)], '#231a4a') + path([(x, y + h + 2, w, 2)], '#3a2f72') +
             path([(x, y + h + 10, w, 8)], pk.INK))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


ROCKET = ('....R....', '...RRR...', '..WWWWW..', '..WWCWW..', '..WCCCW..', '..WWCWW..', '..WWWWW..',
          '..WWWWW..', '.RWWWWWR.', 'RRWWWWWRR', 'RR.WWW.RR')


def build_footer():
    H, HZ = 236, 168
    svg = pk.Svg(W, H, 'Thanks for visiting - see you in space')
    rng = random.Random(4242)
    b = [pk.bands(svg, 0, W, [(0, pk.BG), (60, '#100c2c'), (104, '#170f3a'), (136, '#221246'), (156, '#2f1450'), (HZ, None)]),
         pk.starfield(svg, rng, (6, 4, W - 6, 150), 60, 18, 4),
         moon(svg, 760, 58, 10, 3),
         pk.shooting_star(svg, 520, 6, 120, 10, 3), pk.shooting_star(svg, 240, 14, 100, 12, 9, direction=1)]
    flame_cls = ('.rf0{animation:fl .2s steps(1,end) infinite}.rf1{animation:fl .2s steps(1,end) infinite reverse}'
                 '@keyframes fl{0%{opacity:1}50%{opacity:0}}')
    svg.css(flame_cls, '.rk{animation:rk 12s cubic-bezier(.5,0,.9,.5) infinite}'
            '@keyframes rk{0%,50%{transform:translateY(0)}78%,100%{transform:translateY(-250px)}}')
    rk = pk.outline(ROCKET, 'K', pad=1)
    rocket = pk.sprite(rk, {'K': pk.INK, 'R': pk.RED, 'W': pk.WHITE, 'C': pk.CYAN}, 3)
    flames = ("<g class='rf0'>%s</g><g class='rf1'>%s</g>"
              % (pk.sprite(('...SOS...', '....O....'), {'S': pk.SUN_L, 'O': pk.ORANGE}, 3, 3, 36),
                 pk.sprite(('...OSO...', '...SOS...', '....O....'), {'S': pk.SUN_L, 'O': pk.ORANGE}, 3, 3, 36)))
    b.append("<g transform='translate(118 %d)'><g class='rk'>%s%s</g></g>" % (HZ - 30, flames, rocket))
    b.append(mountains(rng, 0, W, HZ + 6, [(30, 30, .45), (200, 22, .4), (420, 34, .5), (610, 26, .45), (820, 32, .5)],
                       '#22134a', '#4a2a8a'))
    b.append(pk.bands(svg, 0, W, [(HZ + 4, '#18203a'), (HZ + 20, '#121a30'), (H - 12, '#0d1226'), (H, None)]))
    b.append(path([(0, HZ + 4, W, 2)], '#2f5a3a'))
    for k in range(5):
        sx = 140 + k * 10
        name = 'smk%d' % k
        svg.css('.%s{opacity:0;animation:%s 12s linear infinite}@keyframes %s{0%%,48%%{opacity:0;transform:translate(0,0)}'
                '52%%{opacity:.9}66%%{opacity:0;transform:translate(%dpx,-10px)}100%%{opacity:0}}' % (name, name, name, (k - 2) * 14))
        b.append("<g class='%s'>%s</g>" % (name, path([(sx - 8, HZ + 2, 10, 6), (sx - 6, HZ, 6, 2)], '#b4aee0')))
    svg.css('.sw{animation:sw 2.2s steps(1,end) infinite}@keyframes sw{0%{transform:translateX(0)}50%{transform:translateX(3px)}}')
    body, head, fw, fh = pk.mini_flower(2, 0, 0, stem=6, face=False)
    svg.add_def("<g id='fb0'>%s</g><g id='fh0'>%s</g>" % (body, head))
    back = []
    for i in range(16):
        x = 20 + i * 54 + rng.randrange(-8, 9)
        back.append("<use href='#fb0' x='%d' y='%d'/><use class='sw' style='animation-delay:-%ss' href='#fh0' x='%d' y='%d'/>"
                    % (x, HZ - 18, n(round(rng.uniform(0, 2), 1)), x, HZ - 18))
    b.append("<g opacity='.55'>%s</g>" % ''.join(back))
    for stem in (7, 9, 11):
        body, head, fw, fh = pk.mini_flower(3, 0, 0, stem=stem, face=True)
        svg.add_def("<g id='fb%d'>%s</g><g id='fh%d'>%s</g>" % (stem, body, stem, head))
    for i, x in enumerate((200, 300, 390, 470, 560, 650, 735)):
        stem = 7 + (i % 3) * 2
        y = H - 10 - (12 + stem) * 3
        b.append("<use href='#fb%d' x='%d' y='%d'/><use class='sw' style='animation-delay:-%ss' href='#fh%d' x='%d' y='%d'/>"
                 % (stem, x, y, n(round(i * 0.3, 1)), stem, x, y))
    b.append(path([(rng.randrange(0, W, 4), rng.randrange(HZ + 10, H - 12, 2), 4, 2) for _ in range(60)], '#2a5a36'))
    svg.css('.ff{animation:ff 5s ease-in-out infinite}@keyframes ff{0%,100%{transform:translate(0,0);opacity:.2}'
            '25%{opacity:1}50%{transform:translate(10px,-8px);opacity:.4}75%{transform:translate(-6px,-14px);opacity:1}}')
    for _ in range(12):
        fx, fy = rng.randrange(150, W - 40, 2), rng.randrange(HZ - 30, H - 30, 2)
        b.append("<g class='ff' style='animation-duration:%ss;animation-delay:-%ss'>%s%s</g>"
                 % (n(round(rng.uniform(3.5, 6.5), 1)), n(round(rng.uniform(0, 5), 1)),
                    "<path fill='%s' d='%s'/>" % (pk.dither(svg, pk.SUN, 2), d_rects([(fx - 2, fy - 2, 6, 6)])),
                    path([(fx, fy, 2, 2)], pk.SUN_L)))
    title = 'THANKS FOR VISITING!'
    b.append(pk.text2(title, pk.cx_text(title, 3, 'b'), 30, 3, pk.SUN_L, pk.ORANGE))
    sub = 'See you in space'
    b.append(pk.text(sub, pk.cx_text(sub, 2), 66, 2, pk.SOFT, shadow=pk.INK))
    note = 'auto-updated daily by GitHub Actions'
    b.append(pk.text(note, pk.cx_text(note, 2), 90, 2, pk.MUTED, shadow=pk.INK))
    b.append(pk.mascot(svg, 34, H - 10 - 102, 3, delay=0.8, blink=4.6))
    b.append(pk.side_frame(W, H) + pk.cap_frame(W, H, top=False))
    return svg.render(b)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    jobs = [('hero.svg', build_hero), ('profile.svg', build_profile), ('inventory.svg', build_inventory),
            ('btn-repos.svg', lambda: build_button('REPOSITORIES', 'book', pk.CYAN2, '#6fe8f2', pk.CYAN3, pk.SNOW, 'left')),
            ('btn-stars.svg', lambda: build_button('STARRED LIST', 'star', pk.SUN2, pk.SUN_L, pk.SUN3, pk.INK, 'right')),
            ('arcade.svg', build_arcade), ('footer.svg', build_footer)]
    for name, fn in jobs:
        svg = fn()
        with open(out / name, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(svg)
        print('%s %d bytes' % (out / name, len(svg.encode('utf-8'))))


if __name__ == '__main__':
    main(sys.argv)
