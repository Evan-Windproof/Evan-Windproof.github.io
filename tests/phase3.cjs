const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({locale:'en-US',viewport:{width:1440,height:900}});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8000');
 const open=async id=>page.locator(`.dock [data-app="${id}"]`).click();
 await open('aelthoren');const win=page.locator('[data-id="aelthoren"]'),address=win.locator('.address');
 const nav=async value=>{await address.fill(value);await address.press('Enter')};
 const toolbar=async()=>{const boxes=await win.locator('.browser-toolbar [data-browser],.address').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}));for(const b of boxes)assert.ok(Math.abs(b.y-boxes[0].y)<5);const sorted=boxes.sort((a,b)=>a.x-b.x);for(let i=1;i<sorted.length;i++)assert.ok(sorted[i].x>=sorted[i-1].x+sorted[i-1].w-1)};
 await toolbar();assert.equal(await page.locator('.dock button').count(),6);
 await win.locator('.browser-home [data-navigate="aelthoren://articles"]').click();assert.equal(await address.inputValue(),'aelthoren://articles');assert.match(await win.locator('.article-list').textContent(),/Example/);
 await win.locator('.article-card button').click();assert.equal(await address.inputValue(),'aelthoren://articles/example');
 await win.locator('.markdown-body[aria-busy="false"]').waitFor();assert.match(await win.locator('.markdown-body').textContent(),/not a real technical study/);assert.equal(await win.locator('.markdown-body pre code').count(),1);assert.ok(await win.locator('time[datetime="2026-11-17"]').isVisible());
 await win.locator('[data-browser="back"]').click();assert.ok(await win.locator('.article-list').isVisible());await win.locator('[data-browser="forward"]').click();await win.locator('.markdown-body[aria-busy="false"]').waitFor();
 await win.locator('[data-browser="reload"]').click();await win.locator('.markdown-body[aria-busy="false"]').waitFor();
 const pos=await win.getAttribute('style');await open('settings');await page.selectOption('#language','zh-CN');await win.locator('.markdown-body[aria-busy="false"]').waitFor();assert.match(await win.locator('.markdown-body').textContent(),/示例文章/);assert.equal(await win.getAttribute('style'),pos);
 await open('aelthoren');await win.locator('.article-back').click();assert.match(await win.locator('.article-card').textContent(),/示例文章/);await open('settings');await page.selectOption('#language','en');assert.match(await win.locator('.article-card').textContent(),/Example article/);
 await open('aelthoren');await nav('aelthoren://articles/nonexistent');assert.match(await win.locator('.browser-page').textContent(),/not found/);
 await page.route('**/articles/example/en.md',r=>r.fulfill({status:404,body:'missing'}));await nav('aelthoren://articles/example');await win.locator('.markdown-body[aria-busy="false"]').waitFor();assert.match(await win.locator('.markdown-body').textContent(),/Unable to load/);await page.unroute('**/articles/example/en.md');
 // Stale reads must not replace a newer page.
 let release,started,finished;const startPromise=new Promise(r=>started=r),finishPromise=new Promise(r=>finished=r);
 await page.route('**/articles/example/en.md',async r=>{started();await new Promise(resolve=>release=resolve);await r.fulfill({body:'# Stale article'});finished()});
 await win.locator('[data-browser="reload"]').click();await startPromise;await nav('aelthoren://home');release();await finishPromise;await page.unroute('**/articles/example/en.md');assert.ok(await win.locator('.browser-home').isVisible());

 const result=await page.evaluate(()=>{
   window.xss=0;const div=document.createElement('div');div.id='security-probe';
   div.append(Articles.markdown('# Test\n\n<img src=x onerror="window.xss=1">\n<script>window.xss=1</script>\n\n[bad](javascript:alert(1)) [data](data:text/html,test) [safe](https://example.com)\n\n```html\n<img src=x onerror=alert(1)>\n```\n\n- \n\n**bold** *italic* `code`'));
   document.body.append(div);return {dangerous:div.querySelectorAll('img,script,iframe,object').length,links:[...div.querySelectorAll('a')].map(a=>a.href),code:div.querySelector('pre code').textContent,text:div.textContent};
 });assert.equal(result.dangerous,0);assert.deepEqual(result.links,['https://example.com/']);assert.match(result.code,/<img/);assert.match(result.text,/javascript:/);assert.equal(await page.evaluate(()=>window.xss),0);await page.locator('#security-probe').evaluate(el=>el.remove());
 for(const size of [{width:320,height:568},{width:390,height:844},{width:768,height:700}]){await page.setViewportSize(size);await nav('aelthoren://articles/example');await win.locator('.markdown-body[aria-busy="false"]').waitFor();await toolbar();assert.equal(await win.evaluate(el=>el.scrollWidth>el.clientWidth),false);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
 assert.deepEqual(errors,[]);await page.setViewportSize({width:1440,height:900});await page.screenshot({path:'work/phase3-article.png'});await browser.close();console.log('PASS: Phase 3 single-row toolbar, articles/history/reload, bilingual reading/list, missing/failed/stale loads, safe Markdown/XSS, mobile; Dock remains six apps');
})().catch(e=>{console.error(e);process.exit(1)});
