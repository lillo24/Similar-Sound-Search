# A03 — Catalogue acquisition evidence

Measured on 12 October 2026 on the local Windows CPU route. **Assessment: partial.** Acquisition/ingestion is implemented and exercised against actual provider audio; the requested 120-recording catalogue is not represented as complete. Final quantities and budget stops are recorded below and in the [frozen catalogue](../manifests/catalogue/starter/summary.json). Retrieval/perceptual quality is unmeasured; no Loulou experiment was run.

## Environment and implementation

Started from current main `3c1f469`, after pulling the A03 prompt; A02 was merged through [PR #3](https://github.com/lillo24/Similar-Sound-Search/pull/3) at `2a14cb0c0065d53149269296b84f0c39acdaf1de`. A03 uses dedicated branch `codex/a03-starter-catalogue`, with PR/merge history as the delivery record. No extra worktree was created.

Python 3.12.14, NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2 and Ruff 0.11.13 run in the project `.venv`. Windows 11 x64, Intel i5-4690/four CPU threads and approximately 16 GiB RAM remain the available route. A detected GTX 1660 SUPER/6 GiB does not establish GPU compute; processing stays on CPU. No FFmpeg/ffprobe or GPU framework was installed.

The pinned existing decoder reads/writes MP3 Layer III. The one added dependency, `truststore==0.10.4`, supplies its public native `SSLContext`: default Python TLS failed the Archive certificate chain on this machine, while native verified TLS succeeded. Certificate verification stays enabled. Its approximately 18.7 KB wheel plus 4.4 KB package metadata are setup traffic, separate from the acquisition ledger and A02's historical environment costs. Editable package version is 0.3.0. [Commands/contracts](../docs/CATALOGUE.md) and the [source map](../src/similar_sound_search/catalogue/README.md) describe ownership and recovery.

## Source/access decision

Rechecked the [official FMA documentation](https://github.com/mdeff/fma): its 342 MiB metadata archive and 7.2 GiB small audio archive are inappropriate default transfers under a 512 MiB cumulative starter budget. Track audio licences are separate from metadata/code terms. The [official MTG-Jamendo repository](https://github.com/MTG/mtg-jamendo-dataset) also distributes large archives. Neither bulk downloader, historical environment nor archive/range adapter was installed or run.

Chosen source: individual MP3s in Internet Archive's `blocsonic` collection, using the [documented metadata API](https://archive.org/services/docs/api/md-read.html) and direct file downloads. [blocSonic](https://blocsonic.com/) publishes Creative Commons releases; the adapter requires item audio-licence evidence and retains per-track attribution, licence URL, snapshot hash and expected provider MD5. It accepts CC BY/BY-SA/BY-NC/BY-NC-SA 1.0–4.0, conservatively excludes ND/missing/unsupported licences and keeps this run local/noncommercial. Audio is not committed or published. Metadata/code licensing is not inferred from audio licensing. For example, [BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) requires attribution and noncommercial use, with conditions for shared adaptations.

The first verified requests established selective audio access; ordinary file URLs returned bounded Archive-host redirects followed by HTTP 200. No range requests or archive extraction occurred. Raw response snapshots, request receipts and full failures remain ignored locally; sanitized descriptors retain their URLs, dates and hashes. Browser research/setup traffic is outside the explicitly defined application-payload ledger.

No authorised local music or Loulou attachment was present in the explicit project input locations. The local import demonstration uses a labelled generated engineering fixture and contributes zero real recordings. The unverified Loulou manifest and archived prompts remain unchanged.

## Frozen population and selection

Search query: `collection:blocsonic AND mediatype:audio AND licenseurl:*`, rows 600, provider identifier ascending. The frozen response contains **424 releases**, all returned; **172** have a supported licence. Eligible releases are ordered by SHA-256 of canonical `{"selection":"a03-ia-1","identifier":ID}`.

The initial 60-release pilot yielded 276 eligible recordings across 31 artists, with 98 selectable under the artist cap. The explicit revision to 80 releases reused the same frozen search and cumulative ledger, recovered a failed metadata fetch and retained selection/policy history. No A02 resource ceiling increased. The final sample has **370 eligible provider recordings across 35 artists**, **106 selected for 120 requested**, with **603 file-size and 6 duration-policy exclusions**. These exclusions count candidate file encodings, not independent songs. The cap is four recordings per artist, 30–360 declared seconds and 5 MiB per audio file. Fourteen requested places cannot be filled by this frozen sample/filter combination even if all 106 selected entries become ready.

Final selection SHA-256: `0d0b92e157ef81efe42625d4c3c3d8a8899bc5e2f598d1fb26c49f18ff07cd3a`. The expanded pilot previously used `613d35ebaaa035cf6b0a910c641e1baa05b5def64381854bc4535ca335dd8c50`; final explicit reselection corrected provider-labelled snippets to unknown-offset excerpts without changing selected recording IDs or replenishing any allowance. See [selection](../manifests/catalogue/starter/selection.json), its saved predecessor, and per-entry `sources/` descriptors. Selection round-robins casefolded provider genre/artist and SHA-ordered recording IDs. It preserves eligible alternate-encoding URLs/checksums, preferring uploaded originals, then smaller bytes/filename. Titles alone never determine equality. Artist/genre metadata determines coverage only, never a timbre label or retrieval score. This single-label sample remains hip-hop biased; raw genre `(4294967295)` is unrecognised metadata, not a musical category.

## Actual runs and quantities

The first exploratory requests and all production source GETs used the same `starter` ledger, created at `2026-10-12T10:06:05.776175+00:00`. Preliminary default-TLS failures received zero bytes but consumed attempts; a small search probe and successful metadata probes remained charged. Their measured request time was added before production coordination. Idle development, browser research, setup and offline tests are outside acquisition worker time.

| Checkpoint | Real/distinct ready | Artists | Usable original seconds | Analysis seconds | Cumulative received/charged payload | Cumulative attempts | Cumulative charged worker seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial 60-release bounded invocation | 3 | 3 | 476.077052154195 | 90 | 17,934,962 bytes | 83 | 461.028 |
| Expanded 12-recording pilot | 12 | 11 | 1676.091111111111 | 360 | 53,389,952 bytes | 130 | 936.121 |

The first invocation ended at its 64-operation limit and recorded metadata timeout `BSMX0130`; this was a visible resumable stop, not an empty-success fallback. The expanded pilot completed successfully with `assessment: partial` against 120. Its invocation took 497.484 seconds (CLI wall 497.750); managed artifacts totaled 96,677,928 bytes. Every pilot recording was provider full-track material, with external-master offsets unknown. Pilot evidence justified the 80-release coverage revision within the same 2,400-second job allowance.

Final assessment: **partial, 72 distinct real recordings from 35 artists for 120 requested**. All 72 are locally retained and fully validated, with zero established duplicate assets. The frozen selection is 14 short; another 34 selected recordings remain not ready after the finite job-time stop. This is 28 below the lower 100-recording target, with exact resource/access evidence rather than synthetic substitutes. No higher tier or new job replenished the allowance.

| Final measurement | Observed value |
| --- | ---: |
| Requested / selected / ready / distinct | 120 / 106 / 72 / 72 |
| Artists | 35 (at most four selected tracks per artist) |
| Original usable duration | 11152.10133786848 seconds (3.098 hours) |
| Prepared analysis duration | 2160 seconds (36 minutes; 30 seconds per recording) |
| Available source kinds | 70 provider full tracks; 2 explicitly labelled unknown-offset excerpts |
| Known external-master offsets | 0; all 72 remain null |
| Source audio | 72 stereo 44.1 kHz MP3 Layer III files; 297,757,623 bytes |
| Analysis derivatives | Stereo 16 kHz float WAV; 276,484,176 bytes |
| Established duplicate assets / alias URLs retained | 0 / 53 |
| Licences | 54 CC BY-NC-SA 3.0; 17 CC BY-NC-SA 4.0; 1 CC BY 3.0 |
| Cumulative received / charged HTTP body | 305,221,282 / 305,221,282 bytes (291.082 MiB) |
| HTTP attempts, including redirects/retries | 256 of 600 |
| Charged worker time | 2400.258 seconds; 2,400-second dispatch allowance exhausted |
| Pending uncertain reads / workers | 0 bytes / 0 seconds |
| Managed storage at final acquisition stop | 588,607,218 bytes |
| Managed storage after setup/import/smoke, before audit report | 589,379,128 bytes (562.076 MiB) |
| Free disk measured by final smoke | 359,339,511,808 bytes |
| Retained staging / abandoned preparation directories | 0 files (0 bytes) / 0 directories |
| Selected entries not ready | 34; never counted as acquired |

The final worker had only 2.820 seconds remaining and was terminated. Its observed process-termination overrun was charged, producing 2400.258 seconds rather than hiding the extra 0.258 seconds. A subsequent `catalogue verify --job starter` dispatched zero workers, returned the explicit exhausted-time failure and left byte/attempt allowances unchanged. This full selected-catalogue verification command could not complete within the acquisition allowance; it is not reported as a pass. Byte/disk ceilings were not exhausted. The earlier provider HTTP 500 for `BS450039/track:2` and `BSMX0130` metadata timeout recovered through explicit resumption/reselection. No permanent rejected public asset remains; incomplete entry 73 never became ready.

The final metadata correction preserved selected recording IDs and saved the prior selection. Its 12-entry warmup completed in 91.360 CLI wall seconds (13 workers, including cached search). The unchanged second 12-entry pilot completed in 27.516 wall seconds: **12/12 reused, zero HTTP attempts, zero charged/received payload delta**, and all **136 original/derivative files** observed across the existing 68 ready entries kept identical size/mtime. The worker-time increment was 17.156 seconds; metadata/ledger updates remain permitted and measured.

The next full pass revalidated old ingestion identities and recovered a prior download failure, stopping after 64 operations (47 reused) in 174.391 wall seconds. Its continuation performed nine operations (four reused) in 140.062 seconds before the lifetime deadline. Both expected bounded stops return exit 1 and `assessment: partial` instead of presenting an incomplete batch as success.

Separate **bounded local validation**, with no acquisition/new ready publication or allowance reset, fully sequentially decoded all 72 ready originals and checked original bytes, canonical PCM, every source sample field, current descriptor/policy/tool identity, prepared bundle hashes and composed mappings. It passed in **63.359 seconds**, within the unchanged 120-second validation bound. This validates the existing subset; it does not turn the incomplete 106-entry acquisition into a completed job.

Coverage labels: Hip-Hop 25, Indie 10, Folk 8, Downtempo/Trip-Hop 4, Improvisation 4, Electropop 3, Punk 3, Electronic / Trap 2, Trap 2, Trip-Hop 2, Hip-Hop / Holiday 2, Downtempo 1, Electronic 1, Pop/Rock 1, Rock 1, and unrecognised `(4294967295)` 3. Six provider titles explicitly say instrumental. These labels demonstrate deterministic coverage, not verified instrumentation or perceptual relevance.

The full audio validation emitted non-fatal mpg123 **ID3 text-encoding/tag-size warnings** for 16 provider files. A separate bounded header diagnosis confirmed all 72 headers still open; all 72 complete sample/PCM/hash checks pass. Artist/title/licence evidence comes from pinned provider JSON, not the affected embedded ID3 strings. Originals were preserved rather than repaired or declared entirely free of metadata defects. Warning provider IDs: `BSOG0054/track:4`, `BSMX0128/track:2`, `BSOG0044/track:3`, `BSOG0064/track:2`, `BSMX0122/track:9`, `BSMX0142/track:3`, `BSOG0061/track:2`, `BSMX0123/track:1`, `MG0016/track:01`, `BSXE0016/track:2`, `BSOG0060/track:42`, `BSMX0140/track:1`, `BSOG0069/track:9`, `BSMX0127/track:1`, `BSMX0152/track:1`, `BSUNI0001/track:1`.

Final setup rebuilt/installed editable 0.3.0 and passed dependency checking. Starter offline smoke passed in 2.813 seconds, with no audio/model/network acquisition and Loulou still unverified/missing. It measured four CPU threads, 17,118,912,512 bytes total RAM and 8,246,575,104 available. The unchanged default smoke tier would refuse this >256 MiB managed footprint; starter runs the same offline diagnostic without changing either tier.

Explicit engineering import, repeated import and private-job verification each passed with one labelled generated two-second recording, zero HTTP/received/charged bytes and **zero real discovery assets**; repeat/verify reused the same original/derivative. The commands executed were:

```powershell
.\.venv\Scripts\sound-search.exe --tier starter catalogue import data/audio/engineering/a02-stereo.wav --context config/local/a03-engineering-context.json --job local-engineering --data-role engineering
.\.venv\Scripts\sound-search.exe --tier starter catalogue verify --job local-engineering
.\.venv\Scripts\sound-search.exe --tier starter smoke
```

The ignored engineering context identifies the project-generated A02 fixture, full-file offset zero with construction evidence, and permission for local tests/derivatives. This command is a demonstration of explicit import, not evidence that user music or Loulou was supplied.


## Audio/identity/timing limits

Original available MP3 bytes (full tracks and explicitly declared snippets) are retained unchanged and checked against provider size/MD5 plus local SHA-256 before publication. Full sequential float32 decode establishes rate/channels/count/duration, finite/non-silent measurements and `sss-pcm-f32le-1` identity. The canonical hash includes canonical JSON rate/channel/count/schema plus LF and frame-major interleaved little-endian float32 samples, with signed zero normalised. No gain, resampling, clipping or perceptual equivalence is implied.

The analysis derivative preserves mixture channels, takes a centred excerpt of at most 30 seconds and resamples to 16 kHz through A02. Full originals remain available; this limited analysis coverage does not promise search of every passage. MP3-derived WAVs remain lossy-source derivatives. Ordinary release-track files retain provider full-track classification; explicit `(Snippet)`/`(Preview)`/`(Excerpt)` qualifiers classify unknown-offset excerpts. Original-master offsets stay null. The verified association is the exact provider file/track, not an independently verified commercial master.

Generated gapless-tagged MP3 fixtures at 32/44.1/48 kHz independently establish exact two-second decoded counts and planted event positions for this route; truncated fixtures fail. Arbitrary encoder priming/padding, absent gapless metadata, compressed seek and external master alignment remain unverified. Future playback must decode the original sequentially and slice its decoded-file coordinates. Known local excerpt offsets compose once; unknown offsets remain file-relative/null in the original timeline.

Groups cover exact bytes, equal canonical decoded samples, repeated provider IDs and explicit provider recording-family evidence. Alias provenance stays intact. Unverified local IDs/titles never establish equality; unknown lossy re-encodings/edits/near-duplicates remain outside coverage. No evaluation split, feature index, model, matcher, separation or search result was created.

## Commands actually exercised

PowerShell, repository root (private stdout reports are optional copies):

```powershell
.\scripts\setup.ps1 -PythonExecutable "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter --take 12
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter --take 12 --reselect
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter
```

The full acquire command was repeated after bounded batch stops, retaining completed originals, partials, frozen descriptors and the same cumulative ledger. Exact final repeat/verification and explicit engineering import evidence follow in the final measurements. Do not delete the ledger or invent a fresh job to replenish this run's allowance. An exhausted finite lifetime allowance remains an explicit stop; A04 can consume the existing validated subset without further acquisition.

## Validation and delivery limits

The complete offline suite passes **58 tests**, including all 32 A02 tests and 26 catalogue tests. Coverage includes independent PCM answers across WAV/FLAC, MP3 timing/truncation, deterministic coverage/caps/aliases/rights, actual local and localhost-HTTP ingestion, unchanged zero-download reuse, interrupted preparation recovery, changed payload/provenance/config/decoder identity, cached corruption, original immutability, full/known/unknown offsets, duplicate grouping, CLI imports/orphan-lock refusal and durable batch cursor, misleading headers/errors/redirect/timeouts/retries, cumulative byte/time reservations and locked cached-disk accounting against actual files. The unsupported-format fixture changed from MP3 to OGG because MP3 support is intentional; tests were not weakened to conceal a failure.

Executed local validation:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

The final full suite passed 58 tests in 32.216 seconds. Ruff lint and format verification passed for all 19 Python files. Dependency checks reported no broken requirements. Local Markdown targets, all public JSON reader-size bounds/self-hashes/frozen descriptor digests and private-artifact exclusions were checked. Setup/smoke/import/final asset audit results are included in the final measurements.

Every versioned JSON is bounded by the existing 1 MiB reader limit; per-entry layout avoids an unreadable aggregate. Public metadata describes successful validation on this machine, while another checkout needs local audio/private registration before counting readiness. Complete originals and valid derivatives survive resumes; unchanged runs make no claim about current remote freshness. Explicit refresh rejects a changed pinned payload and cannot silently reuse an old ready state after failure.

No hosted workflow exists in the inspected repository; no CI pass is claimed or workflow added. Local checks validate the changed runtime, packaging, source/storage/resource contracts and documentation. GitHub delivery requires push, PR, clean mergeability/current main/status/review checks, merge and task-branch cleanup. The resulting PR is the durable delivery reference.

## A04 handoff

Use the validated local discovery subset and its current [group mapping](../manifests/catalogue/starter/groups.json); keep engineering and published human-rated evaluation material separate. A04 owns benchmark access, controlled test generation and frozen protocols before A05 model comparisons. Catalogue metadata/genres are not independent relevance labels. Actual Loulou audio/version/offset evidence is still missing and does not block independent A04 work. D04 remains the first required listening review.
