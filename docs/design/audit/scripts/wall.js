const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const out=[];
 for(const [w,h,label] of [[1920,1080,'1920x1080'],[2560,1440,'2560x1440'],[1440,900,'1440x900']]){
  const ctx=await b.newContext({viewport:{width:w,height:h}});
  const p=await ctx.newPage();
  await p.goto('http://127.0.0.1:8899/?kiosk=1',{waitUntil:'networkidle',timeout:60000}).catch(()=>{});
  await p.waitForTimeout(4000);
  const m=await p.evaluate(()=>{
   const g=s=>{const el=document.querySelector(s);if(!el)return null;const c=getComputedStyle(el);
     return {sel:s,px:parseFloat(c.fontSize),weight:c.fontWeight,color:c.color,text:(el.textContent||'').trim().slice(0,40)};};
   const big=document.querySelector('#wall-line b');
   return {eyebrow:g('.wall .eye'), line:g('#wall-line'),
     numeral:big?{px:parseFloat(getComputedStyle(big).fontSize),color:getComputedStyle(big).color,text:big.textContent}:null,
     why:g('#wall-why'), statLabel:g('.wall .stats .eyebrow'), statNum:g('.wall .stats .num'), foot:g('.wall .foot')};
  });
  out.push({viewport:label,...m});
  console.log(label, JSON.stringify(m));
  await ctx.close();
 }
 fs.writeFileSync(OUT+'/wall-type-sizes.json',JSON.stringify(out,null,1));
 await b.close();
})();
