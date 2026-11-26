const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'evavind-pagination-'));
  let browser;
  try {
    execFileSync('python3', ['-c', 'import runpy,sys; from pathlib import Path; runpy.run_path("tests/test_pagination.py")["fixture"](Path(sys.argv[1]),25)', temp]);
    browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox'] });
    const page = await browser.newPage({ locale: 'en-US', viewport: { width: 320, height: 700 } });
    await page.route('**/blog/**', async route => {
      const url = new URL(route.request().url());
      const file = path.join(temp, url.pathname, url.pathname.endsWith('/') ? 'index.html' : '');
      if (fs.existsSync(file)) await route.fulfill({ path: file });
      else await route.continue();
    });
    const count = async expected => {
      await page.waitForFunction(n => document.querySelectorAll('.post-card').length === n, expected);
      assert.equal(await page.locator('.post-card').count(), expected);
    };
    const base = 'http://localhost:8000/blog/';
    await page.goto(base + 'page/2/');
    await count(12);
    assert.equal(await page.locator('[aria-current="page"]').textContent(), '2');
    await page.getByRole('link', { name: 'Next page' }).click();
    assert.ok(page.url().endsWith('/page/3/#article-list'));
    await count(1);
    await page.goBack();
    await count(12);
    await page.goForward();
    await count(1);

    const search = page.locator('#blog-search');
    await search.pressSequentially('shared keyword');
    await count(12);
    assert.equal(new URL(page.url()).searchParams.get('q'), 'shared keyword');
    await page.getByRole('link', { name: 'Next page' }).click();
    await page.waitForFunction(() => document.querySelector('[aria-current="page"]')?.textContent === '2');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'article-list');
    await page.reload();
    await count(12);
    assert.equal(await page.locator('[aria-current="page"]').textContent(), '2');
    await page.goBack();
    await page.waitForFunction(() => document.querySelector('[aria-current="page"]')?.textContent === '1');
    await page.goForward();
    await page.waitForFunction(() => document.querySelector('[aria-current="page"]')?.textContent === '2');
    for (const [lang, previous, total] of [['zh-CN','上一页','共 24 篇文章'],['zh-TW','上一頁','共 24 篇文章'],['en','Previous page','Articles: 24']]) {
      await page.selectOption('#blog-language', lang);
      assert.ok(await page.getByRole('link', { name: previous }).isVisible());
      assert.equal(await page.locator('.pagination-count').textContent(), total);
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await search.fill('uncommon needle');
    await count(1);
    assert.equal(new URL(page.url()).searchParams.has('page'), false);
    assert.equal(await page.locator('.blog-pagination').count(), 0);
    await page.locator('.tag-link').filter({ hasText: 'Gecko' }).click();
    assert.equal(new URL(page.url()).pathname, '/blog/tags/gecko/');
    await count(12);
    await page.getByRole('link', { name: 'Next page' }).click();
    await count(12);
    await search.fill('shared keyword');
    await page.waitForFunction(() => document.querySelector('.pagination-count')?.textContent === 'Articles: 23');
    assert.equal(await page.locator('[aria-current="page"]').textContent(), '1');

    await page.goto(base + '?q=shared+keyword&page=NaN');
    await page.waitForFunction(() => document.querySelector('[aria-current="page"]')?.textContent === '1');
    assert.equal(new URL(page.url()).searchParams.has('page'), false);
    await page.goto(base + '?q=shared+keyword&page=99');
    await page.waitForFunction(() => document.querySelector('[aria-current="page"]')?.textContent === '2');
    assert.equal(new URL(page.url()).searchParams.get('page'), '2');
    assert.equal((await page.goto(base + 'page/99/')).status(), 404);
    console.log('PASS static/tag/search navigation, deep links, history, refresh, invalid pages, three locales and 320px viewport');
  } finally {
    await browser?.close();
    fs.rmSync(temp, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
