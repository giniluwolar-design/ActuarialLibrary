// Render public, read-only prototype previews in GitHub CI. Not a test suite.
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
  const directory = path.resolve(process.argv[2] || 'vision-previews');
  await fs.mkdir(directory, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    page.on('pageerror', error => console.error('Prototype page error:', error.message));
    for (const variant of ['A', 'B', 'C']) {
      await page.goto(`http://127.0.0.1:8766/index.html?variant=${variant}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: path.join(directory, `library-${variant}.png`), fullPage: true });
    }
    await page.goto('http://127.0.0.1:8766/index.html?variant=A', { waitUntil: 'networkidle' });
    await page.locator('[data-tool="reserving"]').click();
    await page.screenshot({ path: path.join(directory, 'reserving.png'), fullPage: true });
    await page.locator('[data-home]').click();
    await page.locator('[data-tool="annuity"]').click();
    await page.locator('.scenario-details summary').click();
    await page.locator('[data-annuity="partner"]').click();
    await page.screenshot({ path: path.join(directory, 'annuity-partner.png'), fullPage: true });
    await page.locator('[data-home]').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload({ waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(directory, 'library-mobile.png'), fullPage: true });
    console.log(`Public synthetic design previews captured in ${directory}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
