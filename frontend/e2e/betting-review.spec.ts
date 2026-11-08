import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import path from 'node:path';

const golden=JSON.parse(readFileSync(new URL('../../tests/fixtures/betting_demo_v1_golden.json',import.meta.url),'utf8'));
const removal=JSON.parse(readFileSync(new URL('./fixtures/betting-review-removal.json',import.meta.url),'utf8'));

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

async function mockSaved(page:Page,view:any){
  const posts:string[]=[];
  await page.route('**/api/betting-demo/sessions**',async route=>{
    if(route.request().method()!=='GET'){posts.push(route.request().url());await route.abort('failed');return}
    const pathname=new URL(route.request().url()).pathname;
    if(pathname==='/api/betting-demo/sessions'){
      const {observations,analysis,decision,costs,bets,history,results,...header}=view;
      await route.fulfill({json:{scenario_version:view.scenario_version,real_money_enabled:false,sessions:[header]}});
    }else if(pathname==='/api/betting-demo/sessions/'+view.id)await route.fulfill({json:view});
    else await route.continue();
  });
  return posts;
}

test('real review workflow shows source evidence and binds the outer hash through settlement',async({page},info)=>{
  await page.setViewportSize({width:1440,height:1100});await enter(page);
  const created=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/betting-demo/sessions');
  await page.getByRole('button',{name:/^Skapa (ny )?demo-omgång/}).click();
  const sid=(await(await created).json()).id;
  await expect(page.getByRole('region',{name:'Granskning inför analys'})).toBeVisible();
  await page.getByRole('button',{name:'Analysera de sju matcherna'}).click();
  const region=page.getByRole('region',{name:'Sparad rollgranskning'});
  await expect(region).toBeVisible();
  await expect(region).toContainText('Regelbaserad offline-demo – ingen språkmodell, inga hämtade källor.');
  for(const role of ['researcher','analyst','finance','critic'])await expect(page.getByTestId('review-step-'+role)).toBeVisible();
  await expect(page.getByTestId('review-step-analyst')).toContainText('4 grundförslag före kritik');
  await expect(page.getByTestId('review-step-finance')).toContainText('Före kritik');
  await expect(page.getByTestId('review-step-critic')).toContainText('4 slutliga förslag');
  await expect(page.getByTestId('review-step-critic').locator('.badge')).not.toContainText('Förslag togs bort');
  await expect(page.locator('.demo-research')).toHaveCount(7);
  await expect(page.getByTestId('research-syntetisk-5')).toContainText('0 av 4 färska');
  await page.getByTestId('research-syntetisk-5').locator('summary').first().click();
  await expect(page.getByTestId('research-syntetisk-5')).toContainText('För få färska källposter');
  await expect(page.getByTestId('research-syntetisk-5')).toContainText('Offerten är äldre');
  await page.getByTestId('research-syntetisk-6').locator('summary').first().click();
  await expect(page.getByTestId('research-syntetisk-6')).toContainText('3 av 3 färska');
  await expect(page.getByTestId('research-syntetisk-6')).toContainText('För få färska källposter');
  const seventh=page.locator('.betting-match').filter({hasText:'Påhittat hemmalag 7'});
  await expect(seventh).toContainText('Avstå: Ingen avvikelse klarar de låsta provreglerna');
  await expect(page.getByTestId('research-syntetisk-5')).toContainText('Form, skador och laguppställningar saknas');
  await expect(region.locator('a')).toHaveCount(0);await expect(page.locator('.demo-research a')).toHaveCount(0);
  const output=process.env.JARVIS_REVIEW_EVIDENCE_DIR??info.outputDir;
  await region.screenshot({path:path.join(output,'review-desktop.png')});
  for(const evidence of await page.locator('.demo-research').all()){
    if(!await evidence.evaluate(el=>(el as HTMLDetailsElement).open))await evidence.locator('summary').first().click();
  }
  await page.setViewportSize({width:375,height:812});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth)).toBeTruthy();
  const tables=page.locator('.demo-research[open] .research-sources table');
  await expect(tables).toHaveCount(7);
  for(const table of await tables.all()){
    await expect(table).toBeVisible();
    expect(await table.evaluate(el=>el.clientWidth>0&&el.scrollWidth<=el.clientWidth)).toBeTruthy();
  }
  // Preserve the tested375px width; give the whole region room so a sticky
  // header cannot cover its title in the exported component screenshot.
  await page.setViewportSize({width:375,height:1800});
  await region.screenshot({path:path.join(output,'review-mobile.png')});
  await page.setViewportSize({width:375,height:812});
  const saved=await(await page.request.get('/api/betting-demo/sessions/'+sid)).json();
  expect(saved.analysis.proposal_version).toBe(2);
  expect(saved.analysis.proposal_hash).not.toBe(saved.analysis.core_proposal_hash);
  const decisionRequest=page.waitForRequest(r=>r.method()==='POST'&&new URL(r.url()).pathname.endsWith('/'+sid+'/decision'));
  await page.getByRole('button',{name:'Godkänn hela låtsasbatchen',exact:true}).click();
  const decision=(await decisionRequest).postDataJSON();
  expect(decision.proposal_hash).toBe(saved.analysis.proposal_hash);expect(decision.proposal_version).toBe(2);
  expect(decision).not.toHaveProperty('core_proposal_hash');
  await expect(page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true})).toBeEnabled();
  const simulationRequest=page.waitForRequest(r=>r.method()==='POST'&&new URL(r.url()).pathname.endsWith('/'+sid+'/simulate'));
  await page.getByRole('button',{name:'Registrera låtsasinsatser',exact:true}).click();
  expect((await simulationRequest).postDataJSON().proposal_hash).toBe(saved.analysis.proposal_hash);
  await expect(page.getByTestId('demo-open_stake_ore')).toContainText('40,00');
  await page.getByRole('button',{name:'Visa och avräkna simulerade resultat'}).click();
  await expect(page.getByTestId('demo-capital_ore')).toContainText(/1\s*008,10/);
});

test('backend-pinned removal view separates finance before and critic after without sending actions',async({page})=>{
  const posts=await mockSaved(page,structuredClone(removal));await enter(page);
  await expect(page.getByTestId('review-step-analyst')).toContainText('4 grundförslag före kritik');
  await expect(page.getByTestId('review-step-finance')).toContainText('4 förslag, 40,00');
  await expect(page.getByTestId('review-step-critic')).toContainText('3 slutliga förslag');
  await expect(page.getByTestId('review-step-critic')).toContainText('Förslag togs bort');
  const finding=page.locator('.review-findings li').filter({hasText:'Inaktuell eller framtida källa'});
  await expect(finding).toHaveCount(1);await expect(finding).toContainText('syntetisk-1');
  await expect(page.getByTestId('approve-batch-total')).toContainText('30,00');
  await expect(page.getByRole('button',{name:'Godkänn hela låtsasbatchen',exact:true})).toBeEnabled();
  await expect(page.locator('.betting-proposals tbody tr')).toHaveCount(3);
  expect(posts).toEqual([]);
});

for(const version of [undefined,'future-review-v99',''])test(`saved ${version===undefined?'legacy':version===''?'empty-unknown':'unknown'} view has no invented research`,async({page})=>{
  const view=structuredClone(golden.views.analyzed);
  if(version!==undefined)view.workflow_version=version;
  const posts=await mockSaved(page,view);await enter(page);
  if(version!==undefined){
    await expect(page.getByRole('region',{name:'Okänd granskningsversion'})).toContainText('Okänd granskningsversion – visas utan rollkedja');
    await expect(page.getByRole('button',{name:'Godkänn hela låtsasbatchen',exact:true})).toBeDisabled();
  }else await expect(page.getByRole('region',{name:'Äldre granskningsversion'})).toContainText('Ingen research skapas i efterhand');
  await expect(page.locator('.review-steps')).toHaveCount(0);await expect(page.locator('.demo-research')).toHaveCount(0);
  expect(posts).toEqual([]);
});

test('unknown finding codes remain plain text and incomplete saved review blocks actions',async({page})=>{
  const view=structuredClone(removal);view.analysis.review.findings[0].code='FUTURE_CODE_V99';
  const posts=await mockSaved(page,view);await enter(page);
  await expect(page.getByRole('region',{name:'Sparad rollgranskning'})).toContainText('Okänd kod: FUTURE_CODE_V99');
  view.analysis.core_analysis.proposals=[];
  await page.getByRole('button',{name:'Uppdatera sparat demoläge',exact:true}).click();
  await expect(page.getByRole('region',{name:'Ofullständig sparad granskning'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Godkänn hela låtsasbatchen',exact:true})).toBeDisabled();
  expect(posts).toEqual([]);
});

test('review presentation contains no links, raw HTML or unsupported promises',()=>{
  const source=readFileSync(new URL('../src/DemoReview.tsx',import.meta.url),'utf8');
  expect(source).not.toMatch(/dangerouslySetInnerHTML|href\s*=|<a(?:\s|>)/);
  expect(source).not.toMatch(/säker vinst|garanter|bästa spel|AI har (?:granskat|researchat)|hämtad(?:e)? nu/i);
});
