const {chromium}=require('playwright-core');
const fs=require('fs');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const T=[['landing','http://127.0.0.1:8790/index.html'],['node0','http://127.0.0.1:8790/node0/'],
         ['observatory','http://127.0.0.1:8790/observatory/'],['dashboard-node1','http://127.0.0.1:8899/'],
         ['dashboard-clean','http://127.0.0.1:8080/']];
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 const R=[];
 for(const [n,u] of T){
  const ctx=await b.newContext({viewport:{width:1440,height:900}});
  const p=await ctx.newPage();
  await p.goto(u,{waitUntil:'networkidle',timeout:90000}).catch(()=>{});
  await p.waitForTimeout(n==='observatory'?18000:5000);
  const r=await p.evaluate(()=>{
   const named=el=>!!(el.getAttribute('aria-label')||el.getAttribute('aria-labelledby')||el.querySelector(':scope > title')||el.getAttribute('alt'));
   const hidden=el=>el.getAttribute('aria-hidden')==='true';
   const svgs=[...document.querySelectorAll('svg')];
   const cvs=[...document.querySelectorAll('canvas')];
   return {svgTotal:svgs.length, svgHidden:svgs.filter(hidden).length,
           svgUnnamedVisible:svgs.filter(s=>!hidden(s)&&!named(s)).length,
           svgUnnamedSamples:svgs.filter(s=>!hidden(s)&&!named(s)).slice(0,5).map(s=>(s.parentElement?.className||'').toString().slice(0,40)||s.id||'(no class)'),
           canvasTotal:cvs.length, canvasUnnamed:cvs.filter(c=>!named(c)&&!c.textContent.trim()).length};
  });
  R.push({surface:n,...r});
  console.log(n, JSON.stringify(r));
  await ctx.close();
 }
 fs.writeFileSync(OUT+'/chart-accessible-names.json',JSON.stringify(R,null,1));
 await b.close();
})();
