const {chromium} = require('playwright-core');
const fs=require('fs'), path=require('path');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const AXE=fs.readFileSync(__dirname+'/node_modules/axe-core/axe.min.js','utf8');
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const SITE='http://127.0.0.1:8790', NODE1='http://127.0.0.1:8899', CLEAN='http://127.0.0.1:8080';

const TARGETS=[
 ['landing','home',SITE+'/index.html',null],
 ['node0','index',SITE+'/node0/',null],
 ['node0','setup',SITE+'/node0/setup/',null],
 ['observatory','observe-global',SITE+'/observatory/',null],
 ['observatory','understand',SITE+'/observatory/',{group:'understand'}],
 ['observatory','feed',SITE+'/observatory/',{group:'feed'}],
 ['observatory','act',SITE+'/observatory/',{group:'act'}],
 ['observatory','stories',SITE+'/observatory/',{group:'stories'}],
 ['dashboard-node1','now',NODE1+'/',null],
 ['dashboard-node1','network',NODE1+'/',{view:'network'}],
 ['dashboard-node1','setup',NODE1+'/',{view:'setup'}],
 ['dashboard-node1','wall',NODE1+'/?kiosk=1',null],
 ['dashboard-clean','now',CLEAN+'/',null],
];

async function prep(page,p){
  if(!p) return;
  if(p.group){ await page.evaluate(g=>{const b=document.querySelector(`.primary-tabs button[data-group="${g}"]`); if(b)b.click();},p.group).catch(()=>{}); await page.waitForTimeout(1500); }
  if(p.view){ await page.evaluate(v=>{ if(typeof show==='function') show(v); },p.view).catch(()=>{}); await page.waitForTimeout(900); }
}

(async()=>{
  const b=await chromium.launch({executablePath:CHROME});
  const summary=[];
  for(const [surface,view,url,p] of TARGETS){
    const ctx=await b.newContext({viewport:{width:1440,height:900},colorScheme:'light'});
    const page=await ctx.newPage();
    try{
      await page.goto(url,{waitUntil:'networkidle',timeout:45000}).catch(()=>{});
      await page.waitForTimeout(2500); await prep(page,p); await page.waitForTimeout(1200);
      await page.addScriptTag({content:AXE});
      const res=await page.evaluate(async()=>await window.axe.run(document,{resultTypes:['violations'],runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}}));
      const v=res.violations.map(x=>({id:x.id,impact:x.impact,nodes:x.nodes.length,help:x.help}));
      fs.mkdirSync(path.join(OUT,'axe'),{recursive:true});
      fs.writeFileSync(path.join(OUT,'axe',`${surface}--${view}.json`),JSON.stringify({surface,view,url,violations:v},null,1));
      summary.push({surface,view,total:v.reduce((a,c)=>a+c.nodes,0),rules:v.length,v});
      console.log(`AXE ${surface}/${view}: ${v.length} rules, ${v.reduce((a,c)=>a+c.nodes,0)} nodes`);
    }catch(e){ console.log(`AXE FAIL ${surface}/${view}: ${e.message.split('\n')[0]}`); }
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT,'axe','_summary.json'),JSON.stringify(summary,null,1));
  await b.close();
})();
