const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL='http://127.0.0.1:8790/observatory/';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const vis=`el=>{const s=getComputedStyle(el);const r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;}`;
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const ctx=await b.newContext({viewport:{width:1440,height:900}});
 const page=await ctx.newPage();
 const R={};
 await page.goto(URL,{waitUntil:'networkidle',timeout:90000}).catch(()=>{});
 await page.waitForTimeout(5000);
 R.onLoad=await page.evaluate(()=>({mode:document.body.getAttribute('data-view-mode'),
   simplifiedBtnActive:document.querySelector('#view-mode-simplified')?.className,
   advancedBtnActive:document.querySelector('#view-mode-advanced')?.className,
   advVisible:[...document.querySelectorAll('[data-advanced-only]')].filter(el=>getComputedStyle(el).display!=='none').length,
   advTotal:document.querySelectorAll('[data-advanced-only]').length}));
 // click Simplified
 await page.click('#view-mode-simplified').catch(()=>{});
 await page.waitForTimeout(1500);
 R.afterSimplified=await page.evaluate(()=>({mode:document.body.getAttribute('data-view-mode'),
   advVisible:[...document.querySelectorAll('[data-advanced-only]')].filter(el=>getComputedStyle(el).display!=='none').length,
   bodyH:document.body.scrollHeight}));
 await page.click('#view-mode-advanced').catch(()=>{});
 await page.waitForTimeout(1500);
 R.afterAdvanced=await page.evaluate(()=>({mode:document.body.getAttribute('data-view-mode'),
   advVisible:[...document.querySelectorAll('[data-advanced-only]')].filter(el=>getComputedStyle(el).display!=='none').length,
   bodyH:document.body.scrollHeight}));

 // Act group in simplified: are the 5 step buttons still shown while their sections hide?
 await page.click('#view-mode-simplified').catch(()=>{});
 await page.evaluate(()=>{const x=document.querySelector('.primary-tabs button[data-group="act"]');if(x)x.click();});
 await page.waitForTimeout(2000);
 R.actSimplified=await page.evaluate((v)=>{const V=eval(v);
   return {stepButtonsVisible:[...document.querySelectorAll('.act-scroll-nav .act-step')].filter(V).length,
           actSectionsVisible:[...document.querySelectorAll('.act-section')].filter(V).length,
           actSectionsTotal:document.querySelectorAll('.act-section').length};},vis);
 await page.click('#view-mode-advanced').catch(()=>{});
 await page.waitForTimeout(1500);
 R.actAdvanced=await page.evaluate((v)=>{const V=eval(v);
   return {stepButtonsVisible:[...document.querySelectorAll('.act-scroll-nav .act-step')].filter(V).length,
           actSectionsVisible:[...document.querySelectorAll('.act-section')].filter(V).length};},vis);

 // Constellation: does the time scrubber mount?
 await page.evaluate(()=>{const x=document.querySelector('.primary-tabs button[data-group="observe"]');if(x)x.click();});
 await page.waitForTimeout(1200);
 await page.evaluate(()=>{const x=document.querySelector('#observe-subtabs button[data-view="constellation"]');if(x)x.click();});
 await page.waitForTimeout(3500);
 R.constellationScrubber=await page.evaluate((v)=>{const V=eval(v);
   const ranges=[...document.querySelectorAll('input[type=range]')];
   return {ranges:ranges.length, visibleRanges:ranges.filter(V).length,
           ids:ranges.map(r=>r.id||r.getAttribute('aria-label')||r.className).slice(0,8),
           scrubberEls:document.querySelectorAll('[class*=scrub],[id*=scrub]').length};},vis);

 // provenance clicks: is the source visible without any click?
 R.provInline=await page.evaluate((v)=>{const V=eval(v);
   const hosts=[...document.querySelectorAll('[data-viz-source]')];
   return hosts.map(h=>({status:h.getAttribute('data-viz-status'),
     inlineChild:!!h.querySelector('.viz-provenance,.prov-inline,.provenance'),
     visibleSourceText:[...h.querySelectorAll('*')].filter(V).some(e=>/source|cached|live|synthetic/i.test(e.textContent||'')&&e.children.length===0)}));},vis);

 // disclosure banner persistence across reload
 await page.evaluate(()=>{const b=document.querySelector('#welcome-dismiss'); if(b)b.click();});
 await page.waitForTimeout(600);
 await page.reload({waitUntil:'networkidle'}).catch(()=>{});
 await page.waitForTimeout(3000);
 R.afterReload=await page.evaluate(()=>({welcomeVisible:(()=>{const b=document.querySelector('#welcome-band');if(!b)return false;const s=getComputedStyle(b);return s.display!=='none'&&!b.classList.contains('dismissed');})(),
   disclosureSeen:(()=>{try{return localStorage.getItem('planetai-disclosure-seen');}catch(e){return 'err';}})(),
   welcomeSession:(()=>{try{return sessionStorage.getItem('planetai_welcome_dismissed');}catch(e){return 'err';}})()}));

 fs.writeFileSync(OUT+'/observatory-findings-2.json',JSON.stringify(R,null,1));
 console.log(JSON.stringify(R,null,1));
 await b.close();
})();
