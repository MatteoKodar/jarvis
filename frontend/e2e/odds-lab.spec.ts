import {test,expect,type Page} from '@playwright/test';

async function enterLab(page:Page){
 await page.goto('/');
 await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
 await page.getByRole('button',{name:'Öppna kontrollcentralen'}).click();
 await page.getByRole('button',{name:'Oddslabb',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Testa signalerna. Behåll pengarna.'})).toBeVisible();
 const resume=page.locator('.odds-state').getByRole('button',{name:'Återuppta'});
 if(await resume.isVisible())await resume.click();
 await expect(page.getByRole('button',{name:'Visa syntetiskt exempel'})).toBeEnabled();
}

test('football paper lab separates invented profits, losses and abstentions and exports',async({page})=>{
 await page.setViewportSize({width:1440,height:1100});
 await enterLab(page);
 await page.getByRole('button',{name:'Visa syntetiskt exempel'}).click();
 await expect(page.getByText('SYNTETISKT · INGET VINSTBEVIS',{exact:true})).toBeVisible();
 await expect(page.locator('.odds-match')).toHaveCount(7);
 await expect(page.locator('.odds-match header .badge').filter({hasText:/^Vinst$/})).toHaveCount(2);
 await expect(page.locator('.odds-match header .badge').filter({hasText:/^Förlust$/})).toHaveCount(2);
 await expect(page.locator('.odds-match header .badge').filter({hasText:/^Avstå$/})).toHaveCount(3);
 await expect(page.locator('.odds-metrics').first()).toContainText('8,10');
 await page.locator('.odds-match').first().getByText('Visa källor och kontroller',{exact:true}).click();
 await expect(page.locator('.odds-match').first().getByText(/Målbolaget ingår inte i sin egen referens/)).toBeVisible();
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Exportera historik'}).click()]);
 expect(download.suggestedFilename()).toMatch(/^jarvis-odds-[a-f0-9]+\.json$/);
 await page.locator('.odds-match').first().getByText('Visa källor och kontroller',{exact:true}).click();
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'../docs/screenshots/odds-lab-desktop.png',fullPage:true});
 await page.reload();
 await page.getByRole('button',{name:'Oddslabb',exact:true}).click();
 await expect(page.locator('.odds-match')).toHaveCount(7);
 await page.setViewportSize({width:390,height:844});
 await expect(page.locator('.sidebar')).not.toBeInViewport();
 await page.screenshot({path:'../docs/screenshots/odds-lab-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('lost response retries with same identity and does not duplicate series',async({page})=>{
 await enterLab(page);
 const before=await page.locator('.odds-run-list button').count();
 let first=true;
 await page.route('**/api/odds-lab/runs',async route=>{
  if(first&&route.request().method()==='POST'){first=false;await route.fetch();await route.abort('failed')}
  else await route.continue();
 });
 await page.getByRole('button',{name:'Visa syntetiskt exempel'}).click();
 await expect(page.getByRole('alert')).toBeVisible();
 await page.getByRole('button',{name:'Försök samma begäran igen'}).click();
 await expect(page.locator('.odds-run-list button')).toHaveCount(before+1);
 await expect(page.locator('.odds-match')).toHaveCount(7);
});

test('forward series starts empty, blocks example import and never offers real bets',async({page})=>{
 await enterLab(page);
 await page.getByRole('button',{name:'Starta observationsserie',exact:true}).click();
 await expect(page.getByText('MANUELLT IMPORTERAT · EJ OBEROENDE VERIFIERAT',{exact:true})).toBeVisible();
 await expect(page.locator('.odds-match')).toHaveCount(0);
 await expect(page.getByText('Riktiga insatser är alltid avstängda i denna version.',{exact:true})).toBeVisible();
 await page.getByText('Importera en verklig observation',{exact:true}).click();
 const example=await page.evaluate(async()=>await(await fetch('/api/odds-lab/template')).json());
 await page.getByLabel('Observationens JSON').fill(JSON.stringify(example));
 await page.getByRole('button',{name:'Registrera observation före avspark'}).click();
 await expect(page.getByRole('alert')).toContainText('exempeladresser');
 await page.getByRole('button',{name:'Stäng begäran',exact:true}).click();
 await page.reload();
 await page.getByRole('button',{name:'Oddslabb',exact:true}).click();
 await expect(page.getByRole('button',{name:'Öppna observationsserie',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:/placera|sätt in|betta/i})).toHaveCount(0);
});
