# 0026. Checking and fixing a workspace are separate pipelines; the checker is read-only

Date: 2026-09-18
Status: Accepted
Originally: `snt_workspace_bootstrap` D2

## Context

The bootstrap needs two jobs: find out which release a workspace is on, and move it to a release.
A daily, unattended check was the original motivation: it should be safe to schedule and to run
in any workspace without fear of changing it ([`checker.md`](../bootstrap/checker.md) §7.6).

## Decision

Check and fix are **separate pipelines**. `snt_workspace_checker` is read-only: it writes its
report and nothing else; it never deletes, moves, overwrites, deploys or archives.
`snt_workspace_deployer` (and `snt_pipeline_deployer`, [ADR 0035](0035-single-pipeline-deployer.md))
is the only component that changes a workspace.

## Consequences

- The checker can run anywhere, at any time, including in a country workspace, with no risk.
- Whether SNT pipelines can be scheduled in OpenHEXA in practice is still unconfirmed
  ([`checker.md`](../bootstrap/checker.md) §7.6); today the checker is launched by hand.
- Non-negotiables that follow: [`checker.md`](../bootstrap/checker.md) §5.4.
