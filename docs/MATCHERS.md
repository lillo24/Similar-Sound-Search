# A05 development representations and comparison

A05 compares an interpretable acoustic baseline with one genuine pretrained EfficientAT MN04 representation on the frozen development suite. It does not search the real catalogue or run held-out models. [Measured delivery evidence](../reports/A05_MATCHERS.md) records actual results, costs and restrictions; the [subsystem map](../src/similar_sound_search/matchers/README.md) describes ownership.

## Setup and explicit commands

Run ordinary [Python 3.12 setup](RUNTIME.md#setup) first. Optional inference uses a separate Windows AMD64/Python 3.12 CPU lock, `requirements-models.lock`, with exact wheel hashes and all missing transitive packages. It adds Torch 2.6.0+cpu and leaves the renderer's NumPy/SciPy/SoundFile/package identity unchanged. TorchAudio is unnecessary: its DLL extension failed on this Windows installation; the evaluation-only Kaldi mel-bank equations reproduce all 65,664 native coefficients exactly. No machine-wide runtime was installed. The exercised CPU Torch warning about a missing VC redistributable is redirected to stderr without concealing inference errors; actual strict-load/inference smoke is the compatibility evidence.

```powershell
.\scripts\setup.ps1 -PythonExecutable "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
.\scripts\setup-models.ps1
.\.venv\Scripts\python.exe -m pip check
# Prospective, model-independent correction; idempotent repair of canonical mirrors.
.\.venv\Scripts\sound-search.exe --tier starter matchers freeze
# Validates both partitions' audio/truth without scoring held-out models.
.\.venv\Scripts\sound-search.exe --tier starter matchers validate
# Only this operation permits model network access.
.\.venv\Scripts\sound-search.exe --tier starter matchers acquire
# Explicit integration smokes; three charged cases each, no rankings.
.\.venv\Scripts\sound-search.exe --tier starter matchers smoke --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter matchers smoke --method efficientat
# Same 80 development queries, interval policy and device/thread/cache policy.
.\.venv\Scripts\sound-search.exe --tier starter matchers run --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter matchers run --method efficientat
.\.venv\Scripts\sound-search.exe --tier starter matchers compare
# Explicit feature/prediction reuse; retains measured cold-run cost.
.\.venv\Scripts\sound-search.exe --tier starter matchers run --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter matchers run --method efficientat
.\.venv\Scripts\sound-search.exe --tier starter matchers score data/runs/matchers/acoustic-predictions.json
.\.venv\Scripts\sound-search.exe --tier starter matchers score data/runs/matchers/efficientat-predictions.json
.\.venv\Scripts\sound-search.exe --tier starter matchers known-answer
.\.venv\Scripts\sound-search.exe --tier starter smoke
```

These commands share the CLI's explicit `--root`, `--tier` and owned `--report reports/local/NAME.json` options, which precede the command. Every A05 operation defaults to development; `--split held_out` fails before ledger creation or model execution. `score` requires an explicit prediction path; `smoke` and `run` require an explicit shortlisted method. Ordinary setup/tests/smoke never download a model. Optional setup downloads only the finite reviewed wheels, at most 512 MiB, requires 6 GiB initial free space, uses the existing root setuptools, checks full dependency consistency and refuses renderer-version changes. The Windows wheel hashes are not a claim that optional Linux setup was exercised.

The delivery checkout is populated: use starter, since its existing managed footprint exceeds smoke's 256 MiB cap. A fresh checkout needs the frozen audio and matching private registrations described in [A04 evidence](../reports/A04_BENCHMARKS.md). Missing/changed assets fail, never silently replace the original suite with procedural-only material. Preserve the exhausted A03 and existing A04 ledgers.

## Prospective evaluation correction

A04's original source-consistency candidate hit@10 saturates for 24 windows per mixture. The actual real-scorer audit gives constant chronological hit@10 of 100%, hit@1 of 100/100/0% across -12/0/+12 dB, macro 66.6667%. Matching-window counts are 8/7/7. Uniform random expected macro hit@10 is 99.2028238%, and hit@1 is 30.555556%, from `1-C(N-m,K)/C(N,K)`. A seeded order with seed 42105 is a separate diagnostic, not that analytical expectation.

Protocol `2026-10-13.1` changes only the comparison policy before acoustic rankings: complete controlled-render intervals and query-length mixture windows every 0.25 seconds, with a unique final end-aligned tail; primary macro **candidate query hit@1** over source-consistency levels, secondary controlled performance/pitch hit@5, then lower measured model wall time and lexical method/config hash. Eligibility requires technical/resource success and all 80 query outputs. K=1/5/10, pools, family splits, IoU>=0.5, one-to-one matches and construction truth remain unchanged. Empty lists are misses; failed inference is not an eligible empty result. No universal threshold is introduced.

The old protocol/suite hashes remain in `manifests/evaluation/{protocol-history,suite-history}/`. `comparison.json` atomically commits both complete revised records in one self-hashed file. Shared readers prefer that authoritative pair, validating each inner hash and their binding; `protocol.json`/`suite.json` are recoverable canonical mirrors. Repeating `matchers freeze` repairs interrupted mirror writes. Fresh construction uses the revised defaults, and reuse requires generated suite identity to match the authoritative pair. Selection changes do not regenerate/reidentify audio, bump renderer tools, or charge A04 construction. Known-answer checks invoked through A05 charge A05 time only.

## Representation boundary

Adapters receive finite waveform samples and integer rate only. Arithmetic channel mean, deterministic Kaiser-5 constant-zero polyphase resampling and original integer intervals preserve elapsed-time scale one. No original-file name, source/preset/artist/family label, condition or target time reaches feature computation/ranking. Interval generation uses file/query durations, never target times. Every selected sample is retained. Padding short model input does not extend the predicted available-file interval. Inputs are bounded to 30 seconds, eight channels and 192 kHz at the adapter boundary, with the shared stricter decode/worker checks still applicable.

The acoustic baseline produces 56 float32 values: 13 cepstral means/stds, five spectral descriptor means/stds, sixteen relative RMS envelope bins, and four level/crest/peak-time/decay descriptors. The 24 kHz frontend uses a symmetric Hann of 600 samples, FFT1024, hop240 plus a unique final frame; 40 L1-normalised HTK triangular filters from 40 to 12,000 Hz, natural log of normalised power, and orthonormal DCT-II. Cepstral values divide by 10; centroid/bandwidth/rolloff by Nyquist; relative envelope bins multiply by 0.25; log-RMS, crest and log-tail/head ratio use the declared fixed factors in `acoustic.py`. Euclidean distance is lower-better. No learned scaling fit or hidden pitch estimate is used. Explicit level/envelope descriptors remain even though spectral shape uses power proportions. Silence is a declared finite technical input, not a fallback for failed inference.

EfficientAT uses the official `mn04_as_mAP_432.pt` checkpoint, width 0.4, source revision `a425fdce92572e602a1d5634799bd9f1f2efa806`, release `v0.0.1`, asset ID 84971629. Its 4,066,513 bytes have pinned SHA256 `899a8c6217063f6941793102a2780b3dd788ab11fce468d9cf5f0577c453321c`. The release supplies no independent digest; the captured acquisition checksum is committed and required on every later use. The official repository's MIT licence and copyright are retained with the narrow inference adaptation. This is an AudioSet general-audio tagging representation; its published tagging score is not project timbre accuracy.

The pretrained frontend reproduces evaluation preprocessing: 32 kHz mono, preemphasis .97, symmetric Hann800/FFT1024/hop320, centred reflect padding, 128 unnormalised Kaldi mel bands 0..15 kHz, `log(power+1e-5)` then `(x+4.5)/5`. Inputs shorter than 1024 resampled samples receive zero padding; longer inputs retain their complete duration with no 10-second extension. The 384-dimensional embedding averages frequency/time after the final convolution, before the classifier; cosine distance is lower-better. Classification logits and separated stems are not used. Strict tensor-only local state loading, eval/inference mode, deterministic CPU and one numerical thread exclude stochastic augmentation, gradients and hidden base-model fetches.

CIR remains unavailable because the pinned repository/weight terms do not establish reuse permission; its source also requests a pretrained AST and extractor, adding downloads/memory. CLAP's inspected standard checkpoint is 1.86 GB, beyond the 512 MiB project cap; it was not downloaded or allocated a scored slot. Two methods are frozen, with no hyperparameter sweep, ensemble or second checkpoint.

## Reuse, accounting and failure recovery

Feature identity binds byte/canonical-PCM hashes, exact integer interval/rate, decoder/preparation versions, representation code/checkpoint/config, layer/pooling, scales/fit provenance, precision/device and numerical libraries. Source files are fully decoded/hashed before cache acceptance, including completed-run reuse. Float32 `.npy` arrays and self-hashed metadata are atomically published and validated for shape/finite values/hash. Changed dependencies choose a different key; corrupt or orphan arrays fail with the owned artifact ID. Feature timing is persisted at creation, so reuse does not fabricate zero model cost.

`config/matchers.json` supplies a fixed separate A05 lifetime job: 8 MiB model payload, 16 HTTP attempts, 2,400 worker seconds, four model-run operations, 8,000 processed windows, 64 MiB conservative feature publication allocation, batches of at most 96 new windows and twelve smoke-window attempts. Each original method run and explicit complete reuse counts as a run; internal resume batches do not create replacement allowances. Charges occur before inference/writes; uncertain crash work is not refunded. The checkpoint uses the shared verified-TLS/receipt/reservation transport, with only its exact release URL and signed GitHub release-asset redirects added as an explicit source policy. Archive defaults remain unchanged. Every other A05 CLI worker blocks socket connections, including implicit framework downloads.

The original 120-second worker deadline, 1 GiB configured working ceiling, concurrency one, 4 GiB managed storage and 4 GiB free headroom remain unchanged. Model/dependency files under `data/`, feature caches, ignored reports and `manifests/matchers/` count toward managed storage. `.venv/` and package caches are measured separately; free-space checks include their disk cost. Model reservations are 768 MiB, acoustic array reservations 64 MiB; measured worker peak working set/RSS is separately checked against the 1 GiB ceiling. This is sampled process evidence plus bounded arrays, not a new OS allocation sandbox.

`matchers run` serially resumes finite 96-window workers until complete or an explicit failure. Progress and immutable features survive a stop; repeats validate existing inputs/features and continue missing work. A crash between array and metadata publication leaves an actionable orphan. Inspect/quarantine/remove only that owned damaged artifact before resuming; never reset a ledger, raise limits or change a method to escape a refusal. A failed operation has nonzero exit and a private error report. Four run operations and twelve smoke attempts are lifetime allowances, not an invitation to repeatedly time methods.

Reports separate cold adapter loads (including repeated worker loads), feature extraction, ranking, scorer wall time and outer worker time. Selection uses summed measured adapter loads plus unique cold feature extraction plus ranking, under the same batch/device/thread policy for both methods. Cache validation/orchestration time is reported separately. Complete-run reuse retains the original cold model cost. Candidate lists use the shared scorer's deterministic tie and one-to-one rules; refined lists are consistently empty because refinement is unimplemented. Prediction files are saved before ground truth is joined. Selection also requires self-hashed complete progress with matching shortlist and measured cost, so a prediction file left by an interrupted run cannot be selected. Absent score distributions do not establish presence; no rejection calibration or human correlation is enabled.

The choice is provisional controlled-source evidence with placement bias, four procedural families, reused backgrounds and unknown pretrained-data overlap. A05 never sets `stage: A06`. A06 must consume the exact frozen method/config/protocol/suite and explicitly initiate its final held-out check. Loulou validation still needs the actual marked-version audio/provenance; D04 remains the first required listening review.
