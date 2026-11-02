import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'src' / 'getTopFollowers.py'
PREFIX = 'A\r\nkeep top\r\n<!--START_SECTION:top-followers-->'
SUFFIX = '<!--END_SECTION:top-followers-->\r\n<!--START_SECTION:waka-->\r\nW\r\n<!--END_SECTION:waka-->\r\nZ\r\n'
README = PREFIX + '\r\nold\r\n' + SUFFIX
BACKSLASH = chr(92)


def node(i, followers=None, following=0, active=True, name=None):
    return {'login': 'user%02d' % i, 'name': name, 'databaseId': 1000 + i,
            'following': {'totalCount': following},
            'repositories': {'nodes': []}, 'repositoriesContributedTo': {'nodes': []},
            'followers': {'totalCount': 100 - i if followers is None else followers},
            'contributionsCollection': {'hasAnyContributions': active}}


def pages(nodes, size=10):
    out = [{'pageInfo': {'endCursor': 'c%d' % s, 'hasNextPage': s + size < len(nodes)}, 'nodes': nodes[s:s + size]}
           for s in range(0, len(nodes), size)]
    return out or [{'pageInfo': {'endCursor': None, 'hasNextPage': False}, 'nodes': []}]


class TopFollowers(unittest.TestCase):
    def run_script(self, nodes):
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / 'f.json'
            fx.write_text(json.dumps(pages(nodes)), encoding='utf-8')
            rd = Path(d) / 'README.md'
            rd.write_bytes(README.encode('utf-8'))
            env = dict(os.environ, FOLLOWERS_FIXTURE=str(fx))
            proc = subprocess.run([sys.executable, str(SCRIPT), 'me', 'tok', str(rd)], env=env,
                                  capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = rd.read_bytes().decode('utf-8')
        self.assertTrue(out.startswith(PREFIX), 'prefix changed')
        self.assertTrue(out.endswith(SUFFIX), 'suffix changed')
        return out[len(PREFIX):-len(SUFFIX)], proc.stdout

    def test_empty(self):
        mid, _ = self.run_script([])
        self.assertIn('NO SIGNALS YET', mid)
        self.assertNotIn('<tr>', mid)
        self.assertNotIn('</tr>', mid)

    def test_one(self):
        mid, _ = self.run_script([node(0)])
        self.assertEqual((mid.count('<tr>'), mid.count('</tr>'), mid.count('<td ')), (1, 1, 1))
        self.assertIn('avatars.githubusercontent.com/u/1000?s=100', mid)
        self.assertIn('width="100"', mid)
        self.assertNotIn('100px;', mid)

    def test_many_filtered_and_escaped(self):
        inactive, quota = {3, 7, 12}, {5, 9}
        nodes = []
        for i in range(30):
            name = '<b>x' + BACKSLASH + 'g<0></b>' if i == 0 else None
            nodes.append(node(i, following=5000 if i in quota else 0, active=i not in inactive, name=name))
        mid, out = self.run_script(nodes)
        self.assertEqual((mid.count('<tr>'), mid.count('</tr>'), mid.count('<td ')), (3, 3, 21))
        for i in inactive | quota:
            self.assertNotIn('user%02d' % i, mid)
        self.assertEqual(out.count('(inactive)'), 3)
        self.assertEqual(out.count('(quota)'), 2)
        self.assertIn('user25', mid)
        self.assertNotIn('user26', mid)
        self.assertNotIn('<b>', mid)
        self.assertIn('&lt;b&gt;x' + BACKSLASH + 'g&lt;0&gt;&lt;/b&gt;', mid)
        self.assertLess(mid.index('user00'), mid.index('user01'))
        again, _ = self.run_script(nodes)
        self.assertEqual(mid, again)

    def test_all_filtered_falls_back(self):
        mid, out = self.run_script([node(0, active=False), node(1, following=5000)])
        self.assertIn('falling back to the unfiltered list', out)
        self.assertIn('user00', mid)
        self.assertIn('user01', mid)
        self.assertEqual((mid.count('<tr>'), mid.count('</tr>'), mid.count('<td ')), (1, 1, 2))
        self.assertNotIn('NO SIGNALS YET', mid)


if __name__ == '__main__':
    unittest.main()
