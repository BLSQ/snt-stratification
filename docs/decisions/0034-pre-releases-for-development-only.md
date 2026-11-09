# 0034. Pre-releases are for development and testing only

Date: 2026-10-02
Status: Accepted
Originally: `snt_workspace_bootstrap` D27

## Context

Pre-release tags are used to test changes, including staging pre-releases from feature branches
([`release_strategy.md`](../bootstrap/release_strategy.md)). Country users do not care about them,
and listing them in a checker report would bury the releases that matter.

## Decision

- The checker ignores GitHub pre-releases unless one is the target: `list_releases()` drops them,
  and they are absent from the whole report, `releases_considered` included. With a pre-release as
  the target, other pre-releases stay out. No parameter includes them; a developer types the tag.
- The deployer deploys a typed pre-release as usual, and logs a `[WARNING]` saying it is for
  development and testing only. An empty `release_tag` resolves to the latest full release, never a
  pre-release.
- The report's `schema_version` stays 1: the shape is unchanged.

## Consequences

- Testing can use pre-releases on the real repo, with no separate sandbox repo needed for that.
- Tag naming is not decided by this ADR.
- Detail: [`checker.md`](../bootstrap/checker.md) §4.3.
