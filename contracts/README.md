# `contracts/` — the files the units of this repo exchange

A contract is a file whose shape another unit depends on. One subfolder per contract, except the
three bootstrap contracts (manifest, status report, `.snt_release`), which sit at this folder's
root. A subfolder holds that file's JSON Schema (the source of truth for its shape) or a skeleton, a
canonical valid example, any reference instances worth keeping, and a `README.md` carrying the
conventions. Decisions behind a contract are ADRs in [`docs/decisions/`](../docs/decisions/README.md);
open questions are in [`docs/BACKLOG.md`](../docs/BACKLOG.md).

| Contract | What | Producer | Consumer(s) | Schema / reference | Status |
|---|---|---|---|---|---|
| `SNT_config.json` | Per-workspace configuration, one country | Operator, by hand (config editor in future) | Every pipeline; the config editor | [`snt_config/`](snt_config/README.md) — skeleton, the one copy (D-11); `snt_config.schema.json` `[TODO]` ([CFG-3](../docs/BACKLOG.md#cfg-3)) | Skeleton current; schema not written |
| `SNT_metadata.json` | SNT Explorer data-layer catalogue, one country | [`catalogs/SNT_metadata_master.json`](../catalogs/README.md) → `snt_metadata_json_trim` | SNT Explorer (IASO) | [`snt_metadata_json/`](snt_metadata_json/README.md) | **Work in progress**, being validated with the IASO developers |
| `release_manifest.json` | Files and hashes shipped by a release, and by which route each travels | v2: [`tools/build_manifest.py`](../tools/build_manifest.py), run by [`release.yaml`](../.github/workflows/release.yaml) on each published release. v1: the old repo's [`generate_manifest.yaml`](https://github.com/BLSQ/snt_development/blob/94cfc383c0f8804d2eba264f26a4bd3d372d94da/.github/workflows/generate_manifest.yaml) | Deployer, single-pipeline deployer, checker (they read v1 until Phase 4) | v2: [`release_manifest.schema.json`](release_manifest.schema.json); v1: [`release_manifest.v1.schema.json`](release_manifest.v1.schema.json); prose: [`release_manifest.md`](release_manifest.md) | v2 schema, builder and release workflow written; no release yet (the first is `v0.1.0`, Phase 4); v1 frozen (R22) |
| Checker status report | Per file, which releases a workspace matches | `snt_workspace_checker` | A future status page ([BOOT-2](../docs/BACKLOG.md#boot-2)) | [`status_report.schema.json`](status_report.schema.json) | `schema_version: 1`, frozen (R22) |
| `.snt_release` | The release installed in a workspace | Deployer | Checker | [`snt_release_marker.md`](snt_release_marker.md) | Stable |
| `pipeline_map.json`, `pipeline_descriptions.json` | The orchestrator's map and texts, hand-authored, in its bundle | Hand-edited | Orchestrator; `create_pipeline_cards` (curates against the deployed map) | [`orchestrator/`](orchestrator/) | Stable |
| `pipeline_cards.json` | The orchestrator's per-workspace catalog, in the bucket | `create_pipeline_cards` | Orchestrator | [`orchestrator/pipeline_cards.schema.json`](orchestrator/pipeline_cards.schema.json) | Stable |
| Per-dataset outputs | Files, columns and `YEAR` per OpenHEXA dataset | Each `pipeline.py` | Downstream pipelines, SNT Explorer, master list | — | **Planned**, not started ([BACKLOG CFG-5](../docs/BACKLOG.md#cfg-5)) |

How these connect: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#12-how-they-connect).

**These schemas describe target shapes, not necessarily what is deployed.** Read the subfolder's
`README.md` before assuming a field's meaning. Older files that nothing reads any more are archived
in [`deprecated/configuration/`](https://github.com/BLSQ/snt_development/blob/94cfc383c0f8804d2eba264f26a4bd3d372d94da/deprecated/configuration/README.md).

**A new subfolder needs nothing in `.gitignore`.** The repo ignores `*.json` wholesale; the negation
`!contracts/**/*.json` already reaches into any subfolder here. Do not add a per-folder negation,
and do not weaken it to a single `*` — that would stop matching subfolders and silently untrack every
schema below this one.
