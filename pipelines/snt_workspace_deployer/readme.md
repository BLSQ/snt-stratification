# SNT Workspace Deployer Pipeline

The **SNT Workspace Deployer** deploys one GitHub release of this repository — the one named by
`release_tag`, or the latest release when that is left empty — into the workspace it runs in. It moves both halves of the codebase on a single release tag: the R analytics
(notebooks, `utils/*.r` helpers and the shared library in `shared/r/`) are copied into the workspace
filesystem, and each `pipelines/<name>/` folder is zipped and registered as a new **version** of the
matching OpenHEXA pipeline through the GraphQL API. Then each webapp the release lists (the
orchestrator and the config editor) is created or updated as a private static OpenHEXA webapp with
its scopes ([ADR 0048](../../docs/decisions/0048-workspace-deployer-installs-the-webapps.md)). It
publishes nothing to an OpenHEXA dataset — its output is the state of the workspace itself, plus a
`.snt_release` marker file at the workspace root.

It is the Phase 3/4 prototype of [`docs/release_strategy.md`](../../docs/bootstrap/release_strategy.md);
the deployment mechanism is documented in
[`docs/openhexa_deployment.md`](../../docs/bootstrap/openhexa_deployment.md).

> **Status: prototype. It reads release manifest v2, the releases of this repository. It installed
> `v0.1.0`, a pre-release, in a fresh test workspace, and re-ran it with nothing to do; the rest of the
> test plan in [`docs/deployer.md`](../../docs/bootstrap/deployer.md) §6.7 (a newer tag, rollback,
> hand edits, existing files, error messages) is not yet tested.** The first version, which read manifest
> v1 from the old repository, was verified end to end on 2026-09-16 in `snt-development-sandbox` for
> `snt_dhis2_extract` and `snt_map_extracts` only. The webapp step (step 8) is tested offline only;
> it has not run in a workspace yet. It replaces the old repository's per-pipeline
> `Pull scripts` toggle and the Template auto-update subscription, so do not run it against a
> country workspace until the open items in the two documents above are settled.

## Parameters

This pipeline does not read `SNT_config.json` and has no country-specific parameters. None of the
standard SNT flags (`run_report_only`, `use_custom_notebooks`, `overwrite`) apply.

* **`github_repo`** (str, Required):
  * **Name:** GitHub repository
  * **Description:** `owner/repo` to pull the release from. The release must carry a
    `release_manifest.json` asset (schema v2) listing the tracked files and their sha256 hashes, and
    the slim tarball `<repo name>-<tag>.tar.gz` holding them.
  * **Default:** `BLSQ/snt-stratification`.
* **`release_tag`** (str, Optional):
  * **Name:** Release tag
  * **Description:** The GitHub release tag to deploy (e.g. `v0.1.0`). Leave it empty to deploy
    the repository's **latest release** — GitHub's "latest", i.e. the most recent published release
    that is neither a draft nor a pre-release, so a pre-release must be requested by its tag. The
    resolved tag (typed or latest) also becomes the **version name** of every
    pipeline version registered by the run, the **commit message** of every webapp update, and the
    name of the backup subdirectory. When a pipeline
    already has a version with that name and different files, the name gets a suffix (see step 7).
    The whole release is always deployed: there is no option to deploy only part of it.
  * **Default:** `None` — deploy the latest release.
* **`api_connection`** (str, Required):
  * **Name:** OpenHEXA API connection
  * **Description:** Slug of a **CUSTOM** connection holding a workspace API token in a secret field
    named `token`. A run's own `HEXA_TOKEN` is refused with `PERMISSION_DENIED` on `uploadPipeline`
    and `createWebapp`, so deployment cannot use the run's own credentials. Pipeline versions and
    webapp versions are credited to the member whose key the connection holds.
  * **Default:** `openhexa-deploy`.
* **`backup_existing`** (bool, Optional):
  * **Name:** Backup existing files
  * **Description:** Move any existing tracked file to `archive/[RELEASE_TAG]/` before overwriting
    it. Applies to the analytics sync only — pipeline versions are never overwritten, they are
    appended.
  * **Default:** `True`.
* **`dry_run`** (bool, Optional):
  * **Name:** Dry run
  * **Description:** Report what would change without writing any file, registering any version,
    changing any webapp or writing the release marker. The release and the workspace are still
    read, so each `DRY RUN would …` line reflects the real state.
  * **Default:** `False`.

## Functionality Overview

1. **Credentials:** Read the bearer token from the custom connection named by `api_connection`; a
   missing or malformed connection aborts the run before anything is fetched.
2. **Resolve the release:** Fetch the GitHub release by tag or, when `release_tag` is empty, the
   repository's latest release (`/releases/latest`). From here on the resolved tag is used
   everywhere — version names, `archive/<tag>/`, `.snt_release` — never the word "latest". When
   GitHub finds nothing, the run works out why and says so: repository missing or private, no
   published release at all, only pre-releases (never "latest" on GitHub), or a misspelled tag (the
   most recent tags are listed). A pre-release, which can only be typed, is deployed like any
   release but logged as a warning: pre-releases are for development and testing (D27). Then download the release's `release_manifest.json` asset; a release
   without it aborts the run, asking to wait for (or re-run) the release's `release` workflow run.
   A manifest without a `schema_version` this run can read (a v1 manifest from the old
   `snt_development` repository, or a newer one) aborts the run before anything is written.
3. **Split the manifest:** the manifest's `filesystem_files` are the **analytics files to copy**;
   its `pipelines` block names the **pipelines to deploy**, each at `pipelines.<name>.path`. A
   notebook is in both: it ships inside its pipeline's zip and to the filesystem. Everything else
   in a pipeline's folder (`pipeline.py`, `requirements.txt`, …) is deliberately kept off the
   filesystem, because OpenHEXA runs each pipeline from its registered version's zip and never from
   the workspace bucket.
4. **Bootstrap guard:** when the release is older than GitHub's latest full release (by
   `published_at`), the bootstrap pipelines (`kind: bootstrap`, this one included) are left out with
   an info message: a deployer never replaces itself with an older copy (ADR 0042). With no full release
   yet, every release counts as the newest.
5. **Download the slim tarball** `<repo name>-<tag>.tar.gz`, a release asset holding exactly the
   manifest's files, once for the whole release, and extract it to a temporary directory (a per-file
   Contents API fetch would exhaust the unauthenticated rate limit). A release without it aborts the
   run.
6. **Sync analytics:** copy each file in `filesystem_files` into
   `workspace.files_path`, archiving any existing copy first when `backup_existing` is on. A
   manifest entry missing from the tarball is logged as a **warning** and skipped, not raised.
7. **Deploy pipelines:** for each pipeline left after step 4, parse
   its parameters with the SDK's AST-based `get_pipeline()` (no import, so the pipeline's own
   dependencies need not be installed), zip its folder (`.py`, `.ipynb`, `.txt`, `.md`,
   `.r`, `.sql`), and call `uploadPipeline` — or `createPipeline` with a nested version when the
   pipeline does not exist. The OpenHEXA pipeline code is the manifest's `code`, the pipeline
   name with `_` → `-`. For a pipeline that already exists, its current version is read first and
   compared **by file contents** (not by name) with the release:
   * **same files as the release, and already named with this tag:** nothing is registered. Logged
     as "already up to date, skipped" and counted as a success;
   * **same files, another name:** registered again under the tag. Most pipelines do not change
     between releases, and without this the workspace would still read as being at the release
     they last changed in;
   * **different files:** registered under the tag. If the current version already carries the tag,
     it holds something that is not the release (edited by hand, or built from elsewhere), so the
     release is registered as `<tag>+redeploy-<YYYYMMDD>` (`<tag>+redeploy-<YYYYMMDDTHHMMSSZ>` for a
     second one the same day) and a warning says so;
   * **the tag is refused because an older, non-current version holds it** (for example after a
     rollback): the redeploy names above are tried in turn.

8. **Install webapps:** for each entry of the manifest's `webapps` block, in name order
   (`config_editor`, then `orchestrator`). An entry without `name`, `slug` and `scopes` comes from a
   release built before this step: it is skipped with a **warning** that says to deploy a newer
   release or upload the zip by hand. Otherwise:
   * download the release asset `webapp-<name>-<tag>.zip` and check every file in it but the stamped
     `version.json` against the manifest's hashes; a missing or different zip fails that webapp;
   * look the app up **by its slug** (`webapps.<name>.slug`, from `webapps/<name>/webapp.json`),
     never by name, then:
     * **no app at the slug:** `createWebapp` with every bundle file, `version.json` included,
       `isPublic: false` and the manifest's `scopes` as `allowedOperations`. If OpenHEXA gives the
       new app another slug (the slug was taken, possibly by a deleted app), that webapp fails and
       the error names the duplicate to delete;
     * **an app at the slug that is not static** (iframe, Superset): that webapp fails;
     * **the app serves exactly the zip's files, is private and has the scopes:** nothing is sent.
       Logged as "already serves release `<tag>`'s bundle, skipped". As `version.json` changes with
       every release, a new tag always updates the app;
     * **otherwise:** `updateWebapp` writes the files whose content differs, deletes the files the
       zip does not hold, sets `isPublic: false` and the scopes, with the tag as commit message
       (OpenHEXA publishes it at once). An app uploaded by hand is adopted the same way, and a
       **warning** names the privacy and scopes it had when they had to change. When only privacy
       or scopes differ, no file and no commit message is sent.
9. **Write the release marker:** record `{"snt_release": "<tag>", "repo": "<owner/name>"}` in
   `.snt_release` at the workspace root
   ([`contracts/snt_release_marker.md`](../../contracts/snt_release_marker.md)). Skipped on a dry run.
10. **Continue on failure:** one pipeline's or one webapp's failure is logged as an error and does
    not stop the others. After the marker is written, the run stops with an error message listing
    every failed pipeline and webapp. Re-running the same tag converges: pipelines and webapps
    already at the release are skipped (steps 7 and 8).

## Inputs

* **GitHub release `[RELEASE_TAG]` of `[GITHUB_REPO]`**, or its latest release when `release_tag` is
  empty — required. Read unauthenticated, so the repository must be public or the run fails.
  * **`release_manifest.json`** release asset, schema v2 — required; the list of tracked files.
  * **`<repo name>-<tag>.tar.gz`**, the slim tarball asset — required; the actual file contents.
  * **`webapp-<name>-<tag>.zip`**, one asset per `webapps` entry — required for that webapp only;
    without it, that webapp fails and the rest of the release still deploys.
  * **GitHub's latest full release** (`/releases/latest`) — read when the release ships bootstrap
    pipelines, for the guard in step 4; none is fine.
* **CUSTOM connection `[API_CONNECTION]`** with a secret field `token` — always required.
* **The workspace's webapps at each release slug** — read through the API (type, privacy, scopes
  and served files) to decide create, update or skip.
* **`HEXA_SERVER_URL`** from the run environment — the GraphQL endpoint.
* **No `SNT_config.json`, no OpenHEXA dataset, no country code.**

## Outputs

**Workspace filesystem**

* **Every file in the manifest's `filesystem_files`** at its repository-relative path —
  `pipelines/<name>/code/*.ipynb`, `pipelines/<name>/reporting/*.ipynb`, `pipelines/<name>/utils/*.r`,
  `shared/r/**/*.r`.
* **`archive/[RELEASE_TAG]/<path>`** — the previous copy of each overwritten file, when
  `backup_existing` is on.
* **`.snt_release`** at the workspace root — the currently-deployed release tag and its repository.

**Published to a dataset**

* Nothing. This pipeline publishes no dataset and calls no `add_files_to_dataset(...)`.

**OpenHEXA object store**

* **A new version of each pipeline** that is not already current at the release, named after the
  release tag (or `<tag>+redeploy-<date>`, see step 7), described as
  `Deployed by snt_workspace_deployer from release <tag>`, with `externalLink` set to the release's
  GitHub page.
* **Each webapp of the release**, at its slug, private, with its scopes: created (first version
  "Initial content"), or given a new version whose commit message is the release tag. Today:
  `snt-config-editor` (`PIPELINES_READ`, `PIPELINES_RUN`) and `snt-pipelines-orchestrator-cockpit`
  (`FILES_READ`, `PIPELINES_READ`, `PIPELINES_RUN`, `USER_READ`).

> **Notes for the Data Analyst:**
>
> - **Not an analytics pipeline.** It produces no data and touches no country data. It is a
>   deployment tool; the audience is whoever administers a workspace, not whoever reads results.
> - **Deployment is not a file copy.** `pipeline.py` is registered through the API, never written to
>   the workspace filesystem — a `pipeline.py` sitting in the bucket would look authoritative and
>   never execute.
> - **The zip carries the whole folder** (`requirements.txt`, `readme.md`, notebooks), and the
>   manifest lists every file in it (`pipelines.<name>.zip_files`), so the checker can verify all of
>   what is deployed ([`contracts/release_manifest.md`](../../contracts/release_manifest.md)).
> - **Every failure is spelled out in the run's Messages.** A raised exception alone reaches only the
>   run's logs, so each failure the pipeline anticipates (connection, release lookup, manifest,
>   tarball, failed pipelines and webapps) is logged as `Cannot deploy: <reason and what to do>` before
>   the run stops. Anything unanticipated is caught at the top and logged as
>   `Deployment stopped by an unexpected error - <type>: <message>`. If Messages ends on an
>   `INFO` line with no `ERROR` line after it, that is a gap in this coverage — report it.
> - **An empty `release_tag` follows GitHub's "latest", not the newest tag.** A pre-release is never
>   "latest", so until this repository's first full release (`v1.0.0`) an empty tag aborts: type the
>   pre-release's tag. Type the tag when in doubt.
> - **An older release never downgrades the bootstrap pipelines.** Deploying a release older than
>   the latest full one rolls back the SNT pipelines and leaves this deployer, the single-pipeline
>   deployer and the checker as they are (step 4).
> - **One workspace, one release.** The expected use is to keep a workspace on the latest release
>   and deploy forward. To run an older release, use a dedicated workspace rather than rolling this
>   one back. Rolling back works and loses nothing, but leaves `+redeploy-` names and extra versions
>   behind ([`docs/release_strategy.md`](../../docs/bootstrap/release_strategy.md) §1.3).
> - **Partial runs are expected to be re-run.** A failure leaves the workspace partially updated, by
>   design — every failure is named in the final error and re-running converges on the release.
>   Pipelines already at the release (same files, same name) and webapps already serving it are
>   skipped, not refused.
> - **Version names can carry a `+redeploy-` suffix.** It means the plain tag was already taken by a
>   version that was not the release. Not yet verified that OpenHEXA accepts `+` in a version name.
> - **`default=""` breaks a deploy, not a run.** A `str` parameter with an empty-string default is
>   rejected by the SDK's AST parse, so it fails here rather than in the target pipeline. Use
>   `default=None`.
> - **Nothing is ever deleted, so a release cannot be "installed clean".** A pipeline can not delete
>   another pipeline in OpenHEXA. A pipeline that a newer release no longer contains **stays in the
>   workspace** at the code of the release that last deployed it, and the deployer does not mention it.
>   The same holds for analytics files, and for a webapp a newer release no longer lists (files
>   inside a listed webapp are deleted, step 8). Only `snt_workspace_checker` reports stray pipelines
>   and files. A person deletes them by hand in the OpenHEXA UI.
> - **Missing pipelines are always created.** The code is derived from the pipeline name. The run verifies the created code
>   matches the expected slug and raises if it does not; recovery is manual (delete and recreate in
>   the UI).
> - **A webapp at a release slug belongs to the release.** Whatever is at
>   `snt-pipelines-orchestrator-cockpit` or `snt-config-editor` is replaced by the release's files,
>   made private and given the release's scopes, hand edits included. Its name is left as it is. A
>   French config editor uploaded by hand (`webapps/config_editor/design/index_FR.html`) must
>   therefore live under another name, e.g. "SNT Config Editor FR", or the next run replaces it
>   with the English one. Change a webapp through a release, never in the workspace.
> - **A deleted webapp still holds its slug.** OpenHEXA keeps a deleted app's slug, so a create
>   comes back as `<slug>-<6 hex>`; the run fails that webapp and names the duplicate to delete.
>   The slug must then be freed, or the deleted app restored, before a re-run can install it.
> - **The config editor needs `snt_config_publish`.** It publishes by running that pipeline, which
>   step 7 installs from the same release.
> - **`snt_pipeline_deployer` installs no webapp**; only this pipeline does.
> - **R5 interaction.** This pipeline pushes versions **directly into the workspace that runs them**,
>   which creates no OpenHEXA template and so is a different operation from the one
>   [`snt_development`'s `CLAUDE.md`](https://github.com/BLSQ/snt_development/blob/main/CLAUDE.md) **R5** governs. R5 needs rewording before this is used in production
>   — see [`docs/openhexa_deployment.md`](../../docs/bootstrap/openhexa_deployment.md).
