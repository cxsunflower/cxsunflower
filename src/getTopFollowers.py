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
   全部被过滤时回退到未过滤榜单；头像以 24px 内嵌为 data URI 并按像素放大，避免外部图片破坏海报。
"""

import base64
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
import pixelkit as pk  # noqa: E402
from pixelkit import W, d_rects, n, path  # noqa: E402

API = 'https://api.github.com/graphql'
MAX_SHOWN = 21
PER_ROW = 7
CARD_W, CARD_H, GAP = 104, 124, 8
HEADER = 58
AVATAR_PX = 24

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
    if name and pk.ascii_only(name):
        return name
    return login


def avatar_uri(uid):
    url = 'https://avatars.githubusercontent.com/u/%s?s=%d' % (uid, AVATAR_PX)
    req = urllib.request.Request(url, headers={'User-Agent': 'cxsunflower-profile'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            ctype = resp.headers.get_content_type() or 'image/png'
        return 'data:%s;base64,%s' % (ctype, base64.b64encode(data).decode('ascii'))
    except Exception as exc:
        print('头像获取失败 %s: %s' % (uid, exc), file=sys.stderr)
        return None


MEDALS = ((pk.SUN, pk.SUN_L, pk.SUN3), ('#c9d2ea', '#ffffff', '#7d86a8'), ('#e0915a', '#ffc28f', '#8a4a20'))
PLACEHOLDER = ('..####..', '.######.', '.##..##.', '.##..##.', '.######.', '..####..', '.######.', '########')


def crew_card(svg, x, y, i, login, name, uri):
    '''带像素头像、徽章与全息扫光的船员卡。'''
    face = (pk.PANEL, pk.PANEL2, pk.BG2) if i >= 3 else (pk.PANEL2, pk.mix(MEDALS[i][0], -0.35), pk.BG2)
    out = [pk.bevel(x, y, CARD_W, CARD_H, *face)]
    ax, ay = x + (CARD_W - 72) // 2, y + 10
    out.append(path([(ax - 2, ay - 2, 76, 76)], pk.INK))
    if uri:
        out.append("<image x='%d' y='%d' width='72' height='72' href='%s' preserveAspectRatio='xMidYMid slice' "
                   "image-rendering='optimizeSpeed' style='image-rendering:pixelated'/>" % (ax, ay, uri))
    else:
        out.append(path([(ax, ay, 72, 72)], pk.PURPLE3) + pk.sprite(PLACEHOLDER, {'#': pk.PURPLE}, 6, ax + 12, ay + 14))
    clip = svg.uid('av')
    svg.add_def("<clipPath id='%s'><rect x='%d' y='%d' width='72' height='72'/></clipPath>" % (clip, ax, ay))
    band = [(ax - 48 + (72 - r) // 2 // 2 * 2, ay + r, 10, 2) for r in range(0, 72, 2)]
    out.append("<g clip-path='url(#%s)'><path class='holo' style='animation-delay:-%ss' fill='%s' opacity='.35' d='%s'/></g>"
               % (clip, n(round(i * 0.45, 2)), pk.SNOW, d_rects(band)))
    label = display_name(name, login)
    s = 2 if pk.text_w(label, 2) <= CARD_W - 12 else 1
    label = pk.fit(label, s, CARD_W - 10)
    out.append(pk.text(label, x + (CARD_W - pk.text_w(label, s)) // 2, y + 94 + (3 if s == 1 else 0), s, pk.WHITE, shadow=pk.INK))
    if i < 3:
        base, hi, lo = MEDALS[i]
        rank = '#%d' % (i + 1)
        out.append(pk.bevel(x - 6, y - 8, pk.text_w(rank, 2, 'b') + 12, 22, base, hi, lo) + pk.text(rank, x, y - 3, 2, pk.INK, 'b'))
    return ''.join(out)


def empty_card(x, y):
    dash = []
    for k in range(0, CARD_W, 8):
        dash += [(x + k, y, 4, 2), (x + k, y + CARD_H - 2, 4, 2)]
    for k in range(0, CARD_H, 8):
        dash += [(x, y + k, 2, 4), (x + CARD_W - 2, y + k, 2, 4)]
    return (path(dash, pk.LINE) + pk.text('?', x + (CARD_W - pk.text_w('?', 6, 'b')) // 2, y + 24, 6, pk.LINE, 'b') +
            "<g class='blk' style='animation-duration:1.6s'>%s</g>" % pk.text('JOIN', x + (CARD_W - pk.text_w('JOIN', 2, 'b')) // 2, y + 94, 2, pk.PINK, 'b'))


def render_svg(followers, avatars):
    shown = followers[:MAX_SHOWN]
    rows = max(1, math.ceil(len(shown) / PER_ROW))
    if shown and len(shown) % PER_ROW == 0 and len(shown) < MAX_SHOWN:
        rows += 1
    H = HEADER + rows * (CARD_H + 14) + 14
    summary = 'Followers: ' + (', '.join(f[1] for f in shown) if shown else 'no signals yet')
    svg = pk.Svg(W, H, summary)
    svg.css(pk.BLINK_CSS, pk.BOB_CSS,
            '.holo{animation:holo 4s linear infinite}@keyframes holo{0%,60%{transform:translateX(0)}85%,100%{transform:translateX(130px)}}')
    rng = random.Random(404)
    b = [pk.starfield(svg, rng, (6, 2, W - 6, H - 2), 40, 14, 3)]
    b.append(pk.icon('users', 28, 14, 24, pk.CYAN) + pk.text2('CREW', 62, 18, 3, pk.CYAN, pk.CYAN2))
    count = '%d aboard' % len(shown) if shown else 'no signals yet'
    b.append(pk.text(count, W - 28 - pk.text_w(count, 2), 24, 2, pk.MUTED))
    b.append(path([(28, 48, W - 56, 2)], pk.LINE))
    total = rows * PER_ROW
    x0 = (W - (PER_ROW * CARD_W + (PER_ROW - 1) * GAP)) // 2
    for k in range(total):
        col, row = k % PER_ROW, k // PER_ROW
        x, y = x0 + col * (CARD_W + GAP), HEADER + 12 + row * (CARD_H + 14)
        if k < len(shown):
            _, login, _, name = shown[k]
            card = crew_card(svg, x, y, k, login, name, avatars.get(login))
            b.append("<g class='bob' style='animation-duration:2.6s;animation-delay:-%ss'>%s</g>" % (n(round(k * 0.37 % 2.6, 2)), card))
        else:
            b.append(empty_card(x, y))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


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
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes, %d followers, %d avatars' % (target, len(svg.encode('utf-8')), len(followers), len(avatars)))


if __name__ == '__main__':
    main(sys.argv)
