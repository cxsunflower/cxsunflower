#!/usr/bin/env python3
'''从 WakaTime OAuth（或 Wakapi）获取编码时长，生成像素风 assets/waka.svg。

用法: python src/wakaPixel.py [输出路径]

环境变量:
  WAKATIME_OAUTH_TOKEN  WakaTime OAuth access token（优先）
  WAKAPI_API_KEY        兼容旧配置；若以 waka_tok_ 开头也会按 OAuth 处理
  WAKATIME_API_URL      默认 https://wakatime.com
  WAKAPI_BASE_URL       仅在显式使用 Wakapi API key 时需要
  WAKA_FIXTURE          指向 JSON 文件时跳过网络（仅测试）
'''
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import pixelkit as pk  # noqa: E402
from pixelkit import W, d_rects, n, path  # noqa: E402

COLORS = {'kotlin': pk.PURPLE, 'java': pk.ORANGE, 'c++': pk.BLUE, 'c': pk.BLUE, 'typescript': '#5aa2ff',
          'javascript': pk.SUN, 'python': pk.SUN, 'vue': pk.GREEN, 'flutter': pk.CYAN, 'dart': pk.CYAN,
          'markdown': pk.CYAN, 'xml': pk.PINK, 'json': '#c9a6ff', 'rescript': '#ff7a9c', 'html': pk.ORANGE,
          'css': pk.BLUE, 'shell': pk.LEAF, 'bash': pk.LEAF, 'go': pk.CYAN, 'rust': pk.ORANGE, 'yaml': pk.SOFT}
PALETTE = [pk.PURPLE, pk.CYAN, pk.PINK, pk.SUN, pk.GREEN, pk.BLUE, pk.ORANGE, '#c9a6ff']
MAX_ROWS = 8
SEGS = 18


def clean_root(base):
    root = base.strip().rstrip('/')
    for suffix in ('/api/v1', '/api/compat/wakatime/v1', '/api'):
        if root.endswith(suffix):
            root = root[:-len(suffix)]
    return root


def resolve_provider():
    forced = os.environ.get('WAKA_PROVIDER', '').strip().lower()
    oauth = os.environ.get('WAKATIME_OAUTH_TOKEN', '').strip()
    legacy = os.environ.get('WAKAPI_API_KEY', '').strip()
    base = os.environ.get('WAKAPI_BASE_URL', '').strip()
    token = oauth or legacy
    if not token:
        sys.exit('缺少 WAKATIME_OAUTH_TOKEN（或旧的 WAKAPI_API_KEY）')
    if forced == 'wakapi' or (forced != 'wakatime' and not oauth and not token.startswith('waka_tok_') and base):
        root = clean_root(base)
        return 'wakapi', token, root + '/api/compat/wakatime/v1/users/current/stats/all_time'
    if forced == 'wakatime' or oauth or token.startswith('waka_tok_') or not base:
        root = clean_root(os.environ.get('WAKATIME_API_URL', 'https://wakatime.com'))
        return 'wakatime', token, root + '/api/v1/users/current/stats/all_time'
    sys.exit('无法判断 WakaTime/Wakapi 配置')


def fetch_stats():
    fixture = os.environ.get('WAKA_FIXTURE')
    if fixture:
        with open(fixture, 'r', encoding='utf-8') as fh:
            return json.load(fh), 'fixture'

    provider, token, url = resolve_provider()
    if provider == 'wakatime':
        auth = 'Bearer ' + token
        label = 'WakaTime OAuth'
    else:
        auth = 'Basic ' + base64.b64encode(token.encode('utf-8')).decode('ascii')
        label = 'Wakapi API key'
    headers = {'Authorization': auth, 'Accept': 'application/json', 'User-Agent': 'cxsunflower-profile'}
    req = urllib.request.Request(url, headers=headers)
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8')), label
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                sys.exit('%s 请求失败 %s: %s（请检查 token 与 API 地址）' % (label, exc.code, url))
            last = exc
            print('请求失败(%d/3): HTTP %s %s' % (attempt + 1, exc.code, url), file=sys.stderr)
        except Exception as exc:
            last = exc
            print('请求失败(%d/3): %s' % (attempt + 1, exc), file=sys.stderr)
        time.sleep(2 * (attempt + 1))
    sys.exit('%s 请求失败: %s' % (label, last))


def parse(payload):
    data = payload.get('data', payload) or {}
    all_langs = []
    for item in data.get('languages') or []:
        name = str(item.get('name') or 'Other')
        all_langs.append((name, float(item.get('total_seconds') or 0), item.get('percent')))
    total = float(data.get('total_seconds') or sum(x[1] for x in all_langs))
    out = []
    for name, secs, pct in all_langs:
        if name.lower() == 'other':
            continue
        if pct is None:
            pct = secs / total * 100 if total else 0.0
        out.append((name, secs, max(0.0, min(100.0, float(pct)))))
    out.sort(key=lambda x: (-x[1], x[0].lower()))
    return out, total, len(all_langs)


def extras(payload):
    '''可选的日均与最佳单日（不同套餐/接口可能缺失）。'''
    data = payload.get('data', payload) or {}
    out = {}
    if data.get('daily_average'):
        out['daily'] = float(data['daily_average'])
    best = data.get('best_day') or {}
    if best.get('total_seconds'):
        out['best'] = (float(best['total_seconds']), str(best.get('date') or '')[:10])
    return out


def fmt_dur(secs):
    h, m = divmod(int(secs // 60), 60)
    return '%dH %02dM' % (h, m)


def disc(r):
    return [(i, j) for j in range(-r, r) for i in range(-r, r) if (i + .5) ** 2 + (j + .5) ** 2 <= r * r]


def planet_dot(cx, cy, color, r=3, c=2):
    cells = disc(r)
    lit = [(i, j) for i, j in cells if i + j < -r * 0.6]
    dark = [(i, j) for i, j in cells if i + j > r * 0.4]
    return (path(pk.cells_rects(cells, c, cx, cy), color) + path(pk.cells_rects(dark, c, cx, cy), pk.mix(color, -0.4)) +
            path(pk.cells_rects(lit, c, cx, cy), pk.mix(color, 0.5)))


def tile(x, y, w, h, label, accent):
    return (pk.bevel(x, y, w, h, '#100d29', pk.INK, pk.LINE, pk.INK) + path([(x + 4, y + 4, 4, h - 8)], accent) +
            pk.text(label, x + 16, y + 10, 2, pk.MUTED, 'b'))


def render(langs, total, tracked, source, extra=None):
    extra = extra or {}
    rows = langs[:MAX_ROWS]
    H = 392
    summary = 'Coding time %s: %s' % (fmt_dur(total), ', '.join('%s %.2f%%' % (r[0], r[2]) for r in rows) or 'no data')
    svg = pk.Svg(W, H, summary)
    rng = random.Random(1999)
    cycle = 12.0
    b = [pk.starfield(svg, rng, (6, 2, W - 6, H - 2), 30, 10, 2)]
    x, y, w, h = 24, 10, W - 48, H - 22
    b.append(path([(x + 4, y + 4, w, h)], pk.INK) + pk.bevel(x, y, w, h, pk.PANEL, pk.PANEL2, pk.BG2))
    b.append(pk.icon('clock', x + 20, y + 14, 24, pk.CYAN) + pk.text2('FLIGHT LOG', x + 52, y + 16, 3, pk.CYAN, pk.CYAN2))
    tag = 'WAKATIME · ALL TIME'
    b.append(pk.text(tag, x + w - 20 - pk.text_w(tag, 2), y + 22, 2, pk.MUTED))
    b.append(path([(x + 16, y + 50, w - 32, 2)], pk.LINE))
    colors = [COLORS.get(name.lower(), PALETTE[i % len(PALETTE)]) for i, (name, _, _) in enumerate(rows)]
    if not rows:
        msg = 'NO SIGNALS YET'
        b.append(pk.text(msg, x + 40, y + 120, 3, pk.MUTED, 'b'))
    bx, seg = x + 156, 10
    top_pct = max([r[2] for r in rows] + [1e-9])
    for i, ((name, secs, pct), color) in enumerate(zip(rows, colors)):
        ry = y + 68 + i * 30
        b.append(planet_dot(x + 30, ry + 7, color))
        b.append(pk.text(pk.fit(name, 2, 106), x + 46, ry, 2, pk.WHITE, shadow=pk.INK))
        b.append(path([(bx - 2, ry - 3, SEGS * seg + 2, 20)], pk.INK) + path([(bx + j * seg, ry - 1, seg - 2, 16) for j in range(SEGS)], pk.LINE))
        lit = 0 if pct <= 0 else max(1, min(SEGS, int(round(pct / top_pct * SEGS))))
        cells = [(bx + j * seg, ry - 1, seg - 2, 16) for j in range(lit)]
        bar = path(cells, color) + path([(cx_, cy_, cw_, 4) for cx_, cy_, cw_, _ in cells], pk.mix(color, 0.45)) + \
            path([(cx_, cy_ + 12, cw_, 4) for cx_, cy_, cw_, _ in cells], pk.mix(color, -0.3))
        t0 = 0.4 + i * 0.12
        clip = pk.reveal(svg, bx, ry - 3, lit * seg, 20, t0, 0.5, cycle, lit, cycle - 0.4)
        b.append("<g%s>%s</g>" % (clip, bar))
        b.append(pk.text('%.2f%%' % pct, bx + SEGS * seg + 10, ry, 2, color, 'b', shadow=pk.INK))
        hours = '%dh' % int(secs // 3600) if secs >= 3600 else '%dm' % int(secs // 60)
        b.append(pk.text(hours, bx + SEGS * seg + 104, ry, 2, pk.SOFT))
    tx, tw = x + 530, w - 546
    b.append(tile(tx, y + 64, tw, 86, 'TOTAL TIME', pk.CYAN))
    hrs, mins = divmod(int(total // 60), 60)
    b.append(pk.odometer(svg, str(hrs), tx + 18, y + 98, 5, pk.SNOW, 0.3, 1.6, cycle))
    b.append(pk.text('h %02dm' % mins, tx + 18 + len(str(hrs)) * 35 + 4, y + 112, 3, pk.SOFT, 'b', shadow=pk.INK))
    top = rows[0][0] if rows else 'None'
    b.append(tile(tx, y + 158, tw, 58, 'MOST USED', colors[0] if rows else pk.LINE))
    b.append((planet_dot(tx + 26, y + 194, colors[0]) if rows else '') +
             pk.text(pk.fit(top, 3, tw - 60, 'b'), tx + 42, y + 186, 3, colors[0] if rows else pk.MUTED, 'b', shadow=pk.INK))
    half = (tw - 8) // 2
    b.append(tile(tx, y + 224, half, 58, 'LANGS', pk.PINK) + pk.text(str(tracked), tx + 16, y + 252, 3, pk.SNOW, 'b', shadow=pk.INK))
    if 'daily' in extra:
        label, value = 'DAILY', fmt_dur(extra['daily']).replace(' ', '').lower()
    elif 'best' in extra:
        label, value = 'BEST DAY', fmt_dur(extra['best'][0]).replace(' ', '').lower()
    else:
        label, value = 'TRACKED', 'ALL TIME'
    b.append(tile(tx + half + 8, y + 224, tw - half - 8, 58, label, pk.SUN) +
             pk.text(pk.fit(value, 2, tw - half - 32), tx + half + 24, y + 256, 2, pk.SNOW, shadow=pk.INK))
    sy = y + h - 40
    b.append(pk.text('SHARE', x + 20, sy - 2, 2, pk.MUTED, 'b'))
    sx, sw = x + 96, w - 116
    b.append(path([(sx - 2, sy - 4, sw + 4, 22)], pk.INK) + path([(sx, sy - 2, sw, 18)], pk.LINE))
    pos = sx
    for (name, secs, pct), color in zip(rows, colors):
        width = int(round(sw * pct / 100.0) // 2 * 2)
        if width <= 0:
            continue
        b.append(path([(pos, sy - 2, min(width, sx + sw - pos), 18)], color) + path([(pos, sy - 2, min(width, sx + sw - pos), 4)], pk.mix(color, 0.4)))
        pos += width
    clip = svg.uid('sh')
    svg.add_def("<clipPath id='%s'><rect x='%d' y='%d' width='%d' height='18'/></clipPath>" % (clip, sx, sy - 2, sw))
    svg.css('.sweep{animation:sweep 4s linear infinite}@keyframes sweep{0%%,30%%{transform:translateX(0)}70%%,100%%{transform:translateX(%dpx)}}' % (sw + 60))
    b.append("<g clip-path='url(#%s)'><path class='sweep' fill='%s' opacity='.5' d='%s'/></g>"
             % (clip, pk.SNOW, d_rects([(sx - 40 + k * 2, sy - 2 + k * 2, 12, 2) for k in range(9)])))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets' / 'waka.svg'
    payload, source = fetch_stats()
    langs, total, tracked = parse(payload)
    svg = render(langs, total, tracked, source, extras(payload))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes, %d languages, provider=%s' % (out, len(svg.encode('utf-8')), len(langs), source))


if __name__ == '__main__':
    main(sys.argv)
