# A02 runtime and input tooling

A02 provides offline CPU audio plumbing, input registration, and bounded preparation. It does not acquire a catalogue, select an event/model, search, play results, or measure timbre/retrieval quality. [A02 evidence](../reports/A02_RUNTIME.md) records the actual Windows session and pilot; [STATUS.md](STATUS.md) describes the A03 handoff.

## Setup

Use **Python 3.12**; `.python-version` records the exercised patch, **3.12.14**. Run from the repository root in PowerShell:

```powershell
.\scripts\setup.ps1 -PythonExecutable python
.\.venv\Scripts\sound-search.exe smoke
```

Pass the full path to an installed Python 3.12 executable if `python` is a Store alias. This session used the Codex-bundled Python 3.12.14 to create `.venv`; it did not install a global interpreter. The setup script was executed successfully on this machine, including its repeat run. It installs binary wheels from `requirements.lock`, then the project in editable mode without resolving extra dependencies. It checks rather than clears an existing environment. Pip's download cache is `.cache/pip/`; both locations are ignored. Initial setup requires package-index access; all runtime operations below are offline.

The exact interpreter selection used on this detected Windows installation can be reproduced without embedding a personal absolute path:

```powershell
$a02Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
.\scripts\setup.ps1 -PythonExecutable $a02Python
```

That bundled location is installation-specific; other machines should select their own working Python 3.12 executable instead of assuming it exists.

The complete pinned resolution is NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1, CFFI 1.17.1, pycparser 2.22, setuptools 80.9.0, wheel 0.45.1, and Ruff 0.11.13. NumPy supplies arrays/measurements, SciPy the documented polyphase resampler, SoundFile its wheel-bundled libsndfile 1.2.2, and Ruff local validation. No GPU framework or external decoder is installed. Pip itself is bootstrapped by Python's `venv` (25.0.1 in the exercised environment); it is not a runtime dependency.

Linux equivalent, supplied for portability but **not executed on this Windows session**:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip --cache-dir .cache/pip install --only-binary=:all: -r requirements.lock
.venv/bin/python -m pip --cache-dir .cache/pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pip check
.venv/bin/python -m similar_sound_search smoke
```

API references checked against the chosen versions: [Python 3.12 venv](https://docs.python.org/3.12/library/venv.html), [SoundFile 0.13.1](https://python-soundfile.readthedocs.io/en/0.13.1/), [SciPy 1.15.3 resample_poly](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.resample_poly.html), [SciPy 1.15.3 WAV writing](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.io.wavfile.write.html), and [NumPy 2.2 mean](https://numpy.org/doc/2.2/reference/generated/numpy.mean.html). These are stable released APIs. The source uses paths rather than Windows file descriptors with SoundFile.

## Commands and private records

`sound-search` and `python -m similar_sound_search` are equivalent entry points. Global flags go **before** the subcommand: `--root`, `--profile`, `--tier smoke|starter`, `--report`. Defaults are the current directory, `ROOT/config/resource_limits.json`, `smoke`, and `ROOT/reports/local/COMMAND.json`. Explicit input/context/parent/profile paths are relative to the current shell directory; a relative `--report` is relative to `--root`.

```powershell
# Diagnostic: generates engineering fixtures and an atomic private JSON report.
.\.venv\Scripts\python.exe -m similar_sound_search smoke

# An explicit file, or a bounded project input directory. No personal-folder search.
.\.venv\Scripts\sound-search.exe inspect data/audio/engineering/a02-stereo.wav
.\.venv\Scripts\sound-search.exe inspect data/audio/engineering

# All processing choices are explicit. Times refer to this input file.
.\.venv\Scripts\sound-search.exe prepare data/audio/engineering/a02-stereo.wav --rate 16000 --channels channel:1 --start 0.5 --end 1.5

# Compose another preparation back to the same original, retaining its offset once.
$a02Prepared = Get-Content -Raw reports/local/prepare.json | ConvertFrom-Json
$a02Bundle = $a02Prepared.bundle
.\.venv\Scripts\sound-search.exe prepare "$a02Bundle/audio.wav" --rate 8000 --channels preserve --start 0.25 --end 0.75 --parent-record "$a02Bundle/record.json"
```

The composed example follows the engineering crop above, whose impulse is at derivative second 0.5. Larger local inputs can use supplied context (replace these paths with real files):

```powershell
.\.venv\Scripts\sound-search.exe --tier starter inspect data/audio/originals/reference.wav --context config/local/reference.json
.\.venv\Scripts\sound-search.exe --tier starter prepare data/audio/originals/reference.wav --rate 16000 --channels mean --context config/local/reference.json
```

Do not use both `--context` and `--parent-record`. Reprocessing an A02 derivative without its parent record deliberately registers it as a new available file and cannot retain earlier lineage.

`inspect` reports entries as `valid`, `silent`, or `invalid`, with SHA-256, frame count/rate/channels/duration, container/subtype, peak/RMS per channel, and candidate source/context records. Hashes identify bytes, not recording identity. Silence means peak <= `1e-12`; it is a valid technical state. Preparation refuses a silent selected passage or a channel mean that cancels to silence. All samples decode to float32; high-resolution inputs are not promised bit-preserving derivatives. Outputs are float32 WAV, with no loudness normalization or clipping.

An explicit file can be outside the project, but directory inventory must be inside `data/audio/`. Directory walking is sorted and bounded, excludes links and `.gitkeep`, and reports unsupported files instead of hiding them. A genuinely empty directory returns `entries: []`. A failed inventory has `status: failed`, nonzero exit, and any completed entries; a resource stop identifies `resume_target`. Inspect that explicit file or a smaller directory to resume. Registration never edits `manifests/references/loulou.json` or silently links a matching filename to it.

JSON reports and bundle records may contain private input paths/provenance; they stay in ignored locations. `--report` only accepts an owned `.json` path under `reports/local/` and atomically replaces that report. stdout contains the result and exit code 0 means success; 1 means failure (argument errors use 2). Disk/concurrency refusals can prevent report writing: stdout then says `report_written: false`, and any earlier report is retained rather than presented as the current run. Check the current exit code/stdout before using a report.

## Accepted and unsupported audio

Accepted extensions are `.wav`, `.wave`, `.flac` (case insensitive); the decoded container and encoding must also agree. Tests exercised all 21 supported combinations on exact small samples: WAV, WAVEX, and RF64 with PCM_U8/16/24/32 or FLOAT/DOUBLE; FLAC with PCM_S8/16/24. The offline smoke specifically exercises WAV/PCM_16, FLAC/PCM_16, and prepared WAV/FLOAT. It reports libsndfile's advertised formats separately from the CLI's accepted formats and exercised smoke decoders.

MP3, AAC/M4A, OGG/Opus, AIFF, ADPCM/companded WAV, and other codecs are refused even if the installed library advertises them. FFmpeg/ffprobe were absent on this machine. FLAC is decoded sequentially in full within the budget; lossy decoder delay and compressed random-seek behavior remain unverified. No compressed-seek or original-audio playback guarantee is claimed.

## Context and timestamps

See [RECORDS.md](RECORDS.md#a02-input-and-prepared-records-version-02) for the additive 0.2 contract and [example context](../config/input_context.example.json). A context's `kind` is explicitly supplied (`unknown`, `full_track`, `excerpt`), never inferred from duration/name. Missing identity/version/permission/offset remain null or unverified. Supplied verified identity requires a recording ID, version, and evidence. A known original offset additionally requires a known kind and offset evidence; a verified full-track start is explicitly zero. This records supplied evidence, not an automated musical-identity detector. Requested recording intervals are never executable crop instructions.

Channel policy is required: `preserve`, `mean` (arithmetic float32 mean), or `channel:N` (zero based). Sample rate is also required; invalid indices/rates are refused. Crop endpoints must be finite decimal seconds, both present, and satisfy `0 <= start < end <= input duration` before rounding. Start rounds down and end up to source frame boundaries; no bounds are clamped. Cropping always acts on the current available input, so a supplied excerpt is not automatically cropped again at 218 seconds.

Resampling uses SciPy's zero-phase polyphase FIR, Kaiser beta 5, with constant-zero padding and reduced integer up/down factors. It preserves elapsed-time scale **1**, not sample indices or playback-speed ratios. Output frames are `ceil(cropped_frames * output_rate / input_rate)`. Known impulse tests observed zero event shift at 48k→16k and 44.1k→16k; the declared event tolerance is one output sample (62.5 microseconds at 16k), not a measured lossy-decoder tolerance. The rounding excess is under one output frame: `unmapped_tail_seconds` records that fractional bin and the source map never extends beyond real original audio.

Every map composes back to the unchanged original available file. Original recording time adds its verified offset **once** after source-file mapping. Unknown excerpt offsets stay null with `basis: excerpt`; unknown full-track/kind offsets use `basis: file`, with no recording-time claim. Prepared `verified_interval` means checked technical source bounds only, not verified reference association or selected sound events.

## Atomic bundles and resumption

Outputs live at `data/audio/prepared/KEY/{audio.wav,record.json}`. The key includes input byte hash, parent/context contract hash, channel/crop/resample parameters, pipeline/package/Python/library versions. A record carries original/derivative hashes, sample counts, tool/parameter hashes, lineage, a composed time map, and a self-integrity hash. Changing source bytes, context, parameters, or tool versions creates a different key. Code that changes processing semantics must bump the pipeline version.

A new bundle is written into its own `.a02-partial-*` sibling and published by a directory rename only after both files are complete. Existing original files and unrelated bundles are never replaced. Reuse checks the requested key, record integrity, output byte hash, and frame/rate/channel metadata. A corrupt existing bundle fails visibly and is preserved for explicit local inspection/removal. This limited derivative reuse is not C04's catalogue-wide scheduler/cache.

SciPy's public WAV writer emits only `fmt`/`fact`/`data` chunks for float32 derivatives. The libsndfile float writer was deliberately avoided because its `PEAK` chunk contains a wall-clock timestamp, changing byte hashes for identical samples. Tests rebuild across a clock-second boundary and compare complete bytes/records. Pipeline `a02-preparation-3` invalidates earlier development derivatives.

Ordinary write failures remove only their owned staging directory. A hard-killed worker may leave an incomplete `.a02-partial-*` directory or `.a02-fixture-*` temporary file: these have no final content key/name, are never reused, and still count toward managed disk use. Rerun the same command to recover; completed bundles are retained. If space is exhausted, inspect and explicitly remove only the identified incomplete item or unwanted local artifacts before rerunning. The OS project lock releases on process exit/crash; its persistent `data/runs/.a02.lock` byte is not a stale-lock error. Publication is atomic for normal process failures, not a cross-filesystem transaction or guarantee against sudden power loss.

## Resource policy

[resource_limits.json](../config/resource_limits.json) is the required machine-readable source of truth. All byte limits use integers; MiB/GiB below mean powers of 1024. The starter tier is a conservative **per-operation/input cap**, not permission to decode an entire catalogue into RAM.

| Limit | Smoke | Starter |
| --- | --- | --- |
| Input file bytes / duration | 16 MiB / 30s | 256 MiB / 900s |
| Channels / input or output rate | 2 / 96kHz | 8 / 192kHz |
| Decoded float32 allocation | 64 MiB | 256 MiB |
| Estimated working allocation | 256 MiB | 1 GiB |
| Estimated output including record reserve | 16 MiB | 256 MiB |
| Total managed disk | 256 MiB | 4 GiB |
| Free disk after estimated writes | >=1 GiB | >=4 GiB |
| Hard worker wall time | 20s | 120s |
| Inventory file count | 16 | 64 |
| Concurrent operations / numerical threads | 1 / 1 | 1 / 1 |
| Reduced resample up/down factor | <=1024 | <=1024 |
| Future download total / model shortlist | 0 / 0 | 512 MiB / 3 |

Enforced now: file bytes before header probing; declared duration/rate/channels before full read; decoded/working/output estimates before allocation/write; managed size and free disk before writes; inventory count; reduced resample ratio; elapsed checks and a child-process hard timeout including library startup; one project operation lock. Worker numerical threads use process-local `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` = 1; there is no global environment change. Metadata JSON is capped at 1 MiB per input record/context, managed disk inventory at 100,000 files plus the deadline, and derivative lineage at 32 prior operations.

Preparation's working estimate is `16 * input_frames * input_channels + 32 * output_frames * output_channels + 32 MiB`; inspection uses `16 * input_frames * input_channels + 32 MiB`. These are conservative array/workspace estimates, **not an OS RSS enforcement guarantee**. Output reserve includes float32 audio, 4096 header bytes, and 1 MiB record headroom. Actual output is checked before publication. File decoding is full sequential reading rather than random seeking, and the CLI kills even a stuck decoder at its wall deadline. Use the CLI for hard timeout and concurrency guarantees; direct Python helpers only perform cooperative checks.

Managed bytes cover `data/`, `reports/local/`, and `manifests/private/`, including incomplete staging. Inputs outside those locations, `.venv/`, `.cache/pip/`, and package-download caches are separate; free-space checks still see their disk cost. Setup's approximately 67.7 MB of wheel downloads and roughly 247 MiB environment are separately reported, not counted as an offline smoke download. A02 has no downloader/model/index implementation: `max_download_bytes` and `max_model_candidates` are explicit contracts for A03/A05, **not presently enforced acquisition/model limits**. No paid services, private-audio uploads, or public deployment are authorized by either tier.

The detected machine had four CPU threads, ~16 GiB RAM with ~8 GiB available, ample local disk, and optional 6 GiB VRAM. The small pilot took about a second; its fixtures and prepared bundle totaled <1 MiB (the measured managed total also includes earlier development runs). The 1 GiB working ceiling leaves substantial RAM headroom; 4 GiB managed disk, 512 MiB future downloads, and three future candidates keep the first catalogue/model attempt bounded. The 120s starter time is an unmeasured upper bound, not a throughput prediction. Stop on refusal, keep completed work, and use an explicitly reviewed local profile (`--profile config/local/limits.json`) or smaller input to resume; do not silently increase budgets.

## Validation

Complete local A02 validation, without model/network/catalogue checks:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\sound-search.exe smoke
git diff --check
```

The setup's successful editable wheel build checks packaging and the installed console entry point is exercised separately. [Tests](../tests/README.md) assert independent PCM sample/RMS answers, known event coordinates and frame counts, three source-time cases, parent composition, corrupt/unsupported/silent inputs, refusal/recovery, and source/cache identity. There is no existing GitHub Actions workflow or required status check; A02 adds no recurring CI cost. These complete commands remain an explicit manual validation route for later integration checkpoints. Linux execution, GPU compute, lossy decoding/seek, actual Loulou inspection, and retrieval quality have not been validated by this Windows run.
