"""Trusted finite generated-population provider for the unchanged local HTTP/UI API."""

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, ResourceError, contained, digest

from . import contracts, pipeline
from .budget import CatalogueBudget
from .context import MIB, Context


class Runtime:
    budget = CatalogueBudget

    def __init__(self, root, split="development"):
        self.root, self.split = root, split

    def context(self, root, allocation=None):
        owner = Context(root, allocation, self.split)
        if allocation and len(allocation) == 64:
            path = owner.directory / "jobs" / (allocation + ".json")
            if path.exists():
                value = record(path)
                owner.allocation = value["allocation_owner"]
                owner.split = value.get("split", self.split)
            owner.job_id = allocation
        return owner

    consumer = staticmethod(contracts.consumer)

    def validate_request(self, owner, request):
        if request["kind"] not in {
            "register",
            "save",
            "rename",
            "preview",
            "search",
            "validate",
            "native-qa",
        }:
            raise InputError(
                "D02 controlled provider does not offer historical/metadata operations"
            )
        if request["kind"] in {"search", "validate"}:
            spec = request["input"]
            if spec.get("arm") not in {"legacy-mean", "event-multi"} or spec.get("query", {}).get(
                "historical"
            ):
                raise InputError("D02 requires original saved queries and the two frozen policies")
            pipeline.case_for_revision(owner, spec["query"]["revision"])

    @staticmethod
    def estimate(request):
        return 4 * MIB if request["kind"] in {"search", "validate"} else MIB

    @staticmethod
    def allocation(request):
        return "delivery"

    def admit(self, owner, request):
        if owner.pool()["allocations"][owner.allocation]["remaining"] < self.estimate(request):
            raise ResourceError(
                "D02 complete product operation cannot fit its prepaid delivery allocation"
            )
        owner.charge(None, query_jobs=1)

    @staticmethod
    def population_id(owner):
        return contracts.population(owner)["record_hash"]

    def run(self, root, limits, key):
        from .jobs import run

        return run(root, limits, key, self.split)

    @staticmethod
    def inventory(owner):
        base = owner.directory / "library"
        names = [record(p) for p in sorted((base / "names").glob("*.json"))][:64]
        refs = []
        for p in sorted((base / "assets").glob("*.json"))[:64]:
            v = record(p)
            key = v["asset_id"]
            label = owner.directory / "reference-labels" / (key + ".json")
            wave = owner.directory / "reference-overviews" / (key + ".json")
            refs.append(
                dict(
                    asset_id=key,
                    audio=v["identity"]["audio"],
                    label=record(label)["label"] if label.exists() else "D02 reference",
                    **(dict(overview=record(wave)["overview"]) if wave.exists() else {}),
                )
            )
        return dict(
            names=names,
            references=refs,
            historical=dict(
                available=False,
                label="D02 controlled evaluation; Loulou remains on the normal application",
            ),
            historical_saved=[],
            unavailable=dict(
                pitch="D02 pitch off",
                transform="D02 originals only",
                automatic_selection="Explicit native intervals",
                new_query_refinement="Separate historical C03 chain",
            ),
        )

    @staticmethod
    def catalogue(owner):
        pop = contracts.population(owner)
        return dict(
            state="ready-for-validation",
            recordings=len(pop["sources"]),
            native_rows=sum(
                len(record(p)["features"]["rows"])
                for p in (owner.directory / "index").glob("*.json")
            ),
            missing=0,
            message=(
                "D02 generated evaluation: 32 recordings / 31 distinct groups; separate finite pool"
            ),
        )

    def artifact(self, path):
        if not path.startswith("/evaluation/"):
            return None
        owner = self.context(self.root)
        manifest = record(owner.directory / "report-bundle.json")
        key = path[len("/evaluation/") :] or "index.html"
        if key not in manifest["files"]:
            raise InputError("D02 report path outside immutable bundle allowlist")
        target = contained(owner.root / manifest["files"][key]["path"], owner.root)
        if not any(
            target.is_relative_to(base) for base in (owner.directory, owner.audio, owner.reports)
        ):
            raise InputError("D02 report reference outside its own owner roots")
        import hashlib

        if hashlib.sha256(target.read_bytes()).hexdigest() != manifest["files"][key]["sha256"]:
            raise InputError("D02 report bytes differ from the saved bundle")
        mime = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".wav": "audio/wav",
        }
        return target, mime.get(target.suffix, "application/json")


def category(owner, case_id):
    """A fresh product search is a charged technical replay after its initial claim."""
    key = digest([owner.protocol["record_hash"], owner.split, case_id, "initial", None])
    path = owner.directory / "execution-claims" / (key + ".json")
    return "technical" if path.exists() and record(path)["execution"] != owner.job_id else "initial"
