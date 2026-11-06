import importlib.util
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('style_snake', Path(__file__).resolve().parent.parent / 'scripts/style_snake.py')
snake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snake)
NS = '{http://www.w3.org/2000/svg}'
SOURCE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -32 880 192">
<rect width="100%" height="100%" fill="#0b0a1f"/>
<style>.c{width:12px;height:12px}.s{fill:var(--cs);animation:move 3s infinite}@keyframes move{to{transform:translateX(20px)}}</style>
<rect class="c" x="2" y="2" rx="2" ry="2"/>
<rect class="s s0" x="0" y="-16" width="14" height="14" rx="4"/>
</svg>'''


class SnakeArcade(unittest.TestCase):
    def test_grid_lands_on_whole_pixels_and_animation_survives(self):
        out = snake.style_svg(SOURCE)
        root = ET.fromstring(out)
        self.assertEqual(root.get('viewBox').split()[:3], ['0', '0', '846'])
        group = next(g for g in root.iter(NS + 'g') if 'scale(0.875)' in (g.get('transform') or ''))
        tx, ty = map(float, re.match(r'translate\(([\d.]+) ([\d.]+)\)', group.get('transform')).groups())
        self.assertTrue((tx + 0.875 * 2).is_integer() and (ty + 0.875 * 2).is_integer())
        self.assertIn('@keyframes move', out)
        self.assertIn('prefers-reduced-motion', out)
        cells = [n for n in root.iter(NS + 'rect') if (n.get('class') or '').split()[:1] in (['c'], ['s'])]
        self.assertEqual({c.get('rx') for c in cells}, {'0'})
        self.assertNotIn("fill='#0b0a1f' width='100%'", out)

    def test_overrides_follow_snk_style(self):
        out = snake.style_svg(SOURCE)
        self.assertLess(out.index('.c{width:12px'), out.index('.c{width:12.5714px'))
        self.assertLess(out.index('.s{fill:var(--cs)'), out.index('.s.s0{fill:'))


if __name__ == '__main__':
    unittest.main()
