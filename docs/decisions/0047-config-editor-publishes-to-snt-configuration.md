# 0047. The config editor publishes to `SNT_CONFIGURATION` through a pipeline, with its log beside the config

Date: 2026-11-26
Status: Accepted (amends [0043](0043-config-read-from-snt-configuration-dataset.md))

## Context

Every SNT pipeline and notebook reads `SNT_config.json` from the latest version of the
`SNT_CONFIGURATION` dataset, slug `snt-configuration`
([0043](0043-config-read-from-snt-configuration-dataset.md)). Until now people created that dataset
and uploaded each version by hand. The config editor
([`webapps/config_editor/`](../../webapps/config_editor/CLAUDE.md)) could only download the file,
and 0043 left "how the editor writes" to be decided when it was built.

An OpenHEXA webapp can still write datasets through its GraphQL proxy, under the `DATASETS_WRITE`
scope. On 2026-11-26 the OpenHEXA developers said webapp writes, to datasets and to the filesystem,
are kept only temporarily for existing uses and will be removed. A webapp can start a pipeline
(`PIPELINES_RUN`) and read the run's status and log messages (`PIPELINES_READ`), and these are not
being removed.

The editor also writes a `.log.json` sidecar for each valid file (spec §6.5): who saved it, when,
the validation state, the config hash. 0043 says the dataset holds one file, `SNT_config.json`.
Every reader fetches that file by name (`version.get_file("SNT_config.json")` in `snt_lib`,
`version$get_file()` in `shared/r/snt_utils.r`), so a second file in the version is invisible to
them.

Options weighed on 2026-11-26:

- **The webapp writes the dataset itself.** Rejected: that capability is being removed.
- **The user downloads the file, uploads it to the workspace, then runs a pipeline on it.**
  Rejected as the main route: three manual steps where one click will do.
- **Find the dataset by its name only.** Rejected: the pipelines look it up by the slug. A dataset
  named `SNT_CONFIGURATION` with another slug would take the write and no pipeline would read it.
- **Require the dataset to exist and stop otherwise.** Rejected: creating it is one call, and the
  slug it gets can be checked.
- **Publish only `SNT_config.json`.** Rejected: the log belongs with the version it describes, and
  readers ignore it.
- **A version name that says what changed.** Rejected: config versions use the naming the other
  SNT datasets use, so they read the same in the run logs.

## Decision

1. A support pipeline, **`snt_config_publish`**, is the one writer of new `SNT_CONFIGURATION`
   versions. It takes the config text (`config_json`) and, optionally, the editor's log
   (`editor_log_json`) as run parameters. It publishes only a config that passes `snt_lib`'s
   `validate_config()`, the check every SNT pipeline runs at startup.
2. Inside an OpenHEXA workspace, the editor's **Publish** button **runs that pipeline** with the
   file and its log, follows the run, and shows the version name, or the pipeline's error. The
   webapp writes nothing itself. It is **private**, with the scopes **`PIPELINES_READ` and
   `PIPELINES_RUN`**. It finds the pipeline by its code or name, ignoring case and punctuation,
   since the code depends on how the pipeline was installed.
3. A version holds **`SNT_config.json`** and, when the editor sent one that describes this exact
   file (its `file_sha256` matches), **`SNT_config.log.json`**. This amends 0043 point 1: the
   dataset holds the config file and its editor log. Nothing else goes in it.
4. **The target is the dataset with slug `snt-configuration`, and it must be named exactly
   `SNT_CONFIGURATION`.** If no dataset has that slug or that name, the pipeline creates
   `SNT_CONFIGURATION` and checks that it got the slug. In any other case (the slug is held by a
   dataset with another name, the name sits on another slug, or the new dataset got another slug),
   it stops before writing and says why.
5. **Version name:** `SNT_{COUNTRY_CODE}_{YYYYMMDD_HHMM}` in UTC, the convention of `snt_lib`'s
   `add_files_to_dataset()`; `_{YYYYMMDD_HHMMSS}` when a run in the same minute took the name, as
   `snt_metadata_json_trim` does.
6. **Drafts never reach the dataset.** They stay in the browser, with a download, as before.
   **Download stays available** beside Publish. Outside OpenHEXA (the file opened from disk), it is
   the only way out.

## Consequences

- People no longer need to create the dataset or upload the config by hand. The hand upload still
  works, and so does running `snt_config_publish` by hand with the file's text.
- A published config has passed the real `validate_config()`, not only the editor's JavaScript
  reimplementation of it.
- Each config version carries its own record of who published it, what the editor's validation
  said and the config hash.
- Publishing takes as long as a pipeline run, about a minute, instead of a single API call.
- A workspace needs `snt_config_publish` installed for the editor to publish. It ships with the
  release like any other pipeline.
- Live countries run the old `snt_development` repo, which reads `configuration/SNT_config.json`
  from disk and has no `snt_config_publish`. Their editor users keep using Download.

Source: config editor dataset write, discussion 2026-11-26.
