const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SESSION_FILE = path.join(__dirname, '.auth-session', 'state.json');
const SCREENSHOTS = path.join(__dirname, 'screenshots');

fs.mkdirSync(path.dirname(SESSION_FILE), { recursive: true });
fs.mkdirSync(SCREENSHOTS, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 200,
    args: ['--no-sandbox', '--start-maximized'],
  });

  const context = await browser.newContext({
    storageState: fs.existsSync(SESSION_FILE) ? SESSION_FILE : undefined,
    viewport: null,
  });

  const page = await context.newPage();

  // ── Intercept API calls ───────────────────────────────────────────────────
  const issues  = [];
  const requests = [];

  page.on('request', req => {
    if (!req.url().includes('localhost:8000')) return;
    const auth = req.headers()['authorization'] ?? '(none)';
    requests.push({ method: req.method(), path: req.url().replace('http://localhost:8000', ''), auth });
  });

  page.on('response', async res => {
    if (!res.url().includes('localhost:8000')) return;
    const status = res.status();
    const urlPath = res.url().replace('http://localhost:8000', '');
    if (status === 401 || status === 403) {
      let body = '';
      try { body = await res.text(); } catch {}
      issues.push({ status, path: urlPath, body: body.slice(0, 300) });
      console.error(`  ❌ [${status}] ${urlPath}`);
    } else if (status >= 200 && status < 300) {
      console.log(`  ✅ [${status}] ${urlPath}`);
    } else {
      console.log(`  ⚠  [${status}] ${urlPath}`);
    }
  });

  // ── Phase 1: Navigate and wait for auth ───────────────────────────────────
  console.log('\n[1/3] Abriendo app...');
  await page.goto('http://localhost:3000', { timeout: 30000 }).catch(() => {});

  // Wait until we land on /app/... (max 120s for manual login)
  if (!page.url().includes('/app/')) {
    console.log('[1/3] Esperando login manual (tienes 2 minutos)...');
    try {
      await page.waitForURL('**/app/**', { timeout: 120000 });
    } catch {
      console.log('Timeout esperando login. Cerrando.');
      await browser.close();
      return;
    }
  }

  // Save session for future runs
  await context.storageState({ path: SESSION_FILE });
  console.log('[1/3] ✅ Sesión guardada');

  // Let Auth0TokenSync set the token
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCREENSHOTS, '01-workflow.png'), fullPage: true });
  console.log('URL actual:', page.url());

  // ── Phase 2: Test connections page ────────────────────────────────────────
  console.log('\n[2/3] Probando /connections...');
  const tenantBase = page.url().replace(/\/[^/]+$/, ''); // strip last segment
  await page.goto(tenantBase + '/connections', { waitUntil: 'networkidle', timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '02-connections.png'), fullPage: true });

  // ── Phase 3: Test indexing page ───────────────────────────────────────────
  console.log('\n[3/3] Probando /indexing...');
  await page.goto(tenantBase + '/indexing', { waitUntil: 'networkidle', timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '03-indexing.png'), fullPage: true });

  // ── Report ────────────────────────────────────────────────────────────────
  console.log('\n╔════════════════════════════════════════╗');
  console.log('║         HEADERS ENVIADOS AL API        ║');
  console.log('╚════════════════════════════════════════╝');
  for (const r of requests) {
    const tok = r.auth === '(none)' ? '❌ sin token'
      : r.auth.replace(/^Bearer (.{0,15}).*$/, 'Bearer $1...');
    console.log(`  ${r.method.padEnd(6)} ${r.path}`);
    console.log(`         ${tok}`);
  }

  console.log('\n╔════════════════════════════════════════╗');
  console.log('║              RESULTADO FINAL           ║');
  console.log('╚════════════════════════════════════════╝');
  if (issues.length === 0) {
    console.log('  ✅ Sin errores 401/403');
  } else {
    console.log(`  ❌ ${issues.length} error(es) encontrado(s):\n`);
    for (const i of issues) {
      console.log(`  [${i.status}] ${i.path}`);
      console.log(`         ${i.body}`);
    }
  }
  console.log('\nScreenshots guardados en: e2e/screenshots/');
  console.log('Cerrando browser en 5 segundos...');
  await page.waitForTimeout(5000);
  await browser.close();
})();
