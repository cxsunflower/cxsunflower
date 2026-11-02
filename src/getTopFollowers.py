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

   cx 的修改：标准库 urllib 取代 requests；恢复 inactive/quota 过滤；
   修复空列表的残缺表格、替换串转义、昵称 HTML 转义；支持 FOLLOWERS_FIXTURE 离线测试。
"""

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = 'https://api.github.com/graphql'
MAX_SHOWN = 21
PER_ROW = 7

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

SECTION = re.compile(r'(<!--START_SECTION:top-followers-->)(.*?)(<!--END_SECTION:top-followers-->)', re.S)


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
    for page in pages(handle, token):
        for f in page['nodes']:
            if not f:
                continue
            login = f['login']
            number = f['followers']['totalCount']
            following = f['following']['totalCount']
            mark = '*' if number > 500 else ''
            if not f['contributionsCollection']['hasAnyContributions']:
                print('Skipped%s (inactive): https://github.com/%s with %d followers and %d following' % (mark, login, number, following))
                continue
            if following > quota_of(f):
                print('Skipped%s (quota): https://github.com/%s with %d followers and %d following' % (mark, login, number, following))
                continue
            followers.append((number, login, f['databaseId'], f['name'] or login))
            print(followers[-1])
        sys.stdout.flush()
    followers.sort(key=lambda x: (-x[0], x[1].lower()))
    return followers


def render(followers):
    shown = followers[:MAX_SHOWN]
    if not shown:
        return '<p align="center"><code>NO SIGNALS YET</code></p>'
    lines = ['<table>']
    for start in range(0, len(shown), PER_ROW):
        lines.append('  <tr>')
        for _, login, uid, name in shown[start:start + PER_ROW]:
            lg = html.escape(login, quote=True)
            nm = html.escape(name, quote=True)
            lines.append('    <td align="center">')
            lines.append('      <a href="https://github.com/%s">' % lg)
            lines.append('        <img src="https://avatars.githubusercontent.com/u/%s?s=100" width="100" alt="%s"/>' % (uid, lg))
            lines.append('      </a>')
            lines.append('      <br />')
            lines.append('      <a href="https://github.com/%s">%s</a>' % (lg, nm))
            lines.append('    </td>')
        lines.append('  </tr>')
    lines.append('</table>')
    return '\n'.join(lines)


def replace_section(content, block):
    if not SECTION.search(content):
        sys.exit('README 中缺少 top-followers 标记')
    return SECTION.sub(lambda m: m.group(1) + '\n' + block + '\n' + m.group(3), content, count=1)


def main(argv):
    if len(argv) != 4:
        sys.exit('用法: getTopFollowers.py <handle> <token> <readme>')
    handle, token, readme = argv[1:]
    block = render(collect(handle, token))
    with open(readme, 'r', encoding='utf-8', newline='') as fh:
        content = fh.read()
    with open(readme, 'w', encoding='utf-8', newline='') as fh:
        fh.write(replace_section(content, block))


if __name__ == '__main__':
    main(sys.argv)