const puppeteer=require('C:/Users/鱼儿/AppData/Local/npm-cache/_npx/23232c69e5d221f3/node_modules/puppeteer-core');
const exe='C:/Users/鱼儿/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';
(async()=>{
  const b=await puppeteer.launch({executablePath:exe,headless:true,args:['--no-sandbox']});
  const pg=await b.newPage();
  await pg.setViewport({width:1440,height:960,deviceScaleFactor:1});
  await pg.goto('file:///D:/NLp/oasis/docs/prototype/index.html',{waitUntil:'networkidle0'});
  for(const s of ['dash','scenario','pop','cockpit','report']){
    await pg.evaluate(id=>window.go(id),s);
    await new Promise(r=>setTimeout(r,1400));
    await pg.screenshot({path:'shot-'+s+'.png'});
    console.log('shot',s);
  }
  await b.close();
})();
