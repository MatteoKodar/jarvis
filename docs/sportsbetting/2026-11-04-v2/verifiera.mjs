// Dokumentkontroll i installerad Chromium. Inga tjänster eller produktdata startas.
import { createRequire } from 'node:module';
import { readFile, writeFile, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const folder = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(folder, '../../..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = require('@playwright/test');
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'sv-SE' });
const page = await context.newPage();
const errors = [];
const external = [];
await writeFile(path.join(folder, 'verifiering.json'), JSON.stringify({ passed: false, status: 'Pågående dokumentkontroll.' }) + '\n');
page.on('pageerror', e => errors.push(e.message));
page.on('request', r => { if (/^https?:/.test(r.url())) external.push(r.url()); });
const checks = [];
try {
  const mainUrl = pathToFileURL(path.join(folder, 'plan.html')).href;
  await page.goto(mainUrl);
  assert.match(await page.title(), /ekonomisk förstudie/);
  assert.equal(await page.locator('nav a').count(), 13);
  assert.equal(await page.locator('#implementation-text').inputValue(), await readFile(path.join(folder, 'IMPLEMENTATIONSUPPDRAG.md'), 'utf8'));
  assert.equal(await page.locator('#implementation-text').getAttribute('readonly'), '');
  checks.push('Huvudplan, 13 innehållslänkar och exakt kopierbart uppdrag.');
  await page.screenshot({ path: path.join(folder, 'plan-desktop.png') });
  for (const selector of ['#ekonomi', '#pilot', '#slutfragor']) {
    await page.locator(`nav a[href="${selector}"]`).click();
    assert.equal(new URL(page.url()).hash, selector);
    const top = await page.locator(selector).evaluate(e => e.getBoundingClientRect().top);
    assert.ok(Math.abs(top) < 80, `Ankarnavigering ${selector}: ${top}`);
  }
  await page.goBack();
  assert.equal(new URL(page.url()).hash, '#pilot');
  await page.reload();
  assert.equal(new URL(page.url()).hash, '#pilot');
  checks.push('Ankarlänkar, bakåtknapp och omladdning fungerar.');
  const files = ['plan.html', 'ekonomi.html', 'statistik.html', 'data-kallor.html', 'kritikergranskning.html'];
  let links = 0;
  for (const file of files) {
    const current = pathToFileURL(path.join(folder, file)).href;
    await page.goto(current);
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${file} flödar ut vid ${viewport.width}`);
    }
    const urls = await page.locator('a[href]').evaluateAll(items => items.map(e => e.href));
    for (const href of urls) {
      const url = new URL(href);
      if (url.protocol !== 'file:') continue;
      const bare = new URL(url); bare.hash = '';
      await access(fileURLToPath(bare));
      if (url.hash && bare.href === new URL(current).href) {
        assert.equal(await page.locator(`[id="${decodeURIComponent(url.hash.slice(1))}"]`).count(), 1);
      }
      links += 1;
    }
  }
  checks.push(`${files.length} HTML-dokument kontrollerade vid 1280px/390px; ${links} lokala länkar har mål.`);
  await page.goto(mainUrl);
  await page.screenshot({ path: path.join(folder, 'plan-mobil.png') });
  await page.locator('nav a[href="#ekonomi"]').click();
  await page.screenshot({ path: path.join(folder, 'ekonomi-mobil.png') });
  assert.equal(errors.length, 0, errors.join('; '));
  assert.equal(external.length, 0, 'Rapporten får inte hämta externa resurser.');
  checks.push('Inga sidfel eller externa resursanrop i dokumentvisningen.');
  const economics = JSON.parse(await readFile(path.join(folder, 'ekonomi.json'), 'utf8'));
  assert.equal(economics.verified_archive.profit_ore, -23659);
  assert.equal(economics.scenarios.find(s => s.name === 'optimistisk').season_game_net_ore, 1900);
  assert.equal(economics.goals.length, 90);
  assert.equal(economics.cost_sensitivity.length, 36);
  assert.equal(economics.scenarios.find(s => s.name === 'optimistisk').zero_cost_game_net_at_380_signals_ore, 19000);
  const quota = JSON.parse(await readFile(path.join(folder, 'kallor.json'), 'utf8')).pilot_proposal.quota;
  assert.equal(quota.odds_calls_cap * quota.odds_cost_each + quota.score_calls * quota.score_cost_each + quota.reserve_credits, quota.credit_cap);
  assert.equal(quota.sports_calls + quota.events_calls + quota.odds_calls_cap + quota.score_calls + quota.reserve_http_calls, quota.http_cap);
  checks.push('Nyckeltal, 90 målrader, 36 kostnadsfall och 172/146-kvotens aritmetik verifierade.');
  await writeFile(path.join(folder, 'verifiering.json'), JSON.stringify({ checked_at: new Date().toISOString(), passed: true, checks, product_tests: 'Inte körda: endast nya dokument och fristående studieprogram. Inga produktfiler ändrade.', paid_verification_calls: 0 }, null, 2) + '\n');
  console.log(JSON.stringify({ passed: true, checks }, null, 2));
} finally { await browser.close(); }
