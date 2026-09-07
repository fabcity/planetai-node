const {chromium} = require('playwright-core');
const fs = require('fs'), path = require('path');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT = '/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit/shots';
const SITE = 'http://127.0.0.1:8790';
const NODE1 = 'http://127.0.0.1:8899';
const CLEAN = 'http://127.0.0.1:8080';
const VPS = {'375x812':[375,812], '768x1024':[768,1024], '1440x900':[1440,900]};

// surface -> [ [viewName, url, prep] ]
const BANDS = ['room','street','plan','region','act','day','hero'];
const PLAN = {
  landing: [['home', SITE + '/index.html', null]],
  node0: [['index', SITE + '/node0/', null], ['setup', SITE + '/node0/setup/', null], ['more', SITE + '/node0/more/', null]],
  observatory: [
    ['observe-global',        SITE+'/observatory/', {group:'observe', view:'global'}],
    ['observe-bcn',           SITE+'/observatory/', {group:'observe', view:'bcn'}],
    ['observe-attr',          SITE+'/observatory/', {group:'observe', view:'attr'}],
    ['observe-constellation', SITE+'/observatory/', {group:'observe', view:'constellation'}],
    ['understand-index',   SITE+'/observatory/', {group:'understand', sub:'index'}],
    ['understand-matrix',  SITE+'/observatory/', {group:'understand', sub:'matrix'}],
    ['understand-bridge',  SITE+'/observatory/', {group:'understand', sub:'bridge'}],
    ['understand-science', SITE+'/observatory/', {group:'understand', sub:'science'}],
    ['feed-environment', SITE+'/observatory/', {group:'feed', sub:'environment'}],
    ['feed-production',  SITE+'/observatory/', {group:'feed', sub:'production'}],
    ['feed-knowledge',   SITE+'/observatory/', {group:'feed', sub:'knowledge'}],
    ['feed-contribute',  SITE+'/observatory/', {group:'feed', sub:'contribute'}],
    ['act-connect', SITE+'/observatory/', {group:'act', jump:'#act-connect'}],
    ['act-measure', SITE+'/observatory/', {group:'act', jump:'#act-measure'}],
    ['act-learn',   SITE+'/observatory/', {group:'act', jump:'#act-learn'}],
    ['act-design',  SITE+'/observatory/', {group:'act', jump:'#act-design'}],
    ['act-make',    SITE+'/observatory/', {group:'act', jump:'#act-make'}],
    ['stories', SITE+'/observatory/', {group:'stories'}],
  ],
  'dashboard-node1': [
    ['now',      NODE1+'/', null],
    ['network',  NODE1+'/#network', {view:'network'}],
    ['setup',    NODE1+'/#setup', {view:'setup'}],
    ['wall',     NODE1+'/?kiosk=1', {view:'wall'}],
    ...BANDS.map(b => ['only-'+b, NODE1+'/?only='+b, null]),
  ],
  'dashboard-clean': [
    ['now',      CLEAN+'/', null],
    ['network',  CLEAN+'/#network', {view:'network'}],
    ['setup',    CLEAN+'/#setup', {view:'setup'}],
    ['wall',     CLEAN+'/?kiosk=1', {view:'wall'}],
    ...BANDS.map(b => ['only-'+b, CLEAN+'/?only='+b, null]),
  ],
};

async function prep(page, p) {
  if (!p) return;
  if (p.group) {
    await page.evaluate(g => {
      const b = document.querySelector(`.primary-tabs button[data-group="${g}"]`);
      if (b) b.click();
    }, p.group).catch(()=>{});
    await page.waitForTimeout(900);
  }
  if (p.view && p.group) {
    await page.evaluate(v => {
      const b = document.querySelector(`#observe-subtabs button[data-view="${v}"]`);
      if (b) b.click();
    }, p.view).catch(()=>{});
    await page.waitForTimeout(1600);
  } else if (p.view) {
    await page.evaluate(v => { if (typeof show === 'function') show(v); }, p.view).catch(()=>{});
    await page.waitForTimeout(900);
  }
  if (p.sub) {
    await page.evaluate(s => {
      const b = document.querySelector(`button[data-subtab="${s}"]`);
      if (b) b.click();
    }, p.sub).catch(()=>{});
    await page.waitForTimeout(1200);
  }
  if (p.jump) {
    await page.evaluate(j => {
      const b = document.querySelector(`button[data-jump="${j}"]`);
      if (b) b.click();
    }, p.jump).catch(()=>{});
    await page.waitForTimeout(1200);
  }
}

(async () => {
  const browser = await chromium.launch({executablePath: CHROME});
  const only = process.argv[2];
  for (const [surface, views] of Object.entries(PLAN)) {
    if (only && surface !== only) continue;
    for (const [vpName, [w, h]] of Object.entries(VPS)) {
      const ctx = await browser.newContext({
        viewport: {width: w, height: h},
        deviceScaleFactor: 1,
        colorScheme: 'light',
        reducedMotion: 'no-preference',
      });
      for (const [name, url, p] of views) {
        const dir = path.join(OUT, surface, vpName);
        fs.mkdirSync(dir, {recursive: true});
        const page = await ctx.newPage();
        try {
          await page.goto(url, {waitUntil: 'networkidle', timeout: 45000}).catch(()=>{});
          await page.waitForTimeout(2500);
          await prep(page, p);
          await page.waitForTimeout(1200);
          await page.screenshot({path: path.join(dir, name + '.png'), fullPage: true});
          process.stdout.write(`ok ${surface}/${vpName}/${name}\n`);
        } catch (e) {
          process.stdout.write(`FAIL ${surface}/${vpName}/${name}: ${e.message.split('\n')[0]}\n`);
        }
        await page.close();
      }
      await ctx.close();
    }
  }
  await browser.close();
})();
