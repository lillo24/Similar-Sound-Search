"""Lossless bounded group storage; numerical values and order are untouched."""

import base64
import json
import zlib

from ..storage import InputError, canonical, digest


def encode(kind, value):
    if kind != "group-results":
        return value
    value = {k: v for k, v in value.items() if k != "record_hash"}
    raw = canonical(value)
    if len(raw) > 1024**2:
        raise InputError("D01 expanded group exceeds 1 MiB; split support references")
    return dict(
        schema_version="d01-packed-group-1",
        content_hash=digest(value),
        bytes=len(raw),
        data=base64.b64encode(zlib.compress(raw, 6)).decode("ascii"),
    )


def decode(value):
    if value.get("schema_version") != "d01-packed-group-1":
        return value
    stream = zlib.decompressobj()
    raw = stream.decompress(base64.b64decode(value["data"], validate=True), 1024**2 + 1)
    if len(raw) != value["bytes"] or len(raw) > 1024**2 or not stream.eof or stream.unused_data:
        raise InputError("D01 invalid/bomb group codec")
    result = json.loads(raw)
    if digest(result) != value["content_hash"]:
        raise InputError("D01 group numerical payload changed")
    return {**result, "record_hash": value["record_hash"]}
