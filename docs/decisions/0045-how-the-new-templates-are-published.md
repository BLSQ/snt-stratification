# 0045. How the new templates are published

Date: 2026-11-18
Status: Accepted (amends [0040](0040-templates-kept-alongside-the-deployer.md), [0041](0041-new-templates-publishing-workspace.md) and [0042](0042-bootstrap-pipelines-as-templates-on-release.md))

## Context

ADRs 0040–0042 decided that a new template set is published from its own workspace, that bootstrap
pipelines are templates too, and that template-created pipelines must carry the code `snt-<name>`.
Phase 6 of [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md) built it and found that some of the mechanism
differs from what those ADRs assumed:

- A template-created pipeline's code is the slug of the source pipeline's **display name**, not
  the source's code (spike S3, corrected 2026-11-13,
  [Phase 0 findings](../MIGRATION_PLAN.md#phase-0-findings)). 0040 and 0041 say "code".
- `openhexa pipelines push --code` only **selects** an existing pipeline. In a workspace that does
  not have it yet, the push fails. A first push without `--code` creates a plain pipeline, which
  becomes a template's source only when it is published as a template in the UI. Seen on
  2026-11-18 for all 25 pipelines.
- 0041 left open the workspace's name and whether it publishes on every merge or on release. 0042
  put the bootstrap push in `release.yaml`, whose manual trigger already builds test release assets.
- Colleagues needed to see the new set before `v1.0.0` exists, and full releases are only made by
  promoting a verified rc.

## Decision

1. The publishing workspace is **`snt-templates`** (repository variable `OH_TEMPLATES_WORKSPACE`,
   secret `OH_TEMPLATES_TOKEN`).
2. Each source pipeline's **display name is its `@pipeline` id** (`snt_map_extracts`), so pipelines
   created from its template get the code `snt-map-extracts`. Each **template's name is also the
   `@pipeline` id**, so the new set cannot be mistaken for the old one ("B.2 MAP Extracts").
3. A pipeline is **pushed and published as a template by hand once**, from a release tarball,
   before the workflow can push it. That includes every pipeline added to the registry later.
4. **One workflow**, [`push_templates.yaml`](../../.github/workflows/push_templates.yaml), publishes
   every `snt`, `support` and `bootstrap` pipeline. `release.yaml` no longer has a template job.
5. It runs **on each full release**, and **by hand** for a given tag. The tag must be a published
   GitHub release. A pre-release tag is refused unless the run ticks `allow_prerelease`.

## Consequences

- Where 0040 and 0041 say a source pipeline "carries the code `snt-<name>`", read "is named after
  its `@pipeline` id". Their decisions stand.
- 0042's decision (1) holds with `push_templates.yaml` in place of `release.yaml`. The full-release
  rule holds for the automatic trigger; a manual run can publish a pre-release only on purpose.
  Every such run reaches each auto-updating workspace, so it is for demos and for workspaces that
  expect untested code.
- OpenHEXA numbers template versions itself (1, 2, …). The pipeline version behind each is named
  after the tag, so the tag is found through the pipeline version, not the template version.
- Adding a pipeline gains a step: publish it as a template once, before the next full release.
- A template-built workspace still lacks `shared/r/` ([REL-6](../BACKLOG.md#rel-6)).

Source: migration plan Phase 6, spikes S3 and S6, discussion 2026-11-18.
