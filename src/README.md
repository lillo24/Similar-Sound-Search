# Audio input runtime

`similar_sound_search/` owns A02's CPU input pipeline. It has no model, catalogue acquisition, or retrieval code. The installed `sound-search` command and `python -m similar_sound_search` both enter `cli.py`.

| File | Responsibility and relationship |
| --- | --- |
| `similar_sound_search/__init__.py`, `__main__.py` | Package version and module entry point |
| `similar_sound_search/cli.py` | Parse explicit operations, hold the project lock, run a worker with a hard timeout, and publish private JSON reports |
| `similar_sound_search/resources.py` | Validate required tier limits and enforce file, allocation, disk, inventory, and elapsed-time boundaries |
| `similar_sound_search/storage.py` | Hash/JSON identity, path containment, atomic reports, errors, and OS process lock |
| `similar_sound_search/inputs.py` | Probe/decode bounded WAV/FLAC, measure peak/RMS/silence, and register explicit files/directories |
| `similar_sound_search/records.py` | Validate supplied context and compose elapsed-time mappings independently of recording identity |
| `similar_sound_search/preparation.py` | Apply explicit crop/channel/resample choices; publish immutable bundles and validate reuse/lineage |
| `similar_sound_search/diagnostics.py` | Generate deterministic plumbing fixtures, check independent known answers, and report actual environment capabilities |

The CLI imports numerical/decoder libraries only in the bounded worker. Inputs feed candidate records; preparation retains those source records and composes maps back to the original available file. Storage and resource checks are shared across both paths. See [runtime commands and limitations](../docs/RUNTIME.md) and [record fields](../docs/RECORDS.md).
