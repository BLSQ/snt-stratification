# 0037. One release train for pipelines, webapps and bootstrap

Date: 2026-11-02
Status: Accepted

## Context

With everything in one repo ([ADR 0036](0036-one-monorepo.md)), each unit could still be released
on its own (per-unit tags) or all together. The deployer installs a release as a whole
([ADR 0031](0031-deployer-deploys-the-whole-release.md)), and the checker attributes a workspace to
releases by file hashes, so a tag that means "one tested combination" is what both tools assume.
The old repos' tags were only ever tests.

## Decision

- **One tag `vX.Y.Z` = one tested combination** of pipelines, webapps and bootstrap.
- The release manifest gains a `webapps` section, and each webapp release zip carries a
  `version.json` stamped at release time.
- A webapp-only fix is a patch release. A pipeline whose files did not change gets no new code:
  the deployer only registers its version again under the new tag (bootstrap D22).
- Numbering starts from scratch: `v0.x.y` pre-releases first, `v1.0.0` for the first production
  release. No live workspace's `.snt_release` marker can collide with an old-repo tag.

## Consequences

- A fix to one unit ships with whatever else is on `main`. Release from `main` only when it is green
  on a release candidate; patch releases are cheap.
- The multi-source bootstrap design (`docs/bootstrap/roadmap.md` §1, one release source per repo)
  is no longer needed.
- Not built yet: the release workflow, manifest v2 and the stamped webapp zips are Phases 3 and 7 of
  [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md).

Source: migration plan D-2, D-8.
