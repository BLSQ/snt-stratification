# `docs/decisions/` — architecture decision records

One file per decision that shapes how this repository works, so the *why* survives after the people
who made it move on. Format after Michael Nygard's
[ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
**One sequence for the whole repo**: pipelines, webapps, bootstrap and contracts alike.

- An ADR records a decision **and its reasoning**. The rule itself lives where people apply it
  (`CLAUDE.md`'s Register, a nested `CLAUDE.md`, a contract README, a pipeline readme); the ADR is
  what that rule links to for "why".
- **Never edit an accepted ADR to change the decision.** Write a new one and mark the old one
  `Superseded by NNNN`. Fixing a typo or a link is fine.
- Open questions do not belong here: they go to [`../BACKLOG.md`](../BACKLOG.md). When a backlog
  item is settled by a decision, delete it there and write the ADR here.
- Where the original date or reason was never written down, the ADR says so. Do not fill the gap
  with a plausible guess.
- Working specs and implementation plans live in the local, git-ignored `ignore/` folder. Once a
  decision in one of them is settled and durable, promote it to an ADR here.
- Implementation detail of the bootstrap pipelines (statuses, scoring, naming) stays in
  [`../bootstrap/decisions.md`](../bootstrap/decisions.md) as `D<n>`.

## Index

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-no-dag-engine.md) | No DAG engine or scheduler: pipelines are launched by hand | Accepted | not recorded |
| [0002](0002-alternative-methods-last-run-wins.md) | Alternative methods overwrite each other: last run wins | Accepted | not recorded |
| [0003](0003-country-variants-outside-pull-scripts.md) | Country-specific notebook variants live outside `Pull scripts` | Accepted | not recorded |
| [0004](0004-publish-only-from-snt-development.md) | Publish SNT pipelines only from `snt-development` | Accepted | not recorded |
| [0005](0005-no-codeowners.md) | No `CODEOWNERS` file: review by convention | Accepted | not recorded |
| [0006](0006-retire-snt-assemble-results.md) | Retire `snt_assemble_results`; the Explorer reads datasets directly | Accepted | 2026-10 |
| [0007](0007-snt-metadata-json-format.md) | `SNT_metadata.json`: a pointer per layer, keyed on config keys, time via `YEAR` | Proposed | 2026-09-08 |
| [0008](0008-master-list-maintained-by-hand.md) | The SNT Explorer master list is edited by hand; no generator | Accepted | 2026-10-12 |
| [0009](0009-conda-and-pep621-side-by-side.md) | conda for desk tools, with an accepted PEP 621 duplicate | Accepted | not recorded |
| [0010](0010-record-decisions-as-adrs.md) | Record architecture decisions as ADRs; working plans stay local | Accepted | 2026-10-19 |
| [0011](0011-catalog-in-workspace-bucket.md) | The pipeline catalog lives in the workspace bucket, with no fallback | Accepted | 2026-08-04 |
| [0012](0012-catalog-parameters-from-deployed-version.md) | Catalog parameters come from the deployed pipeline version, not GitHub | Accepted | 2026-08-04 |
| [0013](0013-generator-curates-against-deployed-map.md) | The generator curates against the deployed orchestrator map | Accepted | not recorded |
| [0014](0014-catalog-not-in-workspace-configuration.md) | The catalog is not stored in `workspace.configuration` | Accepted | not recorded |
| [0015](0015-node-id-is-python-function-name.md) | The node `id` (Python function name) is the only cross-workspace key | Accepted | not recorded |
| [0016](0016-multi-file-bundle-no-build.md) | A flat multi-file bundle: no build step, no CDN, no layout library | Accepted | not recorded |
| [0017](0017-one-bilingual-app.md) | One bilingual app with an EN/FR toggle, French first for v1 | Accepted | 2026-07-15 |
| [0018](0018-cockpit-only-flowchart-parked.md) | Cockpit is the only maintained UI; Flowchart is parked | Accepted | 2026-10-19 |
| [0019](0019-hardcoded-saas-front-end-base.md) | The SaaS front-end base `app.openhexa.org` is hardcoded | Accepted | not recorded |
| [0020](0020-repo-is-not-a-deployment-record.md) | The repo is the reference source, not a deployment record | Accepted | 2026-10-19 |
| [0021](0021-one-folder-per-deployable-unit.md) | One self-contained folder per deployable unit | Accepted | 2026-10-19 |
| [0022](0022-fresh-repo-without-history.md) | A fresh public repo from one snapshot; history and `deprecated/` stay in the archived repo | Accepted | 2026-10-20 |
| [0023](0023-ship-openhexa-dev-js.md) | Ship OpenHEXA's `dev.js` in the bundle for local development | Accepted | 2026-10-20 |
| [0024](0024-webapp-may-run-the-generator.md) | The webapp may run the catalogue generator | Accepted | 2026-10-21 |
| [0025](0025-readmes-from-deployed-version.md) | Pipeline READMEs come from the deployed version, copied by the generator | Accepted | 2026-10-21 |
| [0026](0026-checker-and-deployer-are-separate-pipelines.md) | Checking and fixing a workspace are separate pipelines; the checker is read-only | Accepted | 2026-09-18 |
| [0027](0027-checker-report-is-a-workspace-file.md) | The checker's report is a workspace file, not a dataset or a DB table | Accepted | 2026-09-18 |
| [0028](0028-hash-raw-bytes-no-notebook-normalisation.md) | Hash notebooks as raw bytes; no normalisation | Accepted | 2026-09-29 |
| [0029](0029-no-deployment-workflow-for-bootstrap-pipelines.md) | No deployment workflow for the bootstrap pipelines | Accepted | 2026-09-30 |
| [0030](0030-template-mechanism-being-retired.md) | The pipeline template mechanism is being retired | Accepted | 2026-09-30 |
| [0031](0031-deployer-deploys-the-whole-release.md) | The workspace deployer always deploys the whole release | Accepted | 2026-09-30 |
| [0032](0032-one-workspace-per-release.md) | One workspace per release is the expected usage | Accepted | 2026-10-01 |
| [0033](0033-release-manifest-frozen-json-schema.md) | The release manifest is a contract, frozen as a JSON Schema | Accepted | 2026-10-01 |
| [0034](0034-pre-releases-for-development-only.md) | Pre-releases are for development and testing only | Accepted | 2026-10-02 |
| [0035](0035-single-pipeline-deployer.md) | A separate pipeline deploys a single pipeline of a release | Accepted | 2026-10-30 |

## Imported ADRs: old number → new number

The repo was built in 2026-11 from four source repos ([`../MIGRATION_PLAN.md`](../MIGRATION_PLAN.md)).
Their decisions were merged into the one sequence above (D-14). Each imported ADR carries an
"Originally: …" line. Use this table to read an old citation.

| Source repo | Old ID | New |
|---|---|---|
| `snt_development` | ADR 0001–0009 | 0001–0009 (unchanged) |
| `snt_webapp_orchestrator` | ADR 0001–0016 | 0010–0025 (old number + 9) |
| `snt_workspace_bootstrap` | D2 · D3 · D9 | 0026 · 0027 · 0028 |
| `snt_workspace_bootstrap` | D19 · D20 · D21 | 0029 · 0030 · 0031 |
| `snt_workspace_bootstrap` | D25 · D26 · D27 · D28 | 0032 · 0033 · 0034 · 0035 |
| `snt_workspace_bootstrap` | every other D<n> | not an ADR: stays in [`../bootstrap/decisions.md`](../bootstrap/decisions.md) |
| `openhexa-webapps-edit-snt-config-json` | (no ADRs; its settled choices are listed in [`webapps/config_editor/CLAUDE.md`](../../webapps/config_editor/CLAUDE.md)) | — |

## Template

Copy this into `NNNN-short-title.md`, with the next free number. Keep it short (about 40 lines).

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded by NNNN | Deprecated

## Context

What forced a decision, and the constraints at the time.

## Decision

What was decided, stated as a rule.

## Consequences

What follows — the good, the costs, and what to watch for.
```

Then add a row to the index above.
