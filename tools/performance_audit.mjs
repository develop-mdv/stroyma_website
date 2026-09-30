// Local Chromium benchmark. No orders, forms or remote services are submitted.
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); }
catch {
  const runtime = process.env.PLAYWRIGHT_MODULE_DIR;
  if (!runtime) throw new Error('Install playwright or set PLAYWRIGHT_MODULE_DIR to its package directory.');
  playwright = require(path.join(runtime, 'playwright'));
}
const base = process.env.PERF_BASE_URL || 'http://127.0.0.1:8000';
const out = process.argv[2] || 'performance-results/local.json';
const routes = process.argv.slice(3);
if (!routes.length) routes.push('/', '/catalog/', '/services/', '/about/', '/contact/');
const browser = await playwright.chromium.launch({ headless: true, channel: process.env.PERF_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined) });
const results = [];
try {
  for (const mobile of process.env.PERF_PROFILE === 'mobile' ? [true] : [false, true]) {
    for (const route of routes) {
      const context = await browser.newContext({
        viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 },
        deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile,
        serviceWorkers: 'block',
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => {
        window.__perf = { lcp: 0, cls: 0, layoutShifts: [], longTasks: [], interactions: [] };
        for (const [type, callback] of [
          ['largest-contentful-paint', entries => { for (const e of entries) { window.__perf.lcp = e.startTime; window.__perf.lcpElement = e.element?.className; } }],
          ['layout-shift', entries => { for (const e of entries) if (!e.hadRecentInput) {
            window.__perf.cls += e.value;
            window.__perf.layoutShifts.push({ value: e.value, time: e.startTime,
              sources: e.sources.map(s => ({ element: s.node?.id || s.node?.className,
                before: s.previousRect.toJSON(), after: s.currentRect.toJSON() })) });
          } }],
          ['longtask', entries => { for (const e of entries) window.__perf.longTasks.push(e.duration); }],
          ['event', entries => { for (const e of entries) if (e.interactionId) window.__perf.interactions.push(e.duration); }],
        ]) {
          try { new PerformanceObserver(list => callback(list.getEntries())).observe({ type, buffered: true, durationThreshold: 16 }); } catch {}
        }
      });
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
      await cdp.send('Emulation.setCPUThrottlingRate', { rate: mobile ? 6 : 1 });
      if (mobile) await cdp.send('Network.emulateNetworkConditions', {
        offline: false, latency: 150, downloadThroughput: 200000,
        uploadThroughput: 93750, connectionType: 'cellular3g',
      });
      const response = await page.goto(base + route, { waitUntil: 'load', timeout: 120000 });
      await page.waitForTimeout(2500);
      const measured = await page.evaluate(() => {
        const n = performance.getEntriesByType('navigation')[0];
        const r = performance.getEntriesByType('resource');
        return {
          ...window.__perf, ttfb: n.responseStart, domContentLoaded: n.domContentLoadedEventEnd,
          load: n.loadEventEnd, fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
          requests: r.length + 1, bytes: n.transferSize + r.reduce((s, e) => s + e.transferSize, 0),
          domNodes: document.querySelectorAll('*').length,
          overflow: document.documentElement.scrollWidth > innerWidth,
          largestResources: r.map(e => ({ url: new URL(e.name).pathname, bytes: e.transferSize, duration: Math.round(e.duration) }))
            .sort((a, b) => b.bytes - a.bytes).slice(0, 8),
        };
      });
      // A reproducible input responsiveness sample; it is not field INP.
      const menu = page.locator('#menu-toggle');
      if (mobile && await menu.isVisible()) {
        await menu.click();
        await page.waitForTimeout(400);
        measured.menuOpened = await page.locator('#mobile-menu').evaluate(el => el.classList.contains('is-open'));
        await page.keyboard.press('Escape');
      }
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(2000);
      const interaction = await page.evaluate(() => ({
        interactionMax: Math.max(0, ...window.__perf.interactions),
        longTaskCount: window.__perf.longTasks.length,
        blockingTime: window.__perf.longTasks.reduce((s, d) => s + Math.max(0, d - 50), 0),
      }));
      const result = { profile: mobile ? 'mobile-6x-1.6Mbps-150ms' : 'desktop', route, finalUrl: page.url(), status: response.status(), ...measured, ...interaction, errors };
      results.push(result);
      console.log(JSON.stringify({ profile: result.profile, route, status: result.status,
        lcp: Math.round(result.lcp), fcp: Math.round(result.fcp), load: Math.round(result.load),
        bytes: result.bytes, requests: result.requests, blockingTime: Math.round(result.blockingTime), errors }));
      await context.close();
    }
  }
} finally { await browser.close(); }
await mkdir(path.dirname(out), { recursive: true });
await writeFile(out, JSON.stringify({ date: new Date().toISOString(), base, cache: 'cold; service worker blocked', results }, null, 2));
