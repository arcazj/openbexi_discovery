const assert = require('node:assert/strict');

async function assertCaptions(page, screen) {
  const missing = await page.evaluate(() => [...document.querySelectorAll('button,select,summary,.interpret-organism,.source-chip input')]
    .filter(node => node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden')
    .filter(node => !node.title || !(node.getAttribute('aria-describedby') || '').split(/\s+/)
      .some(id => id.startsWith('control-description-') && document.getElementById(id)?.textContent === node.title))
    .map(node => node.id || node.getAttribute('aria-label') || node.textContent.trim()));
  assert.deepEqual(missing, [], 'All controls have explanatory, screen-reader-accessible captions: ' + screen);
}

async function assertCaptionFits(page) {
  const box = await page.locator('#control-caption').boundingBox();
  assert.ok(box && box.width > 0 && box.x >= 0 && box.y >= 0);
  const viewport = page.viewportSize();
  assert.ok(box.x + box.width <= viewport.width && box.y + box.height <= viewport.height, 'Caption stays inside the viewport');
}

module.exports = {assertCaptions, assertCaptionFits};
