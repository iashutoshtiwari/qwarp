---
name: qwarp
description: Implement QWarp features, bug fixes, referenced GitHub issues, and release work intended for the next release, including version selection, review gates, packaging, CI, and publication.
---

# QWarp next-release workflow

Use this workflow for release-scoped QWarp work. Follow `AGENTS.md` for the
architecture, Qt/threading, compatibility, security, testing, localization, and
packaging invariants; do not repeat them here.

## 1. Inspect efficiently

At task start, read the applicable `AGENTS.md`; inspect the branch, upstream,
worktree, and recent relevant history; then locate only the requested code and
tests. Fetch only when remote freshness is required. Prefer batched local
`git`, `rg`, and targeted reads, and reuse facts already obtained.

Do not scan the whole repository when targeted inspection is sufficient. Use
GitHub MCP only for GitHub-only state such as issues, PRs, Actions, and
releases—not local repository content or history. Browse the web only when
current external behavior or documentation is needed. Do not narrate routine
tool calls.

## 2. Propose the release version

Determine the published/master version from authoritative repository state,
never a stale `release/*` branch. Classify the requested release:

- patch: fixes, regressions, security/reliability work, or compatible internal
  improvements;
- minor: backward-compatible user-visible capabilities or meaningful features;
- major: intentionally breaking contracts, major redesigns, incompatible
  behavior, or a project-defined stable-major transition.

Reply exactly in this compact form, then stop:

`Recommend vX.Y.Z (<patch|minor|major>) — <reason>. Scope: <short scope>. Risk: <low|medium|high>. Reply "go" or give another version.`

Do not create a branch or edit version metadata before approval. `go` accepts
the proposal; an explicit alternate version replaces it. Reject any version
already present in authoritative published state.

## 3. Create or reuse the release branch

After version approval, refresh local knowledge of `master`, confirm the
worktree is safe, and create `release/vX.Y.Z` from current `master`, or safely
reuse that matching active branch. Never base new work on a stale branch for a
published release. Do not create final commits yet.

## 4. Plan minimally

Output only:

`Plan: <affected components>; tests: <tests>; QA: <manual areas>.`

Use a referenced GitHub issue as input; otherwise the prompt is sufficient.
Challenge the requested approach only when architecture, reliability,
security, compatibility, or SemVer materially requires it. Avoid long design
documents unless the change is architectural.

## 5. Implement

Find the root cause of bugs and make the smallest correct change. Avoid
speculative refactors and dependencies; refactor only for correctness,
reliability, testability, or materially lower complexity. Add or update tests
proportional to risk and follow the localization workflow for visible strings.

## 6. Keep tool use lean

Batch compatible read-only commands, use `rg` before opening files, inspect
symbols rather than whole files, and run affected tests first. Do not repeat an
unchanged successful check or rerun an identical failure without changing the
hypothesis or environment. Prefer existing scripts, summarize output unless raw
logs are diagnostic, and stop exploring once evidence is sufficient. After two
failed attempts from essentially the same hypothesis, reassess instead of
repeating commands.

## 7. Verify before review

During development run the narrowest relevant checks. Once stable, run these
non-live gates once, plus any check required by the changed code:

```bash
ruff check src/ tests/
ruff format src/ tests/ --check --diff
QT_QPA_PLATFORM=offscreen pytest tests/ -v --tb=short
```

At this stage do not update release metadata or changelog, create final
commits, push, merge, tag, dispatch workflows, or publish.

## 8. Human review gate — hard stop

After automated verification succeeds, report only:

```text
READY FOR REVIEW
Version: vX.Y.Z
Branch: release/vX.Y.Z
Changed: <very short summary>
Checks: <concise results>
Manual QA: <release-specific checklist>
```

For a patch, request affected-area QA plus core smoke tests; for a minor,
broader affected-feature/regression QA; for a major, full documented live QA.
The maintainer must inspect the diff and perform local/live testing. Stop. Only
an explicit `approved` or equally explicit approval permits preparation;
silence or unrelated messages do not.

## 9. Prepare the release after approval

Update only required documentation and metadata. Synchronize the version in
`src/qwarp/__init__.py`, `CHANGELOG.md`, `PKGBUILD`, `.SRCINFO`,
`.github/workflows/ci.yml`, Debian/RPM metadata, source checksum, and any other
metadata enforced by `scripts/check_release.py`. Follow the existing Keep a
Changelog style. Update README or other docs only for changed user-visible
behavior, configuration, installation, compatibility, or workflows.

If visible strings changed, complete the localization workflow in `AGENTS.md`.
First update release versions and notes, then build the release artifacts. Set
the `PKGBUILD` checksum to the generated source archive's SHA-256 and regenerate
`.SRCINFO` with `makepkg --printsrcinfo > .SRCINFO`. Use the existing release
scripts rather than reconstructing their logic:

```bash
bash scripts/build_artifacts.sh
python scripts/check_release.py --version X.Y.Z --artifacts dist/release
bash scripts/smoke_frozen.sh dist/qwarp-build/qwarp X.Y.Z
(cd dist/release && sha256sum --check SHA256SUMS)
```

Review the exact source checksum in `PKGBUILD` and run the relevant package
ownership/build checks defined by CI. Never weaken or bypass a failure. If
verification requires runtime/application changes, invalidate approval, fix
and test, then return to the human review gate.

## 10. Commit cleanly

Only after approval and successful verification, create clean commits:

1. one coherent Conventional Commit per logical implementation/test change,
   such as `fix(scope): ...`, `feat(scope): ...`, or `refactor(scope): ...`;
2. one `chore(release): prepare vX.Y.Z` commit.

Do not create checkpoint commits.

## 11. Merge through reviewed CI

Push `release/vX.Y.Z`, then use GitHub MCP when available (otherwise existing
authenticated GitHub tooling) to create or update its PR to `master`. Wait for
required CI. Inspect failed/relevant jobs first and fix the root cause with the
smallest investigation. Runtime behavior changes after approval return to the
human review gate.

After required CI passes, merge with the repository's expected strategy and a
title such as `Release QWarp vX.Y.Z`. Do not rewrite published history or force
push release state.

## 12. Publish through the authoritative workflow

On `master`, manually dispatch the existing GitHub `Release` workflow with:

- `version = X.Y.Z`
- `live_qa_completed = true`

The earlier explicit QA approval is the only basis for the attestation. Monitor
through GitHub MCP. The workflow is authoritative for final validation,
artifacts, Arch/Debian/RPM packages, provenance, protected-environment approval,
tagging, AUR publication, and the immutable GitHub release; do not reproduce
those steps locally.

If the protected `release` environment pauses, report the one required
maintainer action and wait. Never force-push AUR, move a tag, or overwrite a
release. On failure, inspect only the failed job/logs, diagnose first, and make
the smallest valid correction.

## 13. Verify publication

After success, verify through GitHub MCP that `vX.Y.Z` exists, the GitHub
release has the expected source, binary, Debian, RPM, and checksum assets, and
the workflow succeeded. Verify AUR `qwarp` is `X.Y.Z-1` with lightweight AUR
RPC or git if needed; do not add an AUR MCP server.

Report only:

`RELEASED vX.Y.Z | GitHub ✓ | AUR X.Y.Z-1 ✓ | CI ✓`

Optionally add a real cleanup item such as deletion of the merged release
branch.

## Durable workflow feedback

When maintainer feedback establishes a recurring repository invariant or
workflow change, update `AGENTS.md` or this skill in the single appropriate
place. Do not encode one-off observations.
