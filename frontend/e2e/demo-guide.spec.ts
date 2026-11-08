import {test, expect} from '@playwright/test';

test('demo guide prepares an editable task and opens the match lab without starting work', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto('/');
  await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
  await page.getByRole('button', {name: 'Öppna kontrollcentralen'}).click();
  const guide = page.getByRole('region', {name: 'Så testar vi bettingagentens arbetsflöde'});
  await expect(guide).toBeVisible();
  await expect(guide).toContainText('Agenternas svar är förskrivna i DEMO');
  const before = await page.evaluate(async () => ({
    state: await (await fetch('/api/state')).json(),
    lab: await (await fetch('/api/odds-lab')).json(),
  }));
  await guide.getByText('Separata agentuppdrag och äldre Oddslabb', {exact:true}).click();
  await guide.getByRole('button', {name: 'Förbered demo-uppdrag'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByLabel('Vad ska teamet undersöka?')).toHaveValue(/Granska tidsstämplar, oddsunderlag och kostnader/);
  await page.getByLabel('Vad ska teamet undersöka?').fill('Mitt eget avgränsade fotbollsuppdrag');
  await page.getByRole('button', {name: 'Stäng', exact: true}).click();
  await guide.getByRole('button', {name: 'Öppna agentförslag'}).click();
  await expect(page).toHaveURL(/#\/forslag$/);
  await page.goto('/#/oversikt');
  await guide.getByRole('button', {name: 'Öppna matchdemot'}).click();
  await expect(page.getByRole('heading', {name: 'Från odds till avräkning.'})).toBeVisible();
  const after = await page.evaluate(async () => ({
    state: await (await fetch('/api/state')).json(),
    lab: await (await fetch('/api/odds-lab')).json(),
  }));
  expect(after.state.tasks.map((t: {id: string}) => t.id)).toEqual(before.state.tasks.map((t: {id: string}) => t.id));
  expect(after.state.settings.state).toBe(before.state.settings.state);
  expect(after.lab.runs).toEqual(before.lab.runs);
  await page.goto('/#/oversikt');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({path: 'test-results/demo-guide-mobile.png', fullPage: true});
  await page.setViewportSize({width: 1440, height: 1100});
  await page.screenshot({path: 'test-results/demo-guide-desktop.png', fullPage: true});
});
