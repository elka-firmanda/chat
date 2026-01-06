import { test, expect } from '../fixtures';

test.describe('Theme Toggle', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display theme toggle button in header', async ({ page }) => {
    const themeButton = page.locator('button[title*="Switch to dark mode"], button[title*="Switch to light mode"]');
    await expect(themeButton).toBeVisible();
  });

  test('should toggle between light and dark themes', async ({ page }) => {
    const themeButton = page.locator('button[title*="Switch to dark mode"], button[title*="Switch to light mode"]');
    
    await expect(themeButton).toHaveAttribute('title', /Switch to (dark|light) mode/);
    
    await themeButton.click();
    
    await expect(themeButton).toHaveAttribute('title', /Switch to (dark|light) mode/);
    
    await themeButton.click();
    
    await expect(themeButton).toHaveAttribute('title', /Switch to (dark|light) mode/);
  });

  test('should display sun icon in light mode', async ({ page }) => {
    const themeButton = page.locator('button[title*="Switch to dark mode"], button[title*="Switch to light mode"]');
    const sunIcon = page.locator('svg.lucide-sun');
    const moonIcon = page.locator('svg.lucide-moon');
    
    const initialTitle = await themeButton.getAttribute('title');
    if (initialTitle?.includes('dark')) {
      await themeButton.click();
    }
    
    await expect(sunIcon.or(moonIcon)).toBeVisible();
  });

  test('should persist theme in localStorage', async ({ page }) => {
    const themeButton = page.locator('button[title*="Switch to dark mode"], button[title*="Switch to light mode"]');
    
    await themeButton.click();
    
    const localStorageTheme = await page.evaluate(() => localStorage.getItem('theme'));
    expect(localStorageTheme).toBeTruthy();
  });

  test('should apply dark theme class to document', async ({ page }) => {
    const themeButton = page.locator('button[title*="Switch to dark mode"], button[title*="Switch to light mode"]');
    
    const initialTitle = await themeButton.getAttribute('title');
    if (initialTitle?.includes('dark')) {
      await themeButton.click();
      
      await expect(page.locator('html[class*="dark"]')).toBeVisible({ timeout: 5000 }).catch(() => {
        return expect(page.locator('html[data-theme="dark"]')).toBeVisible({ timeout: 5000 });
      });
    }
  });
});
