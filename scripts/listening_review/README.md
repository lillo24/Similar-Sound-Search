# D04 companion map

This stdlib-only subsystem owns the listening presentation, outside the frozen
core, evaluation and distribution packages. `../d04-review.py` enters it using
the installed interpreter; `../listen-d04.ps1` supplies the private launch config.

| File | Responsibility and relationship |
| --- | --- |
| `common.py` | D04 canonical identity, exclusive file writes, bounded JSON, containment and output inventories |
| `manifest.py` | Validate the exact saved result, native/media bindings and stable review IDs; format timestamps from frames |
| `prepare.py` | Read the installed provider, verify the retained reference proof, and copy only allowlisted unchanged clips |
| `preservation.py` | Snapshot historical pools/ledgers/configuration/declarations and frozen source; compare prior hashes after QA |
| `feedback.py` | Optional responses, exact review membership, qualitative counts and immutable parent-linked revisions |
| `server.py` | Loopback-only finite routes/ranges and Host/Origin/session-token write protection; no application operations |
| `web/index.html`, `web/review.css`, `web/review.js` | Reference-first accessible cards, exclusive playback, temporary drafts and explicit durable save/export/import |

`../d04-check.py` supervises only D04's small validation allowance using the existing
actual-process timeout pattern. Public manifests/reports contain no raw notes,
private paths or audio. See [listening instructions](../../docs/LISTENING.md) for
boundaries, recovery and reproduction prerequisites.
