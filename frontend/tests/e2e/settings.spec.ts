import { test, expect } from '../fixtures';

test.describe('Settings Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should open settings modal when clicking settings button', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('text=Settings').first()).toBeVisible({ timeout: 5000 });
  });

  test('should close settings modal when clicking close button', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('text=Settings').first()).toBeVisible({ timeout: 5000 });
    
    const closeButton = page.locator('button[aria-label="Close menu"], button:has-text("Close")').first();
    await closeButton.click();
    
    await expect(page.locator('text=Settings').first()).not.toBeVisible({ timeout: 5000 });
  });

  test('should display all tab categories', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('text=General')).toBeVisible();
    await expect(page.locator('text=Database')).toBeVisible();
    await expect(page.locator('text=Master')).toBeVisible();
    await expect(page.locator('text=Planner')).toBeVisible();
    await expect(page.locator('text=Researcher')).toBeVisible();
    await expect(page.locator('text=Tools')).toBeVisible();
    await expect(page.locator('text=DB Agent')).toBeVisible();
  });

  test('should switch between tabs', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('[data-state="active"]', { hasText: 'General' })).toBeVisible();
    
    const researcherTab = page.locator('button:has-text("Researcher")');
    await researcherTab.click();
    
    await expect(page.locator('[data-state="active"]', { hasText: 'Researcher' })).toBeVisible();
  });

  test('should display timezone selector in General tab', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('text=Timezone')).toBeVisible();
    await expect(page.locator('select').first()).toBeVisible();
  });

  test('should display API key inputs in API Keys tab', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    const apiKeysTab = page.locator('button:has-text("API Keys")');
    await apiKeysTab.click();
    
    await expect(page.locator('text=Anthropic API Key')).toBeVisible();
    await expect(page.locator('text=OpenAI API Key')).toBeVisible();
  });

  test('should show profile options', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('text=Fast (Lightweight)')).toBeVisible();
    await expect(page.locator('text=Deep (Comprehensive)')).toBeVisible();
    await expect(page.locator('text=Custom')).toBeVisible();
  });

  test('should have save and cancel buttons', async ({ page }) => {
    const settingsButton = page.locator('button[title="Settings"]');
    await settingsButton.click();
    
    await expect(page.locator('button:has-text("Cancel")')).toBeVisible();
    await expect(page.locator('button:has-text("Save Changes")')).toBeVisible();
  });
});
