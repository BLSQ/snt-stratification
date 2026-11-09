# 0035. A separate pipeline deploys a single pipeline of a release

Date: 2026-10-30
Status: Accepted
Originally: `snt_workspace_bootstrap` D28

## Context

Some workspaces already hold real work, such as a locally hosted OpenHEXA with a running analysis.
Updating the whole release at once is too much change there, but the main deployer deploys only
whole releases ([ADR 0031](0031-deployer-deploys-the-whole-release.md)).

## Decision

A separate pipeline, `snt_pipeline_deployer`, deploys one named pipeline of a release.

- It registers that pipeline's version and copies its own `pipelines/<name>/` R scripts, unless
  `pull_r_scripts` is off.
- It never copies the shared R library (`code/` in the v1 manifest); it names every shared file that
  differs from the release in a `[WARNING]`.
- It writes no `.snt_release`: the workspace is not at the release.
- The code is a copy of the deployer (OpenHEXA zips each pipeline directory on its own, so it cannot
  import from there), kept identical function by function by `tests/test_pipeline_deployer.py`.

## Consequences

- [ADR 0031](0031-deployer-deploys-the-whole-release.md) is unchanged for `snt_workspace_deployer`.
- A workspace deployed this way mixes releases, which is exactly what ADR 0031 prevents. The cost is
  accepted, and the run says so.
- Detail: [`deployer.md`](../bootstrap/deployer.md), section *Single-pipeline deployer*.
