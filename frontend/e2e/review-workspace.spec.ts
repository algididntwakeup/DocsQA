import { expect, test, type Page } from "@playwright/test";

const documentId = "c6a4507d-bbfd-4c71-b64a-5f42f7fd1cde";
const timestamp = "2026-09-04T08:00:00Z";

const documentPayload = {
  id: documentId,
  filename: "inspection.pdf",
  media_type: "application/pdf",
  size_bytes: 8,
  sha256: "a".repeat(64),
  status: "COMPLETED",
  progress_pct: 100,
  page_count: 3,
  workflow_status: "ANALYZING",
  created_at: timestamp,
  updated_at: timestamp,
};

async function mockWorkspace(page: Page) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "11111111-1111-1111-1111-111111111111",
        email: "engineer@reksolindo.co.id",
        full_name: "Review Engineer",
        role: "ENGINEER",
        is_active: true,
        created_at: timestamp,
      }),
    });
  });
  await page.route(`**/api/v1/documents/${documentId}`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(documentPayload),
    });
  });
  await page.route(`**/api/v1/documents/${documentId}/issues**`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        issues: [],
        pagination: { page: 1, page_size: 100, total: 0 },
      }),
    });
  });
  await page.route(`**/api/v1/documents/${documentId}/pdf`, async (route) => {
    await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });
}

test("review workspace resizes, switches panes, and toggles the theme", async ({ page }) => {
  const legacyHost = ["localhost", "8000"].join(":");
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes(legacyHost) || url.includes(":8000/api/")) {
      externalRequests.push(url);
    }
  });
  await mockWorkspace(page);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/documents/${documentId}/review`);

  await expect(page.getByText("inspection.pdf")).toBeVisible();
  const panels = page.locator("[data-panel]");
  await expect(panels).toHaveCount(2);

  const before = await panels.nth(0).boundingBox();
  const findingsBefore = await panels.nth(1).boundingBox();
  expect(before).not.toBeNull();
  expect(findingsBefore).not.toBeNull();

  const separator = page.locator("[data-separator]").first();
  const handle = await separator.boundingBox();
  expect(handle).not.toBeNull();
  await page.mouse.move(handle!.x + handle!.width / 2, handle!.y + handle!.height / 2);
  await page.mouse.down();
  await page.mouse.move(handle!.x + handle!.width / 2 - 150, handle!.y + handle!.height / 2, { steps: 10 });
  await page.mouse.up();

  const after = await panels.nth(0).boundingBox();
  const findingsAfter = await panels.nth(1).boundingBox();
  expect(after!.width).toBeLessThan(before!.width);
  expect(findingsAfter!.width).toBeGreaterThan(findingsBefore!.width);
  await expect(panels.nth(0)).toBeVisible();
  await expect(panels.nth(1)).toBeVisible();

  const bodyBackground = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.getByRole("button", { name: /switch to dark theme/i }).click();
  await expect
    .poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor))
    .not.toBe(bodyBackground);
  expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(true);

  await page.reload();
  expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(true);

  await page.setViewportSize({ width: 600, height: 900 });
  await expect(page.getByRole("button", { name: "Document" })).toBeVisible();
  await page.getByRole("button", { name: /^Findings/ }).click();
  await expect(page.locator("[data-panel]")).toHaveCount(0);

  expect(externalRequests).toEqual([]);
});
