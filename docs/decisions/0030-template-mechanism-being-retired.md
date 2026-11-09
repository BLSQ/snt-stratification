# 0030. The pipeline template mechanism is being retired

Date: 2026-09-30
Status: Accepted
Originally: `snt_workspace_bootstrap` D20

## Context

A pipeline's Python half reached country workspaces through OpenHEXA templates published from
`snt-development`, and its R half through `Pull scripts`, on different cadences. A workspace could
run today's `pipeline.py` against months-old R analytics with nothing reporting it
([`release_strategy.md`](../bootstrap/release_strategy.md)). The deployer pushes pipeline versions
straight into the workspace that runs them, which needs no template.

## Decision

This work, `snt_workspace_deployer` above all, aims to remove pipeline templates altogether. The
mechanism stays documented because it is still in place and affects how `pipeline.py` is
delivered, but new work is not designed around it. R5 ("publish only from `snt-development`",
[ADR 0004](0004-publish-only-from-snt-development.md)) is not reworded for it: it stays true for as
long as templates exist.

## Consequences

- A workspace must not receive `pipeline.py` from both a template subscription and the deployer.
- Pushing a pipeline version into a workspace creates no template, so it does not break R5
  ([`openhexa_deployment.md`](../bootstrap/openhexa_deployment.md) §7.7).
