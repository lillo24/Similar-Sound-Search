# Code Organization for Multi-file Projects
Use a clear **module / feature / package / subsystem boundary** as the main unit of abstraction, following the structure already established by the repository.

- Each file should have a clear **abstract purpose** (what it owns / what it is responsible for).

## Folder map policy

Use folder-level `README.md` files as **navigation maps for the source tree**, not as a ritual.

Keep it for folders that contain real logic, structure, or collaboration between files.
Skip it for folders that are obvious storage buckets, generated output, or already clear from names alone (so repeating the directory listing)

Each folder README should briefly say:

- what the folder owns
- what each file does
- how the files relate

### Rule of thumb

Keep README files in folders that help humans navigate behavior, architecture, or responsibility.
Skip them in folders that mainly store obvious content.

—

# Reproducibility and Traceability
## Doc/Comment Sync (non-obvious changes)

If you introduce or modify **non-obvious behavior** or **configuration**, you must update the closest appropriate documentation (or inline comments) in the same change.

Examples that require an update:

- new env vars / config keys / flags
- default values that change behavior
- implicit assumptions (paths, locale/timezone, encoding, auth, caching)
- new required setup steps
- behavior that differs across environments (dev vs prod, Windows vs Linux)

Where to document:

- prefer the nearest “source of truth”
  E.g. README / “map.txt” / config schema-docs / docstring or comment at the interface

Goal: someone can reproduce the behavior without reading the whole codebase.

—

# Handling Doubts & Architecture Fit
## 1) Underspecified requirements: decide what you can safely assume

If something important is unclear, do **not** silently guess.

- **If multiple reasonable interpretations would materially change product behavior, security/privacy, data permanence, recurring cost, a public contract, or another consequential outcome:** stop and ask, or clearly surface the alternatives when the execution environment allows it.
- **Otherwise, if there is a safe, conservative interpretation consistent with the repository and existing behavior:** proceed, but **state the assumption** explicitly when it matters.

Examples of “important” ambiguity:

- expected output format, business rules, edge-case handling
- security/privacy implications
- breaking changes to interfaces
- performance/caching behavior

**Never** introduce new features “because it might be useful”.

## 2) Architecture quick-check (before editing)
Inspect the current repository and the relevant implementation before making a non-trivial change. Do not assume an older prompt, report, or remembered structure still matches the code.

Before making non-trivial changes:

- Identify the **owner** of the responsibility you’re touching (which file/module is supposed to own it).
- Check for existing patterns (how similar things are done elsewhere).
- Keep changes consistent with the repo’s abstractions unless the request explicitly says to change them.

If your change would violate an existing abstraction, either:

- find the correct place to implement it, or
- clearly propose the refactor as a separate step (do not blend it in silently), thus discuss it with the user

—

# GitHub Repo Workflow
## Branching, Parallel Work, PR Merge, and Cleanup
### Default workflow
Use one **isolated branch/worktree** per `.md` implementation plan.
If the execution environment already provides an isolated managed worktree, use it rather than creating a nested one unnecessarily.

Do not mix unrelated plans in the same branch.

After finishing a plan:

- run checks
- inspect the diff
- commit only intended files
- push the branch
- always open a GitHub PR into main; do not consider an implementation task complete while its changes exist only in a local branch/worktree
- after required CI passes and the PR is cleanly mergeable, merge it automatically unless the active task explicitly requires founder/manual review or there is an unresolved consequential decision that cannot be safely resolved from repository evidence and tests
- when leaving a PR open, state exactly what requires human review; do not leave it open merely because manual approval is possible
- after the PR is merged and no further QA, review, or fix-up work requires the isolated checkout, remove the task worktree if it was created manually or is still present
- then delete the task branch locally and remotely when the repository/workflow expects manual cleanup
- do not leave merged-plan worktrees behind; before creating a new manual worktree, check `git worktree list` and remove stale worktrees from already-merged plans

A PR is required even when automatic merge is expected. The PR is the durable review/traceability artifact for the task.

Code merge and external deployment are separate actions: automatic PR merge does not authorize production deployment, billing changes, DNS changes, destructive production operations, or other external actions that require explicit authorization elsewhere in this file.

Do not push directly to `main` unless the active user/task instruction explicitly authorizes it.


### Parallel tasks
Parallel Codex tasks must use separate branches/worktrees.
The first finished task may merge first.
Every later task must update from latest `main` before merging.

When the coding environment manages worktrees automatically, preserve that isolation and focus on the integration rule above rather than recreating the worktree manually.

## CI / GitHub Actions Resource Discipline

Treat CI as a finite project resource, especially in private repositories where hosted-runner usage may be limited or billed.

Default to **change-scoped validation**:
- run all checks that can reasonably be affected by the changed files/areas;
- do not run expensive unrelated validation merely because a PR changed;
- shared/root/tooling/configuration files must trigger every area they can affect;
- cross-cutting changes should run multiple areas when appropriate.

Expensive integration, database, end-to-end, build, or platform-specific suites should not run on unrelated changes.

Avoid duplicate validation on both the PR and the resulting push to `main` unless the post-merge run has a distinct purpose.

Keep an explicit way to run the **complete validation suite manually** for:
- releases;
- integration checkpoints;
- CI/workflow changes;
- difficult debugging;
- cases where full validation is explicitly requested.

Do not reduce CI cost by weakening meaningful test coverage. Prefer reducing unnecessary trigger frequency and redundant execution.

When changing CI:
- inspect repository dependencies before defining path boundaries;
- preserve required-status-check / branch-protection behavior;
- do not use path filtering in a way that can leave a required check permanently pending;
- document non-obvious CI trigger behavior near the repository's CI configuration;
- justify changes that substantially broaden recurring CI cost.

—

# Libraries and Dependencies

## Follow the versioned documentation
Inspect the dependency manifests, lockfiles, and existing code before relying on an API. When behavior is version-sensitive, use documentation compatible with the version actually resolved or required by the repository.

If you want to use **bleeding-edge** or unreleased features, you must:
- state it explicitly
- explain why it’s worth the risk
- provide a fallback (or avoid it)

## Adding dependencies (be conservative)

- Add a dependency only if it’s clearly justified and not already available in the stack.
- Prefer well-maintained, widely used libraries.
- Follow the repository’s dependency-version policy and package-manager conventions; commit/update lockfiles when the ecosystem expects them.

## Removing dependencies (double-check usage)
Before removing a dependency, run a repo-wide search for the dependency name and common import paths, and verify it is not used in:
- runtime code imports
- build scripts / CI
- tooling configs (lint/format/test)
- documentation examples

—

# Change Discipline (Minimize Unintended Damage)

Default stance: **conservative edits**. Prefer correctness + stability over “improvements”.

## 1) No Unrelated Changes

Unless explicitly needed, do **not**:

- rename files/folders/symbols
- reformat code or reorder imports
- reorganize modules
- “modernize” patterns or style

If formatting happens automatically, try to **limit it** to the smallest area.

## 2) Respect Interfaces (Contracts)

Treat public surfaces as fragile:

- function signatures / return shapes / error behavior
- file formats / schemas
- CLI flags / config keys
- endpoints + payloads (if any)

If you must change a contract:

- update **all** call sites in the same change
- document the change at the interface boundary (docstring/comment + relevant docs)

## 3) Preserve Behavior by Default

- Keep existing behavior unless the request **explicitly** asks to change it.
- If behavior changes, make it:
  - intentional
  - described (briefly) near the code
  - verifiable (test or runnable example when applicable)

## 4) Don’t “Fix” Tests Casually

- Don’t edit tests unless the task requires it or the test encodes a wrong spec.
- If something fails, try fixing **implementation first**.
- If you do change tests, state **why** (what spec changed).

—

# Error Handling (Fail Loud, No “Success-Shaped” Failures)

Default stance: a failure must look like a failure. Don’t hide errors behind “empty but valid” outputs.

## 1) Catch only what you can handle
- Inside domain/business logic, prefer narrow catches for failures you can meaningfully handle.
- Broad catches are allowed at explicit process, request, application, CLI, or background-job boundaries when they report/log useful context and convert the exception into an explicit failure rather than swallowing it.

- Catch specific exception types you expect (I/O, parse errors, network errors).
- If you catch it, you must either:
  - convert it into an explicit error result, or
  - raise with added context (preferred).

## 2) No silent defaults

- Don’t invent fallback values that change behavior without telling anyone.
- If a config value is required for correctness, missing/invalid config must error.
- If a default is acceptable, it must be:
  - explicitly documented near the interface (config schema/docstring), and
  - stable (changing it counts as behavior change -> update docs/tests).

## 3) No “success-shaped” fallbacks
Never return an empty, placeholder, cached, or partial result **to conceal a failed operation**.

Legitimate empty domain states such as `[]`, `{}`, or `""` are allowed when they are valid results and are distinguishable from failure.

Examples of invalid success-shaped fallbacks include:
- placeholder IDs or “OK” status after an operation failed
- partial manifests presented as complete
- “Use last cached result” unless the feature explicitly calls for it and is documented

## 4) Errors must be actionable

When failing, include minimal context:

- which step failed (e.g., fetch, parse, chunk, embed)
- target identifiers (URL/path/doc_id/revision_id)
- what was expected vs what was found (brief)

—

# Last Check (Definition of Done)

This file defines the minimum checks that must pass before a task is considered “done”.

## Required
- Run the smallest complete set of formatting, static-analysis, build, test, migration, integration, or smoke checks that validates **every changed area**.
- Use the repository’s standard commands when they exist.
- Full repository CI should pass before merge unless the repository explicitly defines a narrower merge policy.
- Do not state that a check passed if it was not run.
- If a required check cannot run because of an environment/tool limitation, report the limitation clearly and distinguish it from a failing check.

## When behavior changes

- Add/update tests to cover the new/changed behavior

## If the repository is testless

- Provide at least one of:
  - a runnable example / smoke check command
  - a minimal script that exercises the critical path
  - a documented manual test procedure
