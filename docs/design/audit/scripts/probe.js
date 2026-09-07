const {chromium}=require('playwright-core');
const fs=require('fs'),path=require('path');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit';
const SITE='http://127.0.0.1:8790',NODE1='http://127.0.0.1:8899',CLEAN='http://127.0.0.1:8080';
const F3G={offline:false,downloadThroughput:1.6*1024*1024/8,uploadThroughput:750*1024/8,latency:150};

const PERF=[['landing',SITE+'/index.html'],['node0',SITE+'/node0/'],['observatory',SITE+'/observatory/'],
            ['dashboard-node1',NODE1+'/'],['dashboard-clean',CLEAN+'/']];

async function perf(browser){
  const out=[];
  for(const [name,url] of PERF){
    const ctx=await browser.newContext({viewport:{width:1440,height:900}});
    const page=await ctx.newPage();
    const cdp=await ctx.newCDPSession(page);
    await cdp.send('Network.enable'); await cdp.send('Network.emulateNetworkConditions',F3G);
    let bytes=0,reqs=0;
    page.on('response',async r=>{reqs++;try{const h=r.headers();bytes+=parseInt(h['content-length']||0,10)||0;}catch(e){}});
    const t0=Date.now();
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:120000}).catch(()=>{});
    const dcl=Date.now()-t0;
    // "time to first sentence": the hero line has real content
    let firstSentence=null;
    try{
      await page.waitForFunction(()=>{
        const el=document.querySelector('#hero-line')||document.querySelector('h1')||document.querySelector('.section-title');
        if(!el) return false;
        const t=(el.textContent||'').trim();
        return t.length>12 && !/^Reading the room/.test(t);
      },{timeout:90000});
      firstSentence=Date.now()-t0;
    }catch(e){}
    await page.waitForLoadState('networkidle',{timeout:120000}).catch(()=>{});
    const idle=Date.now()-t0;
    const transfer=await page.evaluate(()=>performance.getEntriesByType('resource').reduce((a,r)=>a+(r.transferSize||0),0)+ (performance.getEntriesByType('navigation')[0]?.transferSize||0));
    out.push({name,url,requests:reqs,transferBytes:transfer,domContentLoadedMs:dcl,firstSentenceMs:firstSentence,networkIdleMs:idle});
    console.log(`PERF ${name}: ${reqs} req, ${(transfer/1024).toFixed(0)} KB, DCL ${dcl}ms, firstSentence ${firstSentence}ms, idle ${idle}ms`);
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT,'perf','fast3g.json'),JSON.stringify(out,null,1));
}

async function coverage(browser){
  const ctx=await browser.newContext({viewport:{width:1440,height:900}});
  const page=await ctx.newPage();
  await page.coverage.startCSSCoverage(); await page.coverage.startJSCoverage();
  await page.goto(SITE+'/observatory/',{waitUntil:'networkidle',timeout:90000}).catch(()=>{});
  await page.waitForTimeout(6000);
  const css=await page.coverage.stopCSSCoverage(), js=await page.coverage.stopJSCoverage();
  const sum=(arr)=>{let tot=0,used=0;for(const e of arr){tot+=(e.text||'').length;for(const r of (e.ranges||[]))used+=r.end-r.start;}return{tot,used};};
  const c=sum(css),j=sum(js);
  const r={cssTotal:c.tot,cssUsed:c.used,jsTotal:j.tot,jsUsed:j.used};
  console.log('COVERAGE observatory on first load:',JSON.stringify(r));
  fs.writeFileSync(path.join(OUT,'perf','observatory-coverage.json'),JSON.stringify(r,null,1));
  await ctx.close();
}

async function reducedMotion(browser){
  const res=[];
  for(const [name,url] of PERF){
    const ctx=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
    const page=await ctx.newPage();
    await page.goto(url,{waitUntil:'networkidle',timeout:60000}).catch(()=>{});
    await page.waitForTimeout(3000);
    const moving=await page.evaluate(()=>{
      const anims=document.getAnimations?document.getAnimations().filter(a=>a.playState==='running'):[];
      const smil=[...document.querySelectorAll('animate,animateTransform,animateMotion')].length;
      const css=[...document.querySelectorAll('*')].filter(el=>{
        const s=getComputedStyle(el);
        return s.animationName!=='none' && s.animationDuration!=='0s';
      }).length;
      return {webAnimations:anims.length, smilElements:smil, cssAnimatedElements:css};
    });
    res.push({name,...moving});
    console.log(`REDUCED-MOTION ${name}: ${JSON.stringify(moving)}`);
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT,'perf','reduced-motion.json'),JSON.stringify(res,null,1));
}

async function focusRings(browser){
  const targets=[['landing',SITE+'/index.html'],['node0',SITE+'/node0/'],['observatory',SITE+'/observatory/'],['dashboard-node1',NODE1+'/']];
  const report=[];
  for(const [name,url] of targets){
    const ctx=await browser.newContext({viewport:{width:1440,height:900}});
    const page=await ctx.newPage();
    await page.goto(url,{waitUntil:'networkidle',timeout:90000}).catch(()=>{});
    await page.waitForTimeout(3500);
    const dir=path.join(OUT,'shots','focus',name); fs.mkdirSync(dir,{recursive:true});
    const stops=[];
    for(let i=1;i<=30;i++){
      await page.keyboard.press('Tab');
      const info=await page.evaluate(()=>{
        const el=document.activeElement; if(!el||el===document.body)return null;
        const s=getComputedStyle(el);
        const r=el.getBoundingClientRect();
        return {tag:el.tagName,txt:(el.textContent||el.getAttribute('aria-label')||'').trim().slice(0,50),
                outline:s.outlineStyle+' '+s.outlineWidth+' '+s.outlineColor, boxShadow:s.boxShadow.slice(0,70),
                w:Math.round(r.width),h:Math.round(r.height), visible:r.width>0&&r.height>0};
      });
      if(!info) continue;
      const noRing=(info.outline.startsWith('none')||info.outline.includes('0px')) && (info.boxShadow==='none'||!info.boxShadow);
      stops.push({i,...info,noVisibleRing:noRing});
      if([3,10,20].includes(i)){
        await page.screenshot({path:path.join(dir,`tab-${i}.png`)}).catch(()=>{});
      }
    }
    report.push({surface:name,stops});
    const bad=stops.filter(s=>s.noVisibleRing&&s.visible).length;
    console.log(`FOCUS ${name}: ${stops.length} stops in 30 tabs, ${bad} with no visible ring`);
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT,'axe','focus-order.json'),JSON.stringify(report,null,1));
}

(async()=>{
  fs.mkdirSync(path.join(OUT,'perf'),{recursive:true});
  const b=await chromium.launch({executablePath:CHROME});
  const what=process.argv[2]||'all';
  if(what==='all'||what==='perf') await perf(b);
  if(what==='all'||what==='coverage') await coverage(b);
  if(what==='all'||what==='motion') await reducedMotion(b);
  if(what==='all'||what==='focus') await focusRings(b);
  await b.close();
})();
