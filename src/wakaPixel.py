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
import html
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import build_assets as ba  # noqa: E402

ba.FONT['#'] = (0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0x00)

COLORS = {'kotlin': ba.PURPLE, 'java': '#ff9a5c', 'c++': '#4aa8ff', 'typescript': '#4aa8ff',
          'python': ba.YELLOW, 'vue': '#3ee08f', 'flutter': ba.CYAN, 'dart': ba.CYAN,
          'markdown': ba.CYAN, 'xml': ba.PINK, 'json': '#c9a6ff', 'rescript': '#ff7a9c'}
PALETTE = [ba.PURPLE, ba.CYAN, ba.PINK, ba.YELLOW, '#3ee08f', '#4aa8ff', '#ff9a5c', '#c9a6ff']
MAX_ROWS = 8
BLOCKS = 26
LIT_CSS = ('.lit{animation:lit 8s ease-in-out infinite;animation-fill-mode:backwards}'
           '@keyframes lit{0%,100%{opacity:.7}20%,80%{opacity:1}}')


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


def fmt_dur(secs):
    h, m = divmod(int(secs // 60), 60)
    return '%dH %02dM' % (h, m)


def render(langs, total, tracked, source):
    W = 900
    rows = langs[:MAX_ROWS]
    H = max(328, 82 + max(len(rows), 1) * 34)
    rng = random.Random(1999)
    body = [ba.starfield(rng, W, H, 34, 12),
            ba.icon('clock', 28, 24, 3),
            ba.path(ba.text_rects('CODING TIME', 68, 24, 3), ba.CYAN),
            ba.path(ba.text_rects('ALL TIME', 470, 28, 2), '#8f86e8')]

    if not rows:
        msg = 'NO SIGNALS YET'
        body.append(ba.path(ba.text_rects(msg, (600 - ba.text_w(msg, 4)) // 2, 110, 4), '#8f86e8'))
    for i, (name, secs, pct) in enumerate(rows):
        y0 = 60 + i * 34
        color = COLORS.get(name.lower(), PALETTE[i % len(PALETTE)])
        body.append("<g transform='translate(46 %d)'>%s</g>"
                    % (y0 + 19, ''.join(ba.disc_paths(3, 3, color))))
        label = name.upper() if len(name) <= 10 else name.upper()[:7] + '...'
        body.append(ba.path(ba.text_rects(label, 72, y0 + 12, 2), ba.WHITE))
        base = [(196 + j * 11, y0 + 16, 9, 18) for j in range(BLOCKS)]
        body.append(ba.path(base, ba.DIM))
        ratio = pct / 100.0
        filled = 0 if pct <= 0 else max(1, min(BLOCKS, int(round(ratio * BLOCKS))))
        for j in range(filled):
            body.append("<path class='lit' style='animation-delay:%ss' fill='%s' d='%s'/>"
                        % (ba.n(round(i * 0.08 + j * 0.03, 2)), color, ba.d_rects([base[j]])))
        body.append(ba.path(ba.text_rects('%.2f%%' % pct, 500, y0 + 18, 2), ba.WHITE))

    px, py = 604, 24
    body.append(ba.path([(px, py, 2, H - 48)], ba.FRAME))
    body.append(ba.icon('signal', 628, py, 3))
    body.append(ba.path(ba.text_rects('FLIGHT TIME', 664, py + 4, 2), ba.PINK))
    body.append(ba.path(ba.text_rects(fmt_dur(total), 628, py + 52, 3), ba.WHITE))
    body.append(ba.path(ba.text_rects('MOST USED', 628, py + 112, 2), '#8f86e8'))
    top = rows[0][0].upper()[:12] if rows else 'NONE'
    body.append(ba.path(ba.text_rects(top, 628, py + 136, 3), ba.CYAN))
    body.append(ba.path(ba.text_rects('%d LANGUAGES' % tracked, 628, py + 196, 2), ba.WHITE))
    body.append(ba.path(ba.text_rects('WAKATIME', 628, H - 32, 2), '#8f86e8'))
    body.append(ba.side_frame(W, H))

    summary = 'Coding time %s: %s' % (fmt_dur(total), ', '.join('%s %.2f%%' % (r[0], r[2]) for r in rows) or 'no data')
    return ba.svg_doc(W, H, html.escape(summary, quote=True), ''.join(body), LIT_CSS)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / 'assets' / 'waka.svg'
    payload, source = fetch_stats()
    langs, total, tracked = parse(payload)
    svg = render(langs, total, tracked, source)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes, %d languages, provider=%s' % (out, len(svg.encode('utf-8')), len(langs), source))


if __name__ == '__main__':
    main(sys.argv)
