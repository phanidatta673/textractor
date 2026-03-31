import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

test.describe('Text Extractor Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('**/presigned-url', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ uploadUrl: 'http://localhost:3000/mock-upload', fileId: '123', key: 'uploads/123.txt' }),
      });
    });

    await page.route('**/mock-upload', async route => {
      await route.fulfill({ status: 200 });
    });

    await page.route('**/start', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Extraction started', fileId: '123' }),
      });
    });

    await page.route('**/status/123', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'COMPLETED', content: 'Extracted text from mock file!' }),
      });
    });

    await page.goto('/');
  });

  test('should display the dashboard title', async ({ page }) => {
    await expect(page.getByText('Text Extractor Dashboard')).toBeVisible();
  });

  test('should handle file selection and upload process', async ({ page }) => {
    // 1. Create a dummy file for testing
    const testFilePath = path.join(__dirname, 'test.txt');
    fs.writeFileSync(testFilePath, 'Hello, this is a test extraction!');

    // 2. Select file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);

    // 3. Verify file appears in list
    await expect(page.getByText('test.txt')).toBeVisible();

    // 4. Click Extract Text
    const extractButton = page.getByRole('button', { name: /Extract Text/i });
    await extractButton.click();

    // 5. Verify status transitions
    await expect(page.getByText('COMPLETED')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Extracted text from mock file!')).toBeVisible();
  });
});
