const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const V=`el=>{const s=getComputedStyle(el);const r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;}`;
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const ctx=await b.newContext({viewport:{width:1440,height:900}});
 const p=await ctx.newPage();
 await p.goto('http://127.0.0.1:8790/observatory/',{waitUntil:'networkidle',timeout:120000}).catch(()=>{});
 await p.waitForTimeout(18000);
 const R={};
 for(const g of ['observe','understand','feed','act','stories']){
  await p.evaluate(x=>{const b=document.querySelector(`.primary-tabs button[data-group="${x}"]`);if(b)b.click();},g);
  await p.waitForTimeout(2500);
  R[g]=await p.evaluate((v)=>{const V=eval(v);
   const pills=[...document.querySelectorAll('.prov')].filter(V);
   const byState={};
   pills.forEach(el=>{const cls=[...el.classList].find(c=>c.startsWith('is-'))||'base';
     const k=cls+'|'+el.textContent.trim().slice(0,28);byState[k]=(byState[k]||0)+1;});
   return {visible:pills.length, states:byState};},V);
 }
 // observe sub-views
 await p.evaluate(()=>{const b=document.querySelector('.primary-tabs button[data-group="observe"]');if(b)b.click();});
 await p.waitForTimeout(1500);
 for(const v of ['global','bcn','attr','constellation']){
  await p.evaluate(x=>{const b=document.querySelector(`#observe-subtabs button[data-view="${x}"]`);if(b)b.click();},v);
  await p.waitForTimeout(3000);
  R['observe:'+v]=await p.evaluate((vv)=>{const V=eval(vv);
   const pills=[...document.querySelectorAll('.prov')].filter(V);
   const byState={};
   pills.forEach(el=>{const cls=[...el.classList].find(c=>c.startsWith('is-'))||'base';
     const k=cls+'|'+el.textContent.trim().slice(0,28);byState[k]=(byState[k]||0)+1;});
   return {visible:pills.length,states:byState};},V);
 }
 fs.writeFileSync(OUT+'/observatory-prov-by-view.json',JSON.stringify(R,null,1));
 console.log(JSON.stringify(R,null,1));
 await b.close();
})();
