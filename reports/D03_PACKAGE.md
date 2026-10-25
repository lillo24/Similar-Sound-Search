# D03 package delivery

25 October 2026. **Complete technical delivery; D04 has not started.**
Repository review/merge artifact: [PR #32](https://github.com/lillo24/Similar-Sound-Search/pull/32).
[Sanitized machine evidence](D03_PACKAGE.json) contains exact job/result/media IDs,
resource counters, source hashes, checks and the ordered D04 cards. The private
catalogue, checkpoint, runtime outputs and local archive are retained locally.

## Actual artifact and exercised launch

- Archive: `dist/similar-sound-search-d03-1.0.0.zip` — **292,441,732 bytes**.
- SHA256: `062f97ac056f75f664440c0bfc45caaea3ed7e52023d6568704098dda7808901`.
- Application wheel: `wheelhouse/similar_sound_search-0.3.0-py3-none-any.whl` — **460,148 bytes**.
- Wheel SHA256: `239ce5dd302eef45b1acd296fe84906128b1727a4c941b40b1d3254eda145e0b`.
- Application/build source: `a19b6af306bba6ba1ee77248560cd665ac003273`. Later commits add reports/navigation only.
- Release inventory SHA256: `b0a244af081c1854fd302c3978aee1f3505b1fdd3787c0cc0bdff33fa0b95920`.
- Supported/exercised target: **Windows 11 / AMD64 / exact Python 3.12.14**,
  observed OS `Windows-11-10.0.22000-SP0`, CPU Torch **2.6.0+cpu**.
- Distribution **d03-1.0.0**, core **0.3.0**. Every core/optional pin is unchanged.

The final installed environment is `%USERPROFILE%\Documents\Sound Search D03 à\installed`;
the extracted code was moved from `code è` to `code à` alongside it. The private
workspace moved from `C:\SSS D03 è\w` to **`C:\SSS D03 à\w`** on the same Windows host.
The environment stays at its installed path because Windows launchers embed it.
No second physical machine was tested. Start from an unrelated directory:

```powershell
& "$env:USERPROFILE\Documents\Sound Search D03 à\installed\Scripts\python.exe" -I -m sound_search_distribution start --workspace "C:\SSS D03 à\w" --port 8776
```

Open **http://127.0.0.1:8776/** and use **Open a completed search**. Ctrl+C stops
owned work. Foreground acceptance servers/browser processes were stopped after QA.
[PACKAGE.md](../docs/PACKAGE.md) gives install, prepare, doctor, restart, relocation,
backup and explicit stopped-request abandonment commands. Example verification:

```powershell
& "$env:USERPROFILE\Documents\Sound Search D03 à\installed\Scripts\python.exe" -I -m sound_search_distribution doctor --workspace "C:\SSS D03 à\w" --deep
```

The standalone archive `setup.py verify` passed again after the code-folder move.
Setup uses the verified 18-wheel closure offline and runs `pip check`; it does not
fetch models/audio or install editably. Actual console, UI and workers import their
installed wheel. `-I` startup has no checkout path in `sys.path`; non-editable
`direct_url.json` identifies the installed wheel. Windows worker bootstrap restores
only that interpreter's explicit package paths and times the actual worker PID.
The isolated environment was created once with the complete offline closure, then
updated non-editably to the final application wheel as the retained repairs landed.
All final pins match. A second full environment installation was not repeated.

## Package and private prerequisites

The wheel includes all three web assets, the unchanged vendored EfficientAT MIT
notice and dependency-notice guidance. Dependency wheels retain their original
license files. The public archive contains no private audio, checkpoint, feature
array, runtime ledger, session token or personal absolute path.

The separate private closure contains **3,518 files /
812,191,037 bytes**. Its original relative paths and producing
identities remain intact: 72 real catalogue recordings, the MN04 checkpoint, actual
C01/C04/query dependency graph, arrays and three exact completed D01 results. Native
candidate coverage is **44,025 legacy + 10,914 long = 54,939 rows**. No C01 receipt
was fabricated and no D02 generated population was substituted. The original Loulou
MP3 and exact original preview are required private assets. Selected historical
metadata/media can be dependencies without exposing their complete old views.
Full optional **C03/D02 views are omitted**; doctor marks them unavailable, and the
D03 UI hides/disables their historical link/refinement route. The original C03
bundle `b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee`
and its inherited listener were preserved, without repair solely for D03 QA.

Local-cache reuse supplied 17 dependency wheels. Only setuptools 80.9.0 was acquired:
**1,216,878 response-body bytes**, two PyPI/file-host requests, no retries; no
model/audio acquisition. This is below the authorized 512 MiB dependency-only
ceiling. HTTP/TLS overhead was not separately sampled. Runtime downloads remain zero.

The final wheel was rebuilt independently. Every member payload, including frozen
matcher raw bytes, matched exactly. Wheel ZIP hashes differed because of timestamps;
byte-identical wheel/archive reproduction is not claimed. The final release checksum
and complete file inventory identify the delivered bytes.

## Real searches, recovery and compatibility

| Installed search | Useful units | Workers | Aggregate worker seconds | Source-read seconds | Driver wall seconds |
| --- | --- | --- | --- | --- | --- |
| Original saved Loulou | 98/98 | 25 | 232.375 | 22,816.024 | 234.922 |
| Newly saved two-example query, including cancel/resume | 98/98 | 27 | 219.076 | 15,518.984 | 15.500 before cancel + 206.765 after resume |

Driver periods exclude manual stopped-server/restart time. All workers remained
within actual-PID 120-second deadlines and each complete search remained below
1,200 worker seconds / 128 workers / 30,000 source-read seconds / 96 MiB ordinary
metadata. Submit-to-close metadata watermarks were 19,684,240 and 26,972,274 bytes;
complete cumulative totals also include admission/control/settlement overhead.
Cached candidates still incur fresh sequential source/PCM/array validation.

Loulou job `06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e` published result
`2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374`. **All 72 complete group payloads in each of legacy-mean
and event-multi match D01 exactly**, including score/order/support, and every displayed
native representative/bound matches. Media record paths differ because D03 owns its
new clips; this is not claimed as byte-identical result JSON. Query hash is unchanged.

The independent generated engineering reference uses seed 31003 and two original
native examples (2..7s and 13..19s in a new 24s stereo reference), without reusing
D01/D02 generation as its query input. New job `835e076af37d8e23458d890f8c10eabf5e694a4443633389e80aa609a2699ee9`
published result `23553b1fb5ed3d32d8e0713f4257e64269dca1374a2f1dba839c4bcaa87b5b94`. Its query hash and scores
belong to its own saved inputs. It encoded **two query rows, zero catalogue rows**.
The new-query feature bytes/hashes remained identical across cancellation, server
shutdown, token rotation and same-job resume. Resume performed fresh committed-source
validation while reusing query features. Changing rankings does not establish relevance.

**Retained failures and scoped repairs:**

1. The first install draft reconstructed SoundFile's wheel filename as Python 2-only.
   Correcting its `py2.py3` filename preserved its bytes, pin and hash. The failed
   setup log/release inventory and archive remain retained.
2. Initial longer private staging hit Windows path error 206 after 2,073 files /
   726,632,028 copied bytes. Its complete inventory/error were retained, then only
   that owned D03 copy was removed before the short-path retry. Preparation now
   preflights 240-character staging paths. Both final paths include spaces/non-ASCII.
3. First search `609d51bfb88a3aa7dc215b71f2b03d252f31e60ce9b9c8fbd0e31529b7a4dd1c` stopped at **41/98** after a Windows
   busy-reader registry replacement PermissionError: **129.956 worker seconds,
   11 workers, 12,025.756 source-read seconds**. Failure state, units, journal and
   spent charges remain. Explicit stopped-request abandonment released only unused
   reservations. The same prepaid replacement temporary now retries for at most
   one second; permanent refusal stays explicit. Exactly **one** additional repair
   search completed Loulou; no optional full comparison sweep ran.
4. An isolated installed test exposed inherited Windows `SO_REUSEADDR` duplicate
   binding. `LoopbackServer` now uses exclusive binding. This repair occurred after
   successful Loulou: that search used installed archive SHA256
   `2f43b2de4b90d7f412a73797fb606f780e0eec486442f9c8e2050aca427930a0`
   / consumer `a07f2aa4…`. The final archive additionally changes the server constructor
   to the exclusive subclass and hides the unavailable history link. The prospective
   AST proof preserves every handler/coordinator and all numerical/ownership modules;
   the exact prior consumer is accepted. **Loulou was reopened and compared under the
   final artifact, without another full search.** The new-query run, native/browser
   acceptance and fresh relocated reopen used the final wheel. No historical producer
   was relabelled. This is the precise scope of installed-search evidence.
5. The first isolated console smoke omitted the required reference manifest and
   failed explicitly. Adding `manifests/references/loulou.json` made it pass; the
   missing-reference error/report remain retained. No timeout was weakened.

The three D01 job/result pairs reopened through the final API and a fresh relocated
browser; their IDs are in the JSON. Full C03/D02 QA was not repeated. Historical
result access is read-only. D03's supported new-query flow uses its installed
runtime library; reopening an old result is not an authorization to mutate old jobs.

## Playback, security and validation

- **40/40** displayed scored/context clips passed independent source-frame,
  sample-count, sample-rate, channel, PCM16 gain and exact sample comparisons.
- **40/40** native browser controls passed real play/pause/seek in Chrome 155,
  without inserted between-player pacing. Headless audio was muted: this is
  technical playback evidence, not listening review. Desktop 1360px and 390px
  layouts passed, including reload and a separate long-label DOM layout fixture.
- A new browser after relocation reopened all five exact completed results, with no
  external page requests, browser exceptions or result substitution.
- WAV MIME/ranges passed; foreign-result candidate media, unscoped candidate media,
  invalid ranges, hostile Host and traversal were refused. Restart rotated the
  session token and rejected the stale token with 403. Duplicate requests reused
  one immutable job; conflicting payloads under the same key returned an error.
- Missing core/optional dependencies, missing/mismatched model, incompatible proof,
  missing/corrupt inventory, unsafe archives, live ports, insufficient disk, exhausted
  ordinary capacity, stale/copied/missing pools, permanent replacement refusal and
  independent protected terminal settlement passed bounded isolated fault checks.
  These fixtures do not substitute for the actual 72-source acceptance.
- Final full suite: **417 tests / 281.216s**, unchanged Python sources during the run.
  Ruff lint/format, JavaScript syntax, all 18 pins and `pip check` passed. The installed
  console passed isolated starter smoke with its resource/reference configuration.
  Pure known answers passed **four scalar pairs and eleven native intervals**.
  No hosted CI/required check is configured; no hosted-CI pass is claimed.

Maximum observed worker peak was **411,422,720 bytes**, server
peak **121,978,880 bytes**, and reported worker/server overlap
bound **532,918,272 bytes**. Numerical working checks use
1 GiB; this is **not an OS-enforced RSS cap**. Actual-PID worker evidence is retained.

## Fixed allocation and storage handoff

One workspace UUID `d4ca10c6-1d83-4c50-b71c-ca3ad49fe042` and allocation UUID
`7ff69006-0383-4528-babc-218dfe1ed9e8` are fenced by the external LocalAppData registry. Every pool
publication advances its generation/checkpoint. Copies/stale backups cannot silently
renew usage. Missing/corrupt initialized state requires explicit consistent-backup
recovery, not empty state. There is no reset, automatic renewal or daily refill.
The verification share is sealed; its completed results remain readable.

| Counter | Verification spent | Ceiling in each share | Normal spent |
| --- | ---: | ---: | ---: |
| job_seconds | 625.877 | 3,600 | 0 |
| workers | 75 | 256 | 0 |
| read_audio_seconds | 54,026.004 | 90,000 | 0 |
| feature_windows | 2 | 512 | 0 |
| processed_window_seconds | 22 | 6,000 | 0 |
| feature_bytes | 134,144 | 33,554,432 | 0 |
| query_jobs | 16 | 64 | 0 |
| clips | 40 | 64 | 0 |
| clip_bytes | 23,921,320 | 134,217,728 | 0 |
| metadata_bytes | 60,451,680 | 268,435,456 | 0 |
| preparation_bytes | 65,194,496 | 67,108,864 | 0 |
| import_bytes | 4,608,088 | 134,217,728 | 0 |
| managed_output_bytes | 93,858,048 | 536,870,912 | 0 |

Metadata includes conservative publication/temporary/pool/settlement geometry.
Ordinary used is **51,339,970 bytes**; protected used is
**9,111,710 bytes**, with zero unsettled worker time. Non-inference QA
has a prepaid **60 MiB** preparation/output envelope within verification; its measured
physical files use **29,308,747 bytes**, below that envelope and the 64 MiB QA cap.
Setup/closure planning and retained early-failure logs predate this QA prepayment and
are included in its final physical inventory, not hidden as free output.

All normal-use counters remain **zero**, including its **32 MiB protected reserve**.
The installed doctor verifies real prerequisites and admits the conservative complete
new-search estimate: 1,200 seconds, 128 workers, 30,000 reads, 96 MiB ordinary plus
12 MiB protected metadata, two query rows, 20 clips and bounded preparation/output.
This is an exercised-policy capacity check, not only unused time. It does not spend
normal allowance to demonstrate readiness. Retain completed outputs by default;
export/back up the full private workspace plus external registry. A later explicit
policy amendment must preserve spent history. User deletion is outside D03.

Separate physical inventories (all retained copies counted):

| Area | Bytes |
| --- | ---: |
| Setup / environments / wheelhouses / archives / build output | 3,030,131,511 / 3,221,225,472 cap |
| Private workspace including runtime/public prerequisites | 858,176,045 |
| Combined current managed data including original checkout | 2,720,657,947 |
| Combined plus the entire 512 MiB normal output reserve | 3,257,528,859 / 4,294,967,296 cap |
| Free disk at inventory | 201,951,334,400 |

Private closure/copy staging stayed below its separate 1 GiB cap; failed long-path
staging was removed before the second full copy. Setup inventories include the failed
install environment, failed archive, superseded numerical-acceptance archive, final
archive, both code copies and rebuilt wheels. File/stream temporaries add bounded
scratch rather than another full private-copy tree. Continuous OS disk high-water
sampling was not performed; retained directory inventories and explicit copy geometry
are the disk evidence. More than 4 GiB remains free after normal reserved writes.

Preservation verified **24,140 / 24,140** old files by size and SHA256: no changed or
missing file, and only declared new manifests. All old configurations, guards,
reservations, arrays, media and evidence are unchanged. In particular the three C01
staging folders whose deletion was denied remain intact; no deletion was retried.
C04 remains historically **partial 145/148**, including its unsettled 120-second
reservation. D02's failed promotion gates remain unchanged. No production deployment
or public private-asset upload occurred.

## D04 handoff — not started

Load completed job `06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e` in the final app. The preserved original
Loulou revision is `c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`,
materialization `0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.
Its available-file event is **218..240s**, frames **[9,613,800, 10,584,000)** at
44.1 kHz, original mixture/pitch off. There is no verified marked-master alignment.

The following are the baseline's actual first ten distinct-song labels in order;
no replacements were selected. Launch the app before using the direct player links.
Integer native bounds/media IDs are in the JSON. Context is unscored.

| Rank | Candidate | Scored available-file interval | Context interval | Immediate playback |
| --- | --- | --- | --- | --- |
| 1 | Shivering Shadows (Featuring Viktor Van River) — Cutside | 03:11.000–03:13.400 | 03:10.000–03:14.400 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/9fc594174a242705bde21b7d86b69b113c45c3b68dd79bc947153dde8468c128) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/fb224d77b846259709d40ecccd1c7b8023067b47a092edcb9bc92c6982d74b39) |
| 2 | Body, soul — Viktor Van River | 02:00.000–02:02.400 | 01:59.000–02:03.400 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/c3e663b785008adb5f347e6f934e56f16ae8ca7c146a3b7302610869380c9084) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/b4ce10a5c2c1331544c3205823196e061ef215f03ddbc9a386602fc8e47bf8ec) |
| 3 | Amaterasu — Cutside | 01:37.000–01:39.400 | 01:36.000–01:40.400 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/2814ee63d4f183a5cb5ef35795d14c31a87bb3f00c05ea9f583f34b2c7d715e9) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/787598c51f7e1bf8b5237d7caf71e991b4e2263ee3ab68501bf164154f48bc44) |
| 4 | Essence 118 — mGee | 02:43.750–02:46.150 | 02:42.750–02:47.150 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/aaf4118dc69febc3d21eb8d56a97afaac37eaa1f154b956e0cb728d518be8f77) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/84a475c6d2b9383be27cfa275d2c53cb28b1a6d6b529f99be6d5efa7994932d1) |
| 5 | Subway Cameo — Pete Lund | 03:14.500–03:16.900 | 03:13.500–03:17.900 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/f514f53d60e2d1ee5f86b272509e73efac74b5bcdbdb2e6804fc7a25e240ec3c) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/8a382ee9eee486e2d15a942053a9cfab9592177d6b3b802ad917cb544dad5fd6) |
| 6 | When I Lay Down — Gary Wood | 02:18.000–02:20.400 | 02:17.000–02:21.400 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/526d07f0d170eeb5c0bbe38f60657ecd10cc8c17655b199ca77bf6400641aeb8) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/ef0cbad5414a499fd91602aacfa942bbe3b84b4ca47147cd1869906b79e45db7) |
| 7 | Absurdius Rex — Jovian Year | 00:07.750–00:10.150 | 00:06.750–00:11.150 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/4208e2fafe19b826bdb0b3a4dca8fd7a3adee7af4ccb99342487f116e8cab4f8) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/4fde4bce16ab6223b7c102c792706e179aade4c36726601663e1faa64b0c7993) |
| 8 | Something To See (De Vries Instrumental) — Donnie Ozone | 03:08.500–03:10.900 | 03:07.500–03:11.900 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/a1d570e1bed157dad28769bdd82541a16079a745e7746dfa949dc0793648ede5) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/278a79b37e4b6d966fc7fd3eed035b2aeb4ac502df5d587da735da769efa1c62) |
| 9 | Confusion — Mos Emvy | 00:10.000–00:12.400 | 00:09.000–00:13.400 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/9f7149e243e0cbf1b3660a98987b748ae9c4d427b4d99b24dc6222fe4378fc62) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/1ea7a33afc1804e3caeac3cd9045fcb92fa5a7eb36f84c675104716e3bf62b40) |
| 10 | Gladiator Season — GLD8TRZ | 03:23.250–03:25.650 | 03:22.250–03:26.650 | [Original](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/77a358a235b8295fb9eebc2c6a21550e8886256ec97e1f2ac795c68f025deac3) · [Context](http://127.0.0.1:8776/result-media/2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374/88303c30ea60d3ef957593162ccc50a666ad8d0b7b0fa5ae46d2f1f105f184ad) |

These are candidate matches, with unmeasured human relevance. Intended layer,
reference version/master alignment, track identity/rights and useful semantic
similarity remain unverified. Optional feedback and the first required listening
review belong to D04. No review was automatically started.
