# SNT Pipeline Deployer Pipeline

The **SNT Pipeline Deployer** deploys **one** pipeline from a GitHub release of this repository into
the workspace it runs in. It zips that pipeline's folder `pipelines/<name>/` and registers it as a new
**version** of the matching OpenHEXA pipeline (creating the pipeline if it is missing), and, with
`pull_r_scripts` on, copies that pipeline's own notebooks and R helpers (the manifest's
`filesystem_files` under `pipelines/<name>/`) into the workspace filesystem. Nothing else in the
workspace is changed.

It is the single-pipeline variant of [`snt_workspace_deployer`](../snt_workspace_deployer/readme.md)
(decision D28), for a workspace that already holds real work and where the release should be taken in
one pipeline at a time. Everything it does not mention here, it does exactly as the deployer does:
release resolution, version naming, failure messages. Spec and test plan:
[`docs/deployer.md`](../../docs/bootstrap/deployer.md) § Single-pipeline deployer.

> **Status: built 2026-10-30 and first run on a local OpenHEXA instance the same day, against
> manifest v1 from the old repository. It now reads manifest v2, the releases of this repository; no
> release exists yet (the first is `v0.1.0`), so that code has not run in a workspace.** Run it with
> `dry_run` first.

> **Read this before using it: the shared R library in `shared/r/` is never updated.** Every
> pipeline's notebooks `source()` the R files in `shared/r/`, so those files are shared by all
> pipelines. Updating them for one pipeline would change every other pipeline, so this pipeline
> **never copies `shared/r/`**. The pipeline you deploy then runs its new notebooks against the shared
> scripts already in the workspace, which may come from another release. If the release changed a
> function in `shared/r/` that its notebooks use, the pipeline fails at run time or gives different
> results, and OpenHEXA does not report the mismatch. Each run therefore compares `shared/r/` with the
> release and logs a `[WARNING]` naming every file that differs or is missing. The warning says *that*
> they differ, not whether it breaks anything: compare those files between the two releases on GitHub.
> To bring `shared/r/` in line, deploy the whole release with `snt_workspace_deployer`.

## Parameters

This pipeline does not read `SNT_config.json` and has no country-specific parameters.

* **`pipeline_name`** (str, Required):
  * **Name:** Pipeline to deploy
  * **Description:** The pipeline's directory name (`snt_dhis2_extract`) or OpenHEXA code
    (`snt-dhis2-extract`); case and surrounding spaces are ignored. A name the release does not
    contain stops the run with an `[ERROR]` listing the release's pipelines.
  * **Default:** none.
* **`github_repo`**, **`release_tag`**, **`api_connection`**: as in
  [`snt_workspace_deployer`](../snt_workspace_deployer/readme.md#parameters). Default repository:
  `BLSQ/snt-stratification`.
* **`pull_r_scripts`** (bool, Optional):
  * **Name:** Pull R scripts
  * **Description:** Also copy the pipeline's notebooks and R helpers (its `filesystem_files` under
    `pipelines/<name>/`) from the release. Off: only the pipeline version is registered, and it runs
    whatever notebooks are already in the workspace. The shared R library in `shared/r/` is never
    copied either way. Named after the
    `Pull scripts` toggle of the SNT pipelines, which fetches the same files from the repository at run
    time and which this deployment mechanism replaces.
  * **Default:** `True`.
* **`backup_existing`** (bool, Optional):
  * **Name:** Backup existing files
  * **Description:** Move each R script about to be overwritten to `archive/[RELEASE_TAG]/` first;
    the run's sync message names that folder, or says the files were overwritten when this is off.
    Pipeline versions are never overwritten, they are appended.
  * **Default:** `True`.
* **`dry_run`** (bool, Optional):
  * **Name:** Dry run
  * **Description:** Report what would change without writing any file or registering any version.
  * **Default:** `False`.

## Functionality Overview

1. **Credentials, release and manifest:** as in the deployer, steps 1–2.
   With `release_tag` empty, the log reads `No release tag given: deploying the latest release: '<tag>'.`
2. **Find the pipeline:** match `pipeline_name` to a key of the manifest's `pipelines` block; stop with
   an `[ERROR]` listing them if none matches.
3. **Bootstrap guard:** a bootstrap pipeline (`kind: bootstrap`: either deployer or the checker) asked
   for from a release older than GitHub's latest full release (by `published_at`) stops the run with
   an `[ERROR]`: a deployer never replaces itself, or another bootstrap pipeline, with an older copy
   (ADR 0042). With no full release yet, every release counts as the newest.
4. **Download the slim tarball** `<repo name>-<tag>.tar.gz` of the release, once; a release without
   it stops the run with an `[ERROR]`.
5. **Sync its R scripts** (only with `pull_r_scripts` on): copy the manifest's `filesystem_files` under
   `pipelines/<name>/` into the workspace, archiving each existing copy first when `backup_existing`
   is on. The log line counts the files synced and says where the previous copies went:
   `…; the 4 previous copies moved to archive/<tag>/pipelines/<name>/`, or
   `…; 4 existing file(s) overwritten, no backup (Backup existing files is off)`. A pipeline with no
   notebook or R helper (e.g. `snt_metadata_json_trim`) has none to copy.
6. **Deploy the pipeline:** as in the deployer, step 7: skipped when already at the release, otherwise
   a new version named after the tag (or `<tag>+redeploy-<date>`), created if missing. Logged as
   `Pipeline <name> successfully deployed!` (also when skipped as already up to date); a failure stops
   the run with an `[ERROR]`.
7. **Check the shared R library:** hash every filesystem file under no pipeline's folder (in practice
   `shared/r/**/*.r`) in the workspace and compare it with the manifest. All equal: an info line,
   `Shared R library (shared/r/, used by all pipelines, not updated by this run): all N file(s) match …`.
   Otherwise one `[WARNING]` naming each differing or missing file (the first 20, then a count).
8. **No release marker:** `.snt_release` is not written, and an existing one is left as it is.

## Inputs

* **GitHub release `[RELEASE_TAG]` of `[GITHUB_REPO]`** (or its latest release), with its
  `release_manifest.json` asset (schema v2) and slim tarball, as for the deployer.
* **GitHub's latest full release** — read only when the pipeline asked for is a bootstrap pipeline.
* **CUSTOM connection `[API_CONNECTION]`** with a secret field `token`.
* **`HEXA_SERVER_URL`** from the run environment.
* **The workspace's own `shared/r/` files**, read (never written) for the drift check.

## Outputs

**Workspace filesystem**

* With `pull_r_scripts` on: the pipeline's **`filesystem_files` under `pipelines/<name>/`** from the
  release, and **`archive/[RELEASE_TAG]/pipelines/<name>/…`** for each file it replaced when
  `backup_existing` is on.
* Nothing else. No `shared/r/` file, no `.snt_release`.

**Published to a dataset**

* Nothing.

**OpenHEXA object store**

* **At most one new version of one pipeline**, described as
  `Deployed by snt_pipeline_deployer from release <tag>`, with `externalLink` set to the release's
  GitHub page.

> **Notes for the Data Analyst:**
>
> - **Not an analytics pipeline.** It is a deployment tool for whoever administers a workspace.
> - **A workspace deployed this way mixes releases** by design: one pipeline at release `X`, the rest
>   and `shared/r/` at whatever they were. `snt_workspace_checker` reports it that way. That is the trade-off
>   of D28 against D21, which keeps the main deployer whole-release only.
> - **The previous version is kept.** OpenHEXA keeps every pipeline version, so a pipeline can be put
>   back on its previous version in the UI. Replaced R scripts are in `archive/<tag>/` when
>   `backup_existing` is on.
> - **This file is a copy of the deployer.** `tests/test_pipeline_deployer.py` fails when a function
>   the two share differs; a change to the deployer is copied here in the same change.
