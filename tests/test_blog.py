"""Protect publication boundaries independently of the example article."""
import importlib.util, tempfile, unittest, xml.etree.ElementTree as ET
from pathlib import Path
spec=importlib.util.spec_from_file_location('build',Path(__file__).resolve().parents[1]/'scripts/build_blog.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class BlogPublication(unittest.TestCase):
 def test_publication(self):
  original=build.ROOT
  with tempfile.TemporaryDirectory() as folder:
   try:
    build.ROOT=Path(folder);content=build.ROOT/'content/blog';content.mkdir(parents=True)
    (build.ROOT/'index.html').write_text('<!-- latest:start --><!-- latest:end -->')
    for slug,draft in [('first',False),('second',False),('private-draft',True)]:
     (content/(slug+'.md')).write_text(f'''---
title: 'Title & <example>'
description: 'A & B <summary>'
date: 2026-11-21
updated: 2026-11-21
tags: [C]
category: Test
slug: {slug}
draft: {str(draft).lower()}
language: zh-CN
---
## Header
<script>alert(1)</script>
[bad](javascript:alert(1))
''')
    build.build()
    rss=ET.parse(build.ROOT/'rss.xml');self.assertEqual(len(rss.findall('./channel/item')),2)
    self.assertEqual(rss.findtext('./channel/item/title'),'Title & <example>')
    for file in ['rss.xml','sitemap.xml','blog/index.html','index.html']:
     self.assertNotIn('private-draft',(build.ROOT/file).read_text())
    article=(build.ROOT/'blog/first/index.html').read_text();self.assertNotIn('<script>alert',article);self.assertNotIn('href="javascript:',article);self.assertIn('/blog/second/',article)
    with_toc=article
    self.assertIn('<details open class="toc">',with_toc)
    self.assertIn('href="#header"',with_toc)
    rss_before=(build.ROOT/'rss.xml').read_bytes()
    source=content/'first.md'
    source.write_text(source.read_text().replace('## Header', 'Plain paragraph without headings.'))
    build.build()
    without_toc=(build.ROOT/'blog/first/index.html').read_text()
    self.assertNotIn('<details open class="toc">',without_toc)
    self.assertIn('Plain paragraph without headings.',without_toc)
    self.assertEqual(rss_before,(build.ROOT/'rss.xml').read_bytes())
    (content/'first.md').unlink();build.build();self.assertFalse((build.ROOT/'blog/first/index.html').exists())
   finally:build.ROOT=original
if __name__=='__main__':unittest.main()
