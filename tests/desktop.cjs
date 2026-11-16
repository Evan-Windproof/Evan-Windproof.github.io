const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8000');
 await page.locator('.dock button').first().waitFor();
 assert.equal(await page.locator('.dock button').count(),5);
 assert.equal(await page.locator('h1').textContent(),'Evavind');
 assert.ok(await page.locator('#clock').textContent());
 for(const id of ['apps','terminal','projects','about','settings']){await page.locator(`.dock [data-app="${id}"]`).click();assert.ok(await page.locator(`.window[data-id="${id}"]`).isVisible());}
 await page.selectOption('#theme','light');await page.check('#hour24');await page.check('#motion');
 await page.reload();assert.match(await page.locator('body').getAttribute('class'),/light/);
 await page.locator('.dock [data-app="settings"]').click();assert.ok(await page.locator('#hour24').isChecked());
 await page.selectOption('#theme','dark');
 await page.locator('.dock [data-app="terminal"]').click();
 const term=page.locator('.window[data-id="terminal"]');const input=term.locator('input');
 for(const command of ['help','echo <img src=x onerror=alert(1)>','unknown']){await input.fill(command);await input.press('Enter');}
 assert.match(await term.locator('pre').textContent(),/未知命令/);assert.equal(await term.locator('img').count(),0);
 await input.press('ArrowUp');assert.equal(await input.inputValue(),'unknown');
 await input.fill('clear');await input.press('Enter');assert.equal(await term.locator('pre').textContent(),'');
 await input.fill('open projects');await input.press('Enter');assert.ok(await page.locator('.window[data-id="projects"]').isVisible());
 await page.locator('.dock [data-app="terminal"]').click();
 await term.locator('[data-action="min"]').click();assert.ok(await term.isHidden());
 await page.locator('.dock [data-app="terminal"]').click();assert.ok(await term.isVisible());
 await term.locator('[data-action="max"]').click();assert.match(await term.getAttribute('class'),/maximized/);await term.locator('[data-action="max"]').click();
 const bar=await term.locator('.titlebar').boundingBox();await page.mouse.move(bar.x+90,bar.y+15);await page.mouse.down();await page.mouse.move(bar.x+150,bar.y+50);await page.mouse.up();const moved=await term.boundingBox();assert.ok(moved.x>bar.x);
 await page.keyboard.press('Escape');assert.equal(await term.count(),0);
 for(const size of [{width:390,height:844},{width:320,height:568},{width:968,height:338}]){await page.setViewportSize(size);await page.locator('.dock [data-app="about"]').click();const box=await page.locator('.window[data-id="about"]').boundingBox();assert.ok(box.x>=0&&box.x+box.width<=size.width);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
 assert.deepEqual(errors,[]);await page.setViewportSize({width:1440,height:900});await page.reload();await page.screenshot({path:'work/desktop.png'});
 await browser.close();console.log('PASS: five apps, terminal safety/history, window controls/drag, settings persistence, three viewport sizes, no runtime errors');
})().catch(e=>{console.error(e);process.exit(1)});
