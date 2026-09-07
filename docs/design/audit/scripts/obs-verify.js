const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const URL='http://127.0.0.1:8790/observatory/';

(async()=>{
  const b=await chromium.launch({executablePath:CHROME});
  const ctx=await b.newContext({viewport:{width:1440,height:900}});
  const page=await ctx.newPage();
  await page.goto(URL,{waitUntil:'networkidle',timeout:90000}).catch(()=>{});
  await page.waitForTimeout(5000);
  const r={};

  r.version=await page.title();
  r.mode=await page.evaluate(()=>document.body.getAttribute('data-view-mode'));

  // P0-1 radar
  r.P0_1_radar=await page.evaluate(()=>({
    barsBtn:!!document.querySelector('#con-mode-bars'),
    radarBtn:!!document.querySelector('#con-mode-radar'),
    defaultActive:document.querySelector('#con-mode-bars')?.classList.contains('active'),
    radarDefault:document.querySelector('#con-mode-radar')?.getAttribute('aria-checked'),
  }));

  // P1-4 provenance depth: clicks to reach source of a number
  r.P1_4_prov=await page.evaluate(()=>{
    const slots=document.querySelectorAll('[data-viz-source]');
    const inline=document.querySelectorAll('.viz-provenance, .prov-slot, .provenance-inline');
    return {vizSourceAttrs:slots.length, inlineBlocksRendered:inline.length,
            firstSource:slots[0]?.getAttribute('data-viz-source')?.slice(0,90)||null};
  });

  // P1-6 Act wizard
  r.P1_6_act=await page.evaluate(()=>{
    const steps=[...document.querySelectorAll('.act-scroll-nav .act-step')];
    return {stepButtons:steps.length,
            numbered:steps.map(s=>s.getAttribute('data-step')),
            locked:steps.filter(s=>s.classList.contains('locked')||s.querySelector('.lock')).length,
            labels:steps.map(s=>s.textContent.trim().replace(/\s+/g,' ').slice(0,28))};
  });

  // P1-7 3D globe
  r.P1_7_globe=await page.evaluate(()=>({
    twoDActive:document.querySelector('#planet-mode-2d')?.classList.contains('active'),
    threeDLabel:document.querySelector('#planet-mode-3d')?.textContent.trim(),
    globeLib:typeof window.Globe!=='undefined',
    hint:document.querySelector('#planet-mode-hint')?.textContent.trim().slice(0,120),
  }));

  // P1-8 synthetic marking
  r.P1_8_synth=await page.evaluate(()=>({
    syntheticContainers:document.querySelectorAll('[data-synthetic="true"]').length,
    syntheticBadges:document.querySelectorAll('.simulated-badge, .synth-pill').length,
    provSynthPills:document.querySelectorAll('.prov.is-synthetic').length,
  }));

  // P1-9 disclosure persistence
  r.P1_9_disclosure=await page.evaluate(()=>({
    disclosureSeen:(()=>{try{return localStorage.getItem('planetai-disclosure-seen');}catch(e){return 'n/a';}})(),
    welcomeStore:'sessionStorage:planetai_welcome_dismissed',
    welcomeVisible:!!document.querySelector('#welcome-band:not(.dismissed)'),
  }));

  // P1-10 time scrubbers
  r.P1_10_scrub=await page.evaluate(()=>{
    const s=[...document.querySelectorAll('input[type=range]')].filter(i=>/scrub|time/i.test(i.id+i.className+(i.getAttribute('aria-label')||'')));
    return {rangeInputs:document.querySelectorAll('input[type=range]').length, timeScrubbers:s.length,
            ids:s.map(i=>i.id||i.getAttribute('aria-label')).slice(0,6)};
  });

  // P1-11 a11y scaffolding
  r.P1_11_a11y=await page.evaluate(()=>({
    skipLink:!!document.querySelector('a.skip-link, a[href="#main-content"]'),
    liveRegions:document.querySelectorAll('[aria-live]').length,
    burger:!!document.querySelector('#burger-btn'),
    tablists:document.querySelectorAll('[role=tablist]').length,
  }));

  // P1-5 simplified actually simplifies — count visible elements in each mode
  const count=async()=>await page.evaluate(()=>{
    const vis=el=>{const s=getComputedStyle(el);const r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0;};
    return {advancedOnlyTotal:document.querySelectorAll('[data-advanced-only]').length,
            advancedOnlyVisible:[...document.querySelectorAll('[data-advanced-only]')].filter(vis).length,
            actStepButtons:[...document.querySelectorAll('.act-scroll-nav .act-step')].filter(vis).length,
            actSectionsVisible:[...document.querySelectorAll('.act-section')].filter(vis).length,
            bodyHeight:document.body.scrollHeight};
  });
  // switch to Act group first so act sections are in play
  await page.evaluate(()=>{const b=document.querySelector('.primary-tabs button[data-group="act"]');if(b)b.click();});
  await page.waitForTimeout(1500);
  const modeBtn=await page.evaluate(()=>{
    const cands=[...document.querySelectorAll('button,a')].filter(b=>/simplified|advanced/i.test(b.textContent||''));
    return cands.map(c=>({t:c.textContent.trim().slice(0,40),id:c.id}));
  });
  r.modeToggleCandidates=modeBtn;
  r.actMode_current=await count();
  // flip mode
  await page.evaluate(()=>{
    const cur=document.body.getAttribute('data-view-mode');
    document.body.setAttribute('data-view-mode', cur==='simplified'?'advanced':'simplified');
  });
  await page.waitForTimeout(1200);
  r.actMode_flipped_to=await page.evaluate(()=>document.body.getAttribute('data-view-mode'));
  r.actMode_after=await count();

  // mobile <720
  await page.setViewportSize({width:375,height:812});
  await page.waitForTimeout(2000);
  r.mobile375=await page.evaluate(()=>({
    docScrollW:document.documentElement.scrollWidth, clientW:document.documentElement.clientWidth,
    horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
    offenders:[...document.querySelectorAll('*')].filter(el=>el.getBoundingClientRect().right>window.innerWidth+2)
              .slice(0,8).map(el=>el.tagName+'.'+(el.className&&el.className.toString?el.className.toString().slice(0,40):'')),
  }));

  fs.writeFileSync(OUT+'/observatory-findings.json',JSON.stringify(r,null,1));
  console.log(JSON.stringify(r,null,1));
  await b.close();
})();
