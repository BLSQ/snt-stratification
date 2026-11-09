# 0031. The workspace deployer always deploys the whole release

Date: 2026-09-30
Status: Accepted
Originally: `snt_workspace_bootstrap` D21

## Context

The deployer had parameters for partial deploys: `sync_analytics`, `deploy_pipelines`,
`only_pipelines` and `create_missing`. The bootstrap exists so that R and Python code move together
on one tag; a partial deploy produces exactly the mixed workspaces it is meant to prevent.

## Decision

`snt_workspace_deployer` always deploys the whole release. The four parameters are removed.
Recovery from a partial run is a plain re-run, which skips what is already done. `dry_run` and
`backup_existing` stay.

## Consequences

- A workspace deployed by this pipeline is at one release, recorded in `.snt_release`.
- Updating one pipeline at a time needs a separate tool: `snt_pipeline_deployer`
  ([ADR 0035](0035-single-pipeline-deployer.md)), which leaves this decision unchanged for the main
  deployer.
- Detail and test plan: [`deployer.md`](../bootstrap/deployer.md) §6.7.
