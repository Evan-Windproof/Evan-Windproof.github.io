const{chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});const p=await b.newPage();p.setDefaultTimeout(7000);let errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.goto('http://localhost:8000/');for (const url of ['https://evanwindproof.top/blog/', 'https://en.evanwindproof.top/']) {
  assert.ok(await p.locator(`.blog-links a[href="${url}"]`).isVisible());
}
assert.ok(await p.locator('.latest-posts a').count());await p.locator('.dock [data-app="apps"]').click();for(const url of ['https://c-skeleton.evanwindproof.top/','https://orfreon.evanwindproof.top/'])assert.ok(await p.locator(`a[href="${url}"]`).count());
await p.goto('http://localhost:8000/blog/');await p.locator('#blog-search').fill('no-such-article');await p.locator('#search-empty').waitFor({state:'visible'});await p.locator('#blog-search').fill('MIT Xok/ExOS复活');await p.locator('.post-card:visible').waitFor({state:'visible'});await p.locator('.post-card:visible h2 a').click();assert.equal((await p.reload()).status(),200);assert.equal(await p.locator('article > header > h1').count(),1);assert.ok(await p.locator('.codehilite').count()>0);assert.ok(await p.locator('.prose table').count());assert.ok(await p.locator('.toc a[href^="#"]').count());assert.ok(await p.locator('link[rel="canonical"]').getAttribute('href')==='https://evanwindproof.top/blog/xok-exos/');await p.selectOption('#blog-language','zh-TW');assert.equal(await p.locator('html').getAttribute('lang'),'zh-TW');assert.equal(await p.locator('article').getAttribute('lang'),'zh-CN');await p.locator('#blog-theme').click();assert.match(await p.locator('body').getAttribute('class'),/light/);
for(const width of[320,390,1440]){await p.setViewportSize({width,height:900});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
const context=await b.newContext({javaScriptEnabled:false});const nojs=await context.newPage();assert.equal((await nojs.goto('http://localhost:8000/blog/xok-exos/')).status(),200);assert.match(await nojs.locator('.prose').textContent(),/ExOS/);assert.equal((await nojs.reload()).status(),200);
const archive='/blog/mlp-os-archive/';
await p.goto('http://localhost:8000/');
assert.ok(await p.locator(`.latest-posts a[href="${archive}"]`).isVisible());
await p.goto('http://localhost:8000/blog/');
await p.locator(`.post-card h2 a[href="${archive}"]`).click();
assert.match(await p.locator('article > header > h1').textContent(), /MLP OS Archive/);
assert.equal(await p.locator('.prose img').getAttribute('src'), 'https://ik.imagekit.io/lp7vr9041i/blog/OS/mlpos.webp');
await p.goto('http://localhost:8000/blog/google-search-milestone/');
assert.ok(await p.locator('.prose img').evaluate(el=>el.complete&&el.naturalWidth>0));
const rss=fs.readFileSync('rss.xml','utf8');assert.match(rss,/<rss version="2.0">/);assert.match(rss,/https:\/\/evanwindproof.top\/blog\/xok-exos\//);assert.match(fs.readFileSync('sitemap.xml','utf8'),/xok-exos/);assert.deepEqual(errors,[]);await b.close();console.log('PASS blog: static/no-JS reading and refresh, search, Markdown, SEO, RSS/sitemap, mobile, Traditional UI and preserved projects')})().catch(e=>{console.error(e);process.exit(1)});
