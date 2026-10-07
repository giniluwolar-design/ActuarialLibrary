// Requires Node >=20, Playwright and Chrome. Synthetic fixture only.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.argv[2] || 'http://127.0.0.1:8080');
    assert(!(await page.locator('body').innerText()).includes('undefined'));
    await page.getByText('Model summary paragraph', { exact: false }).click();
    assert(await page.locator('#provenance-panel').isVisible());
    await page.getByRole('button', { name: 'Connected evidence', exact: true }).click();
    await page.locator('#btn-next-page').waitFor();
    assert.equal(await page.locator('#surface-content .card').count(), 3);
    await page.locator('#btn-next-page').click();
    await page.waitForFunction(() => document.querySelector('#btn-next-page')?.disabled);
    assert.equal(await page.locator('#surface-content .card').count(), 2);
    await page.locator('#btn-prev-page').click();
    await page.waitForFunction(() => document.querySelector('#btn-prev-page')?.disabled);
    assert.equal(await page.locator('#surface-content .card').count(), 3);
    await page.getByRole('button', { name: 'Review overview', exact: true }).click();
    await page.locator('.card--origin').first().click();
    await page.locator('.card--assumption').first().click();
    await page.locator('.card--factor').first().click();
    assert.equal(await page.locator('.card--cell').count(), 3);
    assert((await page.locator('.card--cell').last().innerText()).includes('€0'));
    assert((await page.locator('.card--origin').last().innerText()).includes('Unavailable'));
    await page.locator('.card--cell').last().focus();
    await page.keyboard.press('Enter');
    assert(await page.locator('#provenance-panel').isVisible());
    await page.getByRole('button', { name: 'Source details', exact: true }).click();
    await page.getByRole('button', { name: 'Review subtotal — 2026 Q2', exact: true }).click();
    await page.locator('.fixture-detail').waitFor();
    assert((await page.locator('.fixture-detail').innerText()).includes('"fixture": true'));
    await page.getByRole('button', { name: 'Public synthetic preview', exact: true }).click();
    assert(await page.locator('#export-output').isVisible());
    await page.getByRole('button', { name: 'Review overview', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    console.log('PASS: pagination, deep drill-down, zero/blocked states, provenance, keyboard, source details, preview, mobile overflow; no page errors.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
