# D03 local package

The delivery is a non-editable wheel inside a checksummed offline code archive.
It targets **Windows AMD64, exact Python 3.12.14**, Torch 2.6.0+cpu and the two
unchanged lockfiles. Core 0.3.0 remains the frozen numerical version; the independent
distribution ID is `d03-1.0.0`. Other platforms are unverified product targets.
See [measured delivery evidence](../reports/D03_PACKAGE.md) for the actual artifact
hash, source revision, tested paths, search IDs, costs and retained failures.

## Install and prepare

Extract only after checking the published SHA256. The archive's stdlib `setup.py`
also offers `extract --archive <zip> --destination <absent-directory> --sha256 <hash>`.
It preflights names, duplicate/case conflicts, regular file types, expansion and
disk headroom before writing. It refuses traversal, links/junctions and overwrites.

```powershell
python setup.py verify
python setup.py install --environment C:\SoundSearch\environment
```

Use the exact required interpreter to run setup. It creates a new isolated
environment, installs the verified complete wheel closure with `--no-index
--no-deps --no-cache-dir`, and runs `pip check`. Existing environments are refused,
never silently cleared. No model or audio is downloaded. Keep the environment at
its installed path because Windows launchers embed that path.

The code archive contains no private audio, model checkpoint, candidate arrays,
runtime ledger or token. A separate actual dependency closure must be staged from
the private delivery workspace. Use a **short** Windows root: content-addressed
historical paths must fit 240 characters including staging. Preparation checks
this before copying. Spaces and non-ASCII names are supported.

```powershell
& C:\SoundSearch\environment\Scripts\python.exe -I -m sound_search_distribution prepare --source C:\PrivateOriginal --distribution C:\SoundSearch\code --workspace "C:\SSS D03 è\w"
& C:\SoundSearch\environment\Scripts\python.exe -I -m sound_search_distribution doctor --workspace "C:\SSS D03 è\w" --deep
```

Preparation preserves relative paths, original byte hashes and producing IDs. It
copies the 72 real recordings, MN04, exact C01/C04/query dependency graph and three
completed D01 results; it does not substitute D02's generated population or create
C01 producer receipts. Optional full C03/D02 views are omitted and reported
unavailable. Original C03 bundle/evidence remain in the original checkout.

The installed doctor distinguishes dependency, source/proof, model/private-file
and capacity failures. `--deep` checks every private byte; ordinary startup checks
metadata/availability and model hash. New search owns charged fresh sequential
source/PCM/array audits. Page/status reads never dispatch inference or downloads.

## Start, restart and move

```powershell
& C:\SoundSearch\environment\Scripts\python.exe -I -m sound_search_distribution start --workspace "C:\SSS D03 è\w" --port 8776
```

Open `http://127.0.0.1:8776/`. Startup binds loopback only, refuses live ports and
prints its foreground PID. Ctrl+C stops admission and waits for owned work. Host,
Origin, session token, opaque IDs and complete-result media scope stay enforced.
Restart rotates the token. Cancel/resume retains the same immutable request and
committed features; a failed search remains a failed search.

Stop the server before a same-host workspace move:

```powershell
& C:\SoundSearch\environment\Scripts\python.exe -I -m sound_search_distribution relocate --workspace "C:\SSS D03 è\w" --destination "C:\SSS D03 à\w"
```

The absent destination's parent must exist. This renames the same workspace and
updates its one external canonical binding; UUID, ledger bytes and charges stay
the same. A copied backup cannot run as another allowance. If interrupted between
rename and registry publication, restore the original path before retrying.

One initialization binds the workspace UUID/allocation UUID to
`%LOCALAPPDATA%\SimilarSoundSearch\D03\allocation.json`, outside workspace backups.
Missing/corrupt pools, stale generations or missing registry are explicit recovery
errors. Restore the latest complete workspace **and** its external registry; keep
private backups private. Do not replace them with empty state. The CLI has no reset,
renewal or daily-refill command. A later resource-policy change must preserve spent
history and add a separate explicit authorization.

An unrecoverable stopped incomplete job can be closed with `abandon --job-id <id>`
after server shutdown. Its failed state, units, attempts and spent charges remain;
only demonstrably unused reservations are released. Windows replacement retries
the same prepaid temporary for at most one second; permanent errors retain it and
fail loudly. No older complete result conceals a failed operation.

## Finite normal use

The authorized total is split into fixed verification and normal shares. Each
permits 3,600 worker seconds, 256 workers, 90,000 read seconds, 512 query rows,
6,000 processed seconds, 32 MiB features, 64 jobs, 64 clips/128 MiB, 256 MiB
metadata (32 MiB protected), 64 MiB preparation, 128 MiB imports and 512 MiB output.
The metadata envelope is reserved inside managed output. A complete search also
has 1,200 aggregate worker seconds, 128 workers, 30,000 read seconds and 96 MiB
ordinary metadata ceilings. Admission checks the whole bounded path and disk;
individual maxima cannot all be filled simultaneously.

Workers have a 120-second actual-PID deadline, one numerical thread, 256 MiB
input/decoded/output limits and a 1 GiB checked numerical working estimate. Memory
is measured; this is not an OS-enforced RSS cap. Combined managed storage remains
4 GiB with 4 GiB free after reserved writes. Private copying/staging has a separate
1 GiB live cap; new setup/environments/wheels/archives have a 3 GiB live cap.

Delivery QA uses verification only, with a 64 MiB maximum non-inference artifact
envelope. The normal share remains available for real user requests and completed
results remain readable after exhaustion. Keep/export the complete private
workspace and registry inventory; automatic garbage collection and user deletion
are outside this task. Human relevance, rights, version/master and intended-layer
alignment remain unverified. **D04 has not started.**
