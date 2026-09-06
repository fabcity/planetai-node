const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const ctx=await b.newContext({viewport:{width:1440,height:900}});
 const p=await ctx.newPage();
 const errs=[],failed=[];
 p.on('console',m=>{if(m.type()==='error')errs.push(m.text().slice(0,160));});
 p.on('requestfailed',r=>failed.push(r.url().slice(0,120)+' :: '+(r.failure()?.errorText||'')));
 await p.goto('http://127.0.0.1:8790/observatory/',{waitUntil:'networkidle',timeout:120000}).catch(()=>{});
 await p.waitForTimeout(25000);   // generous
 const state=await p.evaluate(()=>{
  const t=s=>document.querySelector(s)?.textContent.trim()||null;
  return {
   globeBox:t('#planet-globe-status')||t('.globe-status')||(document.querySelector('#globe-container')?.textContent.trim().slice(0,60)||null),
   metrics:['m-total','m-active','m-continents','m-labs','m-sensors','m-flights','m-fires'].map(id=>[id,document.getElementById(id)?.textContent.trim()]),
   connectedSources:[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&/Connected sources/i.test(e.textContent||'')).map(e=>e.textContent.trim())[0]||null,
   canvasCount:document.querySelectorAll('canvas').length,
   canvasesWithPixels:[...document.querySelectorAll('canvas')].filter(c=>c.width>0&&c.height>0).length,
   svgNoLabel:[...document.querySelectorAll('svg')].filter(s=>!s.getAttribute('aria-label')&&!s.querySelector('title')&&s.getAttribute('aria-hidden')!=='true').length,
   svgTotal:document.querySelectorAll('svg').length,
   canvasNoLabel:[...document.querySelectorAll('canvas')].filter(c=>!c.getAttribute('aria-label')&&!c.textContent.trim()&&c.getAttribute('role')!=='img').length,
  };
 });
 await p.screenshot({path:OUT+'/shots/observatory/1440x900/observe-global-after-25s.png',fullPage:true});
 const r={state,consoleErrors:errs.slice(0,25),failedRequests:failed.slice(0,25)};
 fs.writeFileSync(OUT+'/observatory-load-state.json',JSON.stringify(r,null,1));
 console.log(JSON.stringify(r,null,1));
 await b.close();
})();
