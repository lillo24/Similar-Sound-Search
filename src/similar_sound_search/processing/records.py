"""Lossless compact native-row references; full legacy records remain readable."""

from ..storage import InputError


def compact(value):
    if "rows" not in value:
        return value
    fields = {"key", "native_bounds", "row", "vector_sha256", "bundle", "source_key"}
    if any(set(row) != fields for row in value["rows"]):
        raise InputError("C04 compact references: unclassified row field")
    bundles = sorted({(r["bundle"], r["source_key"]) for r in value["rows"]})
    indices = {v: i for i, v in enumerate(bundles)}
    return {
        **{k: v for k, v in value.items() if k != "rows"},
        "row_references": dict(
            schema_version="c04-compact-rows-1",
            bundles=[list(v) for v in bundles],
            rows=[
                [
                    r["key"],
                    r["native_bounds"],
                    r["row"],
                    r["vector_sha256"],
                    indices[r["bundle"], r["source_key"]],
                ]
                for r in value["rows"]
            ],
        ),
    }


def expand(value):
    if "row_references" not in value:
        return value
    saved = value["row_references"]
    if saved.get("schema_version") != "c04-compact-rows-1" or "rows" in value:
        raise InputError("C04 compact references: unsupported schema or mixed rows")
    rows = []
    for item in saved["rows"]:
        if (
            len(item) != 5
            or isinstance(item[4], bool)
            or not isinstance(item[4], int)
            or not 0 <= item[4] < len(saved["bundles"])
        ):
            raise InputError("C04 compact references: invalid bundle index")
        bundle, source_key = saved["bundles"][item[4]]
        rows.append(
            dict(
                key=item[0],
                native_bounds=item[1],
                row=item[2],
                vector_sha256=item[3],
                bundle=bundle,
                source_key=source_key,
            )
        )
    return {**{k: v for k, v in value.items() if k != "row_references"}, "rows": rows}
