# D04 — First listening review

25 October 2026. **Complete technical delivery.** **Listening review pending;
relevance unmeasured.** This Markdown file is a standalone downloadable report.
The page presents ten baseline candidates, without confirmed-match labels or
confidence percentages. Original mixture / legacy mean / pitch off remain defaults.

**Authorized continuation:** the unchanged full-suite regression fixture required more
temporary audio than D04's original 32 MiB QA allowance. A supervised attempt stopped at
that cap and retained a 33,997,853-byte incomplete generated test fixture (the
half-second sampler detected the boundary after a write). Automatic approval
review rejected cleanup with “blocked by policy”; nothing was deleted or retried
through another path. The user explicitly amended D04 to **224 MiB QA, 256 MiB
combined new output and 24 cumulative invocations**, keeping **600 aggregate
seconds**, every earlier charge, all other limits and all D03 pools unchanged.
The amendment is recorded in [PR #34](https://github.com/lillo24/Similar-Sound-Search/pull/34)
and the [versioned allowance](../manifests/listening/preparation-allowance.json).
All final technical checks passed. Human listening remains pending; optional ratings did not gate merge.

## Open and listen on the delivery Windows computer

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-d04.ps1
```

Open **http://127.0.0.1:8777/**. Keep the terminal open; Ctrl+C stops the listener.
127.0.0.1 means the computer running it. A 390px desktop viewport does not mean
phone access; no physical phone or Android playback is claimed. A public clone
requires the separate private review/installed-interpreter artifacts; see
[listening instructions](../docs/LISTENING.md) for exact prerequisites.

The original reference is first and remains easy to replay. Each numbered card
has **Play passage**, a separately labelled **Play context**, and native pause/seek.
Only one player runs at a time. Context is unscored. Timestamps below refer to
the supplied available audio files, with no invented streaming/master offset.

## Frozen reference and candidates

Reference: **daoud — Loulou & the loulous**, full original **03:38.000–04:00.000**
mixture (22 seconds), native **[9,613,800, 10,584,000)** at 44.1 kHz. Its query
context is 03:37.000–04:01.000; reference playback retains the full 22-second event.
The supplied MP3 SHA256 is
`2fc1256b1ac35134cfaef177aaf032277a0e375c676e50d391a1e3b22046ae30`.
Recording identity, marked-version/master alignment, intended layer and rights
remain unverified. Supplied labels do not independently verify song identities.

| ID | Candidate | Scored passage | Unscored context |
| --- | --- | --- | --- |
| D04-01 | Shivering Shadows (Featuring Viktor Van River) — Cutside | 03:11.000–03:13.400 | 03:10.000–03:14.400 |
| D04-02 | Body, soul — Viktor Van River | 02:00.000–02:02.400 | 01:59.000–02:03.400 |
| D04-03 | Amaterasu — Cutside | 01:37.000–01:39.400 | 01:36.000–01:40.400 |
| D04-04 | Essence 118 — mGee | 02:43.750–02:46.150 | 02:42.750–02:47.150 |
| D04-05 | Subway Cameo — Pete Lund | 03:14.500–03:16.900 | 03:13.500–03:17.900 |
| D04-06 | When I Lay Down — Gary Wood | 02:18.000–02:20.400 | 02:17.000–02:21.400 |
| D04-07 | Absurdius Rex — Jovian Year | 00:07.750–00:10.150 | 00:06.750–00:11.150 |
| D04-08 | Something To See (De Vries Instrumental) — Donnie Ozone | 03:08.500–03:10.900 | 03:07.500–03:11.900 |
| D04-09 | Confusion — Mos Emvy | 00:10.000–00:12.400 | 00:09.000–00:13.400 |
| D04-10 | Gladiator Season — GLD8TRZ | 03:23.250–03:25.650 | 03:22.250–03:26.650 |

All ten groups and recording IDs are distinct. The order, scores, selected arm,
native representatives and scored/context media identities come from the saved
publication, checked through the installed read-only provider. No result was
replaced, reordered, regenerated or borrowed from another arm.

Review **d04-v1**, logical hash
`0767f7fdd1cdb294a7050566d93aaab74ecf34894cd2ac402597ee409d8570e5`.
[Immutable manifest](../manifests/listening/d04-v1.json) and
[blank feedback template](../manifests/listening/d04-feedback-template.json).
Changes to reference, candidates or timing require a new review version.

## Playback provenance and engineering scope

The companion copies **21 existing, unchanged WAVs / 15,876,924 bytes**, rather
than rebuilding the distribution or copying its full private closure. The exact
reference WAV SHA256 is
`390f8584e5cf2713bdd38b588571627eb8f6bd5d8aea0495662645bb666094ad`.

The installed reference reader explicitly failed: its inventory contains two
retained copies of the expected filename, while the reader requires one. D04
verified both copies, the original MP3 hash, query native frames and the retained
C03 reference publication `b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee`.
It uses that publication's original 22-second mixture as a private presentation
export. It never calls the charged preview operation. The frozen D03 core and
distribution remain unchanged; this is an explicit companion workaround.

Saved job:
`06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e`.
Result:
`2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374`.
Reference revision:
`c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`.
Materialization:
`0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.

The delivered D03 archive remains **292,441,732 bytes**, SHA256
`062f97ac056f75f664440c0bfc45caaea3ed7e52023d6568704098dda7808901`;
core 0.3.0, distribution d03-1.0.0, exact Python 3.12.14 / Torch 2.6.0+cpu.
Loulou was searched with the preceding installed artifact, consumer `a07f2aa4…`.
The final artifact, consumer `666bb9e0…`, reopened it and verified numerical
agreement; its later repairs were scoped port binding/UI changes. D04 reads that
saved publication, and does not claim a new search with the final archive.

Retained C03 reference and D03 candidate native sample proofs establish their old
audits. D04 freshly verifies bytes, WAV headers/native frame counts, publication
membership and query/arm/population/order. It does not claim a new full-source
audio audit. Muted browser QA establishes controls, never perceptual relevance.

## Technical verification and resources

**435 unique tests passed in bounded batches:** the full 417 existing tests and
18 D04 tests, with the final D04 checks repeated after integrating Leonardo's
amendment commit. Ruff lint/format passed over 251 Python files; JavaScript/CJS
syntax and the PowerShell launcher parser passed. No hosted CI is configured.

The exact installed read-only provider revalidated the saved publication against
the immutable review. All **21 WAV byte hashes, headers and native frame counts**
passed again. All 21 result-bound companion media routes returned correct WAV
MIME/206 ranges and the expected bytes. The final launcher was exercised with the
existing installed interpreter; restart rotated its token, and the fresh human
feedback store is empty. Malformed/foreign/stale cases use isolated fixtures.

**42 real player checks passed:** reference plus all 20 scored/context controls
at both 1360px and 390px, including actual native play/pause/seek and one-player
exclusivity. Reload, a separate fresh browser, long-title layout, missing-media
errors, feedback draft reload, durable JSON export/import, dirty-import refusal
and stale-tab conflicts passed. Chrome 155.0.8059.85 was headless and muted.
The missing-media network fixture altered no live file; no UI success was injected
and no pacing workaround was added. No physical phone was tested. All eight saved
QA feedback revisions are explicitly technical, not Leonardo's responses, and
all their ratings remain not listened. They are separate from the empty human store.

The earlier Windows atomic-replacement failure was resolved independently of the
budget change: D04's monitor now obtains cached directory-entry sizes rather than
opening live fixture files while the frozen writer replaces them; Windows fixture
paths use the extended namespace without moving their actual locations. A native
busy-reader fault still fails explicitly, release restores replacement, and 100
replacements alongside the live monitor pass. The original full procedural test
also passes. The frozen core writer and numerical code are unchanged.

The first browser run exposed a queued-play-event race after all individual
players passed. Custom Play now pauses the previous player synchronously and
ignores stale events from paused clips. The complete browser run then passed.
Both attempts remain charged and retained. One final-audit helper naming error
also remains in the receipts; the corrected audit passed.

**1,345 protected records are byte-identical**, including original/configuration/
manifest/frozen-code records, every inventoried historical pool/ledger/guard,
both D03 shares and the external allocation registry. The normal share's counters
remain zero; verification remains sealed. This scoped preservation check does not
claim another full audit of D03's 24,140 historical audio/feature files.

The D04-only 224 MiB QA / 256 MiB combined-output / 24 cumulative-invocation
amendment is enforced alongside the unchanged 600 aggregate seconds, 120 seconds
per worker, one numerical thread, source allowance and 16 MiB metadata / 64 MiB
media limits. Every earlier attempt and spent charge remains counted; final
settled usage and per-pool hashes are in [the machine evidence](D04_LISTENING.json).
The policy-denied 227-file, 33,997,853-byte incomplete D04 fixture remains intact.
No historical C01 staging was removed or retried. Temporary output peaks and
retained files are included; no extra environment, distribution or private
closure was copied. Combined inherited managed storage, the full 512 MiB normal
reserve and the entire amended D04 allowance are bounded at **3,525,964,315 bytes**,
below 4 GiB. Final free space exceeded 190 GiB, with required headroom reserved.

## Optional human response

Listening review **pending**. Ten items are available on the page; **0 rated,
0 similar, 0 different, 0 unsure, 10 unanswered**. No response from Leonardo has
been received. No play event, successful seek or generated description is a rating.

The reference question concerns the intended recording/section and the sound
within the mixture; an ordinary description or “unsure” is sufficient. Optional
card answers are similar type of sound, different, unsure, or not listened, with
a short reason. A reply such as `reference: …; D04-01 similar; D04-02 different;
D04-03 unsure` works without a form/account or ten mandatory labels.

Local saves create private, immutable response revisions. JSON export/import is
review-bound and explicitly reports status; browser storage alone is a draft.
Raw notes remain ignored. Partial, mixed, negative, absent and declined reviews
are supported independently of the engineering outcome. A wrong section/layer
response stays attached to this full-mixture query; a new crop/search requires a
later concrete task. With one reference/listener, responses supply qualitative
evidence, not calibrated precision or an explanation of the model's failure cause.

No E01 work, retuning, experimental-policy promotion, new acquisition or inference
is part of D04. D02's failed event-multi coverage gates remain unchanged.
