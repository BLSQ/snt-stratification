# 0041. The new templates are published from their own workspace

Date: 2026-11-02
Status: Accepted (amends [0004](0004-publish-only-from-snt-development.md))

## Context

[ADR 0004](0004-publish-only-from-snt-development.md) (rule R5) makes `snt-development` the single
publication point for SNT templates. A push of the same pipeline from another workspace creates a
competing duplicate template. The old templates must keep publishing from `snt-development` for
existing countries, and the new template set ([ADR 0040](0040-templates-kept-alongside-the-deployer.md))
needs source pipelines whose code is `snt-<name>`, which the existing `snt-development` pipelines do
not have.

## Decision

- The **new** template set is published from a **dedicated publishing workspace**, created for it.
  It does not replace `snt-development`.
- `snt-development` stays the single publication point for the **old** templates, from the old repo.
  R5 holds for those.
- Each template set has exactly one publishing workspace. Never push a pipeline of either set from
  any other workspace.

## Consequences

- R5 is reworded to cover both sets when the Register is merged.
- The workspace's name is not chosen yet. Whether it publishes on every merge to `main` or only on
  release is decided in Phase 6 (recommended: only on release, so templates match a tag).

Source: migration plan §4, Phase 6.
