"""Freeze the exact D03 provider seam before installed real-catalogue acceptance."""

import argparse
import ast
import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_distribution.contracts import own_code

root = Path.cwd()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--previous-distribution", type=Path)
parser.add_argument("--http-port-repair", action="store_true")
args = parser.parse_args()
target = root / "manifests/distribution/consumer.json"
if target.exists():
    raise RuntimeError(
        "D03 consumer already frozen; retain any failed acceptance and declare an explicit repair"
    )
before = record(root / "manifests/assessment/consumer.json")
code = code_identity()
allowed = {
    "application/api.py": {"status", "result", "result_media", "completed_searches"},
    "application/history.py": {"consumer", "compatible"},
    "application/queries.py": {"QueryOwner"},
    "application/job.py": {"worker", "execute", "_run", "run"},
    "application/validation.py": {"native"},
    "application/server.py": {"make_server", "LoopbackServer"},
}
changed = sorted(k for k, v in before["code"].items() if code[k] != v)
if set(changed) != set(allowed) or set(code) != set(before["code"]):
    raise RuntimeError("D03 changed the numerical source set")
proof = {}
for name in changed:
    path = "src/similar_sound_search/" + name
    old = subprocess.check_output(["git", "show", "f372fe5:" + path]).decode("utf-8")
    new = (root / path).read_text(encoding="utf-8")

    def stable(source):
        tree = ast.parse(source)
        tree.body = [
            n
            for n in tree.body
            if not isinstance(n, (ast.Import, ast.ImportFrom))
            and getattr(n, "name", None) not in allowed[name]
        ]
        return ast.dump(tree, include_attributes=False)

    if stable(old) != stable(new):
        raise RuntimeError("D03 changed code outside the declared provider boundary: " + name)
    proof[name] = sorted(allowed[name])
previous = []
for version, p in (("d01-consumer-1", "application"), ("d02-consumer-1", "assessment")):
    v = record(root / "manifests" / p / "consumer.json")
    previous.append(
        dict(
            version=version,
            declaration_hash=v["record_hash"],
            numerical_hash=v["numerical_hash"],
            code_hash=digest(v["code"]),
        )
    )
if args.previous_distribution:
    prior = record(args.previous_distribution)
    if prior["numerical_hash"] != before["numerical_hash"]:
        raise RuntimeError("Repair cannot change numerical identity")
    if args.http_port_repair:
        differences = {k for k, h in prior["code"].items() if code[k] != h}
        if differences != {"application/server.py"} or own_code() != prior["distribution_code"]:
            raise RuntimeError("HTTP repair exceeds the exact server binding boundary")
        old = subprocess.check_output(
            ["git", "show", "b03ee15:src/similar_sound_search/application/server.py"]
        ).decode("utf-8")
        if (
            hashlib.sha256(old.replace("\r\n", "\n").encode()).hexdigest()
            != prior["code"]["application/server.py"]
        ):
            raise RuntimeError("HTTP repair predecessor source differs")

        class RenameServer(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id == "ThreadingHTTPServer":
                    node.id = "LoopbackServer"
                return node

        expected = RenameServer().visit(ast.parse(old))
        actual = ast.parse(
            (root / "src/similar_sound_search/application/server.py").read_text(encoding="utf-8")
        )
        for tree in (expected, actual):
            tree.body = [
                n
                for n in tree.body
                if not isinstance(n, (ast.Import, ast.ImportFrom))
                and getattr(n, "name", None) != "LoopbackServer"
            ]
        if ast.dump(expected) != ast.dump(actual):
            raise RuntimeError("HTTP repair changed handlers or coordinator behavior")
    elif prior["code"] != code:
        raise RuntimeError("Persistence repair cannot change inherited source")
    own_changed = {k for k, h in prior["distribution_code"].items() if own_code().get(k) != h}
    if own_changed - {"authority.py", "context.py", "cli.py"}:
        raise RuntimeError("Repair exceeds the bounded Windows persistence/abandon boundary")
    previous.append(
        dict(
            version="d03-consumer-1",
            declaration_hash=prior["record_hash"],
            numerical_hash=prior["numerical_hash"],
            code_hash=digest(prior["code"]),
        )
    )
webroot = root / "src/similar_sound_search/application/web"
web = {
    p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    for p in webroot.iterdir()
    if p.is_file()
}
value = dict(
    schema_version="d03-consumer-1",
    before=before["record_hash"],
    before_code=before["code"],
    code=code,
    changed_files=changed,
    allowed_top_level=proof,
    distribution_code=own_code(),
    accepted_previous=previous,
    numerical_hash=before["numerical_hash"],
    web=web,
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    persistence_repair_previous=None if not args.previous_distribution else prior["record_hash"],
)
atomic_json(target, {**value, "record_hash": digest(value)})
print(digest(value))
