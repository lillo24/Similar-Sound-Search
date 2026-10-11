# A02 runtime evidence — 11 October 2026

**A02 is complete; ready for A03.** This report covers engineering correctness on the actual Windows machine available to this Codex session. It is not a cloud-runner hardware description or evidence of retrieval/perceptual quality. The actual Loulou file was absent from supplied inputs and the explicit project audio locations; its original reference manifest remains unverified and its experiment status is **not run**.

Implementation base: `6bce07d` on `main` (A02 handoff, PR #2). Executed code identifies itself as package `0.2.0`, pipeline `a02-preparation-3`; the implementation PR/merge history identifies the delivered revision. [Runtime instructions](../docs/RUNTIME.md) and [resource configuration](../config/resource_limits.json) are the reproducibility sources of truth. Private JSON reports, exact local input paths, generated audio, environment, and caches remain ignored.

## Detected and exercised environment

| Item | Observed evidence |
| --- | --- |
| OS / shell | Windows 11 Pro x64, WMI version 10.0.22000; PowerShell 7.6.5 |
| CPU | Intel Core i5-4690 @3.50GHz, 4 cores / 4 logical CPUs (WMI); worker numerical threads limited to 1 |
| RAM | 17,118,912,512 bytes visible (~15.94 GiB); 9,461,260,288 bytes available at final pilot start (~8.81 GiB) |
| Project-volume free disk | 361,260,527,616 bytes at final pilot (~336.45 GiB); a changing measurement, not reserved capacity |
| Optional GPU | `nvidia-smi`: GTX 1660 SUPER, 6144 MiB VRAM, driver 610.88; no GPU framework installed or compute exercised |
| Interpreter | Bundled Python 3.12.14 successfully created project `.venv`; PATH Python entries were Store aliases, and py/uv were absent |
| Package tooling | venv pip 25.0.1; delivered setup and repeat setup succeeded; editable wheel built; `pip check` passed |
| Executed numerical/audio libraries | NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1, wheel-bundled libsndfile 1.2.2 |
| External decoders | FFmpeg/ffprobe absent on PATH; no external decoder installed |
| Route | Offline CPU WAV/FLAC; Linux, GPU compute, lossy codecs, compressed seek and playback unverified |

Setup downloaded approximately **67.7 MB** of wheels according to pip's transfer output (not an exact network-byte meter); `.venv` occupied **258,711,233 bytes** (~246.73 MiB) at measurement. These are one-time environment costs, separate from the offline smoke and managed audio/run budget. The repeat setup reused the pinned installed packages. No model, dataset, catalogue, paid service, private upload, or deployment was needed.

## Final offline pilot

Executed the delivered console command twice after the deterministic WAV writer fix:

```powershell
.\.venv\Scripts\sound-search.exe smoke
```

| Measurement | New derivative | Validated reuse |
| --- | --- | --- |
| Result | `ok`, `reused: false` | `ok`, `reused: true` |
| CLI wall time including worker startup | 1.281s | 1.312s |
| Smoke operation time after numerical imports | 0.219s | 0.219s |
| Managed bytes at worker measurement | 1,108,746 | 1,109,298 |

Managed bytes include earlier development derivatives, diagnostic reports, and redirected command output. They are measured before the current parent-written report/stdout; they are **not** an estimate of a fresh catalogue or proof of constant process RSS. The final pilot's two audio fixtures and one bundle total **469,451 bytes**: PCM WAV 384,044; FLAC 14,252; derivative WAV 64,058; record 7,097. Reports add their own bounded size. No runtime download occurred.

The deterministic stereo fixture has 96,000 frames at 48kHz (2 seconds). Its left 0.5-amplitude 1kHz sine occupies file seconds 0.25–0.75; right channel has a single 0.75 impulse at source frame 48,000. Independent RMS expectation is `sqrt(1/32)` within one PCM16 step, and FLAC decoding reproduced the source PCM samples exactly.

Preparation selected channel 1, cropped file seconds 0.5–1.5, and resampled to 16kHz. It produced exactly 16,000 mono frames and the impulse maximum at frame **8,000**, mapping to source second **1.0**. Observed event shift was zero samples on this case; declared tolerance is one output sample (62.5 microseconds). Separate 44.1kHz tests check ceil count and fractional unmapped tail. No lossy decoder/seek delay tolerance was measured.

- Original fixture byte SHA-256: `55bb9dc9637c4bb56af04d0314a47b8c28c561d9b8c52893c71ab00b9e65896d`.
- Final derivative byte SHA-256: `45bced6b0a275e0c1170af22ef22cbce14cae93b99a679dc9560f6183d0bbbb6`.

The final review detected libsndfile's clock-dependent float-WAV `PEAK` chunk. The output path now uses the already-installed SciPy WAV writer; a regression test rebuilt after 1.1 seconds and compared complete bytes and records successfully. This is why pipeline version 3 invalidates earlier development outputs.

## Validation results

- **32 unittest cases passed**, final full run 7.633s. [Test ownership](../tests/README.md) covers known measurements/hashes, all 21 accepted WAV/WAVEX/RF64/FLAC encoding combinations, corrupt/unsupported/silent/non-finite inputs, bounds/context failures, explicit channel behavior, sample rounding, known event timing, full-track/known-excerpt/unknown-excerpt maps, offset-once composition, immutable originals, deterministic bytes/reuse/change invalidation, output/memory/disk refusals, atomic failure recovery/containment, OS locking, actual worker hard timeout, and missing-reference smoke.
- Ruff static checks passed; Ruff formatting check passed on all 13 Python files. `pip check` passed, setup/editable build succeeded, and the installed console entry point was exercised.
- Delivered file and directory `inspect`, explicit `prepare`, and a successive `--parent-record` preparation ran successfully. An actual CLI run with `max_input_bytes: 100` refused the 384,044-byte input with `ResourceError`, exit 1 and a failure JSON report; rerunning under the standard profile succeeded. This tested refusal/recovery, not an automatic budget increase.
- Local documentation/link/JSON, Git-exclusion, preserved-input and whitespace checks form the delivery review recorded by the implementation PR. No GitHub Actions workflow or required CI status existed; no nonexistent CI pass is claimed.

The resource tiers derive from the observed RAM/CPU/free disk and this small pilot. Smoke is 20s / 256 MiB estimated working allocation / 256 MiB managed disk with 1 GiB free headroom. Starter is a conservative unmeasured ceiling of 120s / 1 GiB working / 4 GiB managed with 4 GiB free headroom. Future starter download and model-shortlist contracts are 512 MiB total and 3 candidates; their actual consumers are A03/A05. Larger workloads and throughput have not been measured.

## Remaining input and handoff limits

Still needed for a Loulou-specific experiment: the actual **daoud — Loulou & the loulous** audio from the marked version, either full recording or the existing excerpt around 3:38–4:00, plus available version/provenance and verified excerpt offset evidence. Unknowns can remain null; a readable candidate does not prove identity. The requested 218–240 seconds never becomes an automatic crop, and event selection belongs to B01. Missing reference audio does not block A03's independent catalogue work.

Accepted input capabilities are bounded PCM/IEEE-float WAV (including WAVEX/RF64) and lossless FLAC. MP3/AAC/M4A/OGG/Opus/AIFF and ADPCM/companded WAV are explicitly refused. There is no acquired discovery catalogue, retrieval benchmark, winning model, search result, or measured relevance. The first required listening review remains D04; no similar/dissimilar examples are requested now.
