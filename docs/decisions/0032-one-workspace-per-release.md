# 0032. One workspace per release is the expected usage

Date: 2026-10-01
Status: Accepted
Originally: `snt_workspace_bootstrap` D25

## Context

The deployer can move a workspace forwards or backwards between releases. Making back-and-forth
clean (version names, strays, checker statuses after a rollback) would be costly, and nobody has
yet asked for it.

## Decision

Until real users say otherwise, a country keeps one workspace on one release: typically a main
workspace on the latest release, updated forwards. To run data through an older release, it uses a
dedicated workspace deployed at that release. Rolling one workspace back and forth only has to be
**safe** (nothing deleted, superseded files archived, every failure reported), not **clean**.

## Consequences

- Moving forwards is the path that must be solid.
- `+redeploy-` version names, extra versions, strays and odd checker statuses after a rollback are
  accepted. Do not polish that path before there is feedback from real use.
- Revisit once countries run the release process
  ([`release_strategy.md`](../bootstrap/release_strategy.md) §1.3).
