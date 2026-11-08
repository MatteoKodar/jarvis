import {test,expect,type Page} from '@playwright/test';

async function enter(page:Page) {
  await page.goto('/');
  await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
  await page.getByRole('button',{name:'Öppna kontrollcentralen'}).click();
  await page.getByRole('region',{name:'Så testar vi bettingagentens arbetsflöde'}).getByRole('button',{name:'Öppna matchdemot'}).click();
  await expect(page.getByRole('heading',{name:'Från odds till avräkning.'})).toBeVisible();
  const resume=page.getByRole('button',{name:'Återuppta demot',exact:true});
  if(await resume.isVisible())await resume.click();
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeEnabled();
}

async function create(page:Page) {
  const responsePromise=page.waitForResponse(response=>response.request().method()==='POST'
    &&new URL(response.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/}).click();
  const response=await responsePromise;
  expect(response.status()).toBe(200);
  const created=await response.json();
  expect(created.id).toMatch(/^[a-f0-9]{32}$/);
  await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('jarvis-betting-demo-selected-v1'))).toBe(created.id);
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(created.id.slice(0,8));
  await expect(page.locator('.betting-progress h3')).toHaveText('Omgång skapad');
  return created.id as string;
}

async function analyze(page:Page) {
  await page.getByRole('button',{name:'Analysera de sju matcherna'}).click();
  await expect(page.locator('.betting-progress h3')).toHaveText('Analys sparad');
  await expect(page.getByTestId('demo-simulated_cost_ore')).toContainText('1,40');
}

async function approve(page:Page) {
  await page.getByRole('button',{name:'Godkänn hela låtsasbatchen'}).click();
  await expect(page.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
}

async function state(page:Page,sid:string) {
  return page.evaluate(async id=>await(await fetch('/api/betting-demo/sessions/'+id)).json(),sid);
}

test('persistent full batch workflow shows independent capital and desktop/mobile summaries',async({page})=>{
  await page.setViewportSize({width:1440,height:1100});
  await enter(page);
  const sid=await create(page);
  await expect(page.locator('.betting-match')).toHaveCount(7);
  await expect(page.getByTestId('demo-available_ore')).toContainText(/1\s*000,00/);
  await analyze(page);
  await expect(page.locator('.betting-match .badge').filter({hasText:/^Spelförslag$/})).toHaveCount(4);
  await expect(page.locator('.betting-match .badge').filter({hasText:/^Avstå$/})).toHaveCount(3);
  const saved=await state(page,sid);
  expect(saved.bets).toHaveLength(0);
  expect(saved.results).toBeUndefined();
  await page.screenshot({path:'../docs/betting-demo/2026-11-06/dator.png',fullPage:true});
  await approve(page);
  await page.reload();
  await expect(page.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
  expect((await state(page,sid)).analysis).toEqual(saved.analysis);
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await expect(page.getByTestId('demo-available_ore')).toContainText('958,60');
  await page.getByRole('button',{name:'Visa och avräkna simulerade resultat'}).click();
  await expect(page.locator('.betting-progress h3')).toHaveText('Omgången är avräknad');
  await expect(page.getByTestId('demo-capital_ore')).toContainText(/1\s*008,10/);
  await expect(page.getByTestId('demo-net_ore')).toContainText('8,10');
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('0,00');
  await expect(page.locator('.betting-match .badge').filter({hasText:/^Vinst$/})).toHaveCount(2);
  await expect(page.locator('.betting-match .badge').filter({hasText:/^Förlust$/})).toHaveCount(2);
  const before=await state(page,sid);
  await page.reload();
  await expect(page.locator('.betting-progress h3')).toHaveText('Omgången är avräknad');
  expect(await state(page,sid)).toEqual(before);
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('.sidebar')).not.toBeInViewport();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'../docs/betting-demo/2026-11-06/mobil.png',fullPage:true});
  await create(page);
  await expect(page.getByTestId('demo-available_ore')).toContainText(/1\s*000,00/);
  expect(await state(page,sid)).toEqual(before);
});

test('declining retains analysis costs and never creates stakes',async({page})=>{
  await enter(page);const sid=await create(page);await analyze(page);
  await page.getByRole('button',{name:'Avstå från batchen',exact:true}).click();
  await expect(page.locator('.betting-progress h3')).toHaveText('Du avstod från låtsasinsatserna');
  await expect(page.getByTestId('demo-available_ore')).toContainText('998,60');
  await expect(page.getByTestId('demo-simulated_cost_ore')).toContainText('1,40');
  expect((await state(page,sid)).bets).toHaveLength(0);
  await page.reload();
  await expect(page.locator('.betting-progress h3')).toHaveText('Du avstod från låtsasinsatserna');
});

test('lost simulation response preserves identity across reload and replay after pause',async({page})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  let first=true;const requests:unknown[]=[];
  await page.route('**/api/betting-demo/sessions/*/simulate',async route=>{
    requests.push(route.request().postDataJSON());
    if(first){first=false;await route.fetch();await route.abort('failed')}else await route.continue();
  });
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran'})).toBeVisible();
  await page.evaluate(async()=>{
    const auth=await(await fetch('/api/session')).json();
    await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':auth.csrf},body:JSON.stringify({state:'paused'})});
  });
  await page.reload();
  await expect(page.getByRole('region',{name:'Osäker begäran'})).toBeVisible();
  await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran'})).toHaveCount(0);
  expect(requests).toHaveLength(2);expect(requests[0]).toEqual(requests[1]);
  const saved=await state(page,sid);
  expect(saved.state).toBe('simulated');expect(saved.bets).toHaveLength(4);
  expect(saved.summary.open_stake_ore).toBe(4000);
  expect(saved.history.filter((h:{operation:string})=>h.operation==='simulate')).toHaveLength(1);
});

test('two tabs with different action identities cannot simulate twice',async({page,context})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  const second=await context.newPage();await second.goto('/#/bettingdemo');
  await expect(second.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
  const attempt=(p:Page)=>p.evaluate(async id=>{
    const auth=await(await fetch('/api/session')).json();
    const saved=await(await fetch('/api/betting-demo/sessions/'+id)).json();
    const response=await fetch('/api/betting-demo/sessions/'+id+'/simulate',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':auth.csrf},body:JSON.stringify({action_id:crypto.randomUUID(),proposal_version:saved.analysis.proposal_version,proposal_hash:saved.analysis.proposal_hash})});
    return response.status;
  },sid);
  expect((await Promise.all([attempt(page),attempt(second)])).sort()).toEqual([200,409]);
  expect((await state(page,sid)).bets).toHaveLength(4);
  await second.close();
});

type StorageFaults={get:boolean;set:boolean;remove:boolean};
const pendingKey='jarvis-betting-demo-pending-v1';

async function storageFaults(page:Page,initial:StorageFaults) {
  const install=(flags:StorageFaults)=>{
    (window as any).demoStorageFaults={...flags};
    const key='jarvis-betting-demo-pending-v1';
    const original={get:Storage.prototype.getItem,set:Storage.prototype.setItem,remove:Storage.prototype.removeItem};
    Storage.prototype.getItem=function(name:string){
      if(this===sessionStorage&&name===key&&(window as any).demoStorageFaults.get)throw new DOMException('Blocked read','SecurityError');
      return original.get.call(this,name);
    };
    Storage.prototype.setItem=function(name:string,value:string){
      if(this===sessionStorage&&name===key&&(window as any).demoStorageFaults.set)throw new DOMException('Blocked write','SecurityError');
      return original.set.call(this,name,value);
    };
    Storage.prototype.removeItem=function(name:string){
      if(this===sessionStorage&&name===key&&(window as any).demoStorageFaults.remove)throw new DOMException('Blocked removal','SecurityError');
      return original.remove.call(this,name);
    };
  };
  await page.addInitScript(install,initial);
  await page.evaluate(install,initial);
}

async function readFaults(page:Page,target='') {
  const fault={mode:'none' as 'none'|'catalog'|'detail'|'missing'|'empty',target};
  await page.route('**/api/betting-demo/sessions**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(route.request().method()!=='GET'){await route.continue();return}
    const catalog=path==='/api/betting-demo/sessions';
    if((catalog&&fault.mode==='catalog')||(!catalog&&fault.mode==='detail'&&path.endsWith('/'+fault.target))){
      await route.fulfill({status:503,json:{detail:'Styrt läsfel'}});return;
    }
    if(catalog&&fault.mode==='empty'){await route.fulfill({json:{sessions:[]}});return}
    if(catalog&&fault.mode==='missing'){
      const response=await route.fetch();const saved=await response.json();
      await route.fulfill({response,json:{...saved,sessions:saved.sessions.filter((s:{id:string})=>s.id!==fault.target)}});return;
    }
    await route.continue();
  });
  return fault;
}

async function expectConfirmedBlock(page:Page) {
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Försök samma begäran igen'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeDisabled();
  for(const button of await page.locator('.betting-history button').all())await expect(button).toBeDisabled();
  await expect(page.getByRole('button',{name:'Hämta sparat läge',exact:true})).toBeEnabled();
}

for(const failure of ['catalog','detail'] as const)test(`confirmed simulation with ${failure} failure only recovers by reading the original batch`,async({page})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  const fault=await readFaults(page,sid);
  const posts:{path:string;body:unknown}[]=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/betting-demo/'))posts.push({path:new URL(request.url()).pathname,body:request.postDataJSON()})});
  fault.mode=failure;
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expectConfirmedBlock(page);
  await expect(page.getByRole('alert')).toContainText('Backend har bekräftat begäran');
  await expect(page.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
  await expect(page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true})).toBeDisabled();
  expect(posts).toHaveLength(1);
  expect(posts[0].path).toBe(`/api/betting-demo/sessions/${sid}/simulate`);
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  expect(JSON.parse(original!)).toEqual({path:`/betting-demo/sessions/${sid}/simulate`,body:posts[0].body});
  const backend=await(await page.request.get('/api/betting-demo/sessions/'+sid)).json();
  expect(backend.bets).toHaveLength(4);
  expect(backend.summary.open_stake_ore).toBe(4000);
  expect(backend.history.filter((h:{operation:string})=>h.operation==='simulate')).toHaveLength(1);
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Styrt läsfel');
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('alert')).toContainText('Styrt läsfel');
  await expectConfirmedBlock(page);
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  expect(posts).toHaveLength(1);
  fault.mode='none';
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await expect(page.getByTestId('demo-available_ore')).toContainText('958,60');
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeDisabled();
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeEnabled();
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBeNull();
  expect(posts).toHaveLength(1);
  expect(await state(page,sid)).toEqual(backend);
});

test('first confirmed create with unreadable catalog offers recovery without a displayed session and requires local cleanup',async({page})=>{
  const fault=await readFaults(page);fault.mode='empty';
  await enter(page);
  await expect(page.locator('.betting-progress')).toHaveCount(0);
  await storageFaults(page,{get:false,set:false,remove:true});
  const posts:unknown[]=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/betting-demo/'))posts.push(request.postDataJSON())});
  fault.mode='catalog';
  const responsePromise=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:'Skapa demo-omgång',exact:true}).click();
  const response=await responsePromise;expect(response.status()).toBe(200);
  const saved=await response.json();fault.target=saved.id;
  await expectConfirmedBlock(page);
  await expect(page.locator('.betting-progress')).toHaveCount(0);
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Styrt läsfel');
  await expectConfirmedBlock(page);
  fault.mode='none';
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(saved.id.slice(0,8));
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeDisabled();
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('alert')).toContainText('kan inte rensa den sparade begäran');
  await expectConfirmedBlock(page);
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  await page.evaluate(()=>{(window as any).demoStorageFaults.remove=false});
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeEnabled();
  expect(posts).toHaveLength(1);
  expect(JSON.parse(original!).body).toEqual(posts[0]);
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBeNull();
  expect((await state(page,saved.id)).history.filter((h:{operation:string})=>h.operation==='create')).toHaveLength(1);
});

test('confirmed create recovers its exact round despite missing catalog entry and a newer round in another tab',async({page,context})=>{
  await enter(page);const previous=await create(page);
  const fault=await readFaults(page);fault.mode='catalog';
  const posts:unknown[]=[];const details:string[]=[];
  page.on('request',request=>{
    const path=new URL(request.url()).pathname;
    if(request.method()==='POST'&&path.startsWith('/api/betting-demo/'))posts.push(request.postDataJSON());
    if(request.method()==='GET'&&/^\/api\/betting-demo\/sessions\/[a-f0-9]{32}$/.test(path))details.push(path);
  });
  const responsePromise=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:'Skapa ny demo-omgång',exact:true}).click();
  const response=await responsePromise;expect(response.status()).toBe(200);
  const saved=await response.json();fault.target=saved.id;
  expect(saved.id).not.toBe(previous);
  await expectConfirmedBlock(page);
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(previous.slice(0,8));
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeDisabled();
  const second=await context.newPage();await second.goto('/#/bettingdemo');
  await expect(second.locator('.betting-progress .eyebrow')).toContainText(saved.id.slice(0,8));
  const newer=await create(second);expect(newer).not.toBe(saved.id);
  fault.mode='missing';details.length=0;
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('alert')).toContainText('omgången saknas');
  await expectConfirmedBlock(page);
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(previous.slice(0,8));
  expect(details).toHaveLength(0);
  fault.mode='detail';
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Styrt läsfel');
  await expectConfirmedBlock(page);
  expect(details).toEqual(['/api/betting-demo/sessions/'+saved.id]);
  fault.mode='none';
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(saved.id.slice(0,8));
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeEnabled();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toHaveCount(0);
  expect(details).toEqual(Array(2).fill('/api/betting-demo/sessions/'+saved.id));
  expect(posts).toHaveLength(1);
  expect((await state(page,previous)).state).toBe('created');
  expect((await state(page,saved.id)).state).toBe('created');
  expect((await state(page,newer)).state).toBe('created');
  await second.close();
});

test('reloaded confirmed create cannot clear its request by reading the previously selected round',async({page})=>{
  await enter(page);const previous=await create(page);
  const fault=await readFaults(page);fault.mode='catalog';
  const posts:{path:string;body:unknown}[]=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/betting-demo/'))posts.push({path:new URL(request.url()).pathname,body:request.postDataJSON()})});
  const createdPromise=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:'Skapa ny demo-omgång',exact:true}).click();
  const createdResponse=await createdPromise;expect(createdResponse.status()).toBe(200);
  const created=await createdResponse.json();expect(created.id).not.toBe(previous);
  await expectConfirmedBlock(page);
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  expect(JSON.parse(original!)).toEqual({path:'/betting-demo/sessions',body:posts[0].body});
  expect(await page.evaluate(()=>sessionStorage.getItem('jarvis-betting-demo-selected-v1'))).toBe(previous);
  fault.mode='none';
  await page.reload();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(previous.slice(0,8));
  const close=page.getByRole('button',{name:'Stäng begäran efter kontroll'});
  await expect(close).toBeDisabled();
  await close.evaluate((button:HTMLButtonElement)=>button.click());
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByRole('button',{name:'Hämta sparat läge',exact:true})).toBeEnabled();
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(previous.slice(0,8));
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  await expect(close).toBeDisabled();
  await expect(page.getByRole('button',{name:'Skapa ny demo-omgång',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeDisabled();
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  expect(posts).toHaveLength(1);
  const replayPromise=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
  const replayResponse=await replayPromise;expect(replayResponse.status()).toBe(200);
  expect((await replayResponse.json()).id).toBe(created.id);
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(created.id.slice(0,8));
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Skapa ny demo-omgång',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeEnabled();
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBeNull();
  expect(posts).toHaveLength(2);expect(posts[1]).toEqual(posts[0]);
  expect((await state(page,created.id)).history.filter((h:{operation:string})=>h.operation==='create')).toHaveLength(1);
  expect((await state(page,previous)).state).toBe('created');
});

test('stale approved tab recovers from a simulation conflict by reading its original round without another POST',async({page,context})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  const second=await context.newPage();await second.goto('/#/bettingdemo');
  await expect(second.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
  const posts:{path:string;body:Record<string,unknown>}[]=[];
  context.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/betting-demo/'))posts.push({path:new URL(request.url()).pathname,body:request.postDataJSON()})});
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await expect(second.locator('.betting-progress h3')).toHaveText('Batchen godkänd');
  const conflictPromise=second.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname===`/api/betting-demo/sessions/${sid}/simulate`);
  await second.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  expect((await conflictPromise).status()).toBe(409);
  await expect(second.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  await expect(second.getByRole('button',{name:'Stäng begäran efter kontroll'})).toBeEnabled();
  await expect(second.getByRole('button',{name:'Skapa ny demo-omgång',exact:true})).toBeDisabled();
  const original=await second.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  expect(posts).toHaveLength(2);
  expect(posts.map(post=>post.path)).toEqual(Array(2).fill(`/api/betting-demo/sessions/${sid}/simulate`));
  expect(posts[1].body.action_id).not.toBe(posts[0].body.action_id);
  expect(JSON.parse(original!)).toEqual({path:`/betting-demo/sessions/${sid}/simulate`,body:posts[1].body});
  const backend=await state(page,sid);
  expect(backend.bets).toHaveLength(4);
  expect(backend.summary.open_stake_ore).toBe(4000);
  expect(backend.history.filter((h:{operation:string})=>h.operation==='simulate')).toHaveLength(1);
  await second.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(second.getByRole('button',{name:'Hämta sparat läge',exact:true})).toBeEnabled();
  await expect(second.locator('.betting-progress .eyebrow')).toContainText(sid.slice(0,8));
  await expect(second.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await expect(second.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeDisabled();
  expect(await second.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  await second.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(second.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  await expect(second.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeEnabled();
  await expect(second.getByRole('button',{name:'Skapa ny demo-omgång',exact:true})).toBeEnabled();
  expect(await second.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBeNull();
  expect(posts).toHaveLength(2);
  expect(await state(page,sid)).toEqual(backend);
  await second.close();
});

test('failed pending storage write sends no POST and leaves the action available',async({page})=>{
  await enter(page);
  await storageFaults(page,{get:false,set:true,remove:false});
  const posts:string[]=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/betting-demo/'))posts.push(request.url())});
  const createButton=page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/});
  await createButton.click();
  await expect(page.getByRole('alert')).toContainText('Ingen begäran skickades');
  expect(posts).toHaveLength(0);
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBeNull();
  await expect(createButton).toBeEnabled();
  await page.evaluate(()=>{(window as any).demoStorageFaults.set=false});
  await create(page);
  expect(posts).toHaveLength(1);
});

test('confirmed create with failed local cleanup displays the correct round and replays its original identity',async({page})=>{
  await enter(page);
  const previous=await create(page);
  await storageFaults(page,{get:false,set:false,remove:true});
  const requests:unknown[]=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/betting-demo/sessions'))requests.push(request.postDataJSON())});
  const responsePromise=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/api/betting-demo/sessions'));
  await page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/}).click();
  const saved=await(await responsePromise).json();
  expect(saved.id).not.toBe(previous);
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  await expect(page.locator('.betting-progress .eyebrow')).toContainText(saved.id.slice(0,8));
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeDisabled();
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  expect(JSON.parse(original!).body).toEqual(requests[0]);
  await page.reload();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  await page.evaluate(()=>{(window as any).demoStorageFaults.remove=false});
  await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeEnabled();
  expect(requests).toHaveLength(2);expect(requests[1]).toEqual(requests[0]);
  expect((await state(page,saved.id)).history.filter((h:{operation:string})=>h.operation==='create')).toHaveLength(1);
});

test('unreadable pending at startup blocks new writes and explicit storage recovery never resends automatically',async({page})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  const requests:unknown[]=[];let first=true;
  await page.route('**/api/betting-demo/sessions/*/simulate',async route=>{
    requests.push(route.request().postDataJSON());
    if(first){first=false;await route.fetch();await route.abort('failed')}else await route.continue();
  });
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  await storageFaults(page,{get:true,set:false,remove:false});
  await page.reload();
  await expect(page.getByRole('region',{name:'Lagringskontroll krävs'})).toBeVisible();
  await expect(page.locator('.betting-progress h3')).toHaveText('Låtsasinsatserna är öppna');
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeDisabled();
  expect(requests).toHaveLength(1);
  await page.evaluate(()=>{(window as any).demoStorageFaults.get=false});
  await page.getByRole('button',{name:'Kontrollera sessionslagringen'}).click();
  await expect(page.getByRole('region',{name:'Lagringskontroll krävs'})).toHaveCount(0);
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  expect(requests).toHaveLength(1);
  await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
  expect(requests).toHaveLength(2);expect(requests[1]).toEqual(requests[0]);
  const saved=await state(page,sid);
  expect(saved.bets).toHaveLength(4);
  expect(saved.history.filter((h:{operation:string})=>h.operation==='simulate')).toHaveLength(1);
});

test('lost simulation followed by confirmed replay with cleanup failure keeps one batch and permits read-only cleanup',async({page})=>{
  await enter(page);const sid=await create(page);await analyze(page);await approve(page);
  await storageFaults(page,{get:false,set:false,remove:true});
  const requests:unknown[]=[];let first=true;
  await page.route('**/api/betting-demo/sessions/*/simulate',async route=>{
    requests.push(route.request().postDataJSON());
    if(first){first=false;await route.fetch();await route.abort('failed')}else await route.continue();
  });
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
  const original=await page.evaluate(key=>sessionStorage.getItem(key),pendingKey);
  await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toBeVisible();
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeDisabled();
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  await page.getByRole('button',{name:'Hämta sparat läge',exact:true}).click();
  await expect(page.getByRole('button',{name:'Hämta sparat läge',exact:true})).toBeEnabled();
  expect(requests).toHaveLength(2);expect(requests[1]).toEqual(requests[0]);
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('kan inte rensa den sparade begäran');
  expect(await page.evaluate(key=>sessionStorage.getItem(key),pendingKey)).toBe(original);
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeDisabled();
  expect(requests).toHaveLength(2);
  await page.evaluate(()=>{(window as any).demoStorageFaults.remove=false});
  await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
  await expect(page.getByRole('region',{name:'Bekräftad begäran',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeEnabled();
  expect(requests).toHaveLength(2);
  const saved=await state(page,sid);
  expect(saved.bets).toHaveLength(4);
  expect(saved.summary.open_stake_ore).toBe(4000);
  expect(saved.history.filter((h:{operation:string})=>h.operation==='simulate')).toHaveLength(1);
});
