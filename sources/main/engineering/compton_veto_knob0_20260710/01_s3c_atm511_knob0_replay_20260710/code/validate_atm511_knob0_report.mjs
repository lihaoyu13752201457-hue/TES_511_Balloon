#!/usr/bin/env node
/** Render-level QA for the self-contained atm511 Knob0 technical report. */

import { spawn } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const CODE = path.dirname(new URL(import.meta.url).pathname);
const PACKAGE = path.dirname(CODE);
const HTML = path.join(PACKAGE, 'report', 's3c_atm511_knob0_report.html');
const OUTPUT = path.join(PACKAGE, 'report', 's3c_atm511_knob0_report_qa.json');
const CHROME = '/home/ubuntu/.agent-browser/browsers/chrome-149.0.7827.22/chrome';
const PORT = 9740 + Math.floor(Math.random() * 180);
const PROFILE = await mkdtemp(path.join(tmpdir(), 'knob0-atm-report-'));
const screenshots = {
  desktop: path.join(tmpdir(), 'knob0_atm511_report_desktop_qa.png'),
  narrow: path.join(tmpdir(), 'knob0_atm511_report_narrow_qa.png'),
};

const chrome = spawn(CHROME, [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  '--disable-background-networking', '--disable-component-update', '--disable-default-apps',
  '--disable-extensions', '--disable-sync', '--metrics-recording-only', '--no-first-run',
  '--allow-file-access-from-files', `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });

let chromeErrors = '';
chrome.stderr.on('data', (chunk) => { chromeErrors += chunk.toString(); });
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForEndpoint() {
  for (let index = 0; index < 120; index += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      if (response.ok) return await response.json();
    } catch (_) { /* Chrome starting. */ }
    await delay(100);
  }
  throw new Error(`Chrome endpoint failed. ${chromeErrors.slice(-1200)}`);
}

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
  }
  async open() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', (event) => {
      const payload = JSON.parse(event.data);
      if (!payload.id) {
        if (payload.method === 'Runtime.exceptionThrown' || payload.method === 'Log.entryAdded') this.events.push(payload);
        return;
      }
      if (!this.pending.has(payload.id)) return;
      const { resolve, reject } = this.pending.get(payload.id);
      this.pending.delete(payload.id);
      if (payload.error) reject(new Error(JSON.stringify(payload.error)));
      else resolve(payload.result || {});
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { this.ws.close(); }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}

async function navigate(cdp, { width, height, javascript, dark }) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height,
  });
  await cdp.send('Emulation.setEmulatedMedia', {
    media: '', features: [{ name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' }],
  });
  await cdp.send('Emulation.setScriptExecutionDisabled', { value: !javascript });
  await cdp.send('Page.navigate', { url: `${pathToFileURL(HTML).href}?qa=${Date.now()}` });
  for (let index = 0; index < 240; index += 1) {
    const readyState = await evaluate(cdp, 'document.readyState');
    const readyCharts = await evaluate(cdp, 'document.querySelectorAll("[data-recharts-chart][data-recharts-ready=\\"true\\"]").length');
    if (readyState === 'complete' && (!javascript || readyCharts === 2)) break;
    await delay(50);
  }
  await delay(javascript ? 350 : 100);
}

const inspect = `(() => {
  const visible = (node) => {
    const style = getComputedStyle(node); const rect = node.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 1 && rect.height > 1;
  };
  const hosts = [...document.querySelectorAll('[data-recharts-chart]')].map((host) => {
    const rect = host.getBoundingClientRect(); const wrap = host.closest('.chart-wrap');
    const style = wrap ? getComputedStyle(wrap) : null;
    const left = style ? parseFloat(style.paddingLeft) || 0 : 0;
    const right = style ? parseFloat(style.paddingRight) || 0 : 0;
    const fallback = host.querySelector('[data-recharts-fallback]');
    const live = host.querySelector('[data-recharts-live]');
    const textOverflow = [...host.querySelectorAll('[data-recharts-live] text')].filter(visible).map((node) => {
      const r = node.getBoundingClientRect(); return { text: node.textContent, l: r.left - rect.left, r: r.right - rect.left };
    }).filter((item) => item.l < -left - 4 || item.r > host.scrollWidth + right + 4);
    const fallbackVisible = Boolean(fallback && visible(fallback));
    const liveVisible = Boolean(live && visible(live));
    return {
      id: host.dataset.rechartsChart, ready: host.dataset.rechartsReady === 'true', fallbackVisible, liveVisible,
      liveSvgCount: live ? live.querySelectorAll('svg').length : 0,
      visibleSurfaceCount: Number(fallbackVisible) + Number(liveVisible), textOverflow,
    };
  });
  const roles = ['title','technical-summary','key-findings','scope-data-and-metric-definitions','methodology','limitations-uncertainty-and-robustness-checks','recommended-next-steps','further-questions'];
  return {
    viewport: { width: innerWidth, height: innerHeight }, hosts,
    readyCharts: hosts.filter((x) => x.ready).length,
    liveSvgs: hosts.reduce((sum, x) => sum + x.liveSvgCount, 0),
    fallbackVisible: hosts.filter((x) => x.fallbackVisible).length,
    badSurfaces: hosts.filter((x) => x.visibleSurfaceCount !== 1),
    textOverflow: hosts.flatMap((x) => x.textOverflow.map((v) => ({ chart: x.id, ...v }))),
    roles: roles.map((role) => ({ role, count: document.querySelectorAll('[data-contract-section="' + role + '"]').length })),
    sourceTooltips: document.querySelectorAll('.source-tooltip').length,
    horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 2,
    documentWidth: document.documentElement.scrollWidth,
    title: document.title,
  };
})()`;

async function capture(cdp, output) {
  const metrics = await cdp.send('Page.getLayoutMetrics');
  const size = metrics.cssContentSize || metrics.contentSize;
  const result = await cdp.send('Page.captureScreenshot', {
    format: 'png', fromSurface: true, captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: size.width, height: size.height, scale: 1 },
  });
  await writeFile(output, Buffer.from(result.data, 'base64'));
}

let cdp;
try {
  const targets = await waitForEndpoint();
  const target = targets.find((item) => item.type === 'page');
  if (!target) throw new Error('No Chrome page target');
  cdp = new CDP(target.webSocketDebuggerUrl); await cdp.open();
  await cdp.send('Page.enable'); await cdp.send('Runtime.enable'); await cdp.send('Log.enable');
  const checks = [];
  await navigate(cdp, { width: 1440, height: 900, javascript: true, dark: false });
  checks.push({ mode: 'desktop-live-light', ...(await evaluate(cdp, inspect)) }); await capture(cdp, screenshots.desktop);
  await navigate(cdp, { width: 390, height: 844, javascript: true, dark: true });
  checks.push({ mode: 'narrow-live-dark', ...(await evaluate(cdp, inspect)) }); await capture(cdp, screenshots.narrow);
  await navigate(cdp, { width: 390, height: 844, javascript: false, dark: false });
  checks.push({ mode: 'narrow-static-no-js', ...(await evaluate(cdp, inspect)) });

  const problems = [];
  for (const check of checks) {
    if (check.hosts.length !== 2) problems.push(`${check.mode}: expected 2 chart hosts`);
    if (check.horizontalOverflow) problems.push(`${check.mode}: document horizontal overflow`);
    if (check.badSurfaces.length) problems.push(`${check.mode}: fallback/live swap invalid`);
    if (check.roles.some((entry) => entry.count !== 1)) problems.push(`${check.mode}: technical section map invalid`);
    if (check.sourceTooltips < 2) problems.push(`${check.mode}: missing source affordances`);
    if (check.mode.includes('live')) {
      if (check.readyCharts !== 2 || check.liveSvgs !== 2 || check.fallbackVisible !== 0) problems.push(`${check.mode}: live charts failed`);
      if (check.textOverflow.length) problems.push(`${check.mode}: live chart text overflow`);
    } else if (check.readyCharts !== 0 || check.fallbackVisible !== 2) problems.push(`${check.mode}: static fallbacks failed`);
  }
  if (cdp.events.length) problems.push(`browser emitted ${cdp.events.length} exception/log event(s)`);
  const result = { status: problems.length ? 'FAIL' : 'PASS', html: HTML, checks, browserEvents: cdp.events, problems, screenshots };
  await writeFile(OUTPUT, JSON.stringify(result, null, 2) + '\n');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  if (problems.length) process.exitCode = 1;
} finally {
  if (cdp) cdp.close(); chrome.kill('SIGTERM'); await delay(150); await rm(PROFILE, { recursive: true, force: true });
}
