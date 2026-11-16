const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(7000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://localhost:8000');
 const settings=page.locator('.status [data-app="settings"]');
 const mode=async value=>{await settings.click();await page.selectOption('#dockVisibility',value)};
 const gap=async win=>win.evaluate(el=>{const desktop=document.querySelector('#desktop');return desktop.getBoundingClientRect().top+desktop.clientTop+desktop.clientHeight-el.getBoundingClientRect().bottom});
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  await page.setViewportSize(viewport);
  for(const id of ['aelthoren','terminal','projects','about','apps']){
   await mode('always');await page.locator(`.dock [data-app="${id}"]`).click();const win=page.locator(`[data-id="${id}"]`);
   const original=await win.boundingBox();await win.locator('[data-action="max"]').click();const reserved=await gap(win);assert.ok(reserved>90);
   await mode('hidden');assert.ok(Math.abs(await gap(win)-12)<1);assert.equal(await win.locator('[data-action="max"]').getAttribute('aria-pressed'),'true');
   await mode('auto');assert.ok(Math.abs(await gap(win)-18)<1);
   await page.locator('.dock-trigger').hover();await page.waitForFunction(()=>document.querySelector('#desktop').classList.contains('dock-expanded'));assert.ok(Math.abs(await gap(win)-reserved)<1);
   await page.mouse.move(30,40);await page.waitForFunction(()=>!document.querySelector('#desktop').classList.contains('dock-expanded'));assert.ok(Math.abs(await gap(win)-18)<1);
   await mode('always');assert.ok(Math.abs(await gap(win)-reserved)<1);
   await win.evaluate(el=>el.querySelector('[data-action="max"]').click());const restored=await win.boundingBox();assert.equal(restored.height,original.height);assert.equal(restored.width,original.width);
   await win.evaluate(el=>el.querySelector('[data-action="close"]').click());
  }
  await mode('hidden');const sw=page.locator('[data-id="settings"]');await sw.locator('[data-action="max"]').click();assert.ok(Math.abs(await gap(sw)-12)<1);await sw.locator('[data-action="max"]').click();
 }
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS: maximized windows reclaim hidden Dock space on desktop/mobile; auto reveal reserves space; restore geometry and Settings remain intact');
})().catch(e=>{console.error(e);process.exit(1)});
