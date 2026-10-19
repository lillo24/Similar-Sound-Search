# B02 optional separation and extraction

Original audio remains the default. These are numerical experimental components,
not instrument identification. B02 uses installed NumPy 2.2.6/SciPy 1.15.3 and the
unchanged EfficientAT MN04 matcher. No separator package/checkpoint was acquired or
run. The prospective protocol and actual evidence live in
[manifests/separation](../manifests/separation/README.md) and
[the delivery report](../reports/B02_SEPARATION.md).

## Processing and signal contract

`separation process INPUT --mode original|broad|guided` accepts
`b02-process-input-1`: a `source` containing explicit project-relative `path` and
`sha256`, optionally `context` (A02 input JSON) or `parent_record` (prepared A02
record); half-open native integer `region` and `event` pairs; and optional `cue`
containing the same source fields plus native integer `bounds`. The event must fit
inside the region. Guided extraction requires an audio cue; absent/silent cues fail.
No intended instrument name, source identity, exact hidden stem or evaluation label
is accepted by the extractor. A cue from a different recording is allowed, with its
original/duplicate parents included in every arm's exclusions for equal support.

The [Loulou excerpt template](../config/separation_source.example.json) retains
unverified version/offset context. Its illustrative frames assume 44.1 kHz; run
`inspect data/audio/originals/loulou-excerpt.wav --context config/input_context.example.json`
first, then replace hashes and explicit bounds/cue with actual native metadata.
Never apply second 218 to that short excerpt. The template deliberately fails until
matching audio and identities are supplied; it does not establish the intended layer.

Original mode copies the region's float32 native samples exactly, with no processing
gain. Broad/guided modes require 8–96 kHz mono/stereo, at most 12 seconds of context
and four seconds of cue. One chunk only, at most two components, a 128 MiB temporary
allocation preflight and fixed finite templates/iterations; there are no concealed
chunk seams, time stretch or rate conversion of the mixture. Too-short guided input
(fewer than eight STFT frames) fails explicitly. A cue-rate mismatch uses SciPy's
zero-phase `resample_poly` at the reduced integer rate ratio. Cue channels contribute
mean magnitudes, preserving cancellation-prone source stereo through one shared mask.

Both processed methods use a 1,024-sample periodic Hann window and 256-sample hop.
Explicit 512-sample zero padding centres analysis windows; extra right zeros complete
the hop grid. Inverse FFT overlap-add divides by summed squared windows and removes
exactly the padding to preserve native frame count, zero delay and source coordinates.
There is no fade, stem normalization, automatic gain or fitted time shift.

Let `V` be the channel-mean magnitude spectrogram. HPSS forms `H` by a 17-frame time
median and `P` by a 17-bin frequency median (nearest edge extension). The shared
harmonic mask is `H²/max(H²+P²,1e-30)`; percussive is its complement. These describe
spectral texture, not isolated instruments. **Harmonic is fixed for retrieval** before
scores; the percussive component is inspectable but never searched for a best result.

Guided processing forms four chronological mean cue spectra and eight chronological
mean mixture spectra. Background templates are multiplied by `(1-q)²`, where `q` is
the mean cue spectrum divided by its largest bin. Concatenate, floor at `1e-12`, and
L1-normalize columns to obtain fixed `W`. Starting with all-one activations `A`, perform
exactly 25 updates `A *= (W.T@V)/max(W.T@W@A,1e-20)`. The cue estimate `C=Wcue@Acue`
and background estimate `B=Wbg@Abg` produce `C²/max(C²+B²,1e-30)` and complementary
residual masks with original mixture phase. No RNG or general-model fitting occurs.
The cue exclusion prior prevents identical background templates from absorbing every
cue frequency; it can also remove another sound at the same pitch. Contaminated cues,
modulation, weak attacks and tails can all fail. Same/near-pitch controls distinguish
this limitation from general timbre matching.

Each `b02-transform-1` receipt binds exact source/parent/context/cue hashes, bounds,
configuration, numerical/preprocessing versions, DSP code, output hashes, native
channels/rate, padding/trim/delay, gain and composed original-source map. Unknown
master offsets stay null. Waveform transformation is explicit; its receipt is **not**
an A02 crop record. Subsequent A02 preparation truthfully crops the transformed file.
The B02 query context validates the transformation and unions all source/cue ancestry
before shared PCM deduplication. Original `search.query.parents()` remains unchanged.
Load/reuse checks source/cue bytes, maps, output metadata and feature integrity.

Near silence (`RMS < max(1e-7, original_RMS*1e-4)`) is explicitly recorded; handoff
refuses that component. Failures are not identity/fallback successes. Choose original
mode explicitly when processing is unavailable or harmful. Cache keys include source,
cue, bounds, configuration, versions and DSP code; cue-dependent candidate extraction
cannot become a universal stem. Audio publication is deterministic and atomic per
file, receipt last; interrupted files are verified before reuse and charged retries.

## Protocol and accounting

The distinct B02 plan reuses inspected A04/B01 development families, with new mixtures
and explicit insertion at native frame 36,000 (1.5s). Complete target render ends at
93,600 (3.9s); context is 1.0–4.5s. Twelve positives have complete decay support:
four clean cues, four contaminated cues and four quiet targets. Four controls are
absent, silent, deliberately censored and exact-waveform. Cue performance 2 differs
from reference performance 0 and candidate performance 1. Exact inserted float32
components are evaluator-only; their actual selected-region gains/TBR and individual
note bounds are independently checked before inference. Native float32 multiplication
introduces a recorded two-ULP construction difference; it does not alter waveform truth.

Every primary arm searches the same sixteen complete original 2.4s candidate passages
with identical EfficientAT/cosine/ties/pitch-off and K=1/5/10. The first case additionally
compares original query/processed candidates and paired processed query/processed
candidates over every candidate, with every cue/candidate pair charged. This small
diagnostic is separate from catalogue search and does not add a global stem index.
Oracle controls never route operational components or qualify for promotion.

Retrieval is paired with gain-inclusive aligned SDR, SI-SDR, target/background
projections, first 25ms attack/final 200ms tail retention and clipping. Projections
are descriptive and never applied to samples; correlated leakage can inflate retention.
No arbitrary lag is optimized. Preserving the sum of components is only a correctness
check. Forced rankings on absent mixtures are not a presence detector.

Promotion requires at least two primary top-1 gains, no paired top-1 losses, no loss
at ten; every attack/tail projection in 0.8–1.25 without overload; median SDR improvement
at least 1dB; and every 3.5s processing unit at most 10s. Incomplete/mixed evidence
keeps original audio as default. The settings and denominators are frozen before scores.

`config/separation.json` owns outer limits: 3,600 aggregate seconds, 256 workers,
1,200 processing-input seconds including cues/retries, 4,096 new feature windows,
12,000 feature-audio seconds, 90,000 read equivalents, sixteen query/rank jobs, one
comparison with sixteen cases/128 arm queries, 128 clips/128 MiB and 512 MiB managed
outputs. Prepared audio is additionally capped at 256 MiB, features/query preparation
at 64 MiB each. All work uses one fixed offline ledger under `data/runs/separation`,
one numerical/CPU thread and 120s workers under unchanged starter memory/disk limits.
Policy edits cannot replenish established ceilings. Installation/tests/browser/HTTP
QA and preservation audits are reported separately from delivery compute.

## Windows commands and resumption

Use `.venv\Scripts\sound-search.exe --tier starter --report reports/local/b02-NAME.json`
before each command below. The exercised paths are recorded in the delivery evidence.

```powershell
separation preflight
separation pilot
separation known-answer
separation process data/runs/separation/inputs/real-with-context.json --mode original
separation process data/runs/separation/inputs/real-with-context.json --mode broad
separation process data/runs/separation/inputs/real-with-context.json --mode guided
separation handoff TRANSFORM_RECORD --component original # harmonic / extracted
separation prepare-query HANDOFF_JSON
separation compare
separation compatibility --index A06_INDEX_JSON
separation rank --index A06_INDEX_JSON --query B02_QUERY_JSON --receipt B02_RECEIPT
separation report B02_REPORT_INPUT_JSON
.\scripts\listen-separation.ps1
python scripts/verify-separation.py reports/local/b02-report.json
```

Commit the generated preflight/independent geometry and prospective protocol before
processing/scoring. Repeat the same commands to resume retained completed units, not
to mint a new job. Do not edit producing code/settings during the comparison; its
progress binds the entire consumer tree and rejects drift. The declared later report
repair preserves the completed comparison/producing snapshot and cannot authorize a
replacement batch. Finish implementation tests before
the single necessary delivery compatibility pass. It reuses B01's audited mechanism
under B02-owned paths/counters and never re-embeds the immutable A06 index. Omitted
shared context still means A06 and its historical global guard remains closed.

The listener binds `127.0.0.1:8768`; Ctrl+C stops it. B01/A06 listeners retain ports
8767/8766. B02 HTML labels original context, derived components, cue and original
candidate passages separately, with raw/playback gains and available-file timestamps.
All media are hash verified, allowlisted and range served; missing/stale media fails
visibly. Existing shared report page semantics are unchanged. Private assets stay in
this delivery checkout; a fresh clone needs matching originals/checkpoint/index.

## Method sources and learned-model decision

Reviewed official [Demucs code/docs](https://github.com/facebookresearch/demucs),
[MIT terms](https://github.com/facebookresearch/demucs/blob/main/LICENSE),
[minimal requirements](https://github.com/facebookresearch/demucs/blob/main/requirements_minimal.txt)
and [model declaration](https://github.com/facebookresearch/demucs/blob/main/demucs/remote/htdemucs.yaml).
The archived code's minimal path requires torchaudio below 2.1 alongside several absent
dependencies, while the pinned matcher uses Torch 2.6 CPU. No compatible isolated
learned stack/checkpoint was admitted or downloaded; CPU memory/runtime are unverified.
Two-stem mode still performs full separation, and default stem rescaling would require
explicit gain handling. B02 deliberately chooses the authorized offline numerical
alternative; it makes no pretrained-separator result or checkpoint-size verification claim.

The [HPSS research resource](https://www.audiolabs-erlangen.de/resources/MIR/2018-ICASSP-HPSS_KAM_NMF/)
and [constrained NMF explanation](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C8/C8S3_NMFSpecFac.html)
motivate these independently implemented numerical baselines. Their published results
do not establish project quality. [AudioSep](https://github.com/Audio-AGI/AudioSep) takes
language rather than an operational audio cue and was not used.
