const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  for (const width of [390, 1440]) {
   const context = await browser.newContext({viewport:{width,height:900},timezoneId:'America/Los_Angeles'});
   const page = await context.newPage();
   await page.route('https://**', r => r.abort());
   await page.clock.install({time:new Date('2026-09-10T02:59:59Z')});
   await page.clock.pauseAt(new Date('2026-09-10T03:00:00Z'));
   await page.goto(pathToFileURL(path.resolve('index.html')).href);
   const offer=page.locator('#homepage-nsy2627');
   assert.equal(await offer.isVisible(),true);
   await offer.scrollIntoViewIfNeeded();
   assert.ok(await offer.innerText().then(t=>t.includes('NSY2627')&&t.includes('Speaking/Writing')));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true,'No horizontal overflow');
   const cta=page.locator('[data-cta="homepage_nsy2627_pricing"]');
   const box=await cta.boundingBox();
   assert.ok(box && box.x>=0 && box.x+box.width<=width,'CTA in viewport width');
   assert.equal(await cta.getAttribute('href'),'https://tak12.com/info/bang-gia?ref=njg2odn');
   await page.screenshot({path:`/tmp/tak12-homepage-${width}.png`,fullPage:false});
   await page.clock.fastForward(new Date('2026-09-20T16:59:59.999Z')-new Date('2026-09-10T03:00:00Z'));
   assert.equal(await offer.isVisible(),true);
   await page.clock.fastForward(1001);
   assert.equal(await offer.isVisible(),false);
   await page.reload();
   assert.equal(await offer.isVisible(),false);
   assert.equal(await page.locator('#courses-section').isVisible(),true);
   console.log(`PASS homepage ${width}px: campaign/CTA/overflow/expiry/reload`);
   await context.close();
  }
  const ctx=await browser.newContext({javaScriptEnabled:false});
  const page=await ctx.newPage();
  await page.route('https://**',r=>r.abort());
  await page.goto(pathToFileURL(path.resolve('index.html')).href);
  assert.equal(await page.locator('#homepage-nsy2627').isVisible(),false);
  assert.equal(await page.locator('#courses-section').isVisible(),true);
  console.log('PASS homepage no-JS fallback');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
