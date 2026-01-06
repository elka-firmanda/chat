import { test as base, type Page, type BrowserContext } from '@playwright/test';

export interface TestFixtures {
  page: Page;
  context: BrowserContext;
}

export const test = base.extend<TestFixtures>({
  page: async ({ page }, use) => {
    await use(page);
  },
  context: async ({ context }, use) => {
    await use(context);
  },
});

export { expect } from '@playwright/test';
