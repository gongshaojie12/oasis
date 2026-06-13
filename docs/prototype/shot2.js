const puppeteer=require('C:/Users/鱼儿/AppData/Local/npm-cache/_npx/23232c69e5d221f3/node_modules/puppeteer-core');
const exe='C:/Users/鱼儿/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';
(async()=>{
  const b=await puppeteer.launch({executablePath:exe,headless:true,args:['--no-sandbox']});
  const pg=await b.newPage();
  await pg.setViewport({width:1512,height:945,deviceScaleFactor:1});
  await pg.goto('file:///D:/NLp/oasis/docs/prototype/chat.html',{waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,1600));
  await pg.screenshot({path:'shot-chat.png'});
  console.log('chat');
  await pg.evaluate(()=>window.openCockpit('cockpit'));
  await new Promise(r=>setTimeout(r,1600));
  await pg.screenshot({path:'shot-chat-cockpit.png'});
  console.log('cockpit');
  await b.close();
})();
