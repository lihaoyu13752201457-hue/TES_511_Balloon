#!/usr/bin/env node
/** Validate every slide for viewport overflow using the local headless Chrome. */

import { spawn } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const WORK = path.dirname(new URL(import.meta.url).pathname);
const HTML = path.join(WORK, 'index.html');
const REPORT = path.join(WORK, 'deck_viewport_validation.json');
const CHROME = '/home/ubuntu/.agent-browser/browsers/chrome-149.0.7827.22/chrome';
const PORT = 9320 + Math.floor(Math.random() * 200);
const PROFILE = await mkdtemp(path.join(tmpdir(), 'mass511-deck-chrome-'));
const VIEWPORTS = [
  { width: 1920, height: 1080, name: 'fhd' },
  { width: 1440, height: 900, name: 'laptop' },
  { width: 1366, height: 768, name: 'wxga' },
  { width: 1280, height: 720, name: 'hd' },
];

const chrome = spawn(CHROME, [
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  '--disable-dev-shm-usage',
  '--disable-background-networking',
  '--disable-component-update',
  '--disable-default-apps',
  '--disable-extensions',
  '--disable-sync',
  '--host-resolver-rules=MAP fonts.googleapis.com 0.0.0.0, MAP fonts.gstatic.com 0.0.0.0',
  '--metrics-recording-only',
  '--no-first-run',
  '--allow-file-access-from-files',
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${PROFILE}`,
  'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });

let chromeErrors = '';
chrome.stderr.on('data', (chunk) => { chromeErrors += chunk.toString(); });

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForEndpoint() {
  for (let i = 0; i < 100; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      if (response.ok) return await response.json();
    } catch (_) { /* Chrome is still starting. */ }
    await delay(100);
  }
  throw new Error(`Chrome debugging endpoint did not start. ${chromeErrors.slice(-1000)}`);
}

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
  }

  async open() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', (event) => {
      const payload = JSON.parse(event.data);
      if (!payload.id || !this.pending.has(payload.id)) return;
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
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}

async function waitForReady(cdp) {
  for (let i = 0; i < 200; i += 1) {
    const ready = await evaluate(cdp, 'document.querySelectorAll(".slide").length === 21 && typeof goTo === "function"');
    if (ready) return;
    await delay(50);
  }
  throw new Error('deck DOM did not reach interactive state');
}

const overflowExpression = (slideIndex) => `(() => {
  const slide = document.querySelectorAll('.slide')[${slideIndex}];
  const tolerance = 2.5;
  const bad = [];
  const ignored = 'script,style,.glow-blob,.sr-only';
  [slide, ...slide.querySelectorAll('*')].forEach((el) => {
    if (el.matches && el.matches(ignored)) return;
    if (el.closest && el.closest('.glow-blob')) return;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    const rect = el.getBoundingClientRect();
    if (rect.width < .5 || rect.height < .5) return;
    const overflow = {
      left: rect.left < -tolerance,
      top: rect.top < -tolerance,
      right: rect.right > innerWidth + tolerance,
      bottom: rect.bottom > innerHeight + tolerance,
    };
    if (overflow.left || overflow.top || overflow.right || overflow.bottom) {
      bad.push({
        tag: el.tagName,
        cls: String(el.className || '').slice(0, 120),
        text: String(el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 100),
        rect: { left: +rect.left.toFixed(1), top: +rect.top.toFixed(1), right: +rect.right.toFixed(1), bottom: +rect.bottom.toFixed(1) },
        overflow,
      });
    }
  });
  const imageFailures = [...slide.querySelectorAll('img')]
    .filter((img) => !img.complete || img.naturalWidth === 0)
    .map((img) => img.getAttribute('src'));
  return {
    slide: ${slideIndex},
    viewport: { width: innerWidth, height: innerHeight },
    slideBox: { width: slide.clientWidth, height: slide.clientHeight, scrollWidth: slide.scrollWidth, scrollHeight: slide.scrollHeight },
    bad: bad.slice(0, 20),
    imageFailures,
  };
})()`;

let cdp;
try {
  const targets = await waitForEndpoint();
  const target = targets.find((item) => item.type === 'page');
  if (!target) throw new Error('no page target from Chrome');
  cdp = new CDP(target.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Network.enable');
  await cdp.send('Network.setBlockedURLs', { urls: ['https://fonts.googleapis.com/*', 'https://fonts.gstatic.com/*'] });
  await cdp.send('Page.navigate', { url: pathToFileURL(HTML).href });
  await waitForReady(cdp);
  await evaluate(cdp, `(() => {
    const style = document.createElement('style');
    style.id = 'qa-no-motion';
    style.textContent = '#deck .slide{transition:none!important;}#deck .slide.active *,#deck .slide.active *::before,#deck .slide.active *::after{animation:none!important;transition:none!important;opacity:1!important;filter:none!important;}';
    document.head.appendChild(style);
    return document.fonts ? document.fonts.ready.then(() => true) : true;
  })()`);

  const totalSlides = await evaluate(cdp, 'document.querySelectorAll(".slide").length');
  const results = [];
  const screenshots = [];
  for (const viewport of VIEWPORTS) {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: viewport.width,
      screenHeight: viewport.height,
    });
    await evaluate(cdp, 'window.dispatchEvent(new Event("resize")); true');
    for (let index = 0; index < totalSlides; index += 1) {
      await evaluate(cdp, `goTo(${index}); true`);
      await delay(25);
      const result = await evaluate(cdp, overflowExpression(index));
      result.viewportName = viewport.name;
      results.push(result);
      const captureFhd = viewport.name === 'fhd' && [0, 5, 15, 16, 17, 18, 20].includes(index);
      const captureHd = viewport.name === 'hd' && [15, 16, 17, 18, 20].includes(index);
      if (captureFhd || captureHd) {
        const capture = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true });
        const screenshot = path.join(tmpdir(), `mass511_s3_deck_slide_${String(index).padStart(2, '0')}_${viewport.name}.png`);
        await writeFile(screenshot, Buffer.from(capture.data, 'base64'));
        screenshots.push(screenshot);
      }
    }
  }

  const problems = results.filter((entry) => entry.bad.length || entry.imageFailures.length);
  const report = {
    status: problems.length ? 'FAIL' : 'PASS',
    chrome: CHROME,
    html: HTML,
    slides: totalSlides,
    viewports: VIEWPORTS,
    checks: results.length,
    problems,
    screenshots,
  };
  await writeFile(REPORT, JSON.stringify(report, null, 2) + '\n');
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
  if (problems.length) process.exitCode = 1;
} finally {
  if (cdp) cdp.close();
  chrome.kill('SIGTERM');
  await delay(150);
  await rm(PROFILE, { recursive: true, force: true });
}
