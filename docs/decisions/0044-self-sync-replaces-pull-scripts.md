# 0044. Pipelines self-sync their R half; `custom/` is the escape hatch

Date: 2026-11-17
Status: Accepted (amended by [0046](0046-country-variants-in-the-repo.md): country variants are committed and synced with the pipeline version)

## Context

Each pipeline's R half (`code/*.ipynb`, `reporting/*.ipynb`, `utils/*.r`) already travels inside
its pipeline zip, and spike S2b showed that `pipeline.py` can copy it to the workspace when a run
starts ([migration plan, Phase 0 findings](../MIGRATION_PLAN.md#phase-0-findings)). The only
in-pipeline route today is the `Pull scripts` flag. `snt_lib`'s `pull_scripts_from_repository()`
pulls from the old `snt_development` repo, so in a workspace the deployer installed, one tick
replaces that release's notebooks with older ones. Removing the flag changes the parameter form and
`{CC}_parameters.json`, which after `v1.0.0` would be a breaking change. Self-sync overwrites
any hand edit to a generic notebook, so analysts need a supported way to run an edited notebook.
Options weighed on 2026-11-17:

- **Run the notebooks straight from the bundle** (spike S2a). Rejected: notebooks `source()` their
  utils from workspace paths, so the files must be on disk anyway.
- **A file-picker parameter that names one replacement notebook per run.** Rejected: a pipeline
  runs several notebooks (`snt_dhis2_formatting` runs six), and the edit has no stable home.
- **Fold `_<CC>` country variants into the custom folder.** Rejected: a country would have to tick
  the switch on every run, or its variant would silently stop running.

## Decision

1. **Every SNT pipeline syncs its R half on each run**, report-only runs included, before
   loading the config. Every `code/*.ipynb`, `reporting/*.ipynb` and `utils/*.r` in the bundle
   whose sha256 differs from the workspace copy, or has no copy, is copied to
   `pipelines/<name>/`. A replaced file first moves to
   `archive/self_sync/<UTC stamp>/pipelines/<name>/<path>`, with a `[WARNING]` naming it. The sync
   never deletes and never touches `custom/`. If it fails, the run stops with an `[ERROR]`.
2. **`Pull scripts` is removed** from every pipeline in this repo. A new standard flag,
   **`use_custom_notebooks`** (default off), replaces it.
3. **Escape hatch:** an edited notebook goes in `pipelines/<name>/custom/` under the generic
   notebook's file name. With the flag on, it runs instead of the repo notebook. Only notebooks:
   `utils/*.r` always comes from the bundle. With the flag on and no custom notebook matching any
   of the pipeline's notebooks, the run stops with an `[ERROR]`.
4. **Which notebook runs:** flag on → `custom/<generic>`, else `<generic>_<CC>`, else the repo
   copy; flag off → `<generic>_<CC>`, else the repo copy. Every notebook that is not the repo
   copy logs a `[WARNING]`. A custom notebook's output is named `<stem>_CUSTOM_OUTPUT_<stamp>`.
5. **`{CC}_parameters.json` records it** in `NOTEBOOK_OVERRIDES`, one entry per overridden notebook:
   `NOTEBOOK`, `SOURCE` (`custom` or `country_variant`), `PATH` and `SHA256`. An empty list means
   every notebook was the repo copy.
6. The sync, resolution and record logic lives in `snt_lib` (R3). `pipeline.py` passes its bundle
   folder, its notebook list and the flag.

## Consequences

- A run always executes the pipeline's own release of its notebooks and utils, whatever the route
  (deployer or template). A hand edit to a generic notebook survives only in `archive/`.
- Overridden notebooks are visible in the run log, the output names and `{CC}_parameters.json`.
  A `_<CC>` variant, silent until now, is recorded too. Variants run automatically as before
  ([0003](0003-country-variants-outside-pull-scripts.md)); `Pull scripts` is gone, so its
  reason for keeping them out of the list no longer applies.
- "Only repo utils" is a convention, not something code can enforce: a custom notebook can
  `source()` any file.
- `shared/r/` is not synced. It still reaches a workspace only through the deployer, so a
  template-installed workspace lacks it ([REL-6](../BACKLOG.md#rel-6)).
- Custom notebooks and variants are still versioned by nobody (OD-10, narrowed). The checker
  reports files in `custom/` as `untracked`.
- Live countries run the old `snt_development` repo, where `Pull scripts` is unchanged.

Source: migration plan Phase 5, OD-9, discussion 2026-11-17.
