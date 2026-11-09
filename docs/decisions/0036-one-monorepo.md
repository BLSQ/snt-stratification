# 0036. One public monorepo for SNT stratification

Date: 2026-11-02
Status: Accepted

## Context

SNT stratification on OpenHEXA lived in four tightly coupled repos, versioned and documented
separately: `snt_development` (the SNT pipelines), `snt_webapp_orchestrator` (the orchestrator and
`create_pipeline_cards`), `snt_workspace_bootstrap` (deployer and checker) and
`openhexa-webapps-edit-snt-config-json` (the config editor, spec stage). Every cross-repo contract
(the release manifest, pipeline ids ↔ the orchestrator map, the config skeleton ↔ the editor) needed
paired PRs, and rules copied between repos drifted apart. The release mechanism (tag → manifest →
deployer) was designed for one source repo. The orchestrator backlog asked which way to converge
(REPO-1); its layout was already neutral ([ADR 0021](0021-one-folder-per-deployable-unit.md)).

## Decision

- One new public repo, `BLSQ/snt-stratification`, built as a clean snapshot of the four repos with no
  history, as the orchestrator did before ([ADR 0022](0022-fresh-repo-without-history.md)). The
  snapshot SHAs are in the [README](../../README.md) provenance table.
- The old repos stay as read-only backups and are archived later. `snt_development` stays
  maintenance-only (critical fixes for live countries, ported by hand) until no workspace depends on
  its template CI or `Pull scripts`.
- `snt_lib` (`BLSQ/snt_utils`) stays external for now, pinned to a real tag in every
  `requirements.txt`. Moving it in is a long-term option, agreed with its maintainer first.

## Consequences

- One PR changes a contract and every producer and consumer of it. R22 becomes an in-repo rule, and
  the cross-repo framing of [ADR 0033](0033-release-manifest-frozen-json-schema.md) no longer applies
  to the manifest's producer and consumers, which now live here.
- One CLAUDE.md router, one Register, one BACKLOG and one ADR sequence
  ([ADR 0010](0010-record-decisions-as-adrs.md), with the mapping in [`README.md`](README.md)).
- Two live systems for a while: existing country workspaces keep the old repo, the old template CI
  and the old templates, unchanged.
- History before the snapshot is read in the source repos, at the provenance SHAs.

Source: migration plan D-1, D-3, D-4, D-6 ([`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md) §2).
