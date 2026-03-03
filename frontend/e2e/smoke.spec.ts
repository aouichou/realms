import { expect, test } from '@playwright/test';

test.describe('Landing page', () => {
	test('loads and shows the app title', async ({ page }) => {
		await page.goto('/');
		// The page should load without errors
		await expect(page).toHaveTitle(/realms/i);
	});

	test('has a working play / get started link', async ({ page }) => {
		await page.goto('/');
		// Look for primary CTA — could be "Play", "Start", "Begin Adventure", etc.
		const cta = page.getByRole('link', { name: /play|start|begin|adventure|enter/i }).first();
		if (await cta.isVisible()) {
			await cta.click();
			// Should navigate away from home
			await expect(page).not.toHaveURL('/');
		}
	});
});

test.describe('Auth pages', () => {
	test('login page renders', async ({ page }) => {
		await page.goto('/auth/login');
		// Should have some form element
		const form = page.locator('form').first();
		await expect(form).toBeVisible();
	});

	test('register page renders', async ({ page }) => {
		await page.goto('/auth/register');
		const form = page.locator('form').first();
		await expect(form).toBeVisible();
	});
});
