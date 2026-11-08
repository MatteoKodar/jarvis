import {test,expect,type Page,type Route} from '@playwright/test';
import {readFileSync} from 'node:fs';
import path from 'node:path';

const input=JSON.parse(readFileSync(new URL('../../tests/fixtures/paper_input_v1.json',import.meta.url),'utf8'));
const results=JSON.parse(readFileSync(new URL('../../tests/fixtures/paper_results_v1.json',import.meta.url),'utf8'));
const base='/api/betting-demo/paper-replay/';
const file=(name:string,data:unknown)=>({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data),'utf8')});

async function login(page:Page){
  await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
  await page.getByRole('button',{name:'Öppna kontrollcentralen'}).click();
}
async function enter(page:Page){
  await page.goto('/');await login(page);await open(page);
}
async function open(page:Page){
  await page.getByRole('button',{name:'Bettingdemo',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Från odds till avräkning.'})).toBeVisible();
  const resume=page.getByRole('button',{name:'Återuppta demot',exact:true});if(await resume.isVisible())await resume.click();
  const panel=page.getByTestId('paper-replay');await panel.locator('summary').first().click();
  await expect(panel.getByRole('button',{name:'Ladda påhittat fil-exempel'})).toBeVisible();
}
async function reviewExample(page:Page){
  const panel=page.getByTestId('paper-replay');await panel.getByRole('button',{name:'Ladda påhittat fil-exempel'}).click();
  const response=page.waitForResponse(r=>new URL(r.url()).pathname===base+'review'&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Granska filens underlag'}).click();
  const r=await response;expect(r.status()).toBe(200);const body=await r.json();
  await expect(page.getByTestId('paper-review')).toBeVisible();return body;
}
async function holdFirst(page:Page,endpoint:string){
  let release!:()=>void,received!:()=>void,done!:()=>void;
  const gate=new Promise<void>(resolve=>release=resolve),seen=new Promise<void>(resolve=>received=resolve),finished=new Promise<void>(resolve=>done=resolve);
  let first=true;
  await page.route('**'+base+endpoint,async(route:Route)=>{
    if(!first){await route.continue();return}first=false;
    const response=await route.fetch();received();await gate;
    try{await route.fulfill({response})}catch{/* Explicit abort after generation change is expected. */}finally{done()}
  });
  return {seen,release,finished};
}

test('real file workflow reviews all roles, evaluates separate results and exports matching hashes',async({page},info)=>{
  await page.setViewportSize({width:1440,height:1100});await enter(page);
  const panel=page.getByTestId('paper-replay');await expect(page.getByLabel('Välj resultat JSON')).toBeDisabled();
  const request=page.waitForRequest(r=>new URL(r.url()).pathname===base+'review');const report=await reviewExample(page);
  expect((await request).postDataJSON().input).toEqual(input);
  for(const role of ['researcher','analyst','finance','critic'])await expect(page.getByTestId('paper-step-'+role)).toBeVisible();
  await expect(page.getByTestId('paper-step-analyst')).toContainText('2 grundförslag');
  await expect(page.getByTestId('paper-quality-paper-test-3')).toContainText('Saknad tid');
  await expect(page.getByTestId('paper-quality-paper-test-4')).toContainText('Saknad tid');
  await expect(page.getByTestId('paper-quality-paper-test-5')).toContainText('Färre än fyra prisgodkända');
  await expect(page.getByTestId('paper-quality-paper-test-6')).toContainText('För nära avspark');
  await expect(panel).toContainText('Påstått ursprung');await expect(panel).toContainText('aldrig en rekommendation');
  await expect(panel.locator('[href], [src]')).toHaveCount(0);
  const output=process.env.JARVIS_REVIEW_EVIDENCE_DIR??info.outputDir;
  const cards=page.getByTestId('paper-review').locator('.review-steps');
  await cards.scrollIntoViewIfNeeded();await page.evaluate(()=>window.scrollBy(0,-80));
  await cards.screenshot({path:path.join(output,'paper-review-desktop.png')});
  for(const item of await panel.locator('.paper-quality>details').all())await item.locator('summary').click();
  await page.setViewportSize({width:375,height:812});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth)).toBeTruthy();
  const tables=panel.locator('.paper-quality>details[open] table');await expect(tables).toHaveCount(7);
  for(const table of await tables.all()){
    await expect(table).toBeVisible();
    expect(await table.evaluate(el=>el.clientWidth>0&&el.scrollWidth<=el.clientWidth&&el.getBoundingClientRect().right<=el.parentElement!.getBoundingClientRect().right+1)).toBeTruthy();
  }
  await page.setViewportSize({width:375,height:1800});await cards.scrollIntoViewIfNeeded();await page.evaluate(()=>window.scrollBy(0,-80));
  await cards.screenshot({path:path.join(output,'paper-review-mobile.png')});await page.setViewportSize({width:375,height:812});
  await panel.getByRole('button',{name:'Ladda påhittade resultat',exact:true}).click();
  const evaluated=page.waitForResponse(r=>new URL(r.url()).pathname===base+'evaluate');
  await panel.getByRole('button',{name:'Utvärdera samma underlag'}).click();const e=await(await evaluated).json();
  await expect(page.getByTestId('paper-primary')).toContainText('3,35');await expect(page.getByTestId('paper-baseline')).toContainText('8,20');
  expect(e.report_hash).toBe(report.report_hash);
  const event=page.waitForEvent('download');await panel.getByRole('button',{name:'Exportera filgranskning JSON'}).click();
  const download=await event;expect(download.suggestedFilename()).toBe(`paper-review-${input.dataset_id}-${report.report_hash.slice(0,12)}.json`);
  const payload=JSON.parse(readFileSync((await download.path())!,'utf8'));
  expect(payload.input).toEqual(input);expect(payload.results).toEqual(results);expect(payload.origin).toBe('synthetic_fixture');
  expect(payload.report_hash).toBe(report.report_hash);expect(payload.input_hash).toBe(report.input_hash);
  expect(payload.policy_hash).toBe(report.contract.policy_hash);expect(payload.evaluation.primary.summary.net_ore).toBe(335);
  expect(payload.notice).toContain('Osignerad');expect(payload.limitations).toHaveLength(5);
  expect(payload.limitations).toContain('Ingen språkmodell, inga dataleverantörsanrop och inga riktiga insatser.');
  await expect(panel.locator('[href], [src]')).toHaveCount(0);
});

test('late review cannot restore a replaced input generation',async({page})=>{
  await enter(page);const panel=page.getByTestId('paper-replay');await panel.getByRole('button',{name:'Ladda påhittat fil-exempel'}).click();
  const held=await holdFirst(page,'review');await panel.getByRole('button',{name:'Granska filens underlag'}).click();await held.seen;
  const changed=structuredClone(input);changed.dataset_id='replacement-input';
  const aborted=page.waitForEvent('requestfailed',{predicate:r=>new URL(r.url()).pathname===base+'review'});
  await page.getByLabel('Välj matchdata JSON').setInputFiles(file('replacement.json',changed));
  expect((await aborted).failure()?.errorText).toBe('net::ERR_ABORTED');
  await expect(panel.getByTestId('paper-file-state')).toContainText('replacement.json');held.release();await held.finished;
  await expect(page.getByTestId('paper-review')).toHaveCount(0);await expect(page.getByLabel('Välj resultat JSON')).toBeDisabled();
  await panel.getByRole('button',{name:'Granska filens underlag'}).click();
  await expect(page.getByTestId('paper-review').getByRole('heading',{name:'replacement-input',exact:true})).toBeVisible();
});

test('new result file discards a late evaluation and keeps the same review',async({page})=>{
  await enter(page);const report=await reviewExample(page),panel=page.getByTestId('paper-replay');
  await panel.getByRole('button',{name:'Ladda påhittade resultat',exact:true}).click();const held=await holdFirst(page,'evaluate');
  await panel.getByRole('button',{name:'Utvärdera samma underlag'}).click();await held.seen;
  const changed=structuredClone(results);for(const r of changed.records){r.home_score=0;r.away_score=1}
  await page.getByLabel('Välj resultat JSON').setInputFiles(file('all-losses.json',changed));
  await expect(panel.getByTestId('paper-file-state')).toContainText('all-losses.json');held.release();await held.finished;
  await expect(page.getByTestId('paper-evaluation')).toHaveCount(0);await expect(page.getByTestId('paper-review')).toContainText(report.report_hash);
  await panel.getByRole('button',{name:'Utvärdera samma underlag'}).click();
  await expect(page.getByTestId('paper-primary')).toContainText(/[−-]21,40/);await expect(page.getByTestId('paper-baseline')).toContainText(/[−-]31,40/);
});

test('new input discards a late evaluation and clears the old results',async({page})=>{
  await enter(page);await reviewExample(page);const panel=page.getByTestId('paper-replay');
  await panel.getByRole('button',{name:'Ladda påhittade resultat',exact:true}).click();const held=await holdFirst(page,'evaluate');
  await panel.getByRole('button',{name:'Utvärdera samma underlag'}).click();await held.seen;
  const changed=structuredClone(input);changed.dataset_id='new-generation';await page.getByLabel('Välj matchdata JSON').setInputFiles(file('new-generation.json',changed));
  await expect(panel.getByTestId('paper-file-state')).toHaveText('new-generation.json');held.release();await held.finished;
  await expect(page.getByTestId('paper-evaluation')).toHaveCount(0);await expect(page.getByTestId('paper-review')).toHaveCount(0);
  await expect(panel.getByRole('button',{name:'Utvärdera samma underlag'})).toBeDisabled();
});

test('logout unmounts a pending review and login starts with empty file state',async({page})=>{
  await enter(page);const panel=page.getByTestId('paper-replay');await panel.getByRole('button',{name:'Ladda påhittat fil-exempel'}).click();
  const held=await holdFirst(page,'review');await panel.getByRole('button',{name:'Granska filens underlag'}).click();await held.seen;
  await page.locator('button.profile').click();await expect(page.getByLabel('Ägarlösenord')).toBeVisible();
  held.release();await held.finished;await login(page);await open(page);
  await expect(page.getByTestId('paper-review')).toHaveCount(0);await expect(page.getByTestId('paper-file-state')).toHaveText('Ingen indata vald.');
});

for(const change of ['revoked','changed'])test(`session ${change} after a held response clears all file state`,async({page})=>{
  await enter(page);let checks=0;
  await page.route('**/api/session',async route=>{
    checks++;
    if(checks===1){await route.continue();return}
    if(change==='revoked')await route.fulfill({status:401,json:{detail:'Logga in som ägare.'}});
    else await route.fulfill({json:{csrf:'different-test-only-session'}});
  });
  const panel=page.getByTestId('paper-replay');await panel.getByRole('button',{name:'Ladda påhittat fil-exempel'}).click();
  const held=await holdFirst(page,'review');await panel.getByRole('button',{name:'Granska filens underlag'}).click();await held.seen;
  held.release();await held.finished;
  await expect(panel.getByRole('alert')).toContainText('Ägarinloggningen');
  await expect(page.getByTestId('paper-review')).toHaveCount(0);await expect(page.getByTestId('paper-evaluation')).toHaveCount(0);
  await expect(page.getByTestId('paper-file-state')).toHaveText('Ingen indata vald.');
  await expect(panel.getByRole('button',{name:'Granska filens underlag'})).toBeDisabled();
});

test('file bounds, invalid UTF8 and BOM fail before sending a request',async({page})=>{
  await enter(page);const panel=page.getByTestId('paper-replay'),posts:string[]=[];
  page.on('request',r=>{if(new URL(r.url()).pathname.startsWith(base))posts.push(r.url())});
  await page.getByLabel('Välj matchdata JSON').setInputFiles({name:'large.json',mimeType:'application/json',buffer:Buffer.alloc(36001,32)});
  await expect(panel.getByRole('alert')).toContainText('36000');expect(posts).toEqual([]);
  await page.getByLabel('Välj matchdata JSON').setInputFiles({name:'bad-utf8.json',mimeType:'application/json',buffer:Buffer.from([0xc3,0x28])});
  await expect(panel.getByRole('alert')).toContainText('giltig JSON');expect(posts).toEqual([]);
  await page.getByLabel('Välj matchdata JSON').setInputFiles({name:'bom.json',mimeType:'application/json',buffer:Buffer.from([239,187,191,123,125])});
  await expect(panel.getByRole('alert')).toContainText('BOM');expect(posts).toEqual([]);
  await reviewExample(page);expect(posts).toHaveLength(1);
  await page.getByLabel('Välj resultat JSON').setInputFiles({name:'large-results.json',mimeType:'application/json',buffer:Buffer.alloc(9001,32)});
  await expect(panel.getByRole('alert')).toContainText('9000');expect(posts).toHaveLength(1);
  await expect(panel.getByRole('button',{name:'Utvärdera samma underlag'})).toBeDisabled();
});

test('manual provenance and source text never become HTML or links',async({page})=>{
  await enter(page);const changed=structuredClone(input);changed.origin='manual_unverified';changed.source.name='<img src=x onerror=alert(1)>';
  changed.source.permission_note='Eget <script>window.injected=true</script>';
  await page.getByLabel('Välj matchdata JSON').setInputFiles(file('manual.json',changed));
  await page.getByTestId('paper-replay').getByRole('button',{name:'Granska filens underlag'}).click();
  const report=page.getByTestId('paper-review');await expect(report).toContainText('Manuellt angivet · ej oberoende verifierat');
  await expect(report).toContainText(changed.source.name);await expect(report).toContainText(changed.source.permission_note);
  await expect(report.locator('img,script,[href],[src]')).toHaveCount(0);
});

test('stopped state disables new calculations while the existing review remains readable',async({page})=>{
  await enter(page);await reviewExample(page);const panel=page.getByTestId('paper-replay');
  const session=await(await page.request.get('/api/session')).json();
  const stopped=await page.request.post('/api/control',{data:{state:'stopped'},headers:{origin:new URL(page.url()).origin,'x-csrf-token':session.csrf}});
  expect(stopped.status()).toBe(200);
  await expect(panel.getByRole('button',{name:'Granska filens underlag'})).toBeDisabled({timeout:12000});
  await expect(panel.getByRole('button',{name:'Utvärdera samma underlag'})).toBeDisabled();await expect(page.getByTestId('paper-review')).toBeVisible();
});

test('void and missing outcomes remain visibly open without complete ROI',async({page})=>{
  await enter(page);await reviewExample(page);const out=structuredClone(results);
  out.records[0].status='void';out.records[0].home_score=null;out.records[0].away_score=null;
  out.records=out.records.filter((r:{event_id:string})=>r.event_id!=='paper-test-7');
  await page.getByLabel('Välj resultat JSON').setInputFiles(file('void-pending.json',out));
  await page.getByTestId('paper-replay').getByRole('button',{name:'Utvärdera samma underlag'}).click();
  for(const name of ['paper-primary','paper-baseline']){
    const track=page.getByTestId(name);await expect(track).toContainText('1 makulerade, 1 öppna');
    await expect(track).toContainText('saknas – öppna insatser eller ingen insats');
  }
  await expect(page.getByTestId('paper-primary')).toContainText('10,00');
});

test('paper JSX has no source links, raw HTML or legacy core reason rendering',()=>{
  const code=readFileSync(new URL('../src/PaperReplay.tsx',import.meta.url),'utf8');
  expect(code).not.toMatch(/dangerouslySetInnerHTML|window\.open|decision\.reason|explain\(/);
  expect(code).not.toMatch(/<(?:a|img)\b[^>]*(?:href|src)\s*=/);
});
