import { test, expect } from '../fixtures';

test.describe('Responsive Design', () => {
  test('should show sidebar drawer on mobile when menu button is clicked', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const menuButton = page.locator('button[aria-label="Open menu"]');
    await expect(menuButton).toBeVisible();
    
    await menuButton.click();
    
    await expect(page.locator('text=Chats').first()).toBeVisible({ timeout: 5000 });
  });

  test('should hide sidebar on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const sidebar = page.locator('aside').first();
    await expect(sidebar).not.toBeVisible();
  });

  test('should display header on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const header = page.locator('header').first();
    await expect(header).toBeVisible();
  });

  test('should have touch-friendly button sizes on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const sendButton = page.locator('button[aria-label="Send message"]');
    const box = await sendButton.boundingBox();
    
    expect(box?.height).toBeGreaterThanOrEqual(44);
    expect(box?.width).toBeGreaterThanOrEqual(44);
  });

  test('should display full sidebar on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const sidebar = page.locator('aside').first();
    await expect(sidebar).toBeVisible();
  });

  test('should adapt input box size for mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const inputBox = page.locator('textarea[placeholder="Message..."]');
    await inputBox.fill('Test message for mobile');
    
    const box = await inputBox.boundingBox();
    expect(box?.width).toBeLessThan(400);
  });

  test('should handle tablet viewport sizes', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const sidebar = page.locator('aside').first();
    await expect(sidebar).toBeVisible();
    
    const inputBox = page.locator('textarea[placeholder="Message..."]');
    await expect(inputBox).toBeVisible();
  });
});

test.describe('Mobile Drawer Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should close drawer when close button is clicked', async ({ page }) => {
    const menuButton = page.locator('button[aria-label="Open menu"]');
    await menuButton.click();
    
    await expect(page.locator('text=Chats').first()).toBeVisible({ timeout: 5000 });
    
    const closeButton = page.locator('button[aria-label="Close menu"]');
    await closeButton.click();
    
    await expect(page.locator('text=Chats').first()).not.toBeVisible({ timeout: 5000 });
  });

  test('should show new chat button in drawer', async ({ page }) => {
    const menuButton = page.locator('button[aria-label="Open menu"]');
    await menuButton.click();
    
    await expect(page.locator('button:has-text("New Chat")').first()).toBeVisible({ timeout: 5000 });
  });

  test('should show settings button in drawer', async ({ page }) => {
    const menuButton = page.locator('button[aria-label="Open menu"]');
    await menuButton.click();
    
    await expect(page.locator('button:has-text("Settings")').first()).toBeVisible({ timeout: 5000 });
  });
});
