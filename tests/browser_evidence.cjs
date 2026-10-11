// Synthetic browser workflow. Requires Playwright, Node >=20 and Chrome.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.argv[2] || 'http://127.0.0.1:8765');
    await page.locator('#method-table tbody tr').first().waitFor({ state: 'attached' });
    await page.locator('[data-tab="methods"]').first().click();
    await page.getByRole('button', { name: 'Review evidence' }).first().click();
    await page.locator('#evidence-links [data-evidence-node]').first().waitFor();
    assert((await page.locator('#evidence-title').innerText()).includes('Paid Chain Ladder'));
    const resultTitle = await page.locator('#evidence-title').innerText();
    await page.getByText('Recorded identity & provenance', { exact: true }).click();
    const resultProvenance = await page.locator('#evidence-provenance').textContent();
    assert(resultProvenance.includes('calculation_evidence'));
    await page.locator('#evidence-links [data-evidence-class="calc/factor"]').first().click();
    await page.locator('#evidence-links [data-evidence-class="triangle/cell"]').first().waitFor();
    assert((await page.locator('#evidence-breadcrumbs').innerText()).includes(resultTitle));
    await page.locator('#evidence-links [data-evidence-class="triangle/cell"]').first().click();
    await page.getByRole('button', { name: 'Load recorded payload' }).click();
    await page.locator('#evidence-payload:not([hidden])').waitFor();
    const payload = JSON.parse(await page.locator('#evidence-payload').innerText());
    assert.equal(payload.availability, 'observed');
    await page.locator('#evidence-breadcrumbs button').first().click();
    await page.waitForFunction(title => document.querySelector('#evidence-title').textContent === title, resultTitle);
    assert.equal(await page.locator('#evidence-provenance').textContent(), resultProvenance);
    const downloaded = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download local evidence review' }).click();
    const download = await downloaded;
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    const review = JSON.parse(Buffer.concat(chunks).toString());
    assert.equal(review.manifest.export_policy, 'analyst_local_review');
    assert(review.nodes.some(node => node.node_class === 'calc/result'));
    assert(!review.nodes.some(node => node.private));
    const identities = new Set(review.nodes.map(node => `${node.node_id}:${node.revision}`));
    for (const edge of review.edges) {
      assert(identities.has(`${edge.source_node_id}:${edge.source_revision}`));
      assert(identities.has(`${edge.target_node_id}:${edge.target_revision}`));
    }
    await page.reload();
    await page.locator('#method-table tbody tr').first().waitFor({ state: 'attached' });
    await page.locator('[data-tab="methods"]').first().click();
    await page.getByRole('button', { name: 'Review evidence' }).first().focus();
    await page.keyboard.press('Enter');
    await page.locator('#evidence-links [data-evidence-node]').first().waitFor();
    assert.equal(await page.locator('#evidence-provenance').textContent(), resultProvenance);
    await page.locator('#evidence-review').scrollIntoViewIfNeeded();
    await page.screenshot({ path: '/tmp/actuarial-evidence-desktop.png' });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.locator('#evidence-title').scrollIntoViewIfNeeded();
    await page.screenshot({ path: process.argv[3] || '/tmp/actuarial-evidence-mobile.png' });
    assert.deepEqual(errors, []);
    console.log('PASS: saved result → factor → cell, lazy payload, breadcrumbs, downloaded review, restart identity, keyboard, mobile overflow; no page errors.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
