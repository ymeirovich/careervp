# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey.spec.ts >> THE JOURNEY >> J9 export
- Location: tests/e2e/journey.spec.ts:518:7

# Error details

```
TimeoutError: page.waitForEvent: Timeout 240000ms exceeded while waiting for event "download"
=========================== logs ===========================
waiting for event "download"
============================================================
```

# Test source

```ts
  422 | 
  423 |     const questionCards = page.getByTestId("questions-list").locator("> div");
  424 |     const generationFailedBanner = page.getByTestId("generation-failed-banner");
  425 |     const outcome = await Promise.race([
  426 |       questionCards
  427 |         .first()
  428 |         .waitFor({ state: "visible", timeout: GAP_QUESTIONS_TIMEOUT_MS })
  429 |         .then(() => "ready" as const)
  430 |         .catch(() => "exhausted" as const),
  431 |       generationFailedBanner
  432 |         .waitFor({ state: "visible", timeout: GAP_QUESTIONS_TIMEOUT_MS })
  433 |         .then(() => "failed" as const)
  434 |         .catch(() => "exhausted" as const),
  435 |     ]);
  436 | 
  437 |     if (outcome === "failed") {
  438 |       throw new Error("gap-question generation reported status=failed");
  439 |     }
  440 |     if (outcome === "exhausted") {
  441 |       throw new Error("gap-question generation neither completed nor reported failed in time");
  442 |     }
  443 | 
  444 |     const count = await questionCards.count();
  445 |     expect(count).toBeGreaterThan(0);
  446 | 
  447 |     // One question can be open for editing at a time (GapQuestionCard's own
  448 |     // guard) — the rich-text answer field is a contenteditable ProseMirror
  449 |     // node, not a plain <textarea>. Answer → fill → Save, one card at a time.
  450 |     for (let i = 0; i < count; i += 1) {
  451 |       await questionCards.nth(i).getByRole("button", { name: /^answer$/i }).click();
  452 |       const editable = questionCards.nth(i).locator('[contenteditable="true"]');
  453 |       if (i === 0) {
  454 |         // Exercise the AI Assist path for real (RichTextEditor's toolbar
  455 |         // button -> POST /ai/assist -> ai-assist-lambda), not a synthetic
  456 |         // fill — only on the first question, to keep this loop's LLM cost
  457 |         // bounded. The button replaces the editor's content via
  458 |         // editor.commands.setContent on success, so waiting for the field to
  459 |         // stop being empty is the real completion signal (not the button's
  460 |         // own "Generating…" label, which can transiently race the click).
  461 |         await questionCards.nth(i).getByRole("button", { name: /ai assist/i }).click();
  462 |         await expect(editable).not.toBeEmpty({ timeout: GENERATION_TIMEOUT_MS });
  463 |       } else {
  464 |         await editable.fill(
  465 |           "I led a three-person team migrating a monolith to Lambda over eight months.",
  466 |         );
  467 |       }
  468 |       await questionCards.nth(i).getByRole("button", { name: /^save$/i }).click();
  469 |       // Not "the Save button went away": while the request is in flight the
  470 |       // button renders a spinner carrying aria-label="Saving", which makes its
  471 |       // accessible name "Saving Save" and stops /^save$/ matching. That is the
  472 |       // save STARTING. Waiting on it let this loop open the next question
  473 |       // mid-save, where the page's own guard correctly blocked it — read for a
  474 |       // full run as "J4 is broken". Edit only renders once the card has left
  475 |       // edit state holding a stored response, so it means the answer landed.
  476 |       await expect(questionCards.nth(i).getByRole("button", { name: /^edit$/i })).toBeVisible({
  477 |         timeout: PAGE_TIMEOUT_MS,
  478 |       });
  479 |     }
  480 | 
  481 |     await page.getByTestId("submit-all-btn").click();
  482 | 
  483 |     // Submitting redirects to the hub — persistence is the claim, so reload
  484 |     // there before believing the module actually recorded completion.
  485 |     await page.waitForURL((url) => !url.pathname.includes("/gap-analysis"), {
  486 |       timeout: GENERATION_TIMEOUT_MS,
  487 |     });
  488 |     await page.reload();
  489 |     await expect(page.getByText(/complete gap analysis to unlock/i)).toHaveCount(0);
  490 |   });
  491 | 
  492 |   test("J5 VPR generates", async ({ page }) => {
  493 |     test.setTimeout(2 * GENERATION_TIMEOUT_MS + 60_000);
  494 |     // VPR's backend dependency is company_research, not gap_analysis directly
  495 |     // (artifact_dependency_resolver.py DEPENDENCIES) — company research is not
  496 |     // one of the customer-facing steps this journey counts, but it is a real,
  497 |     // mandatory precondition the hub exposes as its own card, so it has to be
  498 |     // driven here or every VPR request 409s upstream_required.
  499 |     await generateFromHub(page, "companyResearch", applicationUrl, /research|overview|about|industry|culture/i);
  500 |     await generateFromHub(page, "vpr", applicationUrl, /value proposition|vpr|match score|fit/i);
  501 |   });
  502 | 
  503 |   test("J6 tailored CV", async ({ page }) => {
  504 |     test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
  505 |     await generateFromHub(page, "tailoredCV", applicationUrl, /experience|summary|skills/i);
  506 |   });
  507 | 
  508 |   test("J7 cover letter", async ({ page }) => {
  509 |     test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
  510 |     await generateFromHub(page, "coverLetter", applicationUrl, /dear|sincerely|regards|hiring/i);
  511 |   });
  512 | 
  513 |   test("J8 interview prep", async ({ page }) => {
  514 |     test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
  515 |     await generateFromHub(page, "interviewPrep", applicationUrl, /question|answer|tell me about|why/i);
  516 |   });
  517 | 
  518 |   test("J9 export", async ({ page }) => {
  519 |     test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
  520 |     await page.goto(`${applicationUrl}/cv-tailored`);
  521 | 
> 522 |     const downloadPromise = page.waitForEvent("download", { timeout: GENERATION_TIMEOUT_MS });
      |                                  ^ TimeoutError: page.waitForEvent: Timeout 240000ms exceeded while waiting for event "download"
  523 |     await page.getByRole("button", { name: /export|download|pdf|docx/i }).first().click();
  524 | 
  525 |     const download = await downloadPromise;
  526 |     const file = await download.path();
  527 |     expect(file).toBeTruthy();
  528 | 
  529 |     // A zero-byte download is a successful-looking failure.
  530 |     const size = file ? fs.statSync(file).size : 0;
  531 |     expect(size).toBeGreaterThan(1000);
  532 |   });
  533 | });
  534 | 
```