#!/usr/bin/env python3
'''从 Wakapi 获取编码时长，生成像素宇宙风 assets/waka.svg（仅标准库，输出确定）。

用法: python src/wakaPixel.py [输出路径]
环境变量: WAKAPI_BASE_URL, WAKAPI_API_KEY
WAKA_FIXTURE 指向 JSON 文件时跳过网络（仅用于测试）。
'''
import base64
import html
import json
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import build_assets as ba  # noqa: E402

ba.FONT['#'] = (0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0x00)

COLORS = {'kotlin': ba.PURPLE, 'java': '#ff9a5c', 'typescript': '#4aa8ff', 'python': ba.YELLOW,
          'vue': '#3ee08f', 'flutter': ba.CYAN, 'dart': ba.CYAN, 'markdown': ba.CYAN, 'xml': ba.PINK}
PALETTE = [ba.PURPLE, ba.CYAN, ba.PINK, ba.YELLOW, '#3ee08f', '#4aa8ff', '#ff9a5c', '#c9a6ff']
MAX_ROWS = 8
BLOCKS = 26
LIT_CSS = ('.lit{animation:lit 10s linear infinite;animation-fill-mode:backwards}'
           '@keyframes lit{0%{opacity:.15}1%{opacity:1}90%{opacity:1}91%,100%{opacity:.15}}')


def api_url(base):
    '''兼容 base 已带 /api、/compat/wakatime 或 /v1 的写法。'''
    root = re.sub(r'(/api)?(/compat/wakatime)?(/v1)?/*$', '', base.strip())
    return root + '/api/compat/wakatime/v1/users/current/stats/all_time'


def fetch_stats():
    fixture = os.environ.get('WAKA_FIXTURE')
    if fixture:
        with open(fixture, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    base = os.environ.get('WAKAPI_BASE_URL', '')
    key = os.environ.get('WAKAPI_API_KEY', '')
    if not base or not key:
        sys.exit('缺少环境变量 WAKAPI_BASE_URL 或 WAKAPI_API_KEY')
    token = base64.b64encode(key.encode('utf-8')).decode('ascii')
    req = urllib.request.Request(api_url(base), headers={'Authorization': 'Basic ' + token, 'Accept': 'application/json'})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:  # 网络或解析错误：重试，最终失败时保留旧文件
            last = exc
            print('请求失败(%d/3): %s' % (attempt + 1, exc), file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    sys.exit('无法获取 Wakapi 数据: %s' % last)


def parse(payload):
    data = payload.get('data', payload) or {}
    langs = []
    for item in data.get('languages') or []:
        langs.append([str(item.get('name') or 'Other'), float(item.get('total_seconds') or 0), item.get('percent')])
    total = float(data.get('total_seconds') or sum(x[1] for x in langs))
    out = []
    for name, secs, pct in langs:
        if pct is None:
            pct = secs / total * 100 if total else 0.0
        out.append((name, secs, max(0.0, min(100.0, float(pct)))))
    out.sort(key=lambda x: -x[1])
    return out, total


def fmt_dur(secs):
    h, m = divmod(int(secs // 60), 60)
    return '%dH %dM' % (h, m) if h else '%dM' % m


def render(langs, total):
    W = 900
    rows = langs[:MAX_ROWS]
    H = 96 + max(len(rows), 1) * 46 + 16
    rng = random.Random(1999)
    tot = 'TOTAL ' + fmt_dur(total)
    body = [ba.starfield(rng, W, H, 30, 10),
            ba.path(ba.text_rects('CODING TIME', 24, 22, 3), ba.CYAN),
            ba.path(ba.text_rects(tot, W - 24 - ba.text_w(tot, 2), 26, 2), ba.PINK),
            ba.path([(24, 64, W - 48, 2)], ba.FRAME)]
    if not rows:
        msg = 'NO SIGNALS YET'
        body.append(ba.path(ba.text_rects(msg, (W - ba.text_w(msg, 4)) // 2, 96, 4), '#8f86e8'))
    for i, (name, secs, pct) in enumerate(rows):
        y0 = 80 + i * 46
        color = COLORS.get(name.lower(), PALETTE[i % len(PALETTE)])
        body.append("<g transform='translate(40 %d)'>%s</g>" % (y0 + 19, ''.join(ba.disc_paths(3, 3, color))))
        body.append(ba.path(ba.text_rects(name.upper()[:12], 70, y0 + 9, 3), ba.WHITE))
        filled = 0 if pct <= 0 else max(1, min(BLOCKS, int(round(pct / 100.0 * BLOCKS))))
        base = [(290 + j * 12, y0 + 10, 9, 18) for j in range(BLOCKS)]
        body.append(ba.path(base, ba.DIM))
        for j in range(filled):
            delay = round(i * 0.15 + j * 0.04, 2)
            body.append("<path class='lit' style='animation-delay:%ss' fill='%s' d='%s'/>"
                        % (ba.n(delay), color, ba.d_rects([base[j]])))
        body.append(ba.path(ba.text_rects('%.2f%%' % pct, 620, y0 + 12, 2), ba.WHITE))
        body.append(ba.path(ba.text_rects(fmt_dur(secs), 712, y0 + 12, 2), '#8f86e8'))
    body.append(ba.frame(W, H))
    summary = 'Coding time %s: %s' % (fmt_dur(total), ', '.join('%s %.2f%%' % (r[0], r[2]) for r in rows) or 'no data')
    return ba.svg_doc(W, H, html.escape(summary, quote=True), ''.join(body), LIT_CSS)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets' / 'waka.svg'
    langs, total = parse(fetch_stats())
    svg = render(langs, total)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes, %d languages' % (out, len(svg.encode('utf-8')), len(langs)))


if __name__ == '__main__':
    main(sys.argv)