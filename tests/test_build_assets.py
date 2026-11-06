import io
import sys
import tempfile
import unittest
import xml.dom.minidom
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build_assets  # noqa: E402
import pixelkit as pk  # noqa: E402

EXPECTED = ['arcade.svg', 'btn-repos.svg', 'btn-stars.svg', 'footer.svg', 'hero.svg', 'inventory.svg', 'profile.svg']


class StaticPosters(unittest.TestCase):
    def test_posters_are_deterministic_pixel_svgs(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            with redirect_stdout(io.StringIO()):
                build_assets.main(['build_assets.py', a])
                build_assets.main(['build_assets.py', b])
            self.assertEqual(sorted(p.name for p in Path(a).glob('*.svg')), EXPECTED)
            for name in EXPECTED:
                svg = (Path(a) / name).read_text(encoding='utf-8')
                self.assertEqual(svg, (Path(b) / name).read_text(encoding='utf-8'), name)
                xml.dom.minidom.parseString(svg)
                self.assertNotIn('<text', svg)
                self.assertNotIn('<script', svg)
                self.assertNotIn('var(', svg)
                self.assertIn("shape-rendering='crispEdges'", svg)
                self.assertIn('prefers-reduced-motion', svg)
                width = pk.W // 2 if name.startswith('btn-') else pk.W
                self.assertIn("viewBox='0 0 %d " % width, svg)

    def test_font_measures_and_fits(self):
        self.assertEqual(pk.text_w('abc', 2), 34)
        self.assertEqual(pk.text_w('ABC', 2, 'b'), 40)
        self.assertTrue(pk.ascii_only('Hello, world! (v1.2)'))
        self.assertFalse(pk.ascii_only('向日葵'))
        clipped = pk.fit('abcdefghijklmnop', 2, 60)
        self.assertTrue(clipped.endswith('…'))
        self.assertLessEqual(pk.text_w(clipped, 2), 60)

    def test_reveal_keeps_text_visible_without_animation(self):
        svg = pk.Svg(100, 20, 't')
        attr = pk.reveal(svg, 0, 0, 60, 20, 0.5, 1.0, 4.0, 5)
        self.assertIn('clip-path', attr)
        css = ''.join(svg.rules)
        self.assertIn('steps(5,end)', css)
        self.assertIn("<rect class='rv1' x='0' y='0' width='60' height='20'/>", ''.join(svg.defs))


if __name__ == '__main__':
    unittest.main()
