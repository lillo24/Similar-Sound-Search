"""Bind shared PCM cache rows to genuine recording-specific native memberships."""

import copy

from similar_sound_search.processing.contracts import source_key
from similar_sound_search.storage import InputError, digest


def bind(budget, owner, source, index, scored, population):
    """Project identity only for a physical alias; retain raw numerical artifacts.

    C04 caches by PCM/native support. C02 rejects two different recording witnesses
    with one row ID inside a duplicate group. The neutral minimum recording ID
    keeps its cache ID; other actual aliases get a membership ID bound to their
    immutable source index and original cache row. Scores/bounds/support counts
    are copied exactly, with no new distance, feature or rank calculation.
    """
    aliases = sorted(
        s["recording_id"]
        for s in population
        if s["group"] == source["group"] and source_key(s) == source_key(source)
    )
    if not aliases or source["recording_id"] not in aliases:
        raise InputError("D02 source lacks its genuine population membership")
    if source["recording_id"] == aliases[0]:
        return scored
    if index["source"] != source:
        raise InputError("D02 alias index/source identity differs")
    rows = {r["key"]: r for r in index["features"]["rows"]}
    raw = owner.get(scored["result"], "score-results")
    if raw["identity"]["candidate_digest"] != digest(
        [[r["key"], r["vector_sha256"]] for r in index["features"]["rows"]]
    ):
        raise InputError("D02 alias raw scores differ from actual cached native rows")
    projected = copy.deepcopy({k: v for k, v in raw.items() if k != "record_hash"})
    memberships = {}
    for bank in projected["banks"]:
        for row in [bank["baseline"], *[r for values in bank["supports"] for r in values]]:
            original = row["key"]
            if original not in rows or row["bounds"] != rows[original]["native_bounds"]:
                raise InputError("D02 scored alias row outside its immutable native membership")
            member = digest(
                ["d02-recording-row-membership-1", source["recording_id"], original, row["bounds"]]
            )
            memberships[original] = member
            row["key"] = member
    projected.update(
        schema_version="d02-alias-score-membership-1",
        raw_scores=scored["result"],
        recording_id=source["recording_id"],
        source_index=dict(
            path=(owner.directory / "index" / (source["recording_id"] + ".json"))
            .relative_to(owner.root)
            .as_posix(),
            record_hash=index["record_hash"],
        ),
        memberships=memberships,
    )
    return dict(result=owner.put(budget, "score-results", projected))
