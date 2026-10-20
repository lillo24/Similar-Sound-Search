# Reusable query owner

B03 separates immutable portable query revisions, validated local materializations
and exact index/preference executions. Original audio and pitch off remain defaults.

| File | Responsibility and relationship |
| --- | --- |
| `contracts.py` | Strict schemas/identifiers, supported choices and fixed finite policy |
| `assets.py` | Explicit hash-checked A02 registrations/bindings; read-only B02 transformation/cue dependencies |
| `library.py` | Canonical revisions, display names/optimistic heads, metadata export/import and unresolved requirements |
| `materialization.py` | Compose revisions with shared native A02/query preparation; retain ready/interrupted/artifact state |
| `features.py` | PCM/representation keyed immutable feature blobs, independently of provenance, label and pitch |
| `pitch.py` | Unchanged classical estimator with exact support provenance/cache; inspectable bounded secondary contribution |
| `execution.py` | Exact revision/materialization/index binding; validate and rerank the entire eligible timbre-winner set |
| `context.py` | Fixed output/accounting roots and explicit shared hooks; delegate historical validation charges to B03 |
| `job.py`, `commands.py` | One offline cumulative ledger, hard worker deadlines and CLI routing; metadata operations do not infer |
| `development.py` | Independently checked native fixture geometry and one fixed paired development batch |
| `validation.py` | Charged pitch known answers and independent native-to-player verification |
| `report.py` | Immutable revision/pitch summary; original context/candidate and explicit derived/cue playback |

Shared preparation, mean-distance ranking/ties/exclusions, frozen pitch/model code,
original feature arrays and historical authorization guards remain their existing
owners. See [contracts and commands](../../../docs/QUERIES.md).
