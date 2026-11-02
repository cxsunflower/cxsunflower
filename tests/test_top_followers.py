import importlib.util
import json
import os
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('topFollowers', ROOT / 'src' / 'getTopFollowers.py')
followers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(followers)


def node(i, following=0, active=True, name=None):
    return {'login': 'user%02d' % i, 'name': name, 'databaseId': 1000 + i,
            'following': {'totalCount': following},
            'repositories': {'nodes': []}, 'repositoriesContributedTo': {'nodes': []},
            'followers': {'totalCount': 100 - i},
            'contributionsCollection': {'hasAnyContributions': active}}


def pages(nodes, size=10):
    return [{'pageInfo': {'endCursor': 'c%d' % s, 'hasNextPage': s + size < len(nodes)},
             'nodes': nodes[s:s + size]} for s in range(0, len(nodes), size)] or [
        {'pageInfo': {'endCursor': None, 'hasNextPage': False}, 'nodes': []}]


class TopFollowers(unittest.TestCase):
    def collect(self, nodes):
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / 'followers.json'
            fx.write_text(json.dumps(pages(nodes)), encoding='utf-8')
            with mock.patch.dict(os.environ, {'FOLLOWERS_FIXTURE': str(fx)}, clear=False):
                return followers.collect('me', 'token')

    def test_empty(self):
        self.assertEqual(self.collect([]), [])
        svg = followers.render_svg([], {})
        self.assertIn('no signals yet', svg)
        self.assertNotIn('<text', svg)
        xml.dom.minidom.parseString(svg)

    def test_one(self):
        out = self.collect([node(0)])
        self.assertEqual([x[1] for x in out], ['user00'])
        svg = followers.render_svg(out, {})
        self.assertIn('Followers: user00', svg)
        self.assertIn('<image', followers.render_svg(out, {'user00': 'data:image/png;base64,AAAA'}))
        xml.dom.minidom.parseString(svg)

    def test_many_filtered(self):
        inactive, quota = {3, 7, 12}, {5, 9}
        nodes = [node(i, following=5000 if i in quota else 0, active=i not in inactive) for i in range(30)]
        out = self.collect(nodes)
        logins = [x[1] for x in out]
        self.assertEqual(len(logins), 25)
        for i in inactive | quota:
            self.assertNotIn('user%02d' % i, logins)
        self.assertIn('user25', logins)
        svg = followers.render_svg(out, {})
        self.assertIn('user25', svg)
        self.assertNotIn('user26', svg)
        self.assertEqual(logins, sorted(logins, key=lambda x: (int(x[4:]), x)))

    def test_all_filtered_falls_back(self):
        out = self.collect([node(0, active=False), node(1, following=5000)])
        self.assertEqual([x[1] for x in out], ['user00', 'user01'])

    def test_non_ascii_name_uses_login(self):
        self.assertEqual(followers.display_name('向日葵', 'cxsunflower'), 'cxsunflower')
        self.assertEqual(followers.display_name('Kyla', 'kpopdev'), 'Kyla')

    def test_render_is_deterministic_pixel_only(self):
        out = self.collect([node(0), node(1)])
        a = followers.render_svg(out, {})
        b = followers.render_svg(out, {})
        self.assertEqual(a, b)
        self.assertNotIn('<text', a)
        self.assertNotIn('<script', a)
        self.assertIn("shape-rendering='crispEdges'", a)
        xml.dom.minidom.parseString(a)


if __name__ == '__main__':
    unittest.main()
