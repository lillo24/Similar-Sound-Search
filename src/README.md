# Audio input runtime

`similar_sound_search/` owns the CPU input pipeline, A03 catalogue acquisition, A04 evaluation construction/scoring, A05 development matchers and A06 bounded exact local search/playback. The installed `sound-search` command and `python -m similar_sound_search` both enter `cli.py`.

| File | Responsibility and relationship |
| --- | --- |
| `similar_sound_search/__init__.py`, `__main__.py` | Package version and module entry point |
| `similar_sound_search/cli.py` | Parse explicit operations, hold the project lock, run a worker with a hard timeout, and publish private JSON reports |
| `similar_sound_search/resources.py` | Validate tier limits; enforce file/allocation/disk/inventory/time boundaries; account locked catalogue writes without repeated full disk walks |
| `similar_sound_search/storage.py` | Hash/JSON identity, path containment, atomic reports, errors, and OS process lock |
| `similar_sound_search/inputs.py` | Probe/decode bounded WAV/FLAC/MP3/AIFF, canonical PCM identity, peak/RMS/silence, and explicit files/directories |
| `similar_sound_search/records.py` | Validate supplied context and compose elapsed-time mappings independently of recording identity |
| `similar_sound_search/preparation.py` | Apply explicit crop/channel/resample choices; publish immutable bundles and validate reuse/lineage |
| `similar_sound_search/diagnostics.py` | Generate deterministic plumbing fixtures, check independent known answers, and report actual environment capabilities |
| `similar_sound_search/catalogue/` | [Subsystem map](similar_sound_search/catalogue/README.md): bounded HTTP/ledger, single provider, shared ingestion, duplicates and durable batches |
| `similar_sound_search/matchers/` | [Subsystem map](similar_sound_search/matchers/README.md): finite optional model acquisition, common representations, feature reuse and development comparison |
| `similar_sound_search/evaluation/` | [Subsystem map](similar_sound_search/evaluation/README.md): benchmark quarantine, procedural recipes, family splits, independent mixture audits and prediction scorers |
| `similar_sound_search/search/` | [Subsystem map](similar_sound_search/search/README.md): serial original indexing, unordered explicit queries, exact distinct-recording ranking, original playback and one guarded final check |
| `similar_sound_search/events/` | [Subsystem map](similar_sound_search/events/README.md): B01 proposals, explicit/manual selection, native crops, fixed development comparison and audited read-only catalogue handoff |
| `similar_sound_search/separation/` | [Subsystem map](similar_sound_search/separation/README.md): B02 optional DSP transformations, audio-cue lineage, fixed paired comparison and truthful original/processed playback |
| `similar_sound_search/queries/` | [Subsystem map](similar_sound_search/queries/README.md): B03 immutable query revisions, explicit bindings/materializations, complete-winner pitch preference and playback |
| `similar_sound_search/indexing/` | [Subsystem map](similar_sound_search/indexing/README.md): C01 versioned passage banks, audited legacy reuse, optional region components, exact per-bank winners and bounded publication |

The CLI imports numerical/decoder libraries only in the bounded worker. Inputs feed candidate records; preparation retains those source records and composes maps back to the original available file. Storage and resource checks are shared across both paths. See [runtime commands and limitations](../docs/RUNTIME.md) and [record fields](../docs/RECORDS.md).

C02 `similar_sound_search/retrieval/` owns exact event supports, capped rank fusion, native overlap consolidation and the C03 shortlist; see its source map.

`similar_sound_search/refinement/` owns C03 audited shortlist import, bounded native timing, atomic evidence, independent accounting and C04 export; see its source map.

`similar_sound_search/processing/` owns C04 input revisions, row cache, transactional
jobs, cumulative pool and D01 API; see its source map and [contract](../docs/PROCESSING.md).

`similar_sound_search/application/` owns the D01 loopback application, native query
editing, protected metadata admission, read-only historical adoption and serial job
orchestration. Its [source map](similar_sound_search/application/README.md) separates
product/API/media ownership from unchanged DSP/ranking owners. C04's historical pool
and partial request remain intact; new work uses only the explicit D01 owner.
