# Listening review identities

`d04-v1.json` freezes the original-mixture/legacy-mean/pitch-off D03 publication:
package identity, query/revision/materialization, result/population, ordered D04
IDs, distinct recordings/groups, scores, native representatives and WAV checksums.
Its `record_hash` is SHA256 over UTF-8 JSON with sorted keys, Python's standard
comma/colon spacing, Unicode preserved and non-finite numbers forbidden, excluding
`record_hash` itself. File SHA256 and logical record identity are separate.

`d04-feedback-template.json` is blank and bound to that review hash. Actual replies,
notes and their evolving revisions remain ignored under `reports/local/d04/`.
Changing reference, membership or timing requires another review version; responses
never silently move between review hashes. [LISTENING.md](../../docs/LISTENING.md)
explains the companion and its private artifacts.

`preparation-allowance.json` records the explicit D04-only continuation amendment:
224 MiB QA, 256 MiB combined new output and 24 cumulative invocations, retaining
600 aggregate seconds and every earlier charge. It is independent of the immutable
review identity and grants no application allocation, inference or numerical change.
