// D04 technical QA only. Use --qa-feedback; fixture notes/controls are not human evidence.
"use strict";
const fs = require("node:fs"), path = require("node:path"), assert = require("node:assert/strict");
const {chromium} = require(process.env.D04_PLAYWRIGHT);
const base = "http://127.0.0.1:8777", out = process.env.D04_QA;
const e = {muted: true, headless: true, physical_phone_tested: false, players: [], viewports: [],
  page_errors: [], external_requests: [], application_operations: [], media_response_bytes: 0};
let browser, context, page;
async function open(width) {
  browser = await chromium.launch({executablePath: process.env.D04_CHROME, headless: true,
    downloadsPath: path.join(out, "downloads"), args: ["--mute-audio", "--disable-gpu", "--disable-background-networking",
      "--disable-component-update", "--disable-sync", "--disable-extensions", "--no-first-run",
      "--disk-cache-size=1048576", "--media-cache-size=1048576"]});
  e.browser = browser.version();
  context = await browser.newContext({viewport: {width, height: width === 390 ? 844 : 1000},
    serviceWorkers: "block", acceptDownloads: true});
  context.setDefaultTimeout(8000);
  context.on("request", r => {
    if (!r.url().startsWith(base + "/") && !r.url().startsWith("blob:")) e.external_requests.push(r.url());
    if (r.method() === "POST" && !["/api/feedback", "/api/validate-feedback"].includes(new URL(r.url()).pathname))
      e.application_operations.push(new URL(r.url()).pathname);
  });
  context.on("response", r => {
    if (r.url().includes("/media/") && r.request().method() === "GET")
      e.media_response_bytes += Number(r.headers()["content-length"] || 0);
  });
  page = await context.newPage();
  page.on("pageerror", x => e.page_errors.push(String(x)));
  await page.goto(base + "/", {waitUntil: "domcontentloaded"});
  await ready();
}
async function ready() {
  await page.waitForFunction(() => document.getElementById("load-status").textContent.startsWith("Saved review ready"));
  assert.equal(await page.locator(".card").count(), 10);
  assert.equal(await page.locator("audio").count(), 21);
}
async function controls(label) {
  const buttons = page.locator("button[data-role]");
  for (let i = 0; i < 21; i++) {
    const button = buttons.nth(i), role = await button.getAttribute("data-role");
    const audio = page.locator("audio").nth(i);
    await button.click();
    const handle = await audio.elementHandle();
    await page.waitForFunction(a => !a.paused && a.currentTime > 0.06, handle);
    const before = await audio.evaluate(a => a.currentTime);
    await audio.press("Space");
    assert.equal(await audio.evaluate(a => a.paused), true);
    const box = await audio.boundingBox();
    await audio.click({position: {x: box.width * 0.58, y: box.height * 0.5}});
    const actual = await audio.evaluate(a => ({time: a.currentTime, duration: a.duration,
      paused: a.paused, error: a.error?.code || null, rate: a.playbackRate, volume: a.volume}));
    assert.equal(actual.error, null); assert.equal(actual.paused, true);
    assert.equal(actual.rate, 1); assert.equal(actual.volume, 1);
    assert.ok(Math.abs(actual.time - before) > 0.1, "Native seek did not move: " + role);
    e.players.push({viewport: label, role, advanced: before, ...actual});
  }
  await buttons.nth(0).click();
  await buttons.nth(1).click();
  assert.equal(await page.locator("audio").nth(0).evaluate(a => a.paused), true);
  assert.equal(await page.locator("audio").evaluateAll(all => all.filter(a => !a.paused).length), 1);
  await buttons.nth(1).click();
  e.viewports.push({width: label, overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)});
  assert.equal(e.viewports.at(-1).overflow, false);
}
async function save() {
  await page.locator("#save").click();
  await page.waitForFunction(() => document.getElementById("save-status").textContent.startsWith("Saved on this computer as revision"));
}
async function main() {
  try {
    fs.mkdirSync(path.join(out, "downloads"), {recursive: true});
    await open(1360);
    assert.equal(await page.locator("audio").evaluateAll(all => all.every(a => a.paused)), true);
    const boot = await page.evaluate(async () => (await fetch("/api/bootstrap")).json());
    assert.equal(boot.review.job_id, "06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e");
    assert.equal(boot.review.record_hash, "0767f7fdd1cdb294a7050566d93aaab74ecf34894cd2ac402597ee409d8570e5");
    assert.equal(boot.feedback_scope, "qa-feedback", "Refuse to write QA fixtures into human feedback");
    if (boot.latest) {
      assert.equal(boot.latest.document.listener, "Automated technical QA fixture, not Leonardo");
      assert.ok(Object.values(boot.latest.document.items).every(i => i.rating === "not-listened"));
    }
    fs.writeFileSync(path.join(out, "previous-session.json"), JSON.stringify({token: boot.token}));
    await controls(1360);
    await page.locator("#reference-player").scrollIntoViewIfNeeded();
    await page.screenshot({path: path.join(out, "desktop.png")});

    // All saved fixtures stay not-listened; they are explicitly technical QA, not Leonardo.
    const note = "Automated technical QA draft. Not a listening response.";
    await page.locator("#listener").fill("Automated technical QA fixture, not Leonardo");
    await page.locator("#reference-note").fill(note);
    await page.reload({waitUntil: "domcontentloaded"}); await ready();
    assert.equal(await page.locator("#reference-note").inputValue(), note);
    assert.match(await page.locator("#save-status").innerText(), /Unsaved browser draft restored/);
    await save();
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#export").click();
    const download = await downloadEvent, exported = path.join(out, "downloads/response.json");
    await download.saveAs(exported);
    const document = JSON.parse(fs.readFileSync(exported, "utf8"));
    assert.equal(document.reference.note, note);
    assert.ok(Object.values(document.items).every(i => i.rating === "not-listened"));
    assert.match(await page.locator("#save-status").innerText(), /cannot confirm a disk save/);
    await page.locator("#reference-note").fill(note + " Second revision.");
    await page.locator("#import").setInputFiles(exported);
    await page.waitForFunction(() => document.getElementById("save-status").textContent.includes("Save your current edits"));
    assert.match(await page.locator("#reference-note").inputValue(), /Second revision/);
    await save();
    await page.locator("#import").setInputFiles(exported);
    await page.locator("#apply-import").waitFor({state: "visible"});
    await page.locator("#apply-import").click();
    assert.equal(await page.locator("#reference-note").inputValue(), note);
    await save();
    const foreign = path.join(out, "downloads/foreign-review.json");
    fs.writeFileSync(foreign, JSON.stringify({...document, review_hash: "0".repeat(64)}));
    await page.locator("#import").setInputFiles(foreign);
    await page.waitForFunction(() => document.getElementById("save-status").textContent.includes("validation/save failed"));
    assert.equal(await page.locator("#reference-note").inputValue(), note);
    const stale = await context.newPage();
    await stale.goto(base + "/", {waitUntil: "domcontentloaded"});
    await stale.waitForFunction(() => document.getElementById("load-status").textContent.startsWith("Saved review ready"));
    await page.locator("#reference-note").fill(note + " Newer saved revision."); await save();
    await stale.locator("#reference-note").fill(note + " Stale-tab draft.");
    await stale.locator("#save").click();
    await stale.waitForFunction(() => document.getElementById("save-status").textContent.includes("newer response exists"));
    assert.match(await stale.locator("#reference-note").inputValue(), /Stale-tab draft/);
    await stale.close();
    e.feedback = {draft_reload: true, saved_revisions: 4, durable_export: true, import_roundtrip: true,
      dirty_import_refused: true, foreign_review_refused: true, stale_tab_conflict: true,
      all_fixture_ratings_not_listened: true, location: "isolated qa-feedback; excluded from human state"};
    await context.close(); await browser.close(); context = browser = null;

    await open(390); // Separate browser process and storage, not a desktop resize alone.
    assert.match(await page.locator("#reference-note").inputValue(), /Newer saved revision/);
    assert.equal(await page.locator("audio").evaluateAll(all => all.every(a => a.paused)), true);
    await controls(390);
    await page.locator("#reference-player").scrollIntoViewIfNeeded();
    await page.screenshot({path: path.join(out, "narrow.png")});
    const title = page.locator(".card h3").first(), originalTitle = await title.innerText();
    await title.evaluate(el => { el.textContent = "LongTitleLayoutFixture".repeat(16); });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    await title.evaluate((el, text) => { el.textContent = text; }, originalTitle);
    e.long_title_fixture = true; e.fresh_browser = true; e.reload = true;
    // Isolated network error fixture; no live package/bundle is edited.
    await page.route(base + "/media/" + boot.review.record_hash + "/D04-10-context", route =>
      route.fulfill({status: 409, contentType: "application/json", body: '{"error":"isolated missing-media fixture"}'}));
    await page.reload({waitUntil: "domcontentloaded"}); await ready();
    await page.waitForFunction(() => document.querySelector('[data-role="D04-10-context"]').disabled);
    assert.match(await page.locator("#D04-10 .error").last().innerText(), /Unavailable/);
    e.missing_media_fixture = "isolated HTTP 409, explicit UI failure, no live file modified";
    assert.deepEqual(e.page_errors, []); assert.deepEqual(e.external_requests, []);
    assert.deepEqual(e.application_operations, []);
    e.passed = true;
  } catch (error) {
    e.passed = false; e.error = String(error.stack || error); process.exitCode = 1;
    if (page) await page.screenshot({path: path.join(out, "failure.png")}).catch(() => {});
  } finally {
    if (context) await context.close(); if (browser) await browser.close();
    e.decoded_wav_seconds_upper_bound = e.media_response_bytes / (44100 * 2 * 2);
    fs.writeFileSync(path.join(out, "browser.json"), JSON.stringify(e, null, 2));
    console.log(JSON.stringify({passed: e.passed, controls: e.players.length, error: e.error,
      decoded_wav_seconds_upper_bound: e.decoded_wav_seconds_upper_bound}));
  }
}
main();
