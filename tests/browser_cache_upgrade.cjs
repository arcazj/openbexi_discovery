// Use real Chromium HTTP caching: Playwright request routing disables the cache.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const {spawn, spawnSync} = require('node:child_process');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.TEST_PYTHON || (fs.existsSync(localPython) ? localPython : 'python');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'discovery-cache-'));
const assets = [...fs.readFileSync(path.join(root, 'index.html'), 'utf8').matchAll(/(?:src|href)="(assets\/[^"?]+)"/g)].map(match => match[1]);
const server = spawn(python, ['run_discovery.py', '--port', '0'], {
  cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  env: {...process.env, OPENAI_API_KEY: '', OPENAI_MODEL: '', OPENAI_REASONING_EFFORT: '',
    DISCOVERY_DATA_DIR: temporary, DISCOVERY_LIBRARY_DIR: ''}
});
let logs = '', upstream, upgraded = false, browser;
server.stdout.on('data', value => logs += value);
server.stderr.on('data', value => logs += value);
const requests = [];
const gateway = http.createServer((req, res) => {
  requests.push(req.url);
  const url = new URL(req.url, 'http://127.0.0.1');
  if (!upgraded) {
    res.setHeader('Cache-Control', 'public, max-age=86400');
    if (url.pathname === '/') {
      res.setHeader('Content-Type', 'text/html');
      res.end('<!doctype html><html><head>' + assets.filter(asset => asset.endsWith('.css')).map(asset =>
        `<link rel="stylesheet" href="${asset}">`).join('') + '</head><body><h1 id="legacy-version">Old version</h1>' +
        assets.filter(asset => asset.endsWith('.js')).map(asset => `<script src="${asset}"></script>`).join('') + '</body></html>');
    } else if (assets.includes(url.pathname.slice(1))) {
      const script = url.pathname.endsWith('.js');
      res.setHeader('Content-Type', script ? 'text/javascript' : 'text/css');
      res.end(script ? 'window.legacyAssetLoaded = true;' : 'body { --legacy-style: cached; }');
    } else { res.statusCode = 404; res.end(); }
    return;
  }
  const proxy = http.request(new URL(req.url, upstream), {method: req.method, headers: req.headers}, response => {
    res.writeHead(response.statusCode, response.headers);
    response.pipe(res);
  });
  proxy.on('error', () => { res.statusCode = 502; res.end('Test backend unavailable'); });
  req.pipe(proxy);
});

async function waitServer() {
  for (let attempt = 0; attempt < 300; attempt++) {
    if (server.exitCode !== null) throw new Error(logs);
    upstream = logs.match(/full application: (http:\/\/127\.0\.0\.1:\d+)/)?.[1];
    if (upstream) {
      try { if ((await fetch(upstream + '/api/health')).ok) return; } catch {}
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('Test backend did not start: ' + logs);
}

(async () => {
  try {
    await waitServer();
    await new Promise(resolve => gateway.listen(0, '127.0.0.1', resolve));
    const port = gateway.address().port, base = 'http://127.0.0.1:' + port;
    const launch = spawnSync(python, ['-c',
      'import sys; from installer.desktop import browser_url; print(browser_url(int(sys.argv[1]), "cache-upgrade-test"))', String(port)],
      {cwd: root, encoding: 'utf8', windowsHide: true});
    assert.equal(launch.status, 0, launch.stderr);
    const launchUrl = launch.stdout.trim();
    assert.equal(new URL(launchUrl).origin, base);
    browser = await chromium.launch({headless: true});
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    assert.equal(await page.locator('#legacy-version').textContent(), 'Old version');
    assert.equal(await page.evaluate(() => window.legacyAssetLoaded), true);
    await page.evaluate(() => {
      localStorage.setItem('cache-upgrade-saved-work', 'Keep this research');
      document.cookie = 'cache_upgrade=keep; SameSite=Strict; path=/';
    });
    assert.ok(assets.every(asset => requests.includes('/' + asset)), 'All unversioned assets are seeded in cache');
    upgraded = true;
    const oldRootRequests = requests.filter(url => url === '/').length;
    await page.goto('about:blank');
    await page.goto(base);
    assert.equal(await page.locator('#legacy-version').textContent(), 'Old version', 'Reproduces the stale UI after upgrade');
    assert.equal(requests.filter(url => url === '/').length, oldRootRequests, 'Old page really came from browser cache');

    const response = await page.goto(launchUrl);
    assert.equal(response.headers()['cache-control'], 'no-store');
    await page.waitForFunction(() => typeof D !== 'undefined' && D.ready);
    const version = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')).version;
    assert.equal(await page.locator('#app-version').textContent(), 'V' + version);
    assert.equal(await page.evaluate(() => window.legacyAssetLoaded), undefined);
    assert.equal(await page.evaluate(() => getComputedStyle(document.body).getPropertyValue('--legacy-style')), '');
    for (const asset of assets) {
      assert.ok(requests.some(value => {
        const url = new URL(value, base);
        return url.pathname === '/' + asset && /^[a-f0-9]{16}$/.test(url.searchParams.get('v'));
      }), 'Loaded current asset with a content fingerprint: ' + asset);
    }
    assert.equal(await page.evaluate(() => localStorage.getItem('cache-upgrade-saved-work')), 'Keep this research');
    assert.ok((await context.cookies()).some(cookie => cookie.name === 'cache_upgrade' && cookie.value === 'keep'));
    const launchPath = new URL(launchUrl).pathname + new URL(launchUrl).search;
    const launchRequests = requests.filter(url => url === launchPath).length;
    await page.goto('about:blank');
    await page.goto(launchUrl);
    await page.waitForFunction(() => typeof D !== 'undefined' && D.ready);
    assert.equal(requests.filter(url => url === launchPath).length, launchRequests + 1, 'Reopening fetches the current HTML');
    assert.deepEqual(errors, []);
    console.log('PASS cached upgrade: old HTML/JS/CSS reproduced, launcher fetches current UI, saved browser data retained.');
  } finally {
    if (browser) await browser.close();
    if (gateway.listening) await new Promise(resolve => { gateway.close(resolve); gateway.closeAllConnections(); });
    server.kill();
    await new Promise(resolve => server.exitCode !== null || server.signalCode !== null ? resolve() : server.once('exit', resolve));
    const resolved = fs.realpathSync(temporary);
    assert.equal(path.dirname(resolved), fs.realpathSync(os.tmpdir()));
    assert.ok(path.basename(resolved).startsWith('discovery-cache-'));
    fs.rmSync(resolved, {recursive: true, force: true});
  }
})().catch(error => { console.error(error); console.error(logs.slice(-2500)); process.exitCode = 1; });
