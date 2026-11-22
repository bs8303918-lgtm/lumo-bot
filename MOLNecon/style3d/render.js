// Render 3D style stills: node render.js [style ...]
// Serves this folder on localhost, opens scene.html in headless Chromium (SwiftShader WebGL),
// screenshots 1080x1920 frames into ./frames/.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = __dirname;
const OUT = path.join(ROOT, 'frames');
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };

const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});

const SHOTS = [
  { style: 'clay', mood: 'setup', cap: 'MONEY' },
  { style: 'toon', mood: 'setup', cap: 'MONEY' },
  { style: 'lowpoly', mood: 'setup', cap: 'MONEY' },
  { style: 'vinyl', mood: 'setup', cap: 'MONEY' },
  { style: 'stick', mood: 'setup', cap: 'MONEY' },
];

(async () => {
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  const want = process.argv.slice(2);
  const shots = process.env.SHOTS ? JSON.parse(process.env.SHOTS) : SHOTS.filter(s => !want.length || want.includes(s.style));
  for (const s of shots) {
    const qs = new URLSearchParams(s).toString();
    await page.goto(`http://localhost:${port}/scene.html?${qs}`);
    await page.waitForFunction('window.__done === true', null, { timeout: 120000 });
    const name = s.out || `${s.style}_${s.mood}.png`;
    await page.screenshot({ path: path.join(OUT, name) });
    console.log('wrote', name);
  }
  await browser.close();
  server.close();
})();
