#!/usr/bin/env python3
'''抓取 GitHub 统计、近期公开动态与 AUR 软件包，生成像素风终端、AUR 列表与任务日志。

用法: python src/githubStats.py <GitHub 用户名> <AUR 维护者> [输出目录]

环境变量:
  GITHUB_TOKEN    GraphQL/REST 访问令牌（Actions 自带的即可）
  STATS_FIXTURE   指向 JSON 文件时跳过网络（测试用），格式见 tests/fixtures/stats_normal.json
'''
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import pixelkit as pk  # noqa: E402
from pixelkit import W, d_rects, n, path  # noqa: E402

GRAPHQL = 'https://api.github.com/graphql'
QUERY = '''
query($login: String!) {
  user(login: $login) {
    login name location createdAt
    followers { totalCount }
    following { totalCount }
    starredRepositories { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { name isFork stargazerCount forkCount primaryLanguage { name } }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
'''
UA = {'User-Agent': 'cxsunflower-profile'}


def request(url, data=None, headers=None, tries=3):
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, headers=dict(UA, **(headers or {})))
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                raise
            last = exc
        except Exception as exc:
            last = exc
        print('请求失败(%d/%d): %s %s' % (attempt + 1, tries, url, last), file=sys.stderr)
        time.sleep(2 * (attempt + 1))
    raise last


def fetch_user(login, token):
    body = json.dumps({'query': QUERY, 'variables': {'login': login}}).encode('utf-8')
    payload = request(GRAPHQL, body, {'Authorization': 'bearer ' + token, 'Content-Type': 'application/json'})
    user = (payload.get('data') or {}).get('user')
    if not user:
        raise RuntimeError('GraphQL 返回异常: ' + json.dumps(payload)[:500])
    return user


def fetch_events(login, token):
    url = 'https://api.github.com/users/%s/events/public?per_page=60' % urllib.parse.quote(login)
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = 'bearer ' + token
    return request(url, headers=headers)


def fetch_aur(maintainer):
    url = 'https://aur.archlinux.org/rpc/v5/search/%s?by=maintainer' % urllib.parse.quote(maintainer)
    data = request(url)
    if data.get('type') == 'error':
        raise RuntimeError(data.get('error'))
    return data.get('results') or []


def load(login, maintainer, token):
    '''返回 (user, events, aur, today)；events/aur 抓取失败时为 None，对应面板保持原样。'''
    fixture = os.environ.get('STATS_FIXTURE')
    if fixture:
        data = json.loads(Path(fixture).read_text(encoding='utf-8'))
        return data['user'], data.get('events'), data.get('aur'), dt.date.fromisoformat(data['now'])
    if not token:
        sys.exit('缺少 GITHUB_TOKEN')
    user = fetch_user(login, token)
    events = aur = None
    try:
        events = fetch_events(login, token)
    except Exception as exc:
        print('动态获取失败，保留旧的 log.svg: %s' % exc, file=sys.stderr)
    try:
        aur = fetch_aur(maintainer)
    except Exception as exc:
        print('AUR 获取失败，保留旧的 aur.svg: %s' % exc, file=sys.stderr)
    return user, events, aur, dt.datetime.now(dt.timezone.utc).date()


def calendar_days(user):
    weeks = user['contributionsCollection']['contributionCalendar']['weeks']
    return [(dt.date.fromisoformat(d['date']), d['contributionCount']) for w in weeks for d in w['contributionDays']]


def streaks(days, today):
    counts = dict(days)
    run = best = 0
    for _, c in sorted(days):
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    day = today if counts.get(today, 0) > 0 else today - dt.timedelta(days=1)
    cur = 0
    while counts.get(day, 0) > 0:
        cur += 1
        day -= dt.timedelta(days=1)
    return cur, best


def weekly(days, weeks=26):
    out = []
    for i in range(0, len(days), 7):
        out.append(sum(c for _, c in days[i:i + 7]))
    return out[-weeks:]


def age(created, today):
    c = dt.date.fromisoformat(created[:10])
    months = (today.year - c.year) * 12 + today.month - c.month - (1 if today.day < c.day else 0)
    years, months = divmod(max(0, months), 12)
    parts = []
    if years:
        parts.append('%d year%s' % (years, '' if years == 1 else 's'))
    if months or not years:
        parts.append('%d month%s' % (months, '' if months == 1 else 's'))
    return ', '.join(parts)


def summarize(user, today):
    repos = user['repositories']['nodes']
    own = [r for r in repos if not r['isFork']]
    langs = {}
    for r in own:
        if r.get('primaryLanguage'):
            name = r['primaryLanguage']['name']
            langs[name] = langs.get(name, 0) + 1
    days = calendar_days(user)
    cur, best = streaks(days, today)
    cc = user['contributionsCollection']
    return {
        'login': user['login'],
        'location': user.get('location') or '',
        'age': age(user['createdAt'], today),
        'since': user['createdAt'][:4],
        'repos': user['repositories']['totalCount'],
        'sources': len(own),
        'stars': sum(r['stargazerCount'] for r in own),
        'forks': sum(r['forkCount'] for r in own),
        'langs': [k for k, _ in sorted(langs.items(), key=lambda kv: (-kv[1], kv[0].lower()))][:3],
        'followers': user['followers']['totalCount'],
        'following': user['following']['totalCount'],
        'starred': user['starredRepositories']['totalCount'],
        'prs': user['pullRequests']['totalCount'],
        'issues': user['issues']['totalCount'],
        'contributed': user['repositoriesContributedTo']['totalCount'],
        'commits': cc['totalCommitContributions'],
        'contribs': cc['contributionCalendar']['totalContributions'],
        'streak': cur,
        'best': best,
        'weekly': weekly(days),
    }


TERM_X, TERM_W = 24, W - 48
TERM_BODY = '#0c0a1d'
TERM_BAR = '#1b1745'
PROMPT = (('[', pk.SOFT), ('cx', pk.GREEN), ('@', pk.SOFT), ('sunflower', pk.CYAN), (' ~', pk.BLUE), (']$ ', pk.SOFT))
DOT = ('.####.', '######', '######', '######', '######', '.####.')


def segments(parts, x, y, s=2, style='r'):
    out = []
    for t, color in parts:
        out.append(pk.text(t, x, y, s, color, style))
        x += len(t) * pk.advance('a', style) * s
    return ''.join(out), x


def term_frame(svg, H, top=True, bottom=False, title='cx@sunflower: ~'):
    x, w = TERM_X, TERM_W
    y0 = 10 if top else 0
    y1 = H - 12 if bottom else H
    out = [path([(x + 4, y0 + 4, w, y1 - y0)], pk.INK), path([(x, y0, w, y1 - y0)], pk.INK),
           path([(x + 2, y0 + (2 if top else 0), w - 4, y1 - y0 - (2 if top else 0) - (2 if bottom else 0))], TERM_BODY)]
    out.append(path([(x + 2, y0, 2, y1 - y0), (x + w - 4, y0, 2, y1 - y0)], '#16133a'))
    if top:
        out.append(path([(x + 2, y0 + 2, w - 4, 24)], TERM_BAR) + path([(x + 2, y0 + 2, w - 4, 2)], '#2b2563') +
                   path([(x + 2, y0 + 26, w - 4, 2)], pk.INK))
        for i, c in enumerate((pk.RED, pk.SUN, pk.GREEN)):
            out.append(pk.sprite(DOT, {'#': c}, 2, x + 12 + i * 20, y0 + 8))
            out.append(path([(x + 14 + i * 20, y0 + 10, 2, 2)], pk.SNOW))
        out.append(pk.text(title, x + (w - pk.text_w(title, 2)) // 2, y0 + 9, 2, pk.SOFT))
    body_top = y0 + 28 if top else 0
    out.append(pk.scanlines(svg, x + 4, body_top, w - 8, y1 - body_top - (2 if bottom else 0), opacity=0.25))
    return ''.join(out)


def type_command(svg, cmd, x, y, t0, cycle, dt_char=0.09, t_off=None):
    '''提示符 + 逐字输入的命令 + 跟随光标；返回 (svg, 输入结束时间)。'''
    prompt, cx = segments(PROMPT, x, y)
    adv = pk.advance('a') * 2
    dur = len(cmd) * dt_char
    clip = pk.reveal(svg, cx, y - 2, len(cmd) * adv, 22, t0, dur, cycle, len(cmd), t_off)
    cur = pk.typing_cursor(svg, cx, y, 10, 14, pk.SNOW, t0, dur, cycle, len(cmd), len(cmd) * adv, t_hide=t0 + dur + 0.25)
    return prompt + "<g%s>%s</g>" % (clip, pk.text(cmd, cx, y, 2, pk.WHITE)) + cur, t0 + dur


def show(svg, t_on, t_off, cycle, inner):
    return "<g class='%s'>%s</g>" % (pk.window_cls(svg, t_on, t_off, cycle), inner)


def render_terminal(st):
    H = 352
    summary = ('GitHub stats for %s: %d public repos, %d stars, %d commits and %d contributions in the last year, '
               'streak %d (best %d), %d followers' % (st['login'], st['repos'], st['stars'], st['commits'],
                                                      st['contribs'], st['streak'], st['best'], st['followers']))
    svg = pk.Svg(W, H, summary)
    cycle, x0 = 16.0, TERM_X + 20
    b = [term_frame(svg, H)]
    cmd, t = type_command(svg, 'neofetch', x0, 52, 0.3, cycle, t_off=cycle - 0.6)
    b.append(cmd)
    off = cycle - 0.6
    logo_rows, logo_colors = pk.LOGOS['arch_big']
    b.append(show(svg, t + 0.2, off, cycle, pk.sprite(logo_rows, logo_colors, 4, x0 + 8, 92)))
    rows = [('OS', 'Arch Linux x86_64'),
            ('Uptime', '%s on GitHub' % st['age']),
            ('Packages', '%s (aur)' % st.get('aur_count', '?')),
            ('Langs', ' · '.join(st['langs']) or 'Kotlin · Python'),
            ('Repos', '%d public · ★ %d stars' % (st['repos'], st['stars'])),
            ('Commits', '%d in the last year' % st['commits']),
            ('PR/Issue', '%d pull requests · %d issues' % (st['prs'], st['issues'])),
            ('Contribs', '%d in the last year' % st['contribs']),
            ('Streak', '%d day%s · best %d' % (st['streak'], '' if st['streak'] == 1 else 's', st['best'])),
            ('Social', '%d followers · %d following' % (st['followers'], st['following']))]
    if st['location']:
        rows.insert(1, ('Location', st['location']))
    ix, iy, lh = x0 + 176, 88, 18
    line_t = t + 0.35
    head, _ = segments((('cx', pk.GREEN), ('@', pk.SOFT), ('sunflower', pk.CYAN)), ix, iy, 2, 'b')
    b.append(show(svg, line_t, off, cycle, head))
    b.append(show(svg, line_t + 0.06, off, cycle, pk.text('-' * 12, ix, iy + lh, 2, pk.SOFT)))
    for i, (k, v) in enumerate(rows):
        y = iy + (i + 2) * lh
        line = pk.text(k, ix, y, 2, pk.PINK if i % 2 else pk.CYAN, 'b') + pk.text(pk.fit(v, 2, 440), ix + 132, y, 2, pk.WHITE)
        b.append(show(svg, line_t + 0.12 + i * 0.07, off, cycle, line))
    by = iy + (len(rows) + 2) * lh + 8
    colors = (pk.INK, pk.RED, pk.GREEN, pk.SUN, pk.BLUE, pk.PURPLE, pk.CYAN, pk.WHITE)
    blocks = ''.join(path([(ix + i * 26, by, 26, 12)], c) + path([(ix + i * 26, by + 12, 26, 12)], pk.mix(c, 0.35))
                     for i, c in enumerate(colors))
    b.append(show(svg, line_t + 0.2 + len(rows) * 0.07, off, cycle, blocks))
    weeks = st['weekly'] or [0]
    bw = 5
    cx0, cy0, cw, chh = x0 + 8, 252, len(weeks) * bw + 2, 62
    peak = max(weeks) or 1
    chart = [path([(cx0 - 2, cy0 - 2, cw + 4, chh + 4)], '#0a0819'), path([(cx0 - 2, cy0 + chh, cw + 4, 2)], pk.LINE),
             pk.text('26 WEEKS', cx0, cy0 - 20, 2, pk.MUTED, 'b')]
    gt = svg.uid('gr')
    svg.css('.%s{transform-box:fill-box;transform-origin:50%% 100%%;animation:%s %ss steps(4,end) infinite}'
            '@keyframes %s{0%%,%s{transform:scaleY(0)}%s,%s{transform:scaleY(1)}%s,100%%{transform:scaleY(0)}}'
            % (gt, gt, n(cycle), gt, pk.pc((line_t + 0.2) / cycle * 100), pk.pc((line_t + 1.0) / cycle * 100),
               pk.pc(off / cycle * 100), pk.pc(off / cycle * 100 + 0.01)))
    for i, v in enumerate(weeks):
        h = max(2, int(round(v / float(peak) * (chh - 10))) // 2 * 2) if v else 2
        level = 0 if not v else 1 + min(3, int(v / float(peak) * 3.999))
        col = (pk.LINE, pk.PURPLE3, pk.PURPLE2, pk.PURPLE, pk.PINK)[level]
        chart.append("<path class='%s' fill='%s' d='%s'/>" % (gt, col, d_rects([(cx0 + 1 + i * bw, cy0 + chh - h, bw - 1, h)])))
    chart.append(pk.text('peak %d/wk' % peak, cx0, cy0 + chh + 10, 2, pk.SOFT))
    b.append(show(svg, line_t + 0.2, off, cycle, ''.join(chart)))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


def render_aur(pkgs, maintainer):
    pkgs = sorted(pkgs, key=lambda p: (-int(p.get('NumVotes') or 0), p.get('Name', '')))
    rows = max(1, len(pkgs))
    H = 64 + rows * 40 + 64
    label = 'AUR packages maintained by %s: %s' % (
        maintainer, ', '.join('%s %s' % (p['Name'], p['Version']) for p in pkgs) or 'none')
    svg = pk.Svg(W, H, label)
    cycle, x0 = 16.0, TERM_X + 20
    off = cycle - 0.6
    b = [term_frame(svg, H, top=False, bottom=True)]
    cmd, t = type_command(svg, 'yay -Ss --searchby maintainer ' + maintainer, x0, 14, 2.6, cycle, dt_char=0.05, t_off=off)
    b.append(cmd)
    y = 46
    if not pkgs:
        b.append(show(svg, t + 0.3, off, cycle, pk.text(' -> No packages found', x0, y, 2, pk.SOFT)))
    for i, p in enumerate(pkgs):
        name, ver = p['Name'], p['Version']
        votes, pop = int(p.get('NumVotes') or 0), float(p.get('Popularity') or 0)
        line, cx = segments((('aur/', pk.PINK), (name, pk.WHITE), (' ', pk.WHITE), (ver, pk.GREEN),
                             (' (+%d %.2f)' % (votes, pop), pk.SUN)), x0, y, 2, 'b')
        if p.get('OutOfDate'):
            line += pk.text(' (Out-of-date)', cx, y, 2, pk.RED, 'b')
        desc = p.get('Description') or ''
        updated = dt.datetime.fromtimestamp(int(p.get('LastModified') or 0), dt.timezone.utc).strftime('%Y-%m-%d')
        detail = (desc + ' · ' if desc and pk.ascii_only(desc) else '') + 'updated ' + updated
        line += pk.text('    ' + pk.fit(detail, 2, TERM_W - 90), x0, y + 18, 2, pk.SOFT)
        b.append(show(svg, t + 0.3 + i * 0.15, off, cycle, line))
        y += 40
    total = sum(int(p.get('NumVotes') or 0) for p in pkgs)
    end = t + 0.45 + len(pkgs) * 0.15
    foot, _ = segments(((':: ', pk.BLUE), ('%d package%s · %d votes in total' % (len(pkgs), '' if len(pkgs) == 1 else 's', total), pk.WHITE)),
                       x0, y + 4, 2, 'b')
    b.append(show(svg, end, off, cycle, foot))
    prompt, px = segments(PROMPT, x0, y + 30)
    svg.css(pk.BLINK_CSS)
    b.append(show(svg, end + 0.2, off, cycle, prompt + "<g class='blk'>%s</g>" % path([(px, y + 30, 10, 14)], pk.SNOW)))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


EVENT_STYLE = {
    'PushEvent': ('upload', pk.GREEN), 'CreateEvent': ('plus', pk.CYAN), 'WatchEvent': ('sparkles', pk.SUN),
    'ForkEvent': ('git-branch', pk.BLUE), 'PullRequestEvent': ('git-pull-request', pk.PURPLE),
    'PullRequestReviewEvent': ('eye', pk.PURPLE), 'IssuesEvent': ('bug', pk.ORANGE),
    'IssueCommentEvent': ('message', pk.SOFT), 'ReleaseEvent': ('label', pk.PINK), 'PublicEvent': ('globe', pk.CYAN),
    'DeleteEvent': ('trash', pk.MUTED), 'MemberEvent': ('user', pk.CYAN), 'GollumEvent': ('book-open', pk.SOFT),
    'CommitCommentEvent': ('message', pk.SOFT), 'PullRequestReviewCommentEvent': ('message', pk.PURPLE),
}


def describe(ev):
    kind, repo = ev.get('type'), (ev.get('repo') or {}).get('name', '?')
    p = ev.get('payload') or {}
    if kind == 'PushEvent':
        size = p.get('distinct_size') or p.get('size')
        if size:
            return 'Pushed %d commit%s to %s' % (size, '' if size == 1 else 's', repo)
        return 'Pushed to ' + repo
    if kind == 'CreateEvent':
        if p.get('ref_type') == 'repository':
            return 'Created repository ' + repo
        return 'Created %s %s in %s' % (p.get('ref_type', 'ref'), p.get('ref') or '', repo)
    if kind == 'DeleteEvent':
        return 'Deleted %s %s in %s' % (p.get('ref_type', 'ref'), p.get('ref') or '', repo)
    if kind == 'WatchEvent':
        return 'Starred ' + repo
    if kind == 'ForkEvent':
        return 'Forked ' + repo
    if kind in ('PullRequestEvent', 'IssuesEvent'):
        item = p.get('pull_request') or p.get('issue') or {}
        num = p.get('number') or item.get('number') or ''
        action = p.get('action', 'updated')
        if kind == 'PullRequestEvent' and action == 'closed' and item.get('merged'):
            action = 'merged'
        noun = 'PR' if kind == 'PullRequestEvent' else 'issue'
        return '%s %s #%s in %s' % (action.capitalize(), noun, num, repo)
    if kind == 'PullRequestReviewEvent':
        return 'Reviewed PR #%s in %s' % ((p.get('pull_request') or {}).get('number', ''), repo)
    if kind in ('IssueCommentEvent', 'PullRequestReviewCommentEvent'):
        item = p.get('issue') or p.get('pull_request') or {}
        return 'Commented on #%s in %s' % (item.get('number', ''), repo)
    if kind == 'ReleaseEvent':
        return 'Released %s in %s' % ((p.get('release') or {}).get('tag_name', ''), repo)
    if kind == 'PublicEvent':
        return 'Made %s public' % repo
    if kind == 'MemberEvent':
        return 'Joined %s as collaborator' % repo
    if kind == 'GollumEvent':
        return 'Updated the wiki of ' + repo
    if kind == 'CommitCommentEvent':
        return 'Commented on a commit in ' + repo
    return None


def activity(events, limit=6):
    '''按时间倒序，把同一天对同一仓库的推送/建分支合并，返回 [(类型, 文本, 日期, 次数)]。'''
    out, seen = [], {}
    for ev in sorted(events or [], key=lambda e: e.get('created_at') or '', reverse=True):
        kind = ev.get('type')
        p = ev.get('payload') or {}
        if kind == 'DeleteEvent' or (kind == 'CreateEvent' and p.get('ref_type') == 'tag'):
            continue
        text = describe(ev)
        if not text:
            continue
        day = (ev.get('created_at') or '')[:10]
        repo = (ev.get('repo') or {}).get('name')
        key = (kind, repo, day) if kind in ('PushEvent', 'CreateEvent') and p.get('ref_type') != 'repository' else None
        if key and key in seen:
            seen[key][3] += 1
            continue
        item = [kind, text, day, 1]
        if key:
            seen[key] = item
        out.append(item)
    for item in out:
        if item[0] == 'CreateEvent' and item[3] > 1:
            item[1] = 'Created %d branches in %s' % (item[3], item[1].rsplit(' in ', 1)[-1])
            item[3] = 1
    return [tuple(x) for x in out[:limit]]


MONTHS = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')


def render_log(items):
    rows = max(1, len(items))
    H = 76 + rows * 34 + 24
    label = 'Recent public activity: ' + ('; '.join(t for _, t, _, _ in items) if items else 'no recent signals')
    svg = pk.Svg(W, H, label)
    b = [pk.starfield(svg, random.Random(606), (6, 2, W - 6, H - 2), 24, 8, 1)]
    x, y, w, h = 24, 10, W - 48, H - 20
    b.append(path([(x, y, w, h)], '#0d0b22') + pk.brackets(x, y, w, h, pk.CYAN, 18, 3))
    b.append(path([(x + 24, y + 40, w - 48, 2)], pk.LINE))
    b.append(pk.icon('analytics', x + 20, y + 10, 24, pk.CYAN) + pk.text2('MISSION LOG', x + 52, y + 14, 2, pk.CYAN, pk.CYAN2))
    tag = 'RECENT PUBLIC ACTIVITY'
    b.append(pk.text(tag, x + w - 20 - pk.text_w(tag, 2), y + 16, 2, pk.MUTED))
    cycle = 14.0
    svg.css(pk.BLINK_CSS)
    if not items:
        msg = 'No recent signals. Systems on standby.'
        b.append(pk.text(msg, pk.cx_text(msg, 2), y + 66, 2, pk.SOFT))
    lx = x + 40
    if len(items) > 1:
        b.append(path([(lx + 11, y + 70 + k * 6, 2, 3) for k in range(int((len(items) - 1) * 34 / 6))], pk.LINE))
    scan = svg.uid('scan')
    span = max(0, len(items) - 1) * 34
    svg.css('.%s{animation:%s 3.5s steps(%d,end) infinite}@keyframes %s{to{transform:translateY(%dpx)}}'
            % (scan, scan, max(1, len(items)), scan, span + 34))
    if items:
        b.append("<g class='%s'>%s</g>" % (scan, path([(x + 30, y + 52, w - 60, 30)], pk.CYAN, " opacity='.07'")))
    for i, (kind, text, day, count) in enumerate(items):
        ry = y + 58 + i * 34
        ic, col = EVENT_STYLE.get(kind, ('zap', pk.SOFT))
        row = path([(lx - 2, ry - 4, 28, 28)], '#0d0b22') + pk.icon(ic, lx, ry - 2, 24, col)
        if count > 1:
            text += ' x%d' % count
        row += pk.text(pk.fit(text, 2, w - 230), lx + 40, ry + 4, 2, pk.WHITE)
        try:
            d = dt.date.fromisoformat(day)
            stamp = '%s %02d' % (MONTHS[d.month - 1], d.day)
        except ValueError:
            stamp = ''
        sx = x + w - 24 - pk.text_w(stamp, 2, 'b')
        row += pk.text(stamp, sx, ry + 4, 2, pk.MUTED, 'b')
        b.append(show(svg, 0.3 + i * 0.25, cycle - 0.4, cycle, row))
        if i == 0:
            b.append(show(svg, 0.3, cycle - 0.4, cycle, "<g class='blk'>%s</g>" % (
                pk.bevel(sx - 56, ry, 44, 20, pk.PINK2, pk.PINK, pk.PINK3) + pk.text('NEW', sx - 49, ry + 4, 2, pk.SNOW, 'b'))))
    b.append(pk.side_frame(W, H))
    return svg.render(b)


def previous_aur_count(file):
    '''AUR 暂时不可用时，沿用上一次 aur.svg 标签里的软件包数量。'''
    try:
        label = re.search(r"aria-label='([^']*)'", file.read_text(encoding='utf-8')[:4000]).group(1)
    except (OSError, AttributeError):
        return '?'
    items = label.split(':', 1)[1].strip()
    return 0 if items == 'none' else len(items.split(', '))


def write(path_, svg):
    path_.parent.mkdir(parents=True, exist_ok=True)
    with open(path_, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(svg)
    print('%s %d bytes' % (path_, len(svg.encode('utf-8'))))


def main(argv):
    if len(argv) < 3:
        sys.exit('用法: githubStats.py <GitHub 用户名> <AUR 维护者> [输出目录]')
    login, maintainer = argv[1], argv[2]
    out = Path(argv[3]) if len(argv) > 3 else Path(__file__).resolve().parent.parent / 'assets'
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''
    user, events, aur, today = load(login, maintainer, token)
    st = summarize(user, today)
    if aur is not None:
        st['aur_count'] = len(aur)
        write(out / 'aur.svg', render_aur(aur, maintainer))
    else:
        st['aur_count'] = previous_aur_count(out / 'aur.svg')
    write(out / 'terminal.svg', render_terminal(st))
    if events is not None:
        write(out / 'log.svg', render_log(activity(events)))


if __name__ == '__main__':
    main(sys.argv)
