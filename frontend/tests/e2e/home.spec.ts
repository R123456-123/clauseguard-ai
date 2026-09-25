import { expect, test } from "@playwright/test";

test("shows the contract review entry point", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /understand your legal documents/i }),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "Upload File" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("tab", { name: "Paste Text" })).toBeVisible();
});

test("enforces the minimum pasted contract length", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Paste Text" }).click();

  const submit = page.getByRole("button", { name: /analyse pasted contract/i });
  await expect(submit).toBeDisabled();

  await page.locator("#contract-text-input").fill("A short contract");
  await expect(submit).toBeDisabled();
});