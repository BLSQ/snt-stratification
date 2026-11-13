# 0042. Bootstrap pipelines are published as templates on each full release

Date: 2026-11-12
Status: Accepted (supersedes [0029](0029-no-deployment-workflow-for-bootstrap-pipelines.md), amends [0040](0040-templates-kept-alongside-the-deployer.md))

## Context

[ADR 0029](0029-no-deployment-workflow-for-bootstrap-pipelines.md) gave the bootstrap pipelines
(`snt_workspace_deployer`, `snt_pipeline_deployer`, `snt_workspace_checker`) no deployment workflow,
so every new workspace started with a deployer pushed by hand with the `openhexa` CLI. Users never
manage a workspace with the CLI, because it is too technical (Giulia, 2026-11-12). That leaves
OpenHEXA templates and the bootstrap pipelines themselves as the only realistic routes. Three
options were weighed on 2026-11-12:

- **(A) Templates published from every merge to `main`.** Rejected: untested `main` code would
  reach every auto-updating workspace within minutes, and a template version would match no tag,
  which breaks [ADR 0037](0037-one-release-train.md).
- **(B) Templates published on each full release.** Chosen.
- **(C) No templates: the release carries the bootstrap pipelines, and the first deployer is pushed
  with the CLI.** Rejected: users don't use the CLI, and an old deployer cannot read a newer
  manifest schema.

## Decision

1. On a **full** release only (never a pre-release), `release.yaml` pushes the three bootstrap
   pipelines from the new templates publishing workspace
   ([ADR 0041](0041-new-templates-publishing-workspace.md)), which publishes their template
   versions. A workspace installs them once from the template, so its deployer is the latest full
   release, never older than the release it deploys.
2. They are in the release manifest as `kind: bootstrap`. The deployer deploys them **only when the
   target tag is the latest full release or newer** (a release candidate). For an older target it
   skips them with an `[INFO]`, so it never replaces itself with an older, possibly buggy copy.
3. The deployer reads every manifest `schema_version` from 2 on and refuses an unknown one with a
   clear `[ERROR]`.
4. ADR 0040's rule, "never the same pipeline from a template and the deployer", is narrowed to
   `snt` and `support` pipelines, whose R half the deployer installs with them. For bootstrap
   pipelines both routes deliver the same code from the same tag.

ADR 0037 (one release train) stands.

## Consequences

- Spike S6 (2026-11-12, [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md#phase-3-findings)) showed that
  the deployer can push onto a template-created pipeline and the template link is kept. It also
  showed that auto-update is **opt-in** (`autoUpdateFromTemplate` defaults to off). So the guarded
  self-update in (2) is what keeps a workspace current if nobody ticks auto-update.
- When both routes deliver the same code, the pipeline gets one extra version per release. This is
  accepted: OpenHEXA does not compare contents.
- Template-delivered versions are named `v<N>`, not after the tag. The checker must read such a name
  as "no release claimed" and attribute the code by hash (Phase 4).
- Until the publishing workspace exists, the `release.yaml` job stays disabled and maintainers push
  the bootstrap pipelines by hand. There are no users yet, so that is not a gap.
- The bootstrap starting problem ([`roadmap.md`](../bootstrap/roadmap.md) §3) is solved for
  everything except the `oh` connection, which stays a manual step.

Source: migration plan D-17, spike S6.
