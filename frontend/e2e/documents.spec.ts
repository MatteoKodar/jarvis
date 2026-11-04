import {test, expect, type Page} from '@playwright/test';

async function login(page: Page) {
  await page.goto('/');
  await page.getByLabel('Ägarlösenord').fill('browser-test-only-password');
  await page.getByRole('button', {name: 'Öppna kontrollcentralen'}).click();
  await expect(page.getByRole('heading', {name: 'Fotbollsanalys före riktiga insatser.'})).toBeVisible();
}

test('documents support sections, search, paging, reload and browser history', async ({page}) => {
  await login(page);
  await page.getByRole('button', {name: 'Dokument', exact: true}).click();
  const title = page.getByRole('heading', {name: 'JARVIS Research PoC A1 v0.2.0', exact: true});
  await expect(title).toBeVisible();
  await page.getByRole('navigation', {name: 'Innehållsförteckning'}).getByRole('link', {name: 'Primära mått och slutsats'}).click();
  await expect(page).toHaveURL(/section=/);
  await expect(page.getByRole('heading', {name: 'Primära mått och slutsats', exact: true})).toBeFocused();
  await page.getByLabel('Sök i dokumentet').fill('utkast');
  await expect(page.locator('.document-search-results a').first()).toBeVisible();
  await page.getByRole('button', {name: 'Nästa dokument'}).click();
  await expect(page.getByRole('heading', {name: 'Ämnen och källurval för A1 v0.2.0'})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', {name: 'Ämnen och källurval för A1 v0.2.0'})).toBeVisible();
  await page.goBack();
  await expect(title).toBeVisible();
  await page.getByLabel('Version', {exact: true}).selectOption('v0.1.0');
  await expect(page.getByRole('navigation', {name: 'Dokument i versionen'}).getByRole('link')).toHaveCount(3);
});

test('document reader works on mobile without horizontal overflow', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await login(page);
  await page.getByRole('button', {name: 'Öppna meny'}).click();
  await page.getByRole('button', {name: 'Dokument', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'JARVIS Research PoC A1 v0.2.0', exact: true})).toBeVisible();
  await page.getByRole('navigation', {name: 'Dokument i versionen'}).getByRole('link', {name: /Jämförelse och bedömning/}).click();
  await expect(page.getByRole('heading', {name: 'Jämförelse och bedömning A1 v0.2.0', exact: true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('document text cannot execute HTML or javascript links', async ({page}) => {
  await page.route('**/api/documents/v0.2.0/0', async route => {
    const response = await route.fetch();
    const document = await response.json();
    await route.fulfill({response, json: {...document, content: '# Lokalt innehåll\n\n<img src=x onerror="window.documentExploit=true">\n<script>window.documentExploit=true</script>\n\n[klicka](javascript:alert(1))\n\n~~~text\n# Detta är kod\n~~~'}});
  });
  await login(page);
  await page.getByRole('button', {name: 'Dokument', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Lokalt innehåll'})).toBeVisible();
  await expect(page.locator('.document-body')).toContainText('<img src=x');
  expect(await page.locator('.document-body img, .document-body script, .document-body a[href^="javascript:"]').count()).toBe(0);
  expect(await page.evaluate(() => (window as unknown as Record<string, unknown>).documentExploit)).toBeUndefined();
  await expect(page.getByRole('navigation', {name: 'Innehållsförteckning'}).getByRole('link')).toHaveCount(1);
});
