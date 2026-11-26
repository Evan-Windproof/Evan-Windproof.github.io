import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts import build_blog


def fixture(root, count):
    """Build a disposable site, with the newest post outside the shared tag."""
    source = root / 'content/blog'
    source.mkdir(parents=True, exist_ok=True)
    for old in source.glob('*.md'):
        old.unlink()
    (root / 'index.html').write_text('<!-- latest:start --><!-- latest:end -->')
    for i in range(1, count + 1):
        tags = '[Other]' if i == count else '[Gecko, 测试]'
        description = 'shared keyword' if i > 1 else 'uncommon needle'
        (source / f'post-{i:02}.md').write_text(f'''---
title: 'Fixture {i:02}'
description: '{description}'
date: 2026-11-{i:02}
updated: 2026-11-{i:02}
tags: {tags}
category: Test
slug: fixture-{i:02}
draft: false
language: en
---
Fixture body.
''')
    original = build_blog.ROOT
    try:
        build_blog.ROOT = root
        build_blog.build()
    finally:
        build_blog.ROOT = original


class PaginationTest(unittest.TestCase):
    def test_sizes_sitemap_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # Rebuild largest to smallest to validate the stale-page manifest too.
            for count in (25, 24, 13, 12, 1, 0):
                with self.subTest(count=count):
                    fixture(root, count)
                    sitemap = {node.text for node in ET.parse(root / 'sitemap.xml').findall('.//{*}loc')}
                    for base, total in [('/blog/', count), ('/blog/tags/gecko/', max(0, count - 1))]:
                        pages = max(1, (total + 11) // 12)
                        for page in range(1, 4):
                            path = build_blog.page_path(base, page)
                            file = root / path.lstrip('/') / 'index.html'
                            expected = page <= pages and (base == '/blog/' or total > 0)
                            self.assertEqual(file.is_file(), expected, path)
                            self.assertEqual(build_blog.BASE + path in sitemap, expected)
                            if expected:
                                html = file.read_text()
                                self.assertEqual(html.count('class="post-card"'), min(12, total - (page - 1) * 12))
                                self.assertEqual('class="blog-pagination"' in html, pages > 1)
                                self.assertIn(f'rel="canonical" href="{build_blog.BASE}{path}"', html)
                        first = root / base.lstrip('/') / 'index.html'
                        if first.exists():
                            ids = re.findall(r'<h2><a href="/blog/fixture-(\d+)/', first.read_text())
                            self.assertEqual(ids, sorted(ids, reverse=True))
                    self.assertEqual(len(json.loads((root / 'blog/articles.json').read_text())), count)
                    self.assertEqual(len(ET.parse(root / 'rss.xml').findall('./channel/item')), count)

    def test_ellipsis_keeps_ends_and_neighbors(self):
        nav = build_blog.pagination('/blog/', 10, 20, 240)
        self.assertEqual(nav.count('…'), 2)
        self.assertIn('aria-current="page">10', nav)
        for page in [9, 11, 20]:
            self.assertIn(f'/blog/page/{page}/#article-list', nav)
