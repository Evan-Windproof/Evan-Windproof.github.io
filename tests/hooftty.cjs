const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox']
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });

    await page.goto('http://localhost:8000/');
    await page.locator('.dock [data-app="projects"]').click();
    const projects = page.locator('[data-id="projects"]');
    await projects.locator('[data-project-filter]').selectOption('research');
    await Promise.all([
      page.waitForURL('**/projects/hooftty/'),
      projects.getByRole('link', { name: 'HoofTTY', exact: true }).click()
    ]);

    assert.equal((await page.reload()).status(), 200);
    assert.equal(await page.locator('h1').innerText(), '>_ HoofTTY');
    assert.equal(await page.locator('.terminal img').evaluate(img => img.naturalWidth), 48);
    const release = (await page.locator('#latest-release').innerText()).split(' · ')[0];
    assert.equal(await page.locator('.terminal-screen .green').innerText(), 'HoofTTY OS - ' + release);
    assert.equal(await page.locator('#status a[href="#latest-release"]').innerText(), release);
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://evanwindproof.top/projects/hooftty/');
    const imageURL = new URL(await page.locator('meta[property="og:image"]').getAttribute('content'));
    assert.equal(imageURL.origin, 'https://evanwindproof.top');
    const socialImage = await page.request.get(new URL(imageURL.pathname, page.url()).href);
    assert.equal(socialImage.status(), 200);
    const png = await socialImage.body();
    assert.equal(png.readUInt32BE(16), 1200);
    assert.equal(png.readUInt32BE(20), 630);
    assert.ok(await page.evaluate(async () => {
      await document.fonts.ready;
      return [...document.fonts].some(font => font.family === 'Silkscreen' && font.status === 'loaded');
    }));
    assert.equal(await page.locator('.cursor').evaluate(el => getComputedStyle(el).animationName), 'none');

    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').innerText(), 'Skip to content');
    assert.equal(await page.locator(':focus').evaluate(el => getComputedStyle(el).outlineStyle), 'dashed');

    const nav = page.getByRole('navigation', { name: 'HoofTTY', exact: true });
    for (const fragment of ['download', 'docs', 'changelog', 'status']) {
      await nav.locator(`a[href="#${fragment}"]`).click();
      assert.equal(new URL(page.url()).hash, '#' + fragment);
      assert.equal(await page.locator('#' + fragment).count(), 1);
    }

    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 850 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}px`);
    }

    assert.deepEqual(errors, []);
    console.log('PASS: project card navigation, direct refresh, anchors, focus, reduced motion and responsive widths');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
