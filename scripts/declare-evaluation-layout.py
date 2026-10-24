"""Exact two-rule mobile layout proof; preserve historical renderer declarations."""

import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
name = "src/similar_sound_search/application/web/style.css"
before = subprocess.check_output(["git", "show", "9b376c1:" + name]).replace(b"\r\n", b"\n")
after = (root / name).read_bytes().replace(b"\r\n", b"\n")
expected = before.replace(
    b".workspace{grid-template-columns:1fr}", b".workspace{grid-template-columns:minmax(0,1fr)}"
)
expected = expected.replace(
    b".examples li>span{flex:1}", b".examples li>span{flex:1;min-width:0;overflow-wrap:anywhere}"
)
if expected != after:
    raise RuntimeError("D02 UI proof differs from the two reviewed mobile layout rules")
assets = {}
for filename in ("app.js", "index.html"):
    path = "src/similar_sound_search/application/web/" + filename
    old = subprocess.check_output(["git", "show", "9b376c1:" + path]).replace(b"\r\n", b"\n")
    new = (root / path).read_bytes().replace(b"\r\n", b"\n")
    if old != new:
        raise RuntimeError("D02 layout fix changes player/selection markup or JavaScript")
    assets[filename] = hashlib.sha256(new).hexdigest()
target = root / "manifests/assessment/ui-compatibility.json"
prior = record(target)
if prior["record_hash"] != "92bff8c9debebf33d47ca8f42e6332a2f00d7740d5c0723b6cc445b8a5d13027":
    raise RuntimeError("D02 initial layout declaration differs; preserve existing proofs")
atomic_json(target.parent / "ui-proofs" / (prior["record_hash"] + ".json"), prior)
value = dict(
    schema_version="d02-mobile-layout-compatibility-1",
    file=name,
    before_consumer=record(root / "manifests/application/consumer.json")["record_hash"],
    before_sha256=hashlib.sha256(before).hexdigest(),
    after_sha256=hashlib.sha256(after).hexdigest(),
    unchanged_assets=assets,
    predecessor=prior["record_hash"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    change="Mobile grid minimum and long filename wrapping only; no player/crop/numerical change",
)
atomic_json(target, {**value, "record_hash": digest(value)})
print(digest(value))
