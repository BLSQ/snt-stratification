# 0040. Templates stay as a deploy route, alongside the deployer

Date: 2026-11-02
Status: Accepted (supersedes [0030](0030-template-mechanism-being-retired.md); amended by [0042](0042-bootstrap-pipelines-as-templates-on-release.md): the one-route rule covers `snt` and `support` pipelines)

## Context

[ADR 0030](0030-template-mechanism-being-retired.md) aimed to retire OpenHEXA pipeline templates
altogether, with the workspace deployer as the single update path. But templates are how teams that
do not run the deployer install SNT pipelines today. Existing country workspaces are subscribed to
the old templates published from `snt-development` and must keep working unchanged. A spike
(2026-11-03) showed that a template-created pipeline takes its code from the *source* pipeline, not
from the template name, with a random suffix on collision.

## Decision

Templates are **kept** as a deploy route, alongside the deployer, not retired. Three routes exist:

1. **The deployer** (and the single-pipeline deployer) installs a GitHub release of this repo.
2. **A new template set**, published from this repo, for teams that do not use the deployer. Its
   source pipelines carry the code `snt-<name>`, so the deployer and the checker can take a
   template-built workspace over later.
3. **The old templates**, published from `snt-development` by the old repo's CI, unchanged for
   existing country workspaces until they move.

A workspace still must not receive the same pipeline from a template subscription and the deployer
at once.

## Consequences

- The deployer and the checker must recognise template-created codes, including the
  `snt-<name>-<6 hex>` collision suffix and the legacy `b-2-…` codes.
- How the R half reaches template users (self-sync or `Pull scripts`) is open (OD-9).
- Publishing the new templates needs its own workspace: [ADR 0041](0041-new-templates-publishing-workspace.md).
- Not built yet: Phase 6 of [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md).

Source: migration plan D-4, spike S3, Phase 6.
