import { test, expect } from '@playwright/test';



test('should verify puzzle page loads for admin user', async ({ page }) => {
    // 1. Navigate to Login
    await page.goto('/auth/login');

    // 2. Login with admin@mail.com / admin
    await page.getByLabel('Email Address').fill('admin@mail.com');
    await page.getByLabel('Password').fill('admin');
    await page.getByRole('button', { name: 'Log in' }).click();

    // Wait for redirect to app
    await page.waitForURL('/app');

    // 3. Navigate to Puzzles list
    await page.goto('/app/puzzles');

    // Wait for the Puzzles page to load (check for heading)
    await expect(page.getByRole('heading', { name: 'Circuit Puzzles' })).toBeVisible({ timeout: 30000 });

    // 4. Select a puzzle (e.g., "Binary Adder")
    // We need to wait for the puzzle list to load
    await expect(page.getByRole('heading', { name: 'Binary Adder' })).toBeVisible();

    // Click on the puzzle to go to its page. 
    await page.getByRole('heading', { name: 'Binary Adder' }).click();

    // 5. Assert that the puzzle page title and description are visible
    // Wait for loading to finish
    await expect(page.getByText('Loading…')).not.toBeVisible({ timeout: 15000 });

    // The page title should be "Solve Puzzle" (from metadata) but the content should have the puzzle title.
    await expect(page.getByRole('heading', { name: 'Binary Adder', level: 1 })).toBeVisible();
    await expect(page.getByText('Create a circuit that adds two binary numbers')).toBeVisible();
});

test('should verify puzzle solve grid works', async ({ page }) => {
    // 1. Login
    await page.goto('/auth/login');
    await page.getByLabel('Email Address').fill('admin@mail.com');
    await page.getByLabel('Password').fill('admin');
    await page.getByRole('button', { name: 'Log in' }).click();
    await page.waitForURL('/app');

    // 2. Navigate to Puzzle
    // Use direct navigation to avoid click/hover flakiness
    await page.goto('/app/puzzles');
    await expect(page.getByRole('heading', { name: 'Circuit Puzzles' })).toBeVisible({ timeout: 30000 });
    await page.getByRole('heading', { name: 'Binary Adder' }).click();

    // 3. Select "AND" component
    // 3. Select "AND" component
    // Wait for loading to finish
    await expect(page.getByText('Loading…')).not.toBeVisible({ timeout: 20000 });

    // Ensure Workstation is loaded
    await expect(page.getByText('Working Area')).toBeVisible({ timeout: 20000 });

    // The menu items are buttons with text
    await expect(page.getByText('Current Cost:')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('div', { hasText: 'Current Cost:' })).toContainText('0');

    // Find the AND component button in the menu (it says AND and cost 10)
    const andComponent = page.getByRole('button').filter({ hasText: /^AND/ });
    await expect(andComponent).toBeVisible();
    await andComponent.click();

    // 4. Place component on grid
    // The grid container has "relative h-[calc(100vh-18rem)]"
    const grid = page.locator('div.relative.overflow-hidden.rounded-md.border.border-gray-300.bg-white').last();
    await expect(grid).toBeVisible();

    // Click inside the grid to place
    await grid.click({ position: { x: 200, y: 200 } });

    // 5. Verify Cost Increase
    // Initial cost was 0. AND gate cost is 10.
    await expect(page.locator('div', { hasText: 'Current Cost:' })).toContainText('10');
});
