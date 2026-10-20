# B02 — Optional separation and audio-cue extraction

19–20 October 2026, Windows/Python 3.12.14. This implements B02's authorized numerical
alternative: original native audio, harmonic/percussive components, and a genuinely
audio-conditioned template/activation mask. **Original audio remains the default.**
No learned separator was installed, acquired or run. The unchanged EfficientAT MN04
matcher is reused; this is not a pretrained-separator result or human similarity study.

## Prospective scope and engineering

Main was pulled from B01 merge `99f3e39` to B02 prompt commit `7b1c146`. The isolated
branch is `codex/b02-separation`, in the existing primary delivery checkout. Policy
`21a761d` precedes all processing; eligibility/geometry/protocol `ae8b0a9`/`afdfd50`
precede separator and matcher inference. Implementation `4b6caa9` produces the fixed
comparison. Public records are mapped in [manifests/separation](../manifests/separation/README.md).

The [processing contract](../docs/SEPARATION.md) states exact equations, STFT padding,
reconstruction, numerical versions, templates, iterations and failure/cache behavior.
The small separation owner composes A02 maps, A03 groups, A04 development assets,
frozen A05 representation and A06 read-only features. New transformed waveforms have
`b02-transform-1` receipts; they are never disguised as unchanged A02 crops. The narrow
shared query hook validates receipts and unions original/cue ancestry before PCM
deduplication. Original `parents()`, descriptor bytes, distances/ties/pitch policy,
old report page and A06 global authorization guard stay unchanged.

The numerical pilot uses one independent three-second stereo mixture and cue, charged
to B02. Both methods complete, with 0.1727s combined DSP time, nominal zero delay and
maximum reconstruction error 2.98e-8. The impulse/hop-edge answer also has maximum
error 2.98e-8. These establish numerical feasibility, not separation quality.

Demucs's official archived code, terms, requirements and model declaration were
reviewed. Its minimal requirements request torchaudio below 2.1; this matcher retains
Torch 2.6 CPU. No compatible isolated learned stack/checkpoint was admitted or size/
CPU-memory/runtime verified. No claim that a learned separator ran or is impossible
is made. B02 chooses the permitted installed-stack fallback, with zero model/audio
acquisition. Method/source links and limitations are in the contract documentation.

## Independent geometry and fixed development protocol

This is inspected-development reuse, with new B02 constructions, not a fresh holdout
or a continuation/repair of B01's invalid oracle run. No A06 final check is repeated.
There are four related procedural families, twelve primary positive cases and four
separate controls. Clean versus contaminated cues and quiet targets are distinct
strata. Primary cues use separately generated performance 2; references use performance
0 and alternate-performance candidates use performance 1. Exact hidden target stems
only enter evaluation/oracle controls, never the operational extractor or routing.

Actual source insertion is frame 36,000..93,600 at 24 kHz (1.5..3.9s), including all
three complete releases. Context is 1.0..4.5s. A separate audit checks saved source/cue
hashes, exact inserted components/gains, note bounds, actual selected-region TBR and
candidate truth before inference. All twelve planned positives contain full support.
The actual float32 construction gain differs from an independent float64 calculation
by at most 2.98e-8; the saved inserted component is the evaluator's exact waveform
truth. This was caught before scoring, documented and checked, not hidden by a shift.

Every primary arm searches the same sixteen complete original 2.4s passages, including
same-pitch contrasting sounds and nearby-pitch controls. Harmonic is fixed as the broad
route; percussive/residual outputs are inspectable, not searched for whichever wins.
EfficientAT, cosine/mean, stable ties and pitch off stay fixed. K is 1/5/10. One batch
contains sixteen cases and 68 arm queries, including four paired candidate-side arms.
Failures/abstentions remain in their declared denominators; no replacement cases ran.

Promotion requires at least two additional primary top-1 successes, zero paired losses,
no decrease at ten; every attack/tail projection in 0.8..1.25 without overload; median
gain-inclusive SDR improvement at least 1dB; and each primary processing unit at most
ten seconds. Oracle assistance never qualifies an operational default.

## Retrieval and preservation findings

| Arm | Source hit@1 / 12 | @5 / 12 | @10 / 12 | Event recovery@1 / 24 | @5 / 24 | @10 / 24 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original mixture | 2 | 9 | 12 | 2 | 13 | 21 |
| Fixed harmonic component | 3 | 8 | 11 | 3 | 13 | 19 |
| Audio-cue extraction | 5 | 9 | 12 | 5 | 17 | 21 |
| Exact inserted target oracle | 9 | 12 | 12 | 9 | 24 | 24 |

Broad processing has three paired top-1 gains and two losses. Guided extraction has
four gains and one loss. Both fail the prospective retrieval gate. Median aligned
gain-inclusive SDR improvement is +0.202dB for harmonic and +1.036dB for guided. Both
also fail preservation: attack amplitude projections fall to 0.299 and 0.497. Tail
projections can be inflated by leakage; their lower values already exceed one here,
so they are not proof of isolated target energy. No primary output overloads.
Raw gain remains one, no fade/normalization or arbitrary alignment shift is fitted.
Global waveform distortion, leakage and endpoint projections are separate from
retrieval scores; they are development diagnostics, not perceptual agreement.

| Primary stratum | Original top-1 / 4 | Harmonic / 4 | Guided / 4 |
| --- | ---: | ---: | ---: |
| Clean privileged cue | 1 | 1 | 3 |
| Contaminated cue | 1 | 1 | 1 |
| Quiet target | 0 | 1 | 1 |

The clean-cue improvement does not transfer to the contaminated-cue stratum. Such a
clean example is privileged assistance and is not established for Loulou or the real
substitute. These related cases do not provide independent-family confidence bounds.

Controls remain separate. Silence abstains in every arm. Absent-target operational
arms still force rankings; those outputs are not detections. The deliberately censored
target is recovered at ten in each arm, with incomplete release support retained.
The exact-waveform control succeeds at one in every arm; that is distinct from the
alternate-performance primary result.

The candidate-side diagnostic processes **all sixteen** predeclared passages for one
case, with 32 charged mode/candidate pairs and no temporal-coverage expansion. All four
arms miss at one. Original query/harmonic candidates recovers 1/2 targets at ten;
harmonic query/harmonic candidates 1/2; original query/guided candidates 2/2; guided
query/guided candidates 1/2. These asymmetric results do not justify a global stem
index or later refinement. Original-candidate baseline and all full ranks are retained
in [the immutable comparison record](../manifests/separation/comparison.json).

Controlled localization is limited to known complete 0..57,600 candidate intervals,
with independent native/crop/excerpt/rate mapping tests. It is not a multi-window
localization accuracy estimate for arbitrary music.

## Real demonstration and bounded corrections

Loulou's marked-version audio remains missing in explicit project locations; version,
offset and intended layer stay unverified. The ready input template requires actual
hashes/native bounds/cue and never applies second 218 to a short excerpt. D04 remains
the first required listening review; no labels or ratings were requested.

The predetermined substitute is Donnie Ozone — Christmas Shopping at the Dollar Store.
The unchanged selected event is native frames 441,000..546,840 (10.0..12.4s at 44.1 kHz),
with an adjacent contaminated cue 546,840..652,680 (12.4..14.8s). Neither is a verified
complete note or isolated intended layer. Master offset stays null.

The initial 10..22 context was prospectively adjusted to 9..21 for attack lead before
real processing/catalogue scores. Its 12s stereo STFT allocation preflight then refused
169,924,608 bytes against the fixed 134,217,728-byte temporary ceiling. That failure,
its reservation and the unused original preparation/query remain preserved. A new
committed correction uses the same **9..17s context in every real arm**, preserving 1s
before and 4.6s after the unchanged selected query. Its preflight is 113,392,512 bytes;
no policy, algorithm, cue, selected event, matcher or ranking rule was relaxed/retuned.
No real processed output or catalogue scores existed when that correction was declared.

All three real queries search **43,690 original passages in the same 71 eligible
groups**, exclude the source/cue recording family before PCM deduplication, and return
ten distinct original-mixture candidates each. The 72-recording/44,025-passage/123-shard
A06 index is validated read-only; zero catalogue features are rebuilt. New B02
compatibility validation takes 138.578s wall time / 103.717s worker time. The three rank
wall times are 217.515s original, 329.093s harmonic and 209.391s guided, across bounded
serial workers. A low distance is not a presence or relevance judgment.

Final native context is 352,800 stereo frames at 44.1 kHz in every arm. Original,
harmonic and guided DSP calls take 0.0011s, 0.6373s and 0.2725s respectively; complete
cold processing workers, including validation, take 3.4086s, 3.7921s and 3.0829s.
All real components are finite/non-silent with raw gain one and zero overloaded
samples. Their energy ratios concern the mixture, not isolated target retention.
The unused 12s baseline and final 8s baseline have identical selected query samples.
One guided process/query repeat returns validated reuse in both stages, retaining
read/time charges and creating no replacement processing/features.

The report-only repair after the completed controlled batch derives source/timestamps
from receipts, retains numeric player provenance and recovers only an independently
verified interrupted owned WAV receipt. All other package modules remain byte-identical
to the comparison's producing snapshot. Its predictions/code identity remain intact;
the comparison is not rerun under the new report code.

## Playable delivery and independent verification

The default summary is `reports/local/b02-report.json`. Its verified bundle is
`reports/local/b02/separation-07516efec69a5474991b96d8ad4d8ee53aefc5114d158dad2bbc367f30cea0ed/index.html`,
with bundle hash `948969988a07d99bc8812fb2f37e1970749b4a4c6b5108fd058971beacd2ca03`.
It contains 42 labelled player items / 40 unique WAVs, including original/processed
context, exact selected event crops, the mixed cue, a controlled example and thirty
original candidate cards. Raw processing gain and any PCM16 playback attenuation
are visible; candidate playback always comes from the original catalogue mixture.

From the delivery checkout, the tested startup command is:

```powershell
.\scripts\listen-separation.ps1
```

Visit `http://127.0.0.1:8768/`; Ctrl+C stops the listener. The verified media and other
ignored outputs remain in this checkout. A fresh clone needs matching private source
files, checkpoint, registrations and index; public manifests do not provide the audio.
Exact exercised preparation/process/handoff/query/rank/report and resumption arguments,
including failed commands, are retained in [commands.json](../manifests/separation/commands.json).
[SEPARATION.md](../docs/SEPARATION.md#windows-commands-and-resumption) explains ownership
and safe reuse. The completed comparison rejects changed producer code; its single
batch is not repeatable under the later report-only repair.

Independent native verification passes for **all 42 items / 25 unique input files**:
source hashes, native samples, exact PCM16 conversion/gain, frame bounds, rates/channels
and numeric player/source timestamps agree. It takes 12.891 charged worker seconds,
using `.\.venv\Scripts\python.exe scripts/verify-separation.py reports/local/b02-report.json`.
HTTP QA takes 9.797s: all forty full WAV hashes match (200), sample-payload byte ranges
return 206, outside/encoded traversal paths return 404, malformed/multipart ranges
return 416 and responses use `Cache-Control: no-store`.

Chrome loads all 42 players with zero media errors. Native play/pause and seek controls
are exercised on original, harmonic and guided eight-second contexts (seek to 4s),
plus an original 4.4s candidate (seek to 2.2s). Media time advances while playing,
pausing stops playback, and all controls have ready state 4 with no error. The rendered
header/decision/timestamps are visually inspected. This establishes playback/control
correctness, not human similarity. QA playback is stopped, its owned tab closed and
no listener is left on ports 8766/8767/8768. [validation.json](../manifests/separation/validation.json)
retains the native/HTTP/browser answers separately.

## Validation and finite resource outcome

Full offline regression: **189 tests passed in 87.981s** with OMP/OpenBLAS/MKL numerical
thread counts set to 1, matching delivery workers. Focused B02 coverage is 21 tests.
Earlier unconstrained runs hit existing localhost/deadline fixtures; the first run also
exposed a new HTML test's whitespace assumption, corrected to test rendered text.
Existing assertions and timeouts were not changed. Ruff lint/format and offline
editable install/dependency checks pass; expected malformed-MP3 decoder warnings are
fixture diagnostics. No hosted Actions workflow exists, so no hosted CI pass is claimed.

The isolated starter smoke passes in 1.844s, independently of real-project disk use.
Its root is `reports/local/b02-smoke-project`; it does not replace prior diagnostics.
Core dependencies, package version, frozen matcher adapters and old source proofs stay
unchanged. The independent known-answer and comparison numerical checks pass.

| B02 counter | Charged / ceiling |
| --- | ---: |
| Aggregate worker time | 1,843.613 / 3,600 seconds |
| Workers | 119 / 256 |
| Query/rank jobs | 8 / 16 |
| Comparison batches / cases / arm queries | 1 / 1; 16 / 16; 68 / 128 |
| Separator input, including cues/retries | 310 / 1,200 seconds |
| New feature windows / feature audio | 97 / 4,096; 231.2 / 12,000 seconds |
| Source-read equivalents | 74,499.481 / 90,000 seconds |
| Playback clips / reserved bytes | 40 / 128; 30,991,360 / 134,217,728 |
| Reserved new managed output | 148,364,474 / 536,870,912 bytes |

Pending read/time reservations are zero. At publication, all 679 added managed files
total 127,824,749 bytes; reservations intentionally exceed actual output. Largest
observed feature/rank worker peak is 290,942,976 bytes. DSP temporary preflight estimates
are reported separately from measured working memory. Starter CPU/thread 1, 120s
workers, 1 GiB configured working ceiling, 256 MiB I/O ceilings and 4 GiB combined
managed/free-space limits are unchanged. Transfer and acquisition attempts are zero.

The ledger retains every pilot, geometry preflight, timeout/refusal, unused original,
compatibility/parent/source read, feature/rank/report and native QA charge. Comparison
uses 644.467 worker seconds, ranking 635.820, report 106.484 and native QA 12.891;
remaining action costs are in [resources.json](../manifests/separation/resources.json).
Setup/tests, browser/HTTP QA and protected-file engineering audits are reported
separately; they do not conceal new separator/matcher inference or source reads.

## Preservation and B03 handoff

The pre-processing baseline covers 8,357 prior files / 1,118,068,772 bytes and takes
92.109s to hash. The final full byte/size/mtime audit takes 111.750s: **8,356 historical
files are unchanged**, zero are missing or unexpectedly altered. The only declared
exception is `config/README.md`, whose intended navigation update has a separately
fixed canonical hash. Frozen adapters/attributes, old audio/features/ledgers, manifests,
predictions, reports and archived prompts are preserved. [preservation.json](../manifests/separation/preservation.json)
binds the baseline and [declared exception](../manifests/separation/preservation-policy.json).

No extra worktree is created; verified B02 artifacts already live in the primary
delivery checkout. The GitHub PR is the durable review/merge record for this branch.
Post-merge branch cleanup is followed by a protected-file metadata/owned-path check;
no private audio, features, checkpoint or raw worker artifacts are committed.

B02's numerical implementation, fixed comparison, actual catalogue demonstration and
playback verification are complete. No learned separator ran; intended-layer, Loulou
and human similarity evidence remain unavailable. Failed promotion keeps original
audio as the default.

B03 should manage reusable original/processed query choices with explicit cue availability,
native support and ancestry validation. Keep original default and optional processing
experimental; preserve this inspected protocol/results and all closed allowances.
Further pitch work needs its own prospective task, not a reinterpretation of these
scores. C01/C03 still own global component indexing/refinement; no automatic B03 work
or new listening gate is introduced.
