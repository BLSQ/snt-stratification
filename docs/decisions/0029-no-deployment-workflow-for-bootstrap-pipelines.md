# 0029. No deployment workflow for the bootstrap pipelines

Date: 2026-09-30
Status: Superseded by [0042](0042-bootstrap-pipelines-as-templates-on-release.md)
Originally: `snt_workspace_bootstrap` D19

## Context

Every SNT pipeline in `snt_development` had a `push_snt_*.yaml` workflow that published it to
`snt-development` as a template. Whether the bootstrap pipelines (`snt_workspace_checker`,
`snt_workspace_deployer`) should get one was an open item in `openhexa_deployment.md`. It was
closed on the same day as, and together with, the decision to retire templates
([ADR 0030](0030-template-mechanism-being-retired.md); `openhexa_deployment.md` §7.7). No further
reasoning was written down.

## Decision

No deployment workflow for `snt_workspace_checker` or `snt_workspace_deployer`. They are deployed
by hand (`openhexa pipelines push`) or by `snt_workspace_deployer` itself; nobody adds a workflow.

## Consequences

- A new workspace needs a first deployer pushed by hand: the chicken-and-egg problem of
  [`roadmap.md`](../bootstrap/roadmap.md) §3.
- Under review in the monorepo migration: OD-4 leans towards publishing the bootstrap pipelines as
  templates from their own CI, which would supersede this ADR
  ([`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md) §3).
