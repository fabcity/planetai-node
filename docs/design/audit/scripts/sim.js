const {chromium}=require('playwright-core');
const fs=require('fs'),path=require('path');
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUT='/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit/shots/fab26-simulator';
const F='file:///Users/tomasdiez/Documents/Claude/Projects/FAB26/MIT%20Exhibition/03_Simulators/';
(async()=>{
 const b=await chromium.launch({executablePath:CHROME});
 for(const [w,h,vp] of [[1440,900,'1440x900'],[375,812,'375x812']]){
  const ctx=await b.newContext({viewport:{width:w,height:h}});
  for(const [name,file] of [['desktop','fci_simulator_desktop.html'],['mobile','fci_simulator_mobile.html']]){
   const p=await ctx.newPage();
   await p.goto(F+file,{waitUntil:'networkidle',timeout:45000}).catch(()=>{});
   await p.waitForTimeout(3500);
   const dir=path.join(OUT,vp); fs.mkdirSync(dir,{recursive:true});
   await p.screenshot({path:path.join(dir,name+'.png'),fullPage:true});
   // crop the unit rows and matrix as the Isotype reference
   for(const [sel,tag] of [['#ctl_pito','unitrow-pito'],['#ctl_dido','unitrow-dido'],['#ctl_rho','unitrow-rho'],['table.mxt','matrix']]){
     const el=await p.$(sel);
     if(el) await el.screenshot({path:path.join(dir,`${name}--${tag}.png`)}).catch(()=>{});
   }
   console.log('ok',vp,name);
   await p.close();
  }
  await ctx.close();
 }
 await b.close();
})();
