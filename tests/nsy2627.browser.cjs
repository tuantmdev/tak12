// Run with Node.js and Playwright installed: node tests/nsy2627.browser.cjs
const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const timezoneId of ['Asia/Ho_Chi_Minh', 'America/Los_Angeles', 'Pacific/Auckland']) {
      const context = await browser.newContext({timezoneId, viewport: {width: 390, height: 844}});
      const page = await context.newPage();
      // Avoid analytics traffic during deterministic local tests.
      await page.route('https://**', route => route.abort());
      await page.clock.install({time: new Date('2026-09-10T02:59:59Z')});
      await page.clock.pauseAt(new Date('2026-09-10T03:00:00Z'));
      await page.goto(pathToFileURL(path.resolve('tak12-ma-giam-gia/index.html')).href + '#nsy2627');
      const offer = page.locator('#nsy2627');
      assert.equal(await offer.isVisible(), true, `Active offer must show in ${timezoneId}`);
      assert.ok(await page.evaluate(() => window.scrollY > 0), 'Active dated-offer fragment must scroll after reveal');
      const offerTop = await offer.evaluate(element => element.getBoundingClientRect().top);
      assert.ok(offerTop >= 60 && offerTop < 140, `Offer fragment should respect sticky navigation; top=${offerTop}`);
      await page.clock.fastForward(new Date('2026-09-20T16:59:59.999Z').getTime() - new Date('2026-09-10T03:00:00Z').getTime());
      assert.equal(await offer.isVisible(), true, 'Valid through last millisecond of Vietnam end date');
      await page.clock.fastForward(1001);
      assert.equal(await offer.isVisible(), false, 'Long-open tab must expire at Vietnam midnight');
      await page.reload();
      assert.equal(await offer.isVisible(), false, 'Expired offer must stay hidden after reload');
      assert.equal(await page.locator('[data-cta="coupon_see_all"]').isVisible(), true, 'Evergreen pricing survives');
      await context.close();
      console.log(`PASS active, end boundary, long-open tab, expired reload: ${timezoneId}`);
    }
    const nojs = await browser.newContext({javaScriptEnabled:false});
    const page = await nojs.newPage();
    await page.route('https://**', route => route.abort());
    await page.goto(pathToFileURL(path.resolve('tak12-ma-giam-gia/index.html')).href);
    assert.equal(await page.locator('#nsy2627').isVisible(), false, 'No JS: no stale promotional claim');
    assert.equal(await page.locator('[data-cta="coupon_see_all"]').isVisible(), true);
    console.log('PASS no-JS graceful fallback');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
