const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const official = 'https://hooftty.evanwindproof.top/';

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox']
  });
  try {
    const page = await browser.newPage({ locale: 'en-US' });
    await page.goto(process.env.TEST_BASE_URL || 'http://localhost:8000/');
    await page.locator('.dock [data-app="projects"]').click();
    const desktop = page.locator('.window[data-id="projects"]');
    await desktop.locator('[data-project-filter]').selectOption('research');

    await page.locator('.dock [data-app="aelthoren"]').click();
    const browserWindow = page.locator('.window[data-id="aelthoren"]');
    const address = browserWindow.locator('.address');
    await address.fill('aelthoren://projects');
    await address.press('Enter');

    for (const view of [desktop, browserWindow]) {
      const card = view.locator('.project-card-hooftty');
      assert.ok(await card.isVisible());
      for (const link of [card.locator('h3 a'), card.locator('.project-links a').nth(1)]) {
        assert.equal(await link.getAttribute('href'), official);
        assert.equal(await link.getAttribute('target'), null);
      }
    }
    console.log('PASS: existing desktop and Aelthoren HoofTTY links point to the official site');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
