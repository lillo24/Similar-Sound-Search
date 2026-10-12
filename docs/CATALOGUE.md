# A03 catalogue commands and contracts

A03 acquires actual local audio for discovery and retains immutable provider bytes. It adds one Internet Archive adapter and explicit local import, using A02's CPU decoder, channel/crop/resample preparation, timestamp maps, project lock and resource tiers. Acquisition does not establish timbre relevance. A04 owns evaluation material, A05 matchers, and A06 search/playback.

## Run and resume on Windows

From the repository root, reuse the project environment:

```powershell
.\scripts\setup.ps1 -PythonExecutable "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter --take 12
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter
```

Repeat the last command when a bounded invocation stops. Each invocation dispatches at most 64 workers and stops dispatching at 600 seconds; each worker has the existing 120-second hard deadline. The durable asset cursor advances beyond completed entries, including across a 64-operation boundary. At the end of a complete pass it returns to zero, so another unchanged pass verifies the catalogue again. Changing `--take`, refresh mode, or the frozen selection starts a separate verification pass, retaining all originals and the job's cumulative budget.

```powershell
.\.venv\Scripts\sound-search.exe --tier starter catalogue verify --job starter
```

Repeat verification after a batch stop until `stop_reason` is null. It checks original bytes, preparation metadata/bytes and sample metadata through the shared A02 reuse checks. Repeated unchanged acquisition/verification does not poll or download provider audio and does not regenerate valid derivatives. Verification consumes the same finite job time allowance. `status: failed`/exit 1 identifies a failure or resumable bound; `assessment: partial` separately records a requested-count shortfall. A successful 12-item pilot does not mean the complete requested catalogue is acquired.

Linux equivalents use `.venv/bin/sound-search` after the documented A02 setup. The implementation uses standard paths/locks and native TLS trust; A03's live evidence is Windows only.

## Source, selection and rights

[config/catalogue.json](../config/catalogue.json) is the complete, finite policy. The single source is Internet Archive's `blocsonic` collection, using the [metadata API](https://archive.org/services/docs/api/md-read.html) and individual download URLs. [blocSonic](https://blocsonic.com/) publishes Creative Commons releases in varied genres. This is a bounded label sample with a hip-hop bias, not representative music sampling.

The frozen search requests at most 600 identifier/licence/subject/creator rows, sorted by provider identifier. Audio licences accepted by this adapter are CC BY, BY-SA, BY-NC and BY-NC-SA versions 1.0–4.0 where documented by the item. Missing/unsupported licences and ND licences are excluded conservatively. The local run is noncommercial research; attribution, licence URLs and evidence hashes remain with each asset. No audio is published. Audio rights are separate from provider metadata and code licences; no blanket metadata licence is inferred. Future redistribution/commercial use needs its own source-specific assessment. [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) documents that licence's terms.

Explicit provider title qualifiers `(Snippet)`, `(Preview)` or `(Excerpt)` classify an available track as an excerpt during frozen selection, including selection from cached release metadata. Its original-master offset remains null. Other release-track files retain the provider full-track classification with unverified external-master alignment. Neither filename nor duration establishes a known original offset. A03 preserves a prior selection snapshot when correcting the initially missed snippet qualifiers.

Item order is ascending SHA-256 of canonical JSON `{"selection":"a03-ia-1","identifier":ID}`. Inspect the first 80 qualifying releases. The policy accepts track files of 30–360 provider-declared seconds and at most 5 MiB, with explicit track artist/title and provider MD5. Select one eligible encoding per provider release/track position (or explicit original-file relationship), preferring an uploaded original over a provider derivative, then smaller bytes and filename. Preserve eligible alternative URLs/checksums as aliases.

Round-robin casefolded provider genre and artist, with track order determined by SHA-256 of the canonical provider recording ID, selects up to 120 recordings and at most four per artist. These are coverage fields, not timbre labels or similarity scores. Numeric/unrecognised genre strings remain provider metadata and do not establish a musical category. The selection records actual search/item/track/artist populations, exclusions, exact ordering and hashes. The pilot justified expanding from 60 to 80 releases; no A02 resource ceiling was raised.

An existing job refuses an implicit policy change. An explicit coverage revision uses the same frozen search, preserves selection history and retains the cumulative ledger:

```powershell
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter --take 12 --reselect
```

Use this only after an intentional policy edit. Provider, query and search-row snapshot identity cannot change within that job. Failed release metadata may be retried during explicit reselection. Normal resumption preserves the recorded source failures/exclusions. A fresh checkout can acquire from the versioned frozen `sources/` descriptors without resampling live search metadata; missing private descriptors are restored from those sanitized files.

FMA's [official repository](https://github.com/mdeff/fma) documents 342 MiB metadata and a 7.2 GiB small MP3 archive; the latter exceeds the 512 MiB tier. [MTG-Jamendo](https://github.com/MTG/mtg-jamendo-dataset) likewise distributes large MP3 archives with separate permitted-use terms. Neither bulk downloader, archive, historical environment, nor selective ZIP adapter is installed/run. Direct individual Archive files avoid whole-archive transfer/extraction and range-integrity complexity.

## Decoder and analysis policy

WAV/FLAC remain supported. The smallest format addition is **MP3/MPEG Layer III** through pinned SoundFile 0.13.1/libsndfile 1.2.2. The [SoundFile 0.13.1 API](https://python-soundfile.readthedocs.io/en/0.13.1/) supports the exercised sequential read/write route. MP3 Layer I/II, OGG, AAC/M4A and other previously unsupported encodings remain refused. No FFmpeg, GPU, model or external decoder process is introduced. The only new dependency is pinned `truststore==0.10.4`: [its public SSLContext API](https://truststore.readthedocs.io/en/latest/) uses native certificate verification and can fetch missing intermediates on Windows. Python's default TLS context failed this provider's chain on the actual machine; native verified TLS succeeded. Verification is never disabled.

All original samples are decoded sequentially as float32 with preserved channel order. Source bytes, source format/subtype, decoder/library versions, decoded rate/channels/count/duration and canonical PCM identity are retained. A decoded WAV derivative of MP3 is still a **lossy-source derivative**; it does not become a lossless recording. Silent/non-finite/truncated/unsupported audio is rejected. Provider expected size and MD5 catch changed/truncated transfers before original publication; local SHA-256 identifies the retained file. Structural decodability is not proof that an undocumented source was never edited or truncated before publication. Some live files emit non-fatal ID3 text-encoding warnings despite successful complete audio/PCM validation; the evidence report identifies them. Identity/licence fields come from the pinned provider JSON, and immutable originals retain their metadata defects.

Known generated, gapless-tagged MP3 fixtures at 32/44.1/48 kHz decode to exactly two seconds and preserve the two planted event maxima at their independently known sample positions. This verifies this encoder/decoder route, including its interpreted delay/padding metadata. Arbitrary encoders, absent gapless metadata, external master alignment, and compressed random seek remain unverified. The catalogue's source-time coordinate is the **full sequentially decoded available file**. Future original passage playback must decode that file sequentially and slice decoded coordinates, rather than assuming sample-exact MP3 seek. Ordinary release-track files retain provider full-track classification, explicit provider snippet qualifiers become excerpts, and all original-master offsets remain null; names/duration never establish a known offset.

The explicit analysis derivative preserves mixture channels, resamples to 16 kHz and takes a centred excerpt of at most 30 seconds. Start is `max(0, int((decoded_duration - 30)/2))`; end is `min(int(decoded_duration), start+30)`. Inputs under one second use the complete input; all other rounding/resampling comes from A02. Originals remain full-length and immutable. This bounded coverage does not promise search over every original passage. The derivative's A02 record composes back to source-file seconds; known local offsets are applied once, unknown offsets stay null.

## Import an explicitly authorised local file

No authorised local music was supplied in A03's explicit project input locations. Imports require the actual explicit file and an [A02 context](../config/input_context.example.json) with nonempty `provenance.permitted_use`. Unknown identity/version/offset can remain unknown. Private paths/context stay in ignored job records; local catalogue metadata stays in `manifests/private/catalogue/JOB`.

```powershell
.\.venv\Scripts\sound-search.exe --tier starter catalogue import 'data/audio/incoming/authorised.wav' --context config/local/authorised-context.json --job local-music
.\.venv\Scripts\sound-search.exe --tier starter catalogue verify --job local-music
```

Repeating the same import checks source byte/config/tool identity without duplicating entries. Changed explicit local bytes produce a new immutable original and derivative identity; old originals remain available for inspection. No unrelated personal directory or implicit music library is scanned. Use `--data-role engineering` when exercising this command with generated fixtures; those assets are separately labelled and never count as real discovery music.

## Durable accounting and recovery

The original A02 ceilings stay unchanged: starter 512 MiB cumulative download, 4 GiB managed disk, 4 GiB free-space headroom, concurrency one, per-input decoded/working/output caps and 120-second worker deadline. Smoke has zero network allowance. Managed accounting now also includes `manifests/catalogue/`; originals, derivatives, source metadata, receipts, reports, selection history and retained partials all count. `.venv` and package caches remain setup costs outside the audio-artifact quota.

The accounting unit is **HTTP response-body bytes returned to the application stream plus unresolved conservative read reservations**. Headers, TLS/transport overhead and browser research/setup traffic are not metered as acquisition payload. Metadata, audio, redirects/error bodies actually read, retries and partial reads all count. Each read reserves up to 1 MiB in an fsynced ledger before the network call; measured bytes settle that reservation. Error/redirect body reads are capped at 64 KiB. A killed or failed unmeasurable read leaves its reservation charged. `charged_bytes - received_bytes` therefore identifies conservatively charged uncertain transfer. Resuming or reselection never resets it. Advertised size is checked before transfer; missing sizes are bounded during streaming. Identity HTTP encoding avoids unaccounted decompression. There is no range request or archive extraction.

The locked worker inventories managed disk once and accounts exact owned file-size changes between checks; it refreshes the inventory before and after A02 preparation, whose writer has its own complete allocation preflight. Every worker/crash restart starts from actual disk. Free-space checks still occur before writes. The pilot exposed excessive directory scans/fsyncs at 64 KiB read granularity; the final 1 MiB reservation window and explicit file accounting reduce that overhead without increasing any resource ceiling. Disk preflight remains an estimate assuming no unrelated external writer, not an OS storage reservation.

Each URL has two attempts, 10-second request/read timeout, 0.25-second linear retry backoff, and at most three redirects per attempt. Only public HTTPS Archive hosts are allowed; credentials/signed audio URLs are refused. Every request/redirect counts toward the lifetime 600-attempt cap. The controlled HTTP test server is explicitly enabled only in function-level tests; it is not a production CLI bypass.

The job reserves each worker's possible wall time before dispatch and settles observed wall time afterwards, including library startup. Unsettled worker reservations remain charged after a crash. The initial policy sets **2,400 cumulative worker seconds**, 600 seconds per invocation and 64 operations per invocation; repeated invocations cannot become an unlimited batch. Existing job ceilings can decrease but never replenish when the tier or policy changes. A run stops visibly on an exhausted allowance; it does not increase the tier to reach a count.

Downloads use owned staging files and validate before publishing content-addressed originals. Completed originals survive a later derivative interruption; resumption validates and prepares them without redownload. Rejected/partial files stay under ignored job staging, never count as ready and still consume disk. Existing corrupt originals/derivatives are preserved and cause an invalidated state: inspect/quarantine the **specific reported owned artifact**, then explicitly remove it and rerun (with `--refresh` when reacquiring original bytes). Do not delete the ledger to replenish budget.

Unchanged resumes deliberately use pinned source snapshots; they make no claim about today's remote content. `--refresh` explicitly downloads/checks the pinned payload. Changed bytes/checksums become a visible rejection. A failed refresh cannot silently fall back to the old cached ready state; repeat the explicit refresh after resolving access/content changes. A new provider revision requires a separately documented catalogue version, not an allowance reset to evade an exhausted job.

Public ready records describe successful validation on the delivery machine, not guaranteed file availability on another checkout. Local readiness additionally requires private registration and present matching assets. Use `catalogue verify` before consuming a transferred catalogue. Its bounded pass verifies full original and derivative hashes; summary counts distinguish missing/unregistered local assets. Per-record descriptors and the small selection/group/summary layout keep every JSON document within the existing 1 MiB reader limit.

Once the real catalogue exceeds the 256 MiB smoke-tier managed-disk ceiling, run the same offline diagnostic under starter:

```powershell
.\.venv\Scripts\sound-search.exe --tier starter smoke
```

It remains offline and does not use the download allowance. The unchanged default smoke tier correctly refuses a project footprint above its own ceiling.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\sound-search.exe --tier starter smoke
git diff --check
```

Routine tests are fully offline, including deterministic localhost HTTP failures. Live provider commands are separate and measured in [A03_CATALOGUE.md](../reports/A03_CATALOGUE.md). All existing A02 tests remain required because decoding/storage/resource/CLI code changed. The former unsupported-format fixture now uses OGG because valid MP3 is intentionally supported; dedicated MP3 timing/truncation tests cover the new contract. No hosted CI workflow is added.
