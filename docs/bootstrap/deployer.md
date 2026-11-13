# Workspace Deployer — spec and state

> `snt_workspace_deployer`: what it does, its current state, the phase-5 test plan and its limits;
> and its single-pipeline variant `snt_pipeline_deployer` (D28).
> How a pipeline version is registered through the API is in
> [`openhexa_deployment.md`](openhexa_deployment.md). Section numbers are those of the former
> `PRODUCT_SPEC.md`.

## Workspace Deployer — built, **changed 2026-09-30 and not yet fully tested**

[`snt_workspace_deployer/`](../../pipelines/snt_workspace_deployer/), an OpenHEXA pipeline that
reads the releases of this repository, `BLSQ/snt-stratification` (manifest v2). Parameters:
`github_repo` (default `BLSQ/snt-stratification`), `release_tag`, `api_connection`,
`backup_existing`, `dry_run`. `release_tag` is optional: empty deploys the repository's latest
release (D23), and the resolved tag is what names everything downstream. It always deploys the **whole** release, both halves together
(decision D21): there is no option to sync only the analytics, deploy only the pipelines, restrict to
some pipelines, or skip creating missing ones. It:

1. resolves the release via the GitHub API — by tag, or `/releases/latest` when no tag is given —
   and downloads `release_manifest.json` from its assets;
2. downloads the release's **slim tarball** asset, `<repo name>-<tag>.tar.gz`, which holds exactly
   the manifest's files ([`release_manifest.md`](../../contracts/release_manifest.md#release-assets-beside-the-manifest)),
   and extracts it. A release without that asset stops the run with an `[ERROR]`;
3. copies exactly the manifest's `filesystem_files` into `workspace.files_path`, at their repository
   paths, archiving any existing copy under `archive/<release_tag>/` first;
4. deploys each pipeline through the OpenHEXA API (see below), zipping `pipelines.<name>.path` and
   creating any pipeline that is missing. Bootstrap pipelines only from a recent enough release (see
   below);
5. writes `.snt_release`, naming the tag and the repository
   ([`snt_release_marker.md`](../../contracts/snt_release_marker.md)).

`split_manifest()` takes the filesystem files from `filesystem_files` and the pipelines from the
`pipelines` block; it derives no route from a path, because a notebook ships both in its pipeline's
zip and to the filesystem. `download_manifest()` refuses, with `[ERROR] Cannot deploy: …` before
anything is written, a manifest whose `schema_version` it cannot read: one without the key (a v1
manifest from the old `snt_development` repository) or a newer one
([`release_manifest.md`](../../contracts/release_manifest.md) §2.1).

**Bootstrap guard ([ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md)).**
A deployer must never replace itself, or another bootstrap pipeline (`kind: bootstrap`), with an
older copy. It deploys them only when the release is GitHub's latest full release or was published
at the same time or after it (`published_at`, the checker's order); with no full release yet, every
release counts as the newest. From an older release they are skipped with an `[INFO]`, and the run
deploys the other pipelines and succeeds.

**Version naming on deploy (2026-09-30, D22).** OpenHEXA refuses two versions of one pipeline with
the same name (`DUPLICATE_PIPELINE_VERSION_NAME`), and the deployer names each version after the
release tag. Re-running a tag used to fail for every pipeline already deployed (observed 2026-09-22).
Most pipelines are also byte-identical across many releases, so a workspace deployed at
`v0.1.0-test` and then `v0.2.1-test` used to *look* mostly like `v0.1.0-test`. `deploy_new_version()`
now reads the pipeline's current version and compares its **contents** with the release:

| Current version | Action |
|---|---|
| Same files, already named with this tag | Skip; counts as a success (the re-run case) |
| Same files, another name | Register again under the tag, so the workspace reads as being at the release |
| Different files | Register under the tag |
| Different files, current version already carries the tag | Register as `<tag>+redeploy-<YYYYMMDD>` (`…T<HHMMSS>Z` for a second one that day), with a warning |
| Plain tag refused because an older, non-current version holds it (e.g. a rollback) | Same `+redeploy-` fallback |

So a full run leaves every pipeline's current version named after the tag, at the price of one extra
version per unchanged pipeline per release. `+` in a version name is accepted by OpenHEXA (Giulia,
2026-09-30). The checker reads `<tag>+redeploy-<date>` as claiming `<tag>`, so it compares such a
version with that release's files like any other.

**Failures reach the run's Messages (2026-10-01, D24).** OpenHEXA shows a raised exception only in
the run's logs, so a run could stop with an `INFO` line as the last message and no reason given
(observed with an empty tag resolving to `v0.4.0-test`, which has no manifest). Every anticipated
failure now goes through `abort_run()`, which logs `[ERROR] Cannot deploy: <reason and fix>` before
raising, and the pipeline function catches anything else and logs it as an unexpected error. A
GitHub 404 on the release is diagnosed into its actual cause: repository missing or private, no
published release, only pre-releases, or unknown tag.

**What the deployer cannot do — keep in mind, discuss with the OpenHEXA devs.**

* **A pipeline cannot delete a pipeline in OpenHEXA**, so a "factory reset" (make the workspace hold
  exactly the release and nothing else) cannot be implemented. The same goes for the filesystem: the
  deployer moves superseded files to `archive/`, it never deletes them ([`checker.md`](checker.md) §5.4).
* **A pipeline that a later release drops stays in the workspace**, as a stray left over from an
  earlier release, and it keeps its old code. The deployer does not touch it, does not warn about it,
  and nothing marks it as no longer part of the release. It is confusing for an operator, who sees a
  pipeline in the list that the release no longer ships. Only the checker notices, as
  `pipelines[].in_target: false` (report-and-leave, §7.5). Deleting it is a manual
  UI action. Not being fixed; the open question is whether OpenHEXA could offer a way (an API
  mutation callable from a pipeline, or a way to archive/hide a pipeline).
* The same applies to analytics files a release removes: they remain on the filesystem.

**Testing state.** The 2026-09-30 changes (D21, D22) pass `ruff` and an offline stub test of
`deploy_new_version()` (seven cases). **They have not been run in a workspace.** The full test plan
is §6.7. Still unverified from before: **`backup_existing`**, since every verified
run so far was against an empty workspace. Past verification runs: [`HISTORY.md`](HISTORY.md) §4.2.
Every workspace run so far read manifest v1 from the old repository's releases; the v2 code (slim
tarball, `filesystem_files`, bootstrap guard, marker `repo`) is covered only by the `pytest` stubs
until `v0.1.0` is verified in a test workspace (Phase 4 of [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md)).

## Single-pipeline deployer — built 2026-10-30, **not yet tested in a workspace**

[`snt_pipeline_deployer/`](../../pipelines/snt_pipeline_deployer/) deploys **one** pipeline of a release (D28). It
is meant for a workspace that already holds real work, such as a locally hosted OpenHEXA with a running
analysis, where updating the whole release at once is too much change. It exists alongside the
deployer and does not replace it: D21 still holds for `snt_workspace_deployer`.

Parameters: `pipeline_name` plus the deployer's own, and `pull_r_scripts` (default on). `pipeline_name`
is free text, either the directory name (`snt_dhis2_extract`) or the OpenHEXA code
(`snt-dhis2-extract`), with case and padding ignored. It is checked against the manifest's `pipelines`
block, and an unknown name stops the run with an `[ERROR]` listing the release's pipelines. A dropdown
is not possible: OpenHEXA's `choices` is a static list in the code and would go stale with each release.

What it does differently from the deployer:

| Step | `snt_workspace_deployer` | `snt_pipeline_deployer` |
|---|---|---|
| Pipeline versions | Every pipeline of the release | The one named. Same D22 naming, same create-if-missing |
| Bootstrap pipeline from a release older than the latest full one | Skipped with an `[INFO]` | **Refused** with an `[ERROR]`: it is the one pipeline asked for (ADR 0042) |
| Its `filesystem_files` under `pipelines/<name>/` (notebooks, `utils/*.r`) | Every pipeline's | Only this pipeline's, and only with `pull_r_scripts` on |
| `shared/r/**` (the R library shared by all pipelines) | Copied | **Never copied.** Compared with the release, and each file that differs is named in a `[WARNING]` |
| `.snt_release` | Written | **Not written**: the workspace is not at the release |
| Version description | `Deployed by snt_workspace_deployer …` | `Deployed by snt_pipeline_deployer …` |

**The shared R library in `shared/r/`: the risk you accept with a single-pipeline deploy.** Every
pipeline's notebooks `source()` the R files in `shared/r/`, so those files belong to all pipelines at
once. Updating them for one pipeline would change the code that every other pipeline runs, which is
what this tool exists to avoid. So `shared/r/` stays at whatever version the workspace already has,
and the pipeline just deployed runs its release-`X` notebooks against shared scripts from some other
release. When the two are compatible this works. When release `X` changed a function in `shared/r/`
that its notebooks rely on (a renamed function, a new argument, a changed return shape), the pipeline
fails at run time, or worse, runs and produces different results. Nothing in OpenHEXA reports this.
The deployer's run therefore compares every shared file (a filesystem file under no pipeline's
folder) with the release's sha256 and logs one `[WARNING]` naming each
file that differs or is missing. That message tells you there is a difference, not whether it breaks
anything: check the diff of the files it names between the two releases on GitHub. The way out is to
deploy the whole release with `snt_workspace_deployer`.

With `pull_r_scripts` off, the same reasoning extends to the pipeline's own notebooks: the new
`pipeline.py` runs whatever notebooks are already in `pipelines/<name>/`.

**Other limits:**

* A pipeline's own R scripts are the `filesystem_files` under its `pipelines.<name>.path`. A pipeline
  with none (`snt_metadata_json_trim`, `create_pipeline_cards`, the bootstrap pipelines) has nothing
  to sync.
* An existing `.snt_release` is left as it is, so it still names the last *whole*-release deploy. The
  checker reports a workspace deployed this way as a mix of releases; give it the tag you deployed as
  `release_tag` to check that one pipeline against it. That mixed reading is correct.
* **Drift from the deployer.** The file is a copy. `tests/test_pipeline_deployer.py` fails when a
  function the two share differs, except `build_version_input` (description text) and `get_release`
  (its pre-release warning cannot point at a `.snt_release`, and the latest tag is quoted). `deploy_all`
  is not copied: for one pipeline, `deploy_one` is called directly and the run ends on
  `Pipeline <name> successfully deployed!` (also after an "already up to date, skipped"), not
  `Pipelines: 1/1 deployed.`. A change to the deployer is copied here in the same change.

**Run-time messages specific to it:** the sync line says where replaced files went, e.g.
`R scripts of <name>: 4/4 file(s) synced; the 4 previous copies moved to archive/<tag>/pipelines/<name>/`,
or `…; 4 existing file(s) overwritten, no backup (Backup existing files is off)`. The shared-library
check reads
`Shared R library (shared/r/, used by all pipelines, not updated by this run): all N file(s) match release <tag>.`,
or the same prefix in a `[WARNING]` listing the files that differ.

**Verified:** `ruff check` clean; `get_pipeline` yields `pipeline_name, github_repo, release_tag,
api_connection, pull_r_scripts, backup_existing, dry_run`; offline tests of name resolution,
`pipelines/<name>/` selection, the sync message, the shared-library drift warning and the bootstrap
refusal, plus the drift test against the deployer. Run on a local OpenHEXA instance on 2026-10-30
(manifest v1) and reported working; which test plan steps that covered is not recorded. Nothing since,
manifest v2 included, has been run in a workspace.

**Test plan** (run by a human, on the local instance):

1. `dry_run` on, a pipeline that exists. Logs: the R scripts it would sync (only `pipelines/<name>/`),
   "would register/relabel", the shared-library comparison, "No .snt_release marker written". Nothing changes.
2. A misspelled `pipeline_name`. `[ERROR] Cannot deploy: release … has no pipeline …`, listing them.
3. The same pipeline for real. One new version; `archive/<tag>/pipelines/<name>/…` holds the replaced
   files, and the sync line names that folder; other pipelines and `shared/r/` untouched. Ends on
   `Pipeline <name> successfully deployed!`.
4. Same again. "already up to date, skipped".
5. `pull_r_scripts` off on another pipeline. A version is registered, no file is written.

## 6.7 Phase 5, step 1 — the deployer on its own (written 2026-09-30, **not yet tested**)

The deployer is treated as a standalone pipeline first; integration with the checker (before/after
reports, enriched `.snt_release`) is the next step and has not been started. Changes made, all in
`snt_workspace_deployer/pipeline.py` and its readme:

* **D21:** `sync_analytics`, `deploy_pipelines`, `only_pipelines` and `create_missing` removed. The
  release is always deployed whole. `api_connection` is therefore always required, dry run included.
* **D22:** `deploy_new_version()` compares the current version's contents with the release and
  either skips, relabels or registers, as tabulated in this file (§ Workspace Deployer).
  An identical version *is* registered again when its name is not the tag; it is never registered
  when it already carries the tag.
* **D23 (2026-10-01):** `release_tag` is optional; empty deploys GitHub's latest release, and the
  resolved tag names the versions, the archive folder and `.snt_release`.
* **D24 (2026-10-01):** every failure is logged as an `[ERROR]` message to the run's Messages before
  the run stops (`abort_run()`, plus a catch-all in the pipeline function), and a GitHub 404 on the
  release is diagnosed into its cause.
* **D27 (2026-10-02):** a pre-release (only ever deployed by typing its tag) is deployed as usual,
  with a `[WARNING]` in the run's Messages that it is for development and testing only.
  Not yet tested in a workspace.

**Verified so far:** `ruff check` and `ruff format --check` clean; `get_pipeline` parses the deployer
and yields exactly `github_repo, release_tag, api_connection, backup_existing, dry_run`; an offline
stub of `deploy_new_version()` (fake `upload_version`, fake `current_run`) passes seven cases: skip,
relabel, plain register, `+redeploy-` for a taken current name, fallback when an older version holds
the tag, dry run, no current version. That stub was thrown away; recreate it before extending.
**Verified in `snt-development-sandbox` on 2026-10-01 (D23, D24 only):** an empty tag resolves to the
latest release (`v0.4.0-test`), and its missing manifest now stops the run with an `[ERROR]` message in
Messages. **Not verified: the D21/D22 test plan below**, nor the other D24 diagnoses (no release, only
pre-releases, unknown tag, private repo).

**Test plan** (a test workspace, against pre-releases of this repository, D-18 in
[`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md); use tags never before deployed to these pipelines; run
by a human):

1. Fresh tag `A`. Everything deploys, missing pipelines are created.
2. Same tag `A` again. Every pipeline logs "already up to date, skipped"; the run ends without error.
   This is the case that failed on 2026-09-22.
3. Newer tag `B`. Unchanged pipelines are relabelled `B`, changed ones get a new version `B`. Then run
   the checker with `release_tag=none`: the best fit should be `B`, and pipeline version names should
   read `B` throughout.
4. Roll back to `A`. Pipelines where an older version holds `A` get `A+redeploy-<date>` and a warning.
   Low priority ([`release_strategy.md`](release_strategy.md) §1.3): check it is safe — no error, nothing lost — not that the result is tidy.
5. Hand-edit one pipeline's code under the current tag and re-run that tag: expect a `+redeploy-` name
   and a warning.
6. Dry run of steps 3 and 5: log lines only, nothing registered.
7. Also untested from before: `backup_existing` against a workspace that already holds files.
8. D24 messages: a misspelled tag, and a public repository with no release. Each should end on an
   `[ERROR] Cannot deploy:` line in Messages naming the cause.
9. Bootstrap guard: once a full release exists, deploy an older pre-release. The bootstrap pipelines
   are skipped with an `[INFO]`, the others deploy.

**Known consequences to check or decide:**

* Version count grows by about one per unchanged pipeline per release. Watch for an OpenHEXA limit or
  a slow run (21 uploads instead of a few).
* `+` in a version name is accepted by OpenHEXA, on Giulia's word; confirm in the first test.
* Strays: see §7.5.

## 7.5 ~~Pipelines removed in the target release~~ — **closed 2026-09-29**

**Report-and-leave**, confirmed by Giulia. A pipeline cannot delete another pipeline in OpenHEXA,
and agents are forbidden destructive actions anyway. The report says plainly that the pipeline is
not part of the target (`pipelines[].in_target: false`), and deleting it is a manual UI action.

Two consequences to keep in mind, **not to fix here** and worth raising with the OpenHEXA devs
(Giulia, 2026-09-30):

* **No "factory reset".** Because no pipeline can delete any other, the deployer cannot make a
  workspace hold exactly one release. It can only add and update.
* **Pipelines dropped by a release stay as strays.** When a new release no longer contains a pipeline,
  the workspace keeps it, at the code of whichever release last deployed it. Nothing in the deployer
  says so, and in the OpenHEXA pipeline list it looks like part of the current release. This is
  confusing for operators. Today only the checker surfaces it (`in_target: false`, or
  `in_any_release` for one no release describes). Files on the filesystem that a release drops behave
  the same way ([`checker.md`](checker.md) §6.5, the `fixture_removed.r` leftovers).

The question for the OpenHEXA devs: could a pipeline, or a documented API call, delete or archive a
pipeline? Until then this is a permanent limit of the design, not a bug.
