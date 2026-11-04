import {test,expect,type Page} from '@playwright/test';

async function login(page:Page){
 await page.goto('/');
 await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
 await page.getByRole('button',{name:'Öppna kontrollcentralen'}).click();
 await expect(page.getByRole('heading',{name:'Fotbollsanalys före riktiga insatser.'})).toBeVisible();
}

test('football focus replaces legacy research navigation and old hashes fall back safely',async({page})=>{
 await login(page);
 await expect(page.getByRole('button',{name:'Research',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Researchlabb',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Oddslabb',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Dokument',exact:true})).toBeVisible();
 for(const legacy of ['research','researchlabb']){
  await page.goto('/#/'+legacy);
  await expect(page.getByRole('heading',{name:'Fotbollsanalys före riktiga insatser.'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Kör lokal A0-demo',exact:true})).toHaveCount(0);
  await expect(page.locator('.research-lab')).toHaveCount(0);
 }
 await page.getByRole('button',{name:'Oddslabb',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Testa signalerna. Behåll pengarna.'})).toBeVisible();
 await expect(page.getByText('Riktiga spel avstängda',{exact:true})).toBeVisible();
});

test('archived A0 start is rejected while authentication and CSRF remain enforced',async({page,request})=>{
 expect((await request.get('/api/research-poc/a0')).status()).toBe(401);
 await login(page);
 const outcome=await page.evaluate(async()=>{
  const catalog=await(await fetch('/api/research-poc/a0')).json();
  const session=await(await fetch('/api/session')).json();
  const body={action_id:crypto.randomUUID(),suite_hash:catalog.suite_hash};
  const denied=await fetch('/api/research-poc/a0/runs',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:JSON.stringify(body)});
  const missingCsrf=await fetch('/api/research-poc/a0/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const after=await(await fetch('/api/research-poc/a0')).json();
  return {status:denied.status,message:(await denied.json()).detail,csrfStatus:missingCsrf.status,before:catalog.runs.map((r:{id:string})=>r.id),after:after.runs.map((r:{id:string})=>r.id),body};
 });
 expect(outcome.status).toBe(409);
 expect(outcome.message).toContain('arkiverat');
 expect(outcome.csrfStatus).toBe(403);
 expect(outcome.after).toEqual(outcome.before);
 expect((await request.post('/api/research-poc/a0/runs',{data:outcome.body})).status()).toBe(401);
});

test('football lab respects persistent emergency stop on mobile without legacy controls',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await login(page);
 const resume=page.getByRole('button',{name:'Återuppta',exact:true});
 if(await resume.isEnabled())await resume.click();
 await page.getByRole('button',{name:'Nödstopp',exact:true}).click();
 await expect(page.locator('.state-label')).toHaveText('Nödstoppat');
 await page.getByRole('button',{name:'Öppna meny'}).click();
 await expect(page.getByRole('button',{name:'Researchlabb',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Oddslabb',exact:true}).click();
 await expect(page.getByRole('button',{name:'Visa syntetiskt exempel'})).toBeDisabled();
 await page.reload();
 await expect(page.getByRole('heading',{name:'Testa signalerna. Behåll pengarna.'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Visa syntetiskt exempel'})).toBeDisabled();
 await expect(page.locator('.odds-state')).toContainText('pausat eller nödstoppat');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.locator('.odds-state').getByRole('button',{name:'Återuppta'}).click();
 await expect(page.getByRole('button',{name:'Visa syntetiskt exempel'})).toBeEnabled();
});
