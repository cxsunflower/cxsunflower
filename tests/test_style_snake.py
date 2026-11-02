import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('style_snake', Path(__file__).resolve().parent.parent / 'scripts/style_snake.py')
snake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snake)
NS = '{http://www.w3.org/2000/svg}'


class SnakePoster(unittest.TestCase):
    def test_negative_viewbox_is_fully_covered_and_animation_survives(self):
        source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -32 880 192">
        <rect width="100%" height="100%" fill="#0b0a1f"/>
        <style>.s{animation:move 3s infinite}@keyframes move{to{transform:translateX(20px)}}</style>
        <rect class="s" x="0" y="-16" width="14" height="14" rx="4"/>
        </svg>'''
        root = ET.fromstring(snake.style_svg(source))
        self.assertEqual(root.get('viewBox'), '0 0 900 192')
        backdrop = root.find(NS + 'rect')
        self.assertEqual((backdrop.get('width'), backdrop.get('height'), backdrop.get('fill')), ('900', '192', '#0b0a1f'))
        group = root.find(NS + 'g')
        self.assertEqual(group.get('transform'), 'translate(10 0) scale(1)')
        self.assertEqual(group.find(NS + 'g').get('transform'), 'translate(16 32)')
        self.assertIn('@keyframes move', ''.join(root.itertext()))
        self.assertIn('prefers-reduced-motion', ''.join(root.itertext()))
        head = next(n for n in root.iter(NS + 'rect') if n.get('class') == 's')
        self.assertEqual(head.get('rx'), '0')


if __name__ == '__main__':
    unittest.main()
