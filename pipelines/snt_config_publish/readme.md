# SNT Config Publish Pipeline

The **SNT Config Publish** pipeline checks an `SNT_config.json` with `snt_lib`'s
`validate_config()` and, if it is valid, publishes it as a new version of **`SNT_CONFIGURATION`**,
the dataset every SNT pipeline reads its configuration from. The config editor webapp runs it when
you click **Publish**. It can also be run by hand with the file's text pasted in.
Why it exists: [ADR 0047](../../docs/decisions/0047-config-editor-publishes-to-snt-configuration.md).

## Parameters

* **`config_json`** (str, Required):
  * **Name:** SNT_config.json content
  * **Description:** The whole `SNT_config.json`, as text. Published byte for byte as received, so
    its SHA-256 matches the `file_sha256` in the editor's log.
* **`editor_log_json`** (str, Optional):
  * **Name:** Config editor log (optional)
  * **Description:** The `SNT_config.log.json` the config editor wrote for this exact file:
    author, validation state, checksums. Published beside the config when usable. Leave empty when
    publishing by hand.
  * **Default:** none.

## Functionality Overview

1. **Parse:** read **`config_json`** as JSON. Not JSON, or not a JSON object: `[ERROR]`, nothing
   published.
2. **Validate:** run `validate_config()` (`snt_lib`), the same check every SNT pipeline runs at
   startup. Invalid: `[ERROR]` listing every failing key, nothing published. Read
   **`SNT_CONFIG.COUNTRY_CODE`** for the version name.
3. **Check the log:** keep **`editor_log_json`** only if it is a JSON object whose `file_sha256`,
   when present, is the SHA-256 of the received config text. Otherwise log a `[WARNING]` and
   publish the config without it.
4. **Find the dataset:** the pipelines read the dataset with slug **`snt-configuration`**, so:
   * a dataset with that slug, named exactly **`SNT_CONFIGURATION`**: use it;
   * a dataset with that slug but another name: `[ERROR]`, nothing published;
   * no dataset with that slug, but one named `SNT_CONFIGURATION` (another slug): `[ERROR]`,
     nothing published;
   * neither: create **`SNT_CONFIGURATION`**; if OpenHEXA gives it another slug, `[ERROR]`,
     nothing published.
5. **Publish:** create a version named **`SNT_[COUNTRY_CODE]_[YYYYMMDD_HHMM]`** (UTC), or
   **`…_[YYYYMMDD_HHMMSS]`** if that name is taken by a run in the same minute. Add
   **`SNT_config.json`**, then **`SNT_config.log.json`** if kept. Log the version's name and id.

## Inputs

* **`config_json`** and **`editor_log_json`**, the run parameters above. No file is read from the
  workspace or a dataset; the current `SNT_config.json` is not read.

## Outputs

**Workspace filesystem**

* None. The files are written to a temporary folder for the upload and deleted after it.

**Published to `SNT_CONFIGURATION`** (slug `snt-configuration`), as one new version

* **`SNT_config.json`**, the config as received.
* **`SNT_config.log.json`**, when `editor_log_json` was given and matches the config (step 3).

No `[COUNTRY_CODE]_parameters.json`: the dataset holds the config and its log only (ADR 0047).

> **Notes for the Data Analyst:**
>
> - **Latest version wins:** every SNT pipeline and notebook reads `SNT_config.json` from the
>   latest version of `SNT_CONFIGURATION` when it starts, and logs that version's name and id
>   (most also record them in their `[COUNTRY_CODE]_parameters.json`). Avoid publishing while
>   other pipelines run.
> - **Incomplete version:** if adding `SNT_config.json` fails after the version is created, the
>   run fails with an `[ERROR]` that says so. That empty version is then the latest one and the
>   pipelines stop on it, until this pipeline is run again.
> - **What `validate_config()` does not check:** it checks that the required keys are present and
>   filled, not that the DHIS2 UIDs exist. The config editor's own checks are wider
>   ([`config_analysis_notes.md`](../../contracts/snt_config/config_analysis_notes.md)).
