const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const V=`el=>{const s=getComputedStyle(el);const r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;}`;
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const ctx=await b.newContext({viewport:{width:1440,height:900}});
 const p=await ctx.newPage();
 const R={};
 // LANDING
 await p.goto('http://127.0.0.1:8790/index.html',{waitUntil:'networkidle',timeout:60000}).catch(()=>{});
 await p.waitForTimeout(3000);
 R.landing=await p.evaluate((v)=>{const V=eval(v);
  const links=[...document.querySelectorAll('a[href]')].filter(V);
  return {
   installLineOnPage:/curl .*install/.test(document.body.innerText),
   linksToNode0:links.filter(a=>/node0/.test(a.getAttribute('href'))).length,
   linksToObservatory:links.filter(a=>/observatory/.test(a.getAttribute('href'))).length,
   linksToGithub:links.filter(a=>/github/.test(a.getAttribute('href'))).length,
   heroPrimaryBtn:document.querySelector('.btn.primary')?.getAttribute('href'),
   navCta:document.querySelector('nav.primary a.cta')?.getAttribute('href'),
   liveNumbers:/data-live|id="live-/.test(document.body.innerHTML),
   pageHeightPx:document.body.scrollHeight};},V);
 // NODE0
 await p.goto('http://127.0.0.1:8790/node0/',{waitUntil:'networkidle',timeout:60000}).catch(()=>{});
 await p.waitForTimeout(2500);
 R.node0=await p.evaluate(()=>({
   installLineVisibleWithoutClick:/curl -fsSL planetai\.fab\.city\/node0\/install \| bash/.test(document.body.innerText),
   installAnchorInNav:!!document.querySelector('nav.primary a[href="#install"]'),
   pageHeightPx:document.body.scrollHeight}));
 // OBSERVATORY
 await p.goto('http://127.0.0.1:8790/observatory/',{waitUntil:'networkidle',timeout:120000}).catch(()=>{});
 await p.waitForTimeout(20000);
 R.observatory_load=await p.evaluate((v)=>{const V=eval(v);
  const links=[...document.querySelectorAll('a[href]')].filter(V);
  return {visibleLinksToNode0:links.filter(a=>/node0/.test(a.getAttribute('href'))).length,
          visibleLinksToGithubNode:links.filter(a=>/planetai-node/.test(a.getAttribute('href'))).length,
          visibleLinksHome:links.filter(a=>a.getAttribute('href')==='/').length,
          installLineAnywhere:/curl .*install/.test(document.body.innerText)};},V);
 // one click: Act
 await p.evaluate(()=>{const x=document.querySelector('.primary-tabs button[data-group="act"]');if(x)x.click();});
 await p.waitForTimeout(2500);
 R.observatory_act=await p.evaluate((v)=>{const V=eval(v);
  const links=[...document.querySelectorAll('a[href]')].filter(V);
  return {visibleLinksToNode0:links.filter(a=>/node0/.test(a.getAttribute('href'))).length,
          visibleLinksToGithubNode:links.filter(a=>/planetai-node/.test(a.getAttribute('href'))).length,
          installLine:/curl .*install/.test(document.body.innerText),
          firstStepHeading:document.querySelector('#act-connect h2, #act-connect h3')?.textContent.trim().slice(0,60)};},V);
 // one click: Feed (sources)
 await p.evaluate(()=>{const x=document.querySelector('.primary-tabs button[data-group="feed"]');if(x)x.click();});
 await p.waitForTimeout(2500);
 R.observatory_feed=await p.evaluate((v)=>{const V=eval(v);
  return {provPillsVisible:[...document.querySelectorAll('.prov')].filter(V).length,
          sourceLinksVisible:[...document.querySelectorAll('a[href^="http"]')].filter(V).length};},V);
 fs.writeFileSync(OUT+'/ia-clickpaths.json',JSON.stringify(R,null,1));
 console.log(JSON.stringify(R,null,1));
 await b.close();
})();
