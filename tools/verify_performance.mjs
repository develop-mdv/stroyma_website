// Browser regression checks for optimized resources, offline caching and 3D export.
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(process.env.PLAYWRIGHT_MODULE_DIR, 'playwright'))); }
const base = process.env.PERF_BASE_URL || 'http://127.0.0.1:8000';
const browser = await chromium.launch({ headless: true, channel: process.env.PERF_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined) });
const checks = [];
const ensure = (condition, message) => { if (!condition) throw new Error(message); checks.push(message); };
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const failed = [];
  page.on('response', response => { if (response.status() >= 400) failed.push(response.url()); });
  await page.goto(base + '/about/');
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await page.reload();
  await page.waitForTimeout(800);
  const cached = await page.evaluate(async () => {
    const result = {};
    for (const name of await caches.keys()) result[name] = (await (await caches.open(name)).keys()).map(r => new URL(r.url).pathname);
    return result;
  });
  ensure(Object.values(cached).flat().includes('/about/'), 'Public informational page cached for offline use');
  ensure(!Object.values(cached).flat().some(url => /home_materials_hero|home\.js|catalog\.js/.test(url)), 'PWA does not download unopened page resources');
  const fromWorker = [];
  page.on('response', response => { if (response.fromServiceWorker()) fromWorker.push(response.url()); });
  await page.reload();
  await page.waitForTimeout(500);
  ensure(fromWorker.some(url => url.includes('public.min.css')), 'Repeated visit reuses versioned CSS from service-worker cache');
  await page.goto(base + '/cart/');
  await page.waitForTimeout(400);
  const privateCached = await page.evaluate(async () => {
    for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) {
      if (/\/(?:cart|accounts|checkout)\//.test(new URL(request.url).pathname)) return true;
    }
    return false;
  });
  ensure(!privateCached, 'Cart/account/checkout HTML excluded from offline caches');
  await context.setOffline(true);
  await page.goto(base + '/about/');
  ensure(await page.locator('h1').count() > 0, 'Previously visited informational page works offline');
  await page.goto(base + '/cart/');
  ensure((await page.content()).includes('Нет подключения'), 'Private page shows offline notice instead of a saved cart');
  await context.setOffline(false);
  await page.goto(base + '/');
  await page.waitForTimeout(1200);
  ensure(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'Home page fits mobile viewport');
  ensure((await page.locator('.home-product-image img').first().getAttribute('src')).includes('.thumbnails/'), 'Product list uses prebuilt thumbnails');
  await page.locator('#menu-toggle').click();
  ensure(await page.locator('#mobile-menu').evaluate(el => el.classList.contains('is-open')), 'Mobile menu still opens');
  await page.keyboard.press('Escape');
  await page.locator('#cookie-accept').click().catch(() => {});
  ensure(await page.locator('#home-cart-panel').evaluate(el => el.classList.contains('is-ready')), 'Mobile cart is initialized before being shown');
  await page.locator('#home-cart-toggle').click();
  ensure(await page.locator('#home-cart-body').isVisible(), 'Mobile cart preview can still be expanded');
  await page.locator('#home-cart-toggle').click();
  await mkdir('performance-results', { recursive: true });
  await page.screenshot({ path: 'performance-results/home-mobile.png' });
  await page.goto(base + '/catalog/');
  await page.waitForTimeout(900);
  ensure(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'Catalog fits mobile viewport');
  await page.screenshot({ path: 'performance-results/catalog-mobile.png' });
  await page.goto(base + '/color-selection/');
  ensure(await page.locator('#facadeConfigurator').evaluate(el => !el.getAttribute('src')), '3D code loads only when the visitor opens the model');
  await page.locator('#startConfigurator').click();
  const frame = page.frameLocator('#facadeConfigurator');
  await frame.locator('#view').waitFor();
  const child = page.frames().find(f => f.url().includes('color_configurator/index.html'));
  await child.waitForFunction(() => window.__cfgReady === true);
  await page.waitForTimeout(1500);
  const info = await child.evaluate(() => ({
    boot: window.__cfgBootMs, pixelRatio: window.__cfg.renderer.getPixelRatio(),
    textureWidth: window.__cfg.materials.facade.map.image.width,
    frames: window.__cfg.renderer.info.render.frame,
  }));
  ensure(info.textureWidth === 256 && info.pixelRatio <= 1, 'Touch devices use smaller textures and GPU buffers');
  await page.waitForTimeout(800);
  ensure((await child.evaluate(() => window.__cfg.renderer.info.render.frame)) === info.frames, '3D renderer remains idle when scene and camera are unchanged');
  const downloadPromise = page.waitForEvent('download');
  await frame.locator('#btnShot').click();
  const download = await downloadPromise;
  await download.saveAs('performance-results/facade-export.png');
  ensure((await download.failure()) === null, '3D PNG export works without retaining the drawing buffer');
  ensure(errors.length === 0, `No browser JavaScript exceptions (${errors.length})`);
  ensure(failed.length === 0, `No missing page resources (${failed.length})`);
  await writeFile('performance-results/browser-checks.json', JSON.stringify({ checks, configuration: info }, null, 2));
  console.log(JSON.stringify({ checks, configuration: info }, null, 2));
  await context.close();
} finally { await browser.close(); }
