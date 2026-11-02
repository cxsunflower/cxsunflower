#!/usr/bin/env python3
"""将 snk 的负坐标画布嵌入 900 像素宽的连续深色海报。"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
BG = '#0b0a1f'
FRAME = '#3b2f8f'


def style_svg(source):
    original = ET.fromstring(source)
    x, y, width, height = map(float, original.attrib['viewBox'].split())
    if width <= 0 or height <= 0:
        raise ValueError('蛇图尺寸必须为正数')
    scale = min(1, 880 / width)
    output_height = height * scale
    root = ET.Element('{%s}svg' % NS, {
        'viewBox': '0 0 900 %g' % output_height,
        'width': '900', 'height': '%g' % output_height,
        'role': 'img', 'aria-label': 'GitHub contribution snake',
        'shape-rendering': 'crispEdges',
    })
    ET.SubElement(root, '{%s}title' % NS).text = 'GitHub contribution snake'
    ET.SubElement(root, '{%s}rect' % NS, {'width': '900', 'height': '%g' % output_height, 'fill': BG})
    outer = ET.SubElement(root, '{%s}g' % NS, {'transform': 'translate(%g 0) scale(%g)' % ((900 - width * scale) / 2, scale)})
    inner = ET.SubElement(outer, '{%s}g' % NS, {'transform': 'translate(%g %g)' % (-x, -y)})
    for child in original:
        # 兼容旧工作流已经插入背景和侧框的产物。
        if child.tag == '{%s}rect' % NS and child.get('fill') in (BG, FRAME) and not child.get('class'):
            continue
        inner.append(child)
    for node in root.iter('{%s}rect' % NS):
        if node.get('class', '').split()[:1] in (['c'], ['s']):
            node.set('rx', '0')
            node.set('ry', '0')
    ET.SubElement(root, '{%s}style' % NS).text = (
        '.c,.s{shape-rendering:crispEdges}'
        '@media(prefers-reduced-motion:reduce){*{animation:none!important}}'
    )
    for side in ('2', '896'):
        ET.SubElement(root, '{%s}rect' % NS, {'x': side, 'y': '0', 'width': '2', 'height': '%g' % output_height, 'fill': FRAME})
    return ET.tostring(root, encoding='unicode') + '\n'


if __name__ == '__main__':
    target = Path(sys.argv[1])
    result = style_svg(target.read_text(encoding='utf-8'))
    target.write_text(result, encoding='utf-8', newline='\n')
    print('蛇图已适配连续海报：900 像素宽，完整背景')
