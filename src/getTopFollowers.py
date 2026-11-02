"""
   Copyright 2020-2024 Yufan You <https://github.com/ouuan>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   cx 的修改：输出整幅像素风 assets/followers.svg；恢复 inactive/quota 过滤；
   全部被过滤时回退到未过滤榜单；头像内嵌为 data URI，避免外部图片破坏海报。
"""

import base64
import html
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import build_assets as ba  # noqa: E402

API = 'https://api.github.com/graphql'
MAX_SHOWN = 21
PER_ROW = 7
CELL_W = 128
ROW_H = 104
HEADER = 64

QUERY = '''
query($login: String!, $cursor: String) {
  user(login: $login) {
    followers(first: 10, after: $cursor) {
      pageInfo { endCursor hasNextPage }
      nodes {
        login
        name
        databaseId
        following { totalCount }
        repositories(first: 20, orderBy: {field: STARGAZERS, direction: DESC}) {
          nodes { stargazerCount }
        }
        repositoriesContributedTo(first: 50, contributionTypes: [COMMIT], orderBy: {field: STARGAZERS, direction: DESC}) {
          nodes { stargazerCount }
        }
        followers { totalCount }
        contributionsCollection { hasAnyContributions }
      }
    }
  }
}
'''


def post(variables, token):
    body = json.dumps({'query': QUERY, 'variables': variables}).encode('utf-8')
    headers = {'Authorization': 'bearer ' + token, 'Content-Type': 'application/json', 'User-Agent': 'top-followers'}
    retry = 0
    while True:
        req = urllib.request.Request(API, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            wait = exc.headers.get('Retry-After')
            if wait and wait.isdigit() and retry < 3:
                print('Rate limit exceeded, retry after %s seconds' % wait)
                time.sleep(int(wait))
                retry += 1
                continue
            sys.exit('GraphQL 请求失败: %s %s' % (exc.code, exc.read().decode('utf-8', 'replace')[:2000]))
        except urllib.error.URLError as exc:
            sys.exit('GraphQL 网络错误: %s' % exc)
        user = (payload.get('data') or {}).get('user')
        if not user:
            sys.exit('GraphQL 返回异常: ' + json.dumps(payload)[:2000])
        return user['followers']


def pages(handle, token):
    fixture = os.environ.get('FOLLOWERS_FIXTURE')
    if fixture:
        with open(fixture, 'r', encoding='utf-8') as fh:
            for page in json.load(fh):
                yield page
        return
    cursor = None
    while True:
        page = post({'login': handle, 'cursor': cursor}, token)
        yield page
        if not page['pageInfo']['hasNextPage']:
            return
        cursor = page['pageInfo']['endCursor']


def stars(conn):
    return [r['stargazerCount'] for r in (conn.get('nodes') or []) if r]


def quota_of(f):
    quota = f['followers']['totalCount']
    for i, count in enumerate(stars(f['repositories'])):
        if count <= i:
            break
        quota += count * (i + 1)
    for i, count in enumerate(stars(f['repositoriesContributedTo'])):
        if count <= i:
            break
        quota += i * 5
    return quota


def collect(handle, token):
    followers = []
    candidates = []
    for page in pages(handle, token):
        for f in page['nodes']:
            if not f:
                continue
            login = f['login']
            number = f['followers']['totalCount']
            following = f['following']['totalCount']
            mark = '*' if number > 500 else ''
            entry = (number, login, f['databaseId'], f['name'] or login)
            candidates.append(entry)
            if not f['contributionsCollection']['hasAnyContributions']:
                print('Skipped%s (inactive): https://github.com/%s with %d followers and %d following' % (mark, login, number, following))
                continue
            if following > quota_of(f):
                print('Skipped%s (quota): https://github.com/%s with %d followers and %d following' % (mark, login, number, following))
                continue
            followers.append(entry)
            print(followers[-1])
        sys.stdout.flush()
    order = lambda items: sorted(items, key=lambda x: (-x[0], x[1].lower()))
    followers = order(followers)
    if not followers and candidates:
        print('All followers were filtered out; falling back to the unfiltered list')
        return order(candidates)
    return followers


def display_name(name, login):
    if name and all(c.upper() in ba.FONT for c in name):
        return name
    return login


def avatar_uri(uid):
    url = 'https://avatars.githubusercontent.com/u/%s?s=64' % uid
    req = urllib.request.Request(url, headers={'User-Agent': 'cxsunflower-profile'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            ctype = resp.headers.get_content_type() or 'image/png'
        return 'data:%s;base64,%s' % (ctype, base64.b64encode(data).decode('ascii'))
    except Exception as exc:
        print('头像获取失败 %s: %s' % (uid, exc), file=sys.stderr)
        return None


def render_svg(followers, avatars):
    shown = followers[:MAX_SHOWN]
    rows = max(1, math.ceil(len(shown) / PER_ROW))
    W = 900
    H = HEADER + rows * ROW_H + 12
    rng = random.Random(404)
    body = [ba.starfield(rng, W, H, 36, 12),
            ba.icon('crew', 28, 12, 4),
            ba.path(ba.text_rects('CREW // FOLLOWERS', 68, 14, 3), ba.CYAN),
            ba.path(ba.text_rects('%d SIGNALS' % len(shown), W - 24 - ba.text_w('%d SIGNALS' % len(shown), 2), 20, 2), '#8f86e8')]

    if not shown:
        msg = 'NO SIGNALS YET'
        body.append(ba.path(ba.text_rects(msg, (W - ba.text_w(msg, 4)) // 2, HEADER + 24, 4), '#8f86e8'))

    palette = [ba.PURPLE, ba.CYAN, ba.PINK, ba.YELLOW, '#3ee08f', '#4aa8ff', '#ff9a5c']
    for i, (_, login, uid, name) in enumerate(shown):
        col, row = i % PER_ROW, i // PER_ROW
        row_count = min(PER_ROW, len(shown) - row * PER_ROW)
        cx = (W - row_count * CELL_W) // 2 + CELL_W // 2 + col * CELL_W
        y = HEADER + row * ROW_H
        body.append("<rect x='%d' y='%d' width='72' height='72' fill='none' stroke='%s' stroke-width='2'/>"
                    % (cx - 36, y, ba.FRAME))
        body.append(ba.path([(cx - 36, y, 6, 6), (cx + 30, y, 6, 6), (cx - 36, y + 66, 6, 6), (cx + 30, y + 66, 6, 6)], ba.PINK))
        uri = avatars.get(login)
        if uri:
            body.append("<image x='%d' y='%d' width='64' height='64' href='%s' preserveAspectRatio='xMidYMid slice'/>"
                        % (cx - 32, y + 4, html.escape(uri, quote=True)))
        else:
            body.append("<g transform='translate(%d %d)'>%s</g>"
                        % (cx, y + 36, ''.join(ba.disc_paths(7, 4, palette[i % len(palette)]))))
        label = display_name(name, login).upper()
        scale = 2 if ba.text_w(label, 2) <= CELL_W - 8 else 1
        if ba.text_w(label, scale) > CELL_W - 8:
            label = label[:16] + '...'
        body.append(ba.path(ba.text_rects(label, cx - ba.text_w(label, scale) // 2, y + 80, scale), ba.WHITE))

    body.append(ba.side_frame(W, H))
    summary = 'Followers: ' + (', '.join(f[1] for f in shown) if shown else 'no signals yet')
    return ba.svg_doc(W, H, html.escape(summary, quote=True), ''.join(body))


def main(argv):
    if len(argv) != 4:
        sys.exit('用法: getTopFollowers.py <handle> <token> <output.svg>')
    handle, token, out = argv[1:]
    followers = collect(handle, token)
    avatars = {}
    if not os.environ.get('FOLLOWERS_SKIP_AVATARS'):
        for _, login, uid, _ in followers[:MAX_SHOWN]:
            uri = avatar_uri(uid)
            if uri:
                avatars[login] = uri
    svg = render_svg(followers, avatars)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes, %d followers, %d avatars' % (path, len(svg.encode('utf-8')), len(followers), len(avatars)))


if __name__ == '__main__':
    main(sys.argv)
