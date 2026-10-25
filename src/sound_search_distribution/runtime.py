"""Installed real-catalogue provider; historical results are immutable read-only views."""

from pathlib import Path

from similar_sound_search.application import api, job, queries
from similar_sound_search.application.context import Context as HistoricalContext
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, digest
from sound_search_evaluation.budget import CatalogueBudget

from . import authority, contracts
from .context import Context
from .policy import estimate


class ReadContext(HistoricalContext):
    def readonly(self, *args, **kwargs):
        raise InputError("D03 historical result is read-only; submit a new runtime search")

    charge = publish = admit = reserve_attempt = terminal = release = readonly


class Runtime:
    budget = CatalogueBudget
    consumer = staticmethod(contracts.consumer)

    def __init__(self, root, share="normal", include_history=True):
        self.root, self.share = Path(root).resolve(), share
        self.include_history = include_history

    def context(self, root, allocation=None):
        if allocation and len(allocation) == 64:
            if (self.root / "data/runs/application/jobs" / (allocation + ".json")).exists():
                return ReadContext(self.root, allocation)
            for share in ("verification", "normal"):
                if (
                    self.root / ("data/runs/runtime-" + share) / "jobs" / (allocation + ".json")
                ).exists():
                    return Context(self.root, allocation, share)
        return Context(self.root, allocation, self.share)

    def result_context(self, key):
        return self._record_context("results", key)

    def waveform_context(self, key):
        return self._record_context("waveforms", key)

    def media_context(self, key):
        return self._record_context("media", key)

    def _record_context(self, kind, key):
        api.identifier(key)
        for share in (self.share, "verification" if self.share == "normal" else "normal"):
            owner = Context(self.root, share=share)
            if (owner.directory / kind / (key + ".json")).is_file():
                return owner
        old = ReadContext(self.root)
        if (old.directory / kind / (key + ".json")).is_file():
            return old
        raise InputError("D03 unknown " + kind + " identity: " + key)

    def population_id(self, owner):
        return digest([owner.protocol["snapshot"], owner.binding["allocation_id"], owner.share])

    @staticmethod
    def allocation(request):
        return None

    def estimate(self, request):
        return estimate(request["kind"])["ordinary_bytes"]

    def validate_request(self, owner, request):
        if request["kind"] not in {
            "search",
            "validate",
            "register",
            "copy-reference",
            "save",
            "rename",
            "preview",
            "native-qa",
        }:
            raise InputError("D03 operation is not available in the installed runtime")
        if request["kind"] in {"search", "validate"}:
            spec = request["input"]
            if spec.get("arm") not in {"legacy-mean", "event-multi"}:
                raise InputError(
                    "D03 supports legacy mean and experimental event-multi; historical "
                    "refinement is separate"
                )

    def admit(self, owner, request):
        owner.allocation = owner.job_id
        owner.operation = request["kind"]
        if request["kind"] in {"search", "validate"} and not request["input"]["query"].get(
            "historical"
        ):
            from similar_sound_search.queries.library import revision

            owner.examples = len(
                revision(queries.QueryOwner(owner), request["input"]["query"]["revision"])[
                    "recipe"
                ]["examples"]
            )
        owner.admit(owner.job_id, self.estimate(request), jobs=1)

    def run(self, root, limits, key):
        owner = self.context(root, key)
        if isinstance(owner, ReadContext):
            raise InputError("D03 cannot execute a historical delivery job")
        result = job.run(root, limits, key, runtime=self)
        if result["state"] == "complete":
            owner.release(key)
        else:
            authority.checkpoint(owner, key)
        return result

    @staticmethod
    def units(owner, value):
        return [u for u in job.units(owner, value) if u != "chain"]

    @staticmethod
    def execute(owner, key, limits, validate_units=None, finalization_audit=False):
        return job.execute(
            owner,
            key,
            limits,
            validate_units,
            finalization_audit,
            script=Path(__file__).with_name("worker.py"),
        )

    def perform(self, budget, owner, value, unit, cache):
        kind = value["identity"]["request"]["kind"]
        if kind == "native-qa":
            from similar_sound_search.application.validation import native

            return native(budget, owner, value["identity"]["request"]["input"], runtime=self)
        if unit != "publish":
            return job.perform(budget, owner, value, unit, cache)
        key = value["job_id"]
        spec = value["identity"]["request"]["input"]
        q = owner.get(job.committed(owner, key, "query")["query"], "queries")
        aggregate = owner.get(
            job.committed(owner, key, "aggregate-final")["aggregate"], "aggregates"
        )
        cards = [c for i in range(5) for c in job.committed(owner, key, "media:" + str(i))["cards"]]
        return dict(
            result=owner.put(
                budget,
                "results",
                dict(
                    schema_version="d01-result-1",
                    state="complete",
                    job_id=key,
                    query=job.committed(owner, key, "query")["query"],
                    selection=spec["query"],
                    policy=spec["arm"],
                    consumer=value["consumer"],
                    **aggregate,
                    cards=cards,
                    chain=None,
                    historical_view=False,
                    resource_owner=(owner.directory / "pool.json")
                    .relative_to(owner.root)
                    .as_posix(),
                    runtime_allocation=owner.binding["allocation_id"],
                    share=owner.share,
                    historical_c04_state="partial 145/148",
                    new_catalogue_encodes=0,
                    defaults=dict(audio="original", arm="legacy-mean", pitch="off"),
                    saved_query_feature_hash=q["feature_hash"],
                ),
            )
        )

    def inventory(self, owner):
        base = queries.QueryOwner(owner).directory
        names = [record(p) for p in sorted((base / "names").glob("*.json"))][:64]
        refs = []
        for p in sorted((base / "assets").glob("*.json"))[:64]:
            a = record(p)
            key = a["asset_id"]
            item = dict(asset_id=key, audio=a["identity"]["audio"], label="Saved reference")
            for share in ("verification", "normal"):
                folder = self.root / ("data/runs/runtime-" + share)
                label, wave = (
                    folder / "reference-labels" / (key + ".json"),
                    folder / "reference-overviews" / (key + ".json"),
                )
                if label.is_file():
                    item["label"] = record(label)["label"]
                if wave.is_file():
                    item["overview"] = record(wave)["overview"]
            refs.append(item)
        from similar_sound_search.queries.library import revision
        from similar_sound_search.retrieval.context import QueryView

        old = QueryView(owner)
        rev = revision(old, owner.protocol["delivery"]["revision"])
        return dict(
            names=names,
            references=refs,
            historical=dict(
                label="Loulou 3:38–4:00 · original mixture",
                historical=True,
                **owner.protocol["delivery"],
                event=[9613800, 10584000],
                context=[9569700, 10628100],
                rate=44100,
                asset_id=next(iter(rev["recipe"]["assets"])),
                recipe=rev["recipe"],
                available=True,
                overview=None,
                preview_url="/private-reference/loulou.wav",
                provenance="Identity, rights, version/master alignment and intended layer "
                "unverified",
            ),
            historical_saved=[],
            historical_refinement_available=False,
            unavailable=dict(
                pitch="Pitch off",
                transform="Originals only",
                automatic_selection="Select native intervals",
                new_query_refinement="Not available",
            ),
        )

    def additional_completed(self):
        if not self.include_history:
            return []
        other = "verification" if self.share == "normal" else "normal"
        return api.completed_searches(self.root) + api.completed_searches(
            self.root, runtime=Runtime(self.root, other, False)
        )

    def catalogue(self, owner):
        from .doctor import capacity

        cap = capacity(owner)
        return dict(
            state="ready-for-validation",
            recordings=72,
            native_rows=54939,
            missing=0,
            message="72 recordings · 54,939 native passages. " + cap["reason"],
        )

    def artifact(self, path):
        if path != "/private-reference/loulou.wav":
            return None
        from .files import sha, target

        files = record(self.root / "private-assets.json")["files"]
        choices = [
            n
            for n in files
            if n.endswith("b91a8bffd1e5170651feaa874190096201a2df647833d41a621a5e09ef07bf79.wav")
        ]
        if len(choices) != 1:
            raise InputError("D03 exact original Loulou preview missing")
        p = target(self.root, choices[0])
        if sha(p) != files[choices[0]]["sha256"]:
            raise InputError("D03 original preview bytes changed")
        return p, "audio/wav"
