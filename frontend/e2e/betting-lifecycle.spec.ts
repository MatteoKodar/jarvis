import {test,expect,type Page} from '@playwright/test';

const key='jarvis-betting-demo-pending-v1';
const selectedKey='jarvis-betting-demo-selected-v1';
function gate(){
  let release!:()=>void;
  const promise=new Promise<void>((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Test gate was not released')),15000);
    release=()=>{clearTimeout(timer);resolve()};
  });
  return {promise,release};
}

async function enter(page:Page){
  await page.goto('/');
  await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
  await page.getByRole('button',{name:'Öppna kontrollcentralen'}).click();
  await page.getByRole('button',{name:'Bettingdemo',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Från odds till avräkning.'})).toBeVisible();
  const resume=page.getByRole('button',{name:'Återuppta demot',exact:true});
  if(await resume.isVisible())await resume.click();
  await expect(page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/})).toBeEnabled();
}
async function remount(page:Page){
  await page.getByRole('button',{name:'Översikt',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Från odds till avräkning.'})).toHaveCount(0);
  await page.getByRole('button',{name:'Bettingdemo',exact:true}).click();
  await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
}
async function armOldReadBarrier(page:Page,sid:string){
  await page.evaluate(id=>{
    const nativeFetch=window.fetch.bind(window);
    (window as any).lateDemoReadFinished=false;
    (window as any).lateDemoDetailReads=0;
    window.fetch=async(...args:Parameters<typeof fetch>)=>{
      const response=await nativeFetch(...args);
      if(new URL(String(args[0]),location.href).pathname==='/api/betting-demo/sessions/'+id){
        (window as any).lateDemoDetailReads++;
        if(response.status!==200)throw new Error('The old detail read must succeed');
        const nativeJson=response.json.bind(response);
        response.json=async()=>{
          const result=await nativeJson();
          // This task runs after the resolved JSON's await continuations, including forget().
          setTimeout(()=>{(window as any).lateDemoReadFinished=true},0);
          return result;
        };
      }
      return response;
    };
  },sid);
}
async function pending(page:Page){return page.evaluate(k=>sessionStorage.getItem(k),key)}

test('late unmounted create cannot erase a newer create recovery record',async({page})=>{
  await enter(page);
  const before=await(await page.request.get('/api/betting-demo/sessions')).json();
  const old=gate(), newer=gate(), oldCommitted=gate(), newerCommitted=gate();
  let count=0,oldId='',newId='';const bodies:any[]=[];
  await page.route('**/api/betting-demo/sessions',async route=>{
    if(route.request().method()!=='POST'){await route.continue();return}
    bodies.push(route.request().postDataJSON());count++;
    if(count===1){const response=await route.fetch();oldId=(await response.json()).id;oldCommitted.release();await old.promise;await route.fulfill({response})}
    else if(count===3){const response=await route.fetch();newId=(await response.json()).id;newerCommitted.release();await newer.promise;await route.abort('failed')}
    else await route.continue();
  });
  try{
    await page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/}).click();await oldCommitted.promise;
    await remount(page);
    await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
    expect(bodies[1]).toEqual(bodies[0]);await expect.poll(()=>pending(page)).toBeNull();
    await expect(page.getByRole('button',{name:'Skapa ny demo-omgång'})).toBeEnabled();
    await page.getByRole('button',{name:'Skapa ny demo-omgång'}).click();await newerCommitted.promise;
    const record=await pending(page);expect(JSON.parse(record!).body).toEqual(bodies[2]);
    await armOldReadBarrier(page,oldId);old.release();
    await page.waitForFunction(()=>(window as any).lateDemoReadFinished===true);
    expect(await page.evaluate(()=>(window as any).lateDemoDetailReads)).toBe(1);
    expect(await pending(page)).toBe(record);
    newer.release();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Försök samma begäran igen'})).toBeEnabled();
    await page.reload();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
    expect(await pending(page)).toBe(record);
    await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
    await expect.poll(()=>pending(page)).toBeNull();
    expect(bodies).toHaveLength(4);expect(bodies[3]).toEqual(bodies[2]);
    expect(await page.evaluate(k=>sessionStorage.getItem(k),selectedKey)).toBe(newId);
    const after=await(await page.request.get('/api/betting-demo/sessions')).json();
    expect(after.sessions.length).toBe(before.sessions.length+2);
    expect(after.sessions.filter((s:any)=>s.id===oldId||s.id===newId)).toHaveLength(2);
  }finally{old.release();newer.release();oldCommitted.release();newerCommitted.release();await page.unrouteAll({behavior:'wait'})}
});

test('late unmounted simulation cannot erase the pending settlement of the same round',async({page})=>{
  await enter(page);
  await page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/}).click();
  await expect(page.getByRole('button',{name:'Analysera de sju matcherna'})).toBeEnabled();
  await page.getByRole('button',{name:'Analysera de sju matcherna'}).click();
  await expect(page.getByRole('button',{name:'Godkänn hela låtsasbatchen'})).toBeEnabled();
  await page.getByRole('button',{name:'Godkänn hela låtsasbatchen'}).click();
  await expect(page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true})).toBeEnabled();
  const sid=(await page.evaluate(k=>sessionStorage.getItem(k),selectedKey))!;
  const old=gate(),newer=gate(),oldCommitted=gate(),newerCommitted=gate();
  const calls:{path:string;body:any}[]=[];
  await page.route('**/api/betting-demo/sessions/*/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(route.request().method()!=='POST'){await route.continue();return}
    calls.push({path,body:route.request().postDataJSON()});
    if(path.endsWith('/simulate')){const response=await route.fetch();oldCommitted.release();await old.promise;await route.fulfill({response})}
    else if(path.endsWith('/settle')&&calls.filter(c=>c.path.endsWith('/settle')).length===1){
      await route.fetch();newerCommitted.release();await newer.promise;await route.abort('failed');
    }else await route.continue();
  });
  try{
    await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();await oldCommitted.promise;
    await remount(page);
    await page.getByRole('button',{name:'Stäng begäran efter kontroll'}).click();
    await expect(page.getByRole('button',{name:'Visa och avräkna simulerade resultat'})).toBeEnabled();
    await page.getByRole('button',{name:'Visa och avräkna simulerade resultat'}).click();await newerCommitted.promise;
    const record=await pending(page);expect(JSON.parse(record!).body).toEqual(calls[1].body);
    await armOldReadBarrier(page,sid);old.release();
    await page.waitForFunction(()=>(window as any).lateDemoReadFinished===true);
    expect(await page.evaluate(()=>(window as any).lateDemoDetailReads)).toBe(1);
    expect(await pending(page)).toBe(record);
    newer.release();
    await expect(page.getByRole('button',{name:'Försök samma begäran igen'})).toBeEnabled();
    await page.reload();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toBeVisible();
    expect(await pending(page)).toBe(record);
    await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
    await expect(page.getByRole('region',{name:'Osäker begäran',exact:true})).toHaveCount(0);
    await expect.poll(()=>pending(page)).toBeNull();
    expect(calls).toHaveLength(3);expect(calls[2]).toEqual(calls[1]);
    const saved=await(await page.request.get('/api/betting-demo/sessions/'+sid)).json();
    expect(saved.state).toBe('settled');expect(saved.bets).toHaveLength(4);
    expect(saved.history.filter((h:any)=>h.operation==='simulate')).toHaveLength(1);
    expect(saved.history.filter((h:any)=>h.operation==='settle')).toHaveLength(1);
    expect(saved.summary.capital_ore).toBe(100810);
  }finally{old.release();newer.release();oldCommitted.release();newerCommitted.release();await page.unrouteAll({behavior:'wait'})}
});
