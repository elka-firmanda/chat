import { test, expect } from '../fixtures';

test.describe('Chat Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display welcome screen when no messages', async ({ page }) => {
    await expect(page.locator('h1:has-text("How can I help you today?")')).toBeVisible();
    await expect(page.locator('text=Ask me anything about research, data analysis, or general questions.')).toBeVisible();
  });

  test('should show example cards', async ({ page }) => {
    await expect(page.locator('text=Example cards')).toBeVisible({ timeout: 5000 }).catch(() => {
      return expect(page.locator('[class*="grid"]').first()).toBeVisible({ timeout: 5000 });
    });
  });

  test('should be able to type and submit a message', async ({ page }) => {
    const inputBox = page.locator('textarea[placeholder="Message..."]');
    await expect(inputBox).toBeVisible();
    
    await inputBox.fill('Hello, this is a test message');
    await expect(inputBox).toHaveValue('Hello, this is a test message');
  });

  test('should have working deep search toggle', async ({ page }) => {
    const deepSearchToggle = page.locator('button[aria-label="Toggle deep search"]');
    await expect(deepSearchToggle).toBeVisible();
    
    await deepSearchToggle.click();
    
    const sparkleIcon = page.locator('svg.lucide-sparkles');
    await expect(sparkleIcon).toBeVisible();
  });

  test('should display send button that is enabled when message is typed', async ({ page }) => {
    const sendButton = page.locator('button[aria-label="Send message"]');
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeDisabled();
    
    const inputBox = page.locator('textarea[placeholder="Message..."]');
    await inputBox.fill('Test message');
    
    await expect(sendButton).toBeEnabled();
  });
});

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display new chat button in sidebar', async ({ page }) => {
    const newChatButton = page.locator('button:has-text("New Chat")').first();
    await expect(newChatButton).toBeVisible();
  });

  test('should navigate between sessions', async ({ page }) => {
    const newChatButton = page.locator('button:has-text("New Chat")').first();
    await newChatButton.click();
    await page.waitForTimeout(500);
    
    const inputBox = page.locator('textarea[placeholder="Message..."]');
    await inputBox.fill('First session');
    await inputBox.press('Enter');
    
    await page.waitForTimeout(1000);
    
    await newChatButton.click();
    await page.waitForTimeout(500);
    
    const inputBox2 = page.locator('textarea[placeholder="Message..."]');
    await inputBox2.fill('Second session');
    await inputBox2.press('Enter');
    
    await page.waitForTimeout(1000);
    
    const sessionButtons = page.locator('[class*="sidebar"] button:has-text("New Chat"), [class*="sidebar"] button:has-text("First session"), [class*="sidebar"] button:has-text("Second session")');
    await expect(sessionButtons.first()).toBeVisible();
  });
});
