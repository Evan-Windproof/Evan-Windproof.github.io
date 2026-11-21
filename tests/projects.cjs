const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium', args:['--no-sandbox']});
  try {
    const page = await browser.newPage({locale:'en-US', viewport:{width:1440,height:900}});
    await page.goto('http://localhost:8000/');
    await page.locator('.dock [data-app="projects"]').click();
    const project = page.locator('[data-id="projects"]');
    const slugs = 'Orfreon Evavind-OS Liberpony-OS Glivand-OS Liberums Kernseed_OS HoofTTY LinuxLibOS Aelthuvor Aelthoren liberFPS Evan-Windproof.github.io Orfreon-Website'.split(' ');
    const links = await project.locator('.project-card a[href^="https://github.com/"]').evaluateAll(elements =>
      elements.map(a => [a.href, a.target, a.rel]));
    assert.deepEqual(links, slugs.map(slug => ['https://github.com/Evan-Windproof/' + slug, '_blank', 'noopener noreferrer']));
    assert.ok(await project.locator('.window-content').evaluate(el => el.scrollHeight > el.clientHeight));
    for (const [category,count] of [['systems',4],['research',5],['applications',2],['web',2],['',13]]) {
      await project.locator('select').selectOption(category);
      assert.equal(await project.locator('.project-card:visible').count(),count);
    }
    await project.locator('select').selectOption('applications');
    await page.locator('.dock [data-app="aelthoren"]').click();
    const internal = page.locator('[data-id="aelthoren"]');
    await internal.locator('.address').fill('aelthoren://projects');
    await internal.locator('.address').press('Enter');
    assert.equal(await internal.locator('.project-card:visible').count(),13);
    await internal.locator('[data-project-filter]').selectOption('research');

    await page.locator('.status [data-app="settings"]').click();
    for (const [language,label] of [['zh-CN','应用与工具'],['zh-TW','應用程式與工具'],['en','Applications & Tools']]) {
      await page.selectOption('#language',language);
      assert.equal(await project.locator('select').inputValue(),'applications');
      assert.equal(await project.locator('option:checked').textContent(),label);
      assert.equal(await internal.locator('[data-project-filter]').inputValue(),'research');
      assert.equal(await internal.locator('.project-card:visible').count(),5);
    }
    await page.setViewportSize({width:320,height:650});
    for (const panel of [project.locator('.window-content'),internal.locator('.browser-page')]) {
      assert.ok(await panel.evaluate(el => el.scrollWidth <= el.clientWidth));
    }
    console.log('PASS: 13 unique repository links, project scrolling, filters, three locales, independent browser state, and narrow layout');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
