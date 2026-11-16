const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({locale:'en-US',viewport:{width:1440,height:900}});
 const page=await context.newPage(),errors=[];page.setDefaultTimeout(7000);page.on('pageerror',e=>errors.push(e.message));await page.goto('http://localhost:8000');
 const dock=page.locator('.dock'),trigger=page.locator('.dock-trigger'),settings=page.locator('.status [data-app="settings"]');
 const mode=async value=>{await settings.click();await page.selectOption('#dockVisibility',value)};
 assert.equal(await page.locator('#desktop').getAttribute('data-dock-mode'),'always');assert.ok(await trigger.isHidden());
 await page.locator('.dock [data-app="terminal"]').click();const terminal=page.locator('[data-id="terminal"]');await terminal.locator('input').fill('retained draft');
 await mode('auto');await page.waitForFunction(()=>document.querySelector('.dock').inert);assert.equal(await dock.getAttribute('aria-hidden'),'true');
 await trigger.hover();await page.waitForFunction(()=>!document.querySelector('.dock').inert);await dock.hover();await page.waitForTimeout(450);assert.equal(await dock.getAttribute('aria-hidden'),'false');
 await page.mouse.move(30,200);await page.waitForFunction(()=>document.querySelector('.dock').inert);
 // Keyboard focus on the reveal area reveals the Dock and Tab enters it.
 await trigger.focus();assert.equal(await dock.getAttribute('aria-hidden'),'false');await page.keyboard.press('Tab');assert.ok(await dock.evaluate(el=>el.contains(document.activeElement)));await page.waitForTimeout(450);assert.equal(await dock.getAttribute('aria-hidden'),'false');
 await settings.click();await page.waitForFunction(()=>document.querySelector('.dock').inert);
 await mode('hidden');assert.ok(await dock.isHidden());assert.ok(await trigger.isHidden());assert.equal(await terminal.locator('input').inputValue(),'retained draft');
 await page.reload();assert.ok(await dock.isHidden());await settings.click();assert.equal(await page.locator('#dockVisibility').inputValue(),'hidden');
 await page.keyboard.press('Control+Alt+d');assert.equal(await page.locator('#dockVisibility').inputValue(),'always');assert.ok(await dock.isVisible());await page.keyboard.press('Control+Alt+d');assert.ok(await dock.isHidden());
 await settings.click();await page.selectOption('#language','zh-CN');assert.equal(await page.locator('#dockVisibility option[value="auto"]').textContent(),'自动隐藏');assert.equal(await trigger.getAttribute('aria-label'),'展开 Dock');
 await page.selectOption('#language','en');assert.equal(await page.locator('#dockVisibility option[value="always"]').textContent(),'Always Show');
 await page.selectOption('#dockVisibility','auto');await page.reload();await settings.click();assert.equal(await page.locator('#dockVisibility').inputValue(),'auto');await mode('always');await page.reload();assert.equal(await dock.getAttribute('aria-hidden'),'false');
 const touch=await browser.newContext({isMobile:true,hasTouch:true,viewport:{width:390,height:844}});const tp=await touch.newPage();await tp.goto('http://localhost:8000');await tp.locator('.status [data-app="settings"]').tap();await tp.selectOption('#dockVisibility','auto');
 await tp.locator('.dock-trigger').tap();assert.equal(await tp.locator('.dock').getAttribute('aria-hidden'),'false');await tp.locator('.dock [data-app="about"]').tap();assert.ok(await tp.locator('[data-id="about"]').isVisible());await tp.locator('#clock').tap();assert.equal(await tp.locator('.dock').getAttribute('aria-hidden'),'true');
 await tp.locator('.status [data-app="settings"]').tap();await tp.selectOption('#dockVisibility','hidden');assert.ok(await tp.locator('.dock').isHidden());await tp.locator('.status [data-app="settings"]').tap();await tp.selectOption('#dockVisibility','always');assert.ok(await tp.locator('.dock').isVisible());assert.equal(await tp.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 const blocked=await browser.newContext();await blocked.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('disabled')};Storage.prototype.setItem=()=>{throw Error('disabled')}});const bp=await blocked.newPage();await bp.goto('http://localhost:8000');await bp.locator('.status [data-app="settings"]').click();await bp.selectOption('#dockVisibility','hidden');assert.ok(await bp.locator('.dock').isHidden());await bp.keyboard.press('Control+Alt+d');assert.ok(await bp.locator('.dock').isVisible());
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS: Phase 3.1 three modes, hover/focus/touch reveal, Settings/keyboard recovery, live apps, persistence, i18n, storage disabled');
})().catch(e=>{console.error(e);process.exit(1)});
