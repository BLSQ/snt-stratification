# 0043. Every consumer reads `SNT_config.json` from the `SNT_CONFIGURATION` dataset

Date: 2026-11-16
Status: Accepted (amended by [0047](0047-config-editor-publishes-to-snt-configuration.md): the `snt_config_publish` pipeline, run by the config editor, publishes the versions, and a version may also hold the editor's `SNT_config.log.json`)

## Context

Every SNT pipeline and notebook reads the country config from a file on the workspace disk,
`configuration/SNT_config.json`: 21 `pipeline.py` through `snt_lib`'s `load_configuration_snt()`,
and 46 notebooks, mostly through `load_snt_config()` in `shared/r/`. Nothing records which
version of the file a run used, and anyone can edit it in place. The config editor
([`webapps/config_editor/`](../../webapps/config_editor/CLAUDE.md)) will become the way to create
and change it, and its write step must be built against the final location. Changing the location
after `v1.0.0` would be a breaking change for every workspace installed from this repo. Options
weighed on 2026-11-16:

- **(A) Pipelines copy the dataset file to disk; notebooks keep reading the disk file.** Rejected:
  a notebook run by hand reads whatever copy is on disk, and nothing ties a result to a version.
- **(B) Every consumer reads the dataset itself.** Chosen.
- **A validating pipeline as the only way to publish a version.** Not now: the editor will own
  validation and writing, decided when it is built.
- **Pass the version a run read to its notebooks as a parameter.** Rejected: notebooks read the
  latest version; the version is recorded in `{CC}_parameters.json` instead.

## Decision

1. The config lives in an OpenHEXA dataset named **`SNT_CONFIGURATION`**, slug
   **`snt-configuration`**, one per workspace, holding one file, **`SNT_config.json`**. The slug is
   fixed by convention and hardcoded: it cannot be looked up in the config itself, so it is not in
   `SNT_DATASET_IDENTIFIERS`. The file name has no `{CC}_` prefix because it is read before the
   country is known (a named exception to R7).
2. **Every consumer reads `SNT_config.json` from the latest version of that dataset**: each
   `pipeline.py` and each notebook. None reads `configuration/SNT_config.json` any more. Each logs
   the version it read.
3. A pipeline that publishes `{CC}_parameters.json` records the config version it read there.
4. If the dataset, its latest version or the file is missing, the run stops with an `[ERROR]` that
   says to provide a valid `SNT_config.json` and links to the how-to.
5. Until the config editor writes the dataset, people create it and upload new versions by hand in
   the OpenHEXA UI. Pipelines still validate the file at startup with `validate_config()`.

## Consequences

- A result can be traced to the config version that produced it. To check that every pipeline ran
  on the same config, compare the versions in their `{CC}_parameters.json`.
- Notebooks read the latest version, not the one their pipeline read. A version uploaded during a
  run can reach a later notebook of that run; accepted, since uploads are rare and by hand.
- The Python loader is a change to `snt_lib`, which is external: a new function on a branch of
  `BLSQ/snt_utils` off `release-v1`, which this repo's pipelines pin. The old
  `load_configuration_snt()` stays for the old repo.
- Country-specific notebook variants (`*_<CC>.ipynb`) are not in this repo and keep reading the
  disk file until someone changes them.
- Live countries run the old `snt_development` repo and are not affected.
- Config editor spec §6–7: the save target is now the dataset; how the editor validates and writes
  is decided when it is built.

Source: migration plan Phase 5 (CFG-4), discussion 2026-11-16.
