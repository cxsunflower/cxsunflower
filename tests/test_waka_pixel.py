import importlib.util
import os
import unittest
import xml.dom.minidom
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('wakaPixel', ROOT / 'src' / 'wakaPixel.py')
waka = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(waka)


class WakaPixel(unittest.TestCase):
    def test_parse_filters_other_and_sorts(self):
        payload = {'data': {'total_seconds': 1000, 'languages': [
            {'name': 'Other', 'total_seconds': 100, 'percent': 10},
            {'name': 'Kotlin', 'total_seconds': 600, 'percent': 60},
            {'name': 'Python', 'total_seconds': 300, 'percent': 30},
        ]}}
        langs, total, tracked = waka.parse(payload)
        self.assertEqual(total, 1000)
        self.assertEqual(tracked, 3)
        self.assertEqual([x[0] for x in langs], ['Kotlin', 'Python'])

    def test_provider_prefers_oauth(self):
        with mock.patch.dict(os.environ, {
            'WAKATIME_OAUTH_TOKEN': 'test-oauth-token',
            'WAKAPI_API_KEY': 'legacy',
            'WAKAPI_BASE_URL': 'https://wakapi.example/api',
        }, clear=True):
            kind, token, url = waka.resolve_provider()
        self.assertEqual(kind, 'wakatime')
        self.assertEqual(token, 'test-oauth-token')
        self.assertEqual(url, 'https://wakatime.com/api/v1/users/current/stats/all_time')

    def test_provider_wakapi_fallback(self):
        with mock.patch.dict(os.environ, {
            'WAKA_PROVIDER': 'wakapi',
            'WAKAPI_API_KEY': 'legacy-key',
            'WAKAPI_BASE_URL': 'https://wakapi.example/api/',
        }, clear=True):
            kind, _, url = waka.resolve_provider()
        self.assertEqual(kind, 'wakapi')
        self.assertEqual(url, 'https://wakapi.example/api/compat/wakatime/v1/users/current/stats/all_time')

    def test_render_is_deterministic_and_pixel_only(self):
        payload = {'data': {'total_seconds': 1000, 'languages': [
            {'name': 'Kotlin', 'total_seconds': 600, 'percent': 60},
            {'name': 'Python', 'total_seconds': 300, 'percent': 30},
        ]}}
        langs, total, tracked = waka.parse(payload)
        svg = waka.render(langs, total, tracked, 'WakaTime OAuth')
        again = waka.render(langs, total, tracked, 'WakaTime OAuth')
        self.assertEqual(svg, again)
        self.assertNotIn('<text', svg)
        self.assertNotIn('<script', svg)
        self.assertIn("shape-rendering='crispEdges'", svg)
        xml.dom.minidom.parseString(svg)


if __name__ == '__main__':
    unittest.main()
