import { expect, test } from "@playwright/test";

const documentId = "c6a4507d-bbfd-4c71-b64a-5f42f7fd1cde";
const timestamp = "2026-09-04T08:00:00Z";

test("uploads a document and reaches extracted status", async ({ page }) => {
  await page.route("http://localhost:8000/api/v1/documents/upload", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({
        id: documentId,
        filename: "inspection.pdf",
        status: "QUEUED",
        created_at: timestamp,
        deduplicated: false,
      }),
    });
  });
  await page.route(`http://localhost:8000/api/v1/documents/${documentId}`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: documentId,
        filename: "inspection.pdf",
        media_type: "application/pdf",
        size_bytes: 8,
        sha256: "a".repeat(64),
        status: "COMPLETED",
        review_status: "PENDING",
        progress_pct: 100,
        page_count: 3,
        created_at: timestamp,
        updated_at: timestamp,
      }),
    });
  });
  await page.route(`http://localhost:8000/api/v1/documents/${documentId}/status`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: documentId,
        status: "COMPLETED",
        review_status: "PENDING",
        progress_pct: 100,
        updated_at: timestamp,
        stages: [{
          id: "17471ea1-5671-49bc-825a-8300f4c7bf10",
          name: "extract",
          status: "SUCCEEDED",
          progress_pct: 100,
          attempt: 1,
          started_at: timestamp,
          finished_at: timestamp,
        }],
      }),
    });
  });

  await page.goto("/upload");
  await page.locator("input[type=file]").setInputFiles({
    name: "inspection.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7"),
  });
  await page.getByRole("button", { name: "Begin inspection (1)" }).click();
  await expect(page.getByText("Queued for extraction")).toBeVisible();
  await page.getByRole("link", { name: "View status for inspection.pdf" }).click();
  await expect(page.getByRole("heading", { name: "Extraction progress" })).toBeVisible();
  await expect(page.getByText("Document is extracted")).toBeVisible();
});
