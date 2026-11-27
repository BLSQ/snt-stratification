---
name: release
description: Cut, verify and promote a release of snt-stratification — the pre-cut checklist, cutting a pre-release candidate (v0.x.y, or vX.Y.Z-rc.N from v1.0.0 on), verifying it in fresh test workspaces, one per supported country (deployer, checker, then the DHIS2 chain compared with the previous release's workspace for that country), and promoting a verified rc to a full release. Use when asked to cut, tag, test, verify or promote a release, or to plan the next one.
---

# Release

This file is the procedure. The reasons behind it are in the docs it links, so don't restate them:
the release train ([`ARCHITECTURE.md` §1.4](../../../docs/ARCHITECTURE.md#14-release-train), ADR
0037), testing as pre-releases (D-18 in [`MIGRATION_PLAN.md`](../../../docs/MIGRATION_PLAN.md)),
tags that never move ([`release_strategy.md`](../../../docs/bootstrap/release_strategy.md#release-tags-are-never-moved)),
the release assets ([`release_manifest.md`](../../../contracts/release_manifest.md#release-assets-beside-the-manifest)),
the deployer ([`deployer.md`](../../../docs/bootstrap/deployer.md)), the checker's modes
([`checker.md`](../../../docs/bootstrap/checker.md) §4) and pre-releases in reports (ADR 0034).

**Who runs what.** You hand over commands, and the maintainer runs them and reports back. You never
run `git` or `gh` writes (R19), `openhexa pipelines push`, or a pipeline. Read-only `git`/`gh`
commands can be proposed and run once approved. Give one step at a time, with numbered actions, the
expected result, what to do if it differs, and what to report back. In every command you hand over,
replace `<tag>`, `<sha>` and the other placeholders with literal values. A pasted `<…>` is a shell
redirect.

A release deploys nothing on its own. It changes a workspace only when someone runs the deployer
there, and no country workspace runs from this repo yet (root rule 2).

## 0. Name the release

| Kind | Name | Marked |
|---|---|---|
| Candidate before `v1.0.0` | `v0.x.y` (`v0.1.0` exists) | pre-release |
| Candidate from `v1.0.0` on | `vX.Y.Z-rc.N`, `N` from 1 | pre-release |
| Full release | `vX.Y.Z`, only by promoting a verified rc (§5) | full |

`v0.x.y` releases are never promoted. A webapp-only fix is a patch release (ADR 0037).
**A published tag never moves and is never deleted.** The `v*` tag ruleset enforces this. If a
candidate is wrong, give it a failure note (§4) and cut the next number.

The previous release is the baseline for §3:
`gh release list --repo BLSQ/snt-stratification --limit 5`.

## 1. Before cutting

1. **The commit is `main`'s remote head, and CI is green on it.**
   ```bash
   gh api repos/BLSQ/snt-stratification/commits/main --jq .sha
   gh run list --repo BLSQ/snt-stratification --workflow ci.yaml --commit <sha>
   ```
   The `ci` run on that SHA must be `success`. Always tag that SHA,
   never a local working tree: `tools/build_manifest.py` reads files from disk, so a local build
   proves nothing about the tag ([`sandbox.md`](../../../docs/bootstrap/sandbox.md), "Two traps").
2. **The tag does not exist yet.** `gh release view <tag> --repo BLSQ/snt-stratification` must
   answer `release not found`, and `git ls-remote --tags origin <tag>` must print nothing. If the
   tag exists without a release, `gh release create` attaches to that tag and **silently ignores
   `--target`**. The ruleset forbids deleting the tag, so burn the number and pick the next one.
3. **What changed since the baseline.** You need this list in §3.10 to explain every difference:
   ```bash
   git log --oneline <previous tag>..<sha> -- pipelines shared/r webapps catalogs
   ```
   Note which pipelines changed. Also note any outside the DHIS2 chain of §3.9.
4. **Stale country variants: re-based or accepted.** In the log of the `ci` run from 1.1 (its ID is
   the `ID` column of `gh run list`):
   ```bash
   gh run view <run id> --repo BLSQ/snt-stratification --log | grep -E "country notebook\(s\) checked|\[WARNING\] pipelines/"
   ```
   Each `[WARNING]` names a variant whose generic notebook has changed since the variant was last
   aligned with it, or whose fork point was never recorded. For each one, the maintainer either has
   it re-based first (a pull request ending with `python tools/check_country_variants.py --stamp`),
   or accepts the gap: name the accepted ones in the release notes (§2), and expect that country's
   workspace to run the stale variant in §3.9. Until [VAR-3](../../../docs/BACKLOG.md#var-3) is done,
   `snt_dhis2_incidence_NER.ipynb` is one of them.
5. **Optional, when `release.yaml` or `tools/build_*` changed since the last release:** dry-build
   the assets. Actions → `release` → Run workflow on `main`, version `v0.0.0-test`. This creates no
   release; download the `release-assets-v0.0.0-test` artefact from the run's page.

## 2. Cut the candidate

```bash
gh release create <tag> --repo BLSQ/snt-stratification --target <sha> --prerelease --title "<tag>" --notes "<what changed, one line per item>"
```

The format of release notes is not settled ([REL-5](../../../docs/BACKLOG.md#rel-5)). A short list of
the changes from §1.3 is enough. Then check that the release built its assets:

```bash
gh run list --repo BLSQ/snt-stratification --workflow release.yaml --limit 2
gh release view <tag> --repo BLSQ/snt-stratification --json isPrerelease,assets --jq '.isPrerelease, .assets[].name'
```

**Expected:** `true`, then `release_manifest.json`, `snt-stratification-<tag>.tar.gz` and one
`webapp-<name>-<tag>.zip` per bundle in `webapps/*/app/` (today: `config_editor` and `orchestrator`). If the `assets`
job failed:
- with no code at fault (a runner or network error), re-run it. `--clobber` replaces whatever was
  attached;
- because of the code, fix it in a pull request and cut the next number.

Then download the release into a folder outside the repo. The expected counts for §3 come from its
manifest:

```bash
mkdir -p /tmp/snt-<tag>-check && cd /tmp/snt-<tag>-check
gh release download <tag> --repo BLSQ/snt-stratification --pattern 'release_manifest.json' --pattern 'snt-stratification-<tag>.tar.gz' --clobber
tar xzf snt-stratification-<tag>.tar.gz
python3 -c "
import collections, json
m = json.load(open('release_manifest.json'))
p = m['pipelines']; z = sum(len(v['zip_files']) for v in p.values()); f = len(m['filesystem_files'])
print(len(p), 'pipelines', dict(collections.Counter(v['kind'] for v in p.values())))
print(f, 'filesystem files +', z, 'files in pipeline versions =', f + z, 'checker entries')"
```

`v0.1.0` gave 25 pipelines (20 `snt`, 2 `support`, 3 `bootstrap`) and 90 + 169 = 259 entries.
Below, **P** stands for the pipeline count, **F** for the filesystem-file count, **E** for the
entry count and **W** for the webapp count (the manifest's `webapps`; 2 since the config editor
moved into `app/`).

## 3. Verify in fresh test workspaces, one pair per supported country

Verify in each supported country listed in the
[`README.md`](../../../README.md#-supported-countries) (provisional,
[VAR-8](../../../docs/BACKLOG.md#var-8)), so that its country variants and hooks actually run
([ADR 0046](../../../docs/decisions/0046-country-variants-in-the-repo.md)). Per country, use two
workspaces, and run every comparison step in both:
- **candidate:** a new workspace for this candidate and country, never reused, because the deployer
  cannot delete strays ([`deployer.md`](../../../docs/bootstrap/deployer.md) §7.5; ADR 0032, one
  workspace per release). Slug from the tag and the country code: `snt-v020-bfa-test`,
  `snt-v100-rc1-ner-test`. A slug cannot be changed later;
- **baseline:** that country's test workspace of the previous release, kept as it was (`v0.1.0`
  was verified for BFA only: `snt-v010-test-bootstrap`). It stays on its release; do not deploy the
  candidate into it. A country with no such workspace has no baseline: run 3.9 in the candidate
  only, record that its outputs were not compared, and keep the candidate as that country's
  baseline for the next release.

Run 3.1–3.4, 3.6, 3.9 and 3.10 for every country; 3.5, 3.7 and 3.8 in one candidate workspace is
enough, since they do not depend on the country. A country whose DHIS2 connection or configuration
you cannot get is not verified for this release: name it in 3.11.

**3.1 Set up the candidate workspace.** In this order:
1. Settings → General → **Image** `blsq/openhexa-blsq-r-environment:latest`. A fresh workspace has
   no R image until you set it, and every R pipeline needs it.
2. Connections → the country's DHIS2 connection, **with the same name as in the baseline**. Its
   slug is a pipeline parameter.
3. Datasets → the config, as in the
   [how-to](../../../contracts/snt_config/README.md#snt-configuration-dataset): create the dataset
   `SNT_CONFIGURATION`, check its slug is `snt-configuration`, and upload `SNT_config.json` as a
   new version. Use the same content as the baseline's config: in a baseline on `v0.1.0`, which
   predates ADR 0043, that is Files → `configuration/SNT_config.json`; in a later one, the latest
   version of its `SNT_CONFIGURATION`. With no baseline, start from the country's live config. Its
   `COUNTRY_CODE` must be the country's: it decides which variants run. The file must pass
   `validate_config()` (the how-to shows
   how to check it): a copy that lacks a key the current `snt_lib` requires, such as
   `SNT_DATASET_IDENTIFIERS.SNT_POPULATION_USER_PROVIDED`, stops every pipeline.
4. Connections → New → **Custom**, name `openhexa-deploy`, one field `token`, marked secret. Its value is the
   workspace token shown under Pipelines → Create → "From OpenHEXA CLI"
   ([`openhexa_deployment.md`](../../../docs/bootstrap/openhexa_deployment.md) §7.3b).

**3.2 Push the deployer by hand, from the release's tarball.** A fresh workspace has no deployer,
and its template carries the last published tag, not this candidate.
```bash
cd /tmp/snt-<tag>-check
conda activate snt-stratification
openhexa workspaces add <candidate slug>
openhexa pipelines push /tmp/snt-<tag>-check/snt-stratification-<tag>/pipelines/snt_workspace_deployer --name <tag>
```
`openhexa workspaces add` asks for the same token as in 3.1. **Don't pass `--code`.** In a fresh
workspace it fails with `Pipeline with code '…' not found`, because `--code` only selects an
existing pipeline. Without it the CLI asks which pipeline to update: answer `1` (create one), then
`Y`. **Expected:** code `snt-workspace-deployer`. The version may be named `v1` despite `--name`
(that happened at `v0.1.0`), which is fine: 3.4 relabels it.

**3.3 Deployer, dry run.** Run `snt-workspace-deployer` with GitHub repository
`BLSQ/snt-stratification`, Release tag `<tag>`, OpenHEXA API connection `openhexa-deploy`, Backup existing files
on and **Dry run on**. **Expected:** a pre-release warning, "would …" lines, then
`Pipelines: P inspected, none registered (dry run).`, a `DRY RUN would create webapp …` line per
webapp, and the last line `Webapps: W inspected, none changed (dry run).` Nothing changes.

**3.4 Deployer, for real** (Dry run off). **Expected:** the same warning and no error.
- `Pipelines: P/P deployed.`, then `Webapps: W/W installed or up to date.`, and the last line
  `Wrote release marker: … (BLSQ/snt-stratification@<tag>).`. The bootstrap pipelines are
  included, because a pre-release target counts as newer than the latest full release (ADR 0042).
- Webapps → `snt-config-editor` and `snt-pipelines-orchestrator-cockpit`, both private, with the
  scopes of their `webapps/<name>/webapp.json` (API access tab). The config editor opens. Before
  `create_pipeline_cards` has run, the orchestrator explains the missing catalog (W3), which is
  expected; run `create-pipeline-cards` once (no parameters), reload, and it boots
  ([ADR 0048](../../../docs/decisions/0048-workspace-deployer-installs-the-webapps.md)).
- The deployer itself logs "already up to date, skipped" if 3.2 named it `<tag>`, or
  `… (same files, relabelled)` if 3.2 named it `v1`.
- Pipelines → P pipelines, codes `snt-<name>`, each current version named `<tag>`.
- Files → `pipelines/…` and `shared/r/…` (F files), plus `.snt_release` naming `<tag>` and
  `BLSQ/snt-stratification`.

**3.5 Same tag again.** **Expected:** every pipeline logs "already up to date, skipped", and so does
every webapp ("already serves release `<tag>`'s bundle, skipped"); `Pipelines: P/P deployed.`,
`Webapps: W/W installed or up to date.`, the marker line last, and no new pipeline or webapp
versions appear.

Run 3.6–3.8 **before** 3.9, because the chain's report files show up as `untracked`.

**3.6 Checker, verification mode.** Run `snt-workspace-checker` with Target release tag **empty**,
then download `snt_status/status_latest.json`. **Expected:** `mode` `verification`, target `<tag>`
read from the marker, `match` on all E entries, `errors` empty.

**3.7 Checker, attribution mode** (Target release tag `none`). Attribution leaves pre-releases out
unless one is the target (ADR 0034). Messages log `Left out … pre-release(s)`, naming `<tag>`.
- **Before any full release exists:** `best_fit` null, the F files `untracked`, and every pipeline
  "No release describes this pipeline" (as at `v0.1.0`).
- **After one exists:** the best fit is a full release, and the files this candidate changed do not
  match it ([`checker.md`](../../../docs/bootstrap/checker.md) §5.1 for the statuses).

What this step proves is the mode switch and the pre-release rule; 3.6 already scored every file.

**3.8 Single-pipeline deployer, dry run.** Run `snt-pipeline-deployer` on one changed pipeline (else
`snt_dhis2_extract`), Release tag `<tag>`, `openhexa-deploy`, Pull R scripts on, Dry run on. **Expected:** only
files under `pipelines/<that pipeline>/` are listed. The shared R line reads
`Shared R library (shared/r/, …): all N file(s) match release <tag>.`, and it logs "No .snt_release
marker written". Nothing changes.

**3.9 The DHIS2 chain, in both workspaces.** Run each step in both workspaces before the next one,
with identical parameters. Start the two extracts within minutes of each other, because DHIS2 data
moves. **Use custom notebooks OFF in both workspaces, every run**, so each runs its release's own
notebooks. A previous release older than the self-sync ([ADR 0044](../../../docs/decisions/0044-self-sync-replaces-pull-scripts.md),
`v0.1.0` included) shows **`Pull scripts`** instead: keep it OFF, because ON pulls notebooks from
the *old* `snt_development` repo (root rule 2) and overwrites that release.

| # | Pipeline | Parameters used at `v0.1.0` (Burkina Faso) |
|---|---|---|
| 1 | `snt-dhis2-extract` | DHIS2 connection (its slug); Period start `202301`, end `202412`; Overwrite on |
| 2 | `snt-dhis2-formatting` | defaults |
| 3 | `snt-dhis2-population-transformation` | Population source `DHIS2`; every other field empty |
| 4 | `snt-dhis2-outliers-imputation-mean` | Number of SD `3`; Push outliers table to DB on |
| 5 | `snt-dhis2-reporting-rate-dataset` | defaults |
| 6 | `snt-dhis2-incidence` | N1 method `PRES`; Routine data `imputed`; Population `DHIS2`; the rest empty |
| 7 | `snt-dhis2-quality-of-care` | Data action `imputed` |

"Run reporting only" stays off everywhere. If §1.3 lists a changed pipeline outside these seven,
run it in both workspaces too, after its inputs exist. In each country, use the same parameters in
its two workspaces, with that country's connection and periods.
- **Country notebooks run.** A run that uses a variant logs a `[WARNING]` naming it, and its
  `NOTEBOOK_OVERRIDES` lists it with `SOURCE` `country_variant`; in a country without variants it is
  empty. A variant or hook this candidate ships for the first time makes that country's outputs
  differ from its baseline: explain it in 3.10 by §1.3.
- **Niger, until [VAR-2](../../../docs/BACKLOG.md#var-2) and
  [VAR-3](../../../docs/BACKLOG.md#var-3) are done:** the extract logs a `[WARNING]` from the
  pyramid hook (7 facilities without coordinates), and `snt-dhis2-incidence` is expected to fail at
  `snt_dhis2_incidence_NER.ipynb`. Record both as known, not as findings, and go on to step 7,
  which does not read the incidence output.
- **The same failure in both** (same first `[ERROR]`) comes from code shared by both releases, not
  from this candidate. Record it, and don't go on until it is settled: every later step reads the
  extract.
- **A failure in only one** is a finding. Stop and read that run's Messages.
- **Burkina Faso: the extract may fail because of the DHIS2 server.** At `v0.1.0` the BFA DHIS2
  sent invalid JSON for the organisation units (`Expecting ',' delimiter`), and the old code failed
  the same way. It was checked and confirmed as a problem on the DHIS2 server, not in this repo's
  code, so there is nothing to fix here: expect it again in Burkina Faso. If it happens, the
  workaround: skip step 1 and share **one** existing `snt-dhis2-extracts` dataset into both
  workspaces. Check that its slug equals `DHIS2_DATASET_EXTRACTS` in the config and that neither
  workspace has a local copy of its own. Record that the extract went unverified.

**3.10 Compare the outputs**, country by country. In each workspace, open JupyterHub → new Python notebook, paste all of
[`dataset_summary.py`](dataset_summary.py) into one cell and run it. Then download
`snt_compare/<slug>_summary.json` into `ignore/<tag>_verification/` (git-ignored). From the repo
root:
```bash
python3 .claude/skills/release/compare_summaries.py ignore/<tag>_verification/<baseline slug>_summary.json ignore/<tag>_verification/<candidate slug>_summary.json
```
**Pass** means every `FAIL` line and every `content differs` line is explained by a change in §1.3.
A difference in a pipeline the release did not change, downstream ones included, is a finding.
Expected `info … differs` lines:
- every `{CC}_parameters.json`, because it records run times;
- `BFA_shapes.geojson` from formatting: same size, different bytes, unexplained since `v0.1.0`.

**3.11 Record the results** where the work that asked for the release is tracked (until the
migration ends: [`MIGRATION_PLAN.md`](../../../docs/MIGRATION_PLAN.md)). Record, per country, what
ran, what passed, what was not verified (name it: a country, the extract, the webapp zips, …), the
stale variants accepted in §1.4, and each explained difference.
Reports and summaries hold only paths, counts and hashes, but they stay in `ignore/`: never commit
them.

## 4. If verification fails

Fix the problem in a pull request, merge it, and cut the next number (`v0.x.y+1`, or `rc.N+1`) from
§1, in a new workspace. Never move or reuse the tag. Leave the failed release as a pre-release and
label it, so nobody later mistakes it for a broken workflow:
```bash
gh release edit <tag> --repo BLSQ/snt-stratification --notes "Failed verification: <one line>. Superseded by <next tag>."
```

## 5. Promote a verified rc to a full release

Only a `vX.Y.Z-rc.N` that passed §3 can be promoted. Create a **new** release `vX.Y.Z`, not a
pre-release, on **the exact commit of that rc**. Don't untick "pre-release" on the rc itself.

1. Find the rc's commit and check `vX.Y.Z` is free (§1.2):
   ```bash
   gh api repos/BLSQ/snt-stratification/commits/vX.Y.Z-rc.N --jq .sha
   ```
2. Cut it:
   ```bash
   gh release create vX.Y.Z --repo BLSQ/snt-stratification --target <rc sha> --title "vX.Y.Z" --notes "Promotes vX.Y.Z-rc.N (same commit). <changes since the previous full release>"
   ```
   A full release fires `published`, which runs the assets job as in §2, and `released`, which runs
   [`push_templates.yaml`](../../../.github/workflows/push_templates.yaml): one job per pipeline,
   each publishing a new template version from `snt-templates` to every auto-updating workspace
   ([ADR 0045](../../../docs/decisions/0045-how-the-new-templates-are-published.md)). Expect every
   job green; re-run a failed one alone ("Re-run failed jobs"). A pipeline new since the last
   release fails until it is published as a template by hand once.
3. **Same files as the rc.** Download both manifests into separate folders. Their `files` must be
   equal, and only `version` may differ:
   ```bash
   mkdir -p /tmp/snt-promote/rc /tmp/snt-promote/full && cd /tmp/snt-promote
   gh release download vX.Y.Z-rc.N --repo BLSQ/snt-stratification --pattern 'release_manifest.json' --dir rc --clobber
   gh release download vX.Y.Z --repo BLSQ/snt-stratification --pattern 'release_manifest.json' --dir full --clobber
   python3 -c "
   import json
   a, b = (json.load(open(d + '/release_manifest.json')) for d in ('rc', 'full'))
   print('files equal:', a['files'] == b['files'], '| webapps equal:', {k: v['files'] for k, v in a['webapps'].items()} == {k: v['files'] for k, v in b['webapps'].items()})"
   ```
4. **In one of the rc's test workspaces**, deploy `vX.Y.Z`. **Expected:** no pre-release warning, and
   every pipeline `… (same files, relabelled)`; the bootstrap ones too, since the target is now the
   latest full release. Then run the checker twice. With an empty tag, expect `match` on all E
   entries. With `none`, expect best fit `vX.Y.Z`: this is the first time attribution can score a
   release, so check it.
5. Record the promotion as in 3.11, with the `push_templates` run's result. Until Phase 8 no
   country runs from this repo, so only workspaces subscribed to the new templates change.
