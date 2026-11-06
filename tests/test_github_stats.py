import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest
import xml.dom.minidom
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'tests' / 'fixtures' / 'stats_normal.json'
SPEC = importlib.util.spec_from_file_location('githubStats', ROOT / 'src' / 'githubStats.py')
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)


def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


class GithubStats(unittest.TestCase):
    def assert_pixel_svg(self, svg):
        xml.dom.minidom.parseString(svg)
        self.assertNotIn('<text', svg)
        self.assertNotIn('<script', svg)
        self.assertIn("shape-rendering='crispEdges'", svg)
        self.assertIn('prefers-reduced-motion', svg)

    def test_summary_counts_own_repos_streaks_and_age(self):
        data = fixture()
        st = stats.summarize(data['user'], dt.date(2026, 11, 6))
        self.assertEqual(st['stars'], 15)
        self.assertEqual(st['langs'], ['Kotlin', 'Python'])
        self.assertEqual((st['streak'], st['best']), (3, 3))
        self.assertEqual(st['age'], '6 years, 4 months')
        self.assertEqual(st['weekly'], [7, 8])

    def test_streak_counts_today_when_active(self):
        days = [(dt.date(2026, 11, d), c) for d, c in ((4, 1), (5, 1), (6, 2))]
        self.assertEqual(stats.streaks(days, dt.date(2026, 11, 6)), (3, 3))
        self.assertEqual(stats.streaks(days, dt.date(2026, 11, 8)), (0, 3))

    def test_activity_merges_pushes_and_skips_noise(self):
        items = stats.activity(fixture()['events'])
        self.assertEqual(items, [
            ('PushEvent', 'Pushed to tester/app', '2026-11-05', 2),
            ('WatchEvent', 'Starred someone/cool-lib', '2026-11-04', 1),
            ('PullRequestEvent', 'Merged PR #7 in org/project', '2026-11-03', 1),
            ('CreateEvent', 'Created repository tester/new-repo', '2026-11-02', 1),
            ('IssuesEvent', 'Opened issue #12 in org/project', '2026-11-01', 1),
            ('PushEvent', 'Pushed 3 commits to tester/app', '2026-10-30', 1),
        ])

    def test_panels_are_deterministic_pixel_svgs(self):
        data = fixture()
        st = stats.summarize(data['user'], dt.date(2026, 11, 6))
        st['aur_count'] = 2
        for render in (lambda: stats.render_terminal(st), lambda: stats.render_aur(data['aur'], 'tester'),
                       lambda: stats.render_log(stats.activity(data['events'])), lambda: stats.render_log([])):
            svg = render()
            self.assertEqual(svg, render())
            self.assert_pixel_svg(svg)
        self.assertIn('consolas-font 1.2-2, tiny-tool 1.0-1', stats.render_aur(data['aur'], 'tester'))
        self.assertIn('no recent signals', stats.render_log([]))

    def test_main_writes_all_panels_from_fixture(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {'STATS_FIXTURE': str(FIXTURE)}):
            with redirect_stdout(io.StringIO()):
                stats.main(['githubStats.py', 'tester', 'tester', d])
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ['aur.svg', 'log.svg', 'terminal.svg'])

    def test_failed_sources_keep_previous_panels(self):
        data = fixture()
        with tempfile.TemporaryDirectory() as d:
            old = stats.render_aur(data['aur'], 'tester')
            (Path(d) / 'aur.svg').write_text(old, encoding='utf-8')
            self.assertEqual(stats.previous_aur_count(Path(d) / 'aur.svg'), 2)
            with mock.patch.object(stats, 'load', return_value=(data['user'], None, None, dt.date(2026, 11, 6))):
                with redirect_stdout(io.StringIO()):
                    stats.main(['githubStats.py', 'tester', 'tester', d])
            self.assertEqual((Path(d) / 'aur.svg').read_text(encoding='utf-8'), old)
            self.assertFalse((Path(d) / 'log.svg').exists())
            self.assertTrue((Path(d) / 'terminal.svg').exists())
        self.assertEqual(stats.previous_aur_count(Path(d) / 'missing.svg'), '?')


if __name__ == '__main__':
    unittest.main()
