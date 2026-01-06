import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

page.on('console', msg => {
  if (msg.type() === 'error') {
    console.log('Console error:', msg.text());
  }
});

page.on('pageerror', error => {
  console.log('Page error:', error.message);
});

await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(5000);

// Take a screenshot
await page.screenshot({ path: '/tmp/ui-screenshot.png', fullPage: true });
console.log('Screenshot saved to /tmp/ui-screenshot.png');

// Get page info
console.log('\nPage Information:');
console.log('- Title:', await page.title());
console.log('- URL:', page.url());

// Check key elements
const elements = {
  'Root': '#root',
  'Sidebar': 'aside',
  'Textarea': 'textarea',
  'Buttons': 'button',
  'Headings': 'h1, h2, h3'
};

for (const [name, selector] of Object.entries(elements)) {
  const count = await page.locator(selector).count();
  console.log(`- ${name}: ${count} element(s)`);
}

await browser.close();
