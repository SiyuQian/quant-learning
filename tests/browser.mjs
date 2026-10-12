import assert from 'node:assert/strict';
import fs from 'node:fs';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({headless:true});
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/quant-learning-browser';
fs.mkdirSync(artifactDir,{recursive:true});
const base = process.env.BASE_URL || 'http://127.0.0.1:8765';
try {
 for (const width of [1440,390]) {
  const page = await browser.newPage({viewport:{width,height:900}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  await page.addInitScript(()=>{if(!localStorage.getItem('zhiben-progress-v1'))localStorage.setItem('zhiben-progress-v1',JSON.stringify({completed:[1,10,24],last:10}));});
  await page.goto(base+'/#lesson-1');
  assert.equal(await page.locator('#exercises details').count(),3,'native explained exercises must render');
  assert.equal(await page.locator('#progress-label').textContent(),'3 / 30');
  for (let id=1;id<=30;id++) {
   await page.evaluate(id=>{location.hash=`lesson-${id}`;},id);
   await page.waitForFunction(id=>document.querySelector('#lesson').dataset.lesson===String(id),id);
   assert.equal(await page.locator('#exercises details').count(),3);
   for(const summary of await page.locator('#exercises summary').all())await summary.click();
   for(const detail of await page.locator('#exercises details').all())assert(await detail.getAttribute('open')!==null);
   assert.equal(await page.locator('.deep-section').count(),3);
   assert(await page.locator('.source-guide').textContent());
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`overflow ${width}/${id}`);
   for(const href of await page.locator('[download]').evaluateAll(nodes=>nodes.map(n=>n.href))) {
    const response = await page.request.get(href); assert.equal(response.status(),200,href);
   }
   if(id===24){
    const event=page.waitForEvent('download');
    await page.locator('a[download][href="examples/analysis.py"]').click();
    const download=await event;assert.equal(download.suggestedFilename(),'analysis.py');
    const path=`${artifactDir}/${width}-analysis.py`;await download.saveAs(path);
    assert.equal(await download.failure(),null);
    assert.equal(fs.readFileSync(path,'utf8'),fs.readFileSync('examples/analysis.py','utf8'));
   }
   if([5,17,23,24,27].includes(id))await page.screenshot({path:`${artifactDir}/${width}-lesson-${id}.png`,fullPage:true});
  }
  await page.evaluate(()=>{location.hash='lesson-2';});
  await page.waitForSelector('#principal');
  assert.match(await page.locator('.widget-result').textContent(),/元/);
  await page.locator('#years').fill('0');
  assert.match(await page.locator('#widget-caption').textContent(),/有效数字/);
  await page.locator('#years').fill('10');
  assert.match(await page.locator('.widget-result').textContent(),/元/);
  for(const id of [3,8,11]) {
   await page.evaluate(id=>{location.hash=`lesson-${id}`;},id);
   await page.waitForFunction(id=>document.querySelector('#lesson').dataset.lesson===String(id),id);
   assert.match(await page.locator('.widget-result').textContent(),/元/);
   await page.locator('#principal').fill('');
   assert.match(await page.locator('#widget-caption').textContent(),/有效数字/);
  }
  await page.evaluate(()=>{location.hash='lesson-1';});
  await page.waitForFunction(()=>document.querySelector('#lesson').dataset.lesson==='1');
  const correct=await page.evaluate(()=>lessons.find(l=>l.id===1).quiz.correct);
  await page.locator(`[data-answer="${(correct+1)%3}"]`).click();
  await page.locator('.retry').click();
  await page.locator(`[data-answer="${correct}"]`).click();
  assert.match(await page.locator('.feedback').textContent(),/答对/);
  await page.locator('#complete').click();
  assert.equal(await page.evaluate(()=>location.hash),'#lesson-25');
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('zhiben-progress-v1')));
  assert.deepEqual(saved.completed.sort((a,b)=>a-b),[1,10,24]);
  await page.locator('#previous').click();
  assert.equal(await page.evaluate(()=>location.hash),'#lesson-1');
  await page.locator('#complete').click();
  await page.locator('#complete').click();
  assert.equal(await page.evaluate(()=>location.hash),'#lesson-2');
  await page.reload();
  assert.equal(await page.locator('#progress-label').textContent(),'4 / 30');
  if(width===390){
   await page.locator('.menu-toggle').click();
   await page.locator('[data-lesson="24"]').click();
   assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'),'false');
  }
  assert.deepEqual(errors,[]);
  await page.close();
 }
 const blocked=await browser.newPage();
 await blocked.addInitScript(()=>{Storage.prototype.setItem=()=>{throw Error('blocked');};Storage.prototype.getItem=()=>{throw Error('blocked');};});
 await blocked.goto(base+'/#lesson-1');
 assert.match(await blocked.locator('.progress-card small').textContent(),/本次阅读/);
 await blocked.locator('#complete').click();
 assert.equal(await blocked.evaluate(()=>location.hash),'#lesson-25');
 await blocked.close();
 console.log('30 lessons at 1440/390px, reveals, downloads, quiz retry, saved progress, widgets and blocked storage: PASS');
} finally {await browser.close();}
