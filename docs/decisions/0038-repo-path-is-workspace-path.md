# 0038. Repo path = workspace path; flat `pipelines/`, R half co-located

Date: 2026-11-02 (co-location confirmed 2026-11-03)
Status: Accepted

## Context

The deployer copies each file to its repo-relative path in the workspace, and the checker compares a
workspace on the assumption that workspace path = repo path. In `snt_development`, a pipeline was
split between `<name>/pipeline.py` at the root and its R half under `pipelines/<name>/`, and the
shared R library sat in a root `code/` folder. Two spikes on OpenHEXA (2026-11-03) showed that
`openhexa pipelines push` keeps nested `code/`, `reporting/` and `utils/` folders in the pipeline
zip, and that a running pipeline can sync its bundled notebooks to the workspace filesystem.

## Decision

- **Every file that lands on the workspace filesystem has the same path in the repo.** No mapping
  layer.
- **`pipelines/` is flat**: one folder per pipeline, named after its `@pipeline` id. A pipeline's
  `pipeline.py`, `requirements.txt`, `readme.md` and its R half (`code/`, `reporting/`, `utils/`)
  live in that one folder. The pipeline's kind (`snt`, `support`, `bootstrap`) is recorded in
  `pipelines/registry.json`, not in the path: kind folders would put the kind into every workspace
  path and change the layout analysts know.
- **The shared R library is `shared/r/`**, renamed from `code/`, in the repo and in the workspace.

## Consequences

- Every notebook's `source(…)` of the shared library changed once (Phase 1).
- Workspace paths for a pipeline's own notebooks are unchanged.
- The deployer, the checker and the manifest builder change together when they move to manifest v2,
  where pipelines sit under `pipelines/<name>/` (Phase 4).
- Self-sync of the R half can replace `Pull scripts`. When to switch is still open (OD-9), and so is
  how analysts keep their own edits (OD-10).
- Spike results: [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md) "Phase 0 findings".

Source: migration plan D-5, D-9, §4.2, §4.3.
