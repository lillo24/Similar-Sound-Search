# D04 listening review

D04 presents the completed D03 Loulou publication, with the full original mixture
first and ten distinct saved candidates in their original order. It performs no
inference. [The downloadable report](../reports/D04_LISTENING.md) is readable
without the app; [the review manifest](../manifests/listening/d04-v1.json) freezes
the input, policy, population, native representatives and exact media bytes.

## Open the delivered private review on Windows

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-d04.ps1
```

Open **http://127.0.0.1:8777/**. Keep the foreground terminal open; Ctrl+C stops
the companion. A live port is refused. `-Port 8778` explicitly chooses another
loopback port. **127.0.0.1 refers to the computer running the listener.** A narrow
desktop viewport does not establish phone access; Android playback is untested.

The launcher reads the existing installed D03 interpreter from ignored
`reports/local/d04/metadata/launch.json`. It runs the separate stdlib companion
under `-I`; no installed file, wheel, numerical identity or dependency changes.
The installed app need not be running: preparation already used its read-only
provider to open exact job `06a4ee15…`, resolve result `2319b213…` and copy only
the 21 allowlisted, byte-identical WAVs into `reports/local/d04/bundle/media/`.
No workspace file server or application-operation proxy exists in the companion.

The installed `/private-reference/loulou.wav` provider currently refuses because
its inventory contains two retained copies with the same expected filename. D04
records this failure. Its explicit presentation workaround checks **both** copies,
the supplied MP3 hash, the query's native selection and the exact retained C03
publication, then exports the original 22-second WAV. No clip is regenerated or
substituted. The report distinguishes retained native sample proofs from the new
byte/header/frame checks. The frozen D03 package is unchanged.

## Optional responses and durable copies

First replay the reference: is this the intended recording/section, and which
sound within its mixture do you mean? An everyday description or “unsure” works.
Each candidate optionally accepts similar type of sound, different, unsure, or
not listened, with a short note. Nothing is mandatory and play events never rate
an item. A chat reply using the stable D04 IDs also works without using the form.

Browser drafts are temporary convenience. **Save responses on this computer**
writes a private, immutable JSON revision under
`reports/local/d04/metadata/feedback/`. Status explicitly confirms that write.
Every save retains the prior revision and its parent hash; a stale tab receives a
conflict and keeps its draft. An OS file lock also excludes concurrent companion
processes while reading/appending feedback. The listener field is self-reported, not verified.
Playing/seeking is not recorded as a human response.

**Export responses as JSON** requests a browser download of the current document.
The page cannot confirm where the browser saved it. Keep the downloaded file if
you want a portable copy; an unsaved draft export is not a submitted response.
Import accepts only the same review hash and exact ten IDs, within 64 KiB. Save
current edits first; an import is validated and requires an explicit Apply click.
Applying edits a draft; save again to create the next durable revision. Old
snapshots remain available by `/feedback/<revision-hash>.json` on the same listener.
There are at most 512 saved revisions, within the 16 MiB metadata cap.

Feedback can be pending, partial, completed or explicitly declined. “Not listened”
is unanswered, distinct from different or unsure. A wrong section/layer response
belongs to this original full-mixture review; a corrected crop/search needs a
subsequent task. Notes do not verify rights, master alignment or song identity.
Keep raw notes private; publish only attributed, sanitized summaries.

## Reproduction and boundaries

A public clone has no private bundle, installed Windows environment, reference,
catalogue clips or retained C03 bundle. The launcher fails explicitly if its
private prerequisites are absent. Do not initialize another allocation or use
synthetic audio in their place. To reproduce preparation on this delivery host,
use the existing installed D03 Python with `-I -B scripts/d04-review.py prepare
--workspace <existing-D03-workspace> --root <absent-bundle-D04-output-root>`.
The original checkout's exact C03 bundle, the completed D03 private closure and
the unchanged distribution archive are required. Preparation refuses to overwrite
an existing bundle or change an existing review manifest.

`scripts/d04-check.py --root reports/local/d04 --label <label> -- <command>` records
the small D04-only preparation allowance. It retains starts, failures and elapsed
times, limits aggregate supervised time to 600 seconds / 24 cumulative invocations, and gives
each actual worker at most 120 seconds with one numerical thread. Source audio
reservations total at most 6,000 seconds. The explicitly amended 256 MiB new-output
envelope contains 224 MiB QA, 16 MiB metadata/feedback and 64 MiB private media/export
caps; their sum is still constrained by the total. This D04-only user amendment
retains all ten prior attempts and their 168.501 spent seconds. The versioned
[allowance](../manifests/listening/preparation-allowance.json) is recorded in PR #34.
No processing seconds, source allowance or application pool was increased.
The policy-denied incomplete D04 test fixture remains included in QA and total
output. No deletion retry is authorized or performed.
Final export also includes the public manifests/reports in the combined output
inventory. Temporary
QA output is sampled; receipts distinguish observed peaks from reserved bounds.
The supervisor checks pre-amendment charges are present. On Windows it supplies
the extended path namespace for nested generated fixture paths, without changing
their actual locations or frozen source. The live inventory uses cached directory
entry sizes rather than opening files while the existing atomic writer renames
them; real busy-reader errors remain explicit. This companion does not replenish
or use any application pool. Human listening
and idle foreground service time are separate from processing-worker time.

On 25 October 2026 Leonardo explicitly authorized this D04-only amendment from
32 to 224 MiB QA, 128 to 256 MiB total output, and 16 to 24 invocations. All prior
attempts, spent time, receipts and retained temporary files still count. The
600-second aggregate, 120-second worker, source-read, other category and global
disk limits are unchanged; both D03 pools and the external registry stay untouched.
The automatic approval review's temporary-file cleanup rejection remains in force.
Do not delete those files, retry the rejected cleanup or initialize another QA root
to obtain fresh counters. Resume against the existing receipts and inventory.

Focused tests run with `.venv/Scripts/python.exe -m unittest discover -s tests -p
test_listening_review.py -q`. The complete existing regression suite is also
required for companion code changes, in bounded batches if necessary. Real private
playback, HTTP, layout and accounting checks are recorded separately in the report.
D04 neither retunes the model nor starts E01.
