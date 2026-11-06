#!/usr/bin/env python3
"""把 snk 的贡献贪吃蛇装进街机屏幕：网格重排为 14px 间距、11px 方格，接上 arcade.svg 的机框。"""
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixelkit as pk  # noqa: E402
from pixelkit import W, path  # noqa: E402

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
SRC_PITCH, PITCH, CELL = 16, 14, 11
SCALE = PITCH / SRC_PITCH
BEZEL = '#231a4a'
SCREEN = '#08071a'
COLORS = (':root{--ce:#191538;--c0:#191538;--c1:#3a2a8c;--c2:#6b3fd4;--c3:#a66bff;--c4:#ff5ccf;--cs:%s}'
          '.s.s0{fill:%s}.s.s1{fill:%s}.s.s2{fill:%s}.s.s3{fill:%s}' % (pk.SUN, pk.SUN_L, pk.SUN, pk.SUN2, pk.SUN3))
STICK = ('..RRRR..', '.RRRRRR.', 'RRWRRRRR', 'RRRRRRRR', 'RRRRRRRR', '.RRRRRR.', '..RRRR..', '...KK...',
         '...KK...', '...KK...', '.KKKKKK.', 'KKKKKKKK')


def deck(svg, top, H):
    out = [path([(24, top, W - 48, 10)], BEZEL), path([(24, top + 10, W - 48, 2)], '#3a2f72'),
           path([(28, top + 16, W - 48, H - top - 22)], pk.INK),
           pk.bevel(24, top + 12, W - 48, H - top - 22, '#2a1f5a', '#41348a', '#16103a')]
    mid = top + 12 + (H - top - 22) // 2
    out.append(pk.sprite(STICK, {'R': pk.RED, 'W': pk.SNOW, 'K': pk.INK}, 2, 70, mid - 12))
    svg.css('.btna{animation:btn 1.2s steps(1,end) infinite}.btnb{animation:btn 1.2s steps(1,end) infinite;animation-delay:-.6s}'
            '@keyframes btn{0%{transform:translateY(0)}50%{transform:translateY(2px)}}')
    for i, (cls, color) in enumerate((('btna', pk.PINK), ('btnb', pk.CYAN))):
        bx = W - 140 + i * 40
        out.append(path([(bx, mid - 6, 24, 16)], pk.INK))
        out.append("<g class='%s'>%s</g>" % (cls, pk.bevel(bx, mid - 10, 24, 16, color, pk.mix(color, 0.5), pk.mix(color, -0.4))))
    label = 'CONTRIBUTIONS · LAST 12 MONTHS'
    out.append(pk.text(label, pk.cx_text(label, 2), mid - 7, 2, pk.SOFT, shadow=pk.INK))
    out.append(path([(112 + k * 8, mid - 4, 4, 8) for k in range(6)], '#16103a'))
    out.append(path([(W - 196 + k * 8, mid - 4, 4, 8) for k in range(6)], '#16103a'))
    return ''.join(out)


def style_svg(source):
    original = ET.fromstring(source)
    vx, vy, vw, vh = map(float, original.attrib['viewBox'].split())
    if vw <= 0 or vh <= 0:
        raise ValueError('蛇图尺寸必须为正数')
    cols = max(1, int(round((vw - 32) / SRC_PITCH)))
    grid_w = (cols - 1) * PITCH + CELL
    x0 = (W - grid_w) // 2
    y0 = 22
    screen_bottom = int(y0 + (vh - 32) * SCALE) + 16
    H = screen_bottom + 70
    svg = pk.Svg(W, H, 'GitHub contribution snake')
    sx = x0 - 12
    body = [pk.starfield(svg, random.Random(8), (6, 2, W - 6, H - 2), 10, 4, 0),
            path([(24, 0, sx - 24, screen_bottom), (W - sx, 0, sx - 24, screen_bottom)], BEZEL),
            path([(sx - 2, 0, 2, screen_bottom), (W - sx, 0, 2, screen_bottom)], pk.INK),
            path([(sx, 0, W - 2 * sx, screen_bottom)], SCREEN)]
    body.append(path([(x, 6, 2, screen_bottom - 12) for x in range(sx + 6, W - sx - 6, PITCH * 4)], '#0e0c26'))
    inner = []
    for child in original:
        tag = child.tag.split('}')[-1]
        if tag == 'title' or (tag == 'rect' and not child.get('class')):
            continue
        if tag == 'rect' and (child.get('class') or '').split()[:1] in (['c'], ['s']):
            child.set('rx', '0')
            child.set('ry', '0')
        inner.append(ET.tostring(child, encoding='unicode'))
    tx = x0 - SCALE * 2
    ty = y0 - SCALE * 2
    body.append("<g transform='translate(%g %g) scale(%g)'>%s</g>" % (tx, ty, SCALE, ''.join(inner)))
    # snk 自带的 <style> 在正文里，覆盖规则必须排在它后面才能生效
    body.append('<style>%s.c{width:%.4fpx;height:%.4fpx}.c,.s{shape-rendering:crispEdges}</style>'
                % (COLORS, CELL / SCALE, CELL / SCALE))
    body.append(pk.scanlines(svg, sx, 0, W - 2 * sx, screen_bottom, opacity=0.3))
    svg.css('.beam{animation:beam 5s linear infinite}@keyframes beam{from{transform:translateY(-30px)}to{transform:translateY(%dpx)}}' % (screen_bottom + 30))
    body.append("<path class='beam' fill='%s' opacity='.05' d='%s'/>" % (pk.SNOW, pk.d_rects([(sx, 0, W - 2 * sx, 18)])))
    body.append(deck(svg, screen_bottom, H))
    body.append(pk.side_frame(W, H))
    return svg.render(body)


if __name__ == '__main__':
    target = Path(sys.argv[1])
    result = style_svg(target.read_text(encoding='utf-8'))
    target.write_text(result, encoding='utf-8', newline='\n')
    print('蛇图已装进街机屏幕：846 像素宽，14px 网格')
