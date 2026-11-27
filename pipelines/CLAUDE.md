# `pipelines/` — rules for pipelines, R notebooks and helpers

Loaded by Claude Code only when files under `pipelines/` are read; the root
[`../CLAUDE.md`](../CLAUDE.md) still applies in full. Rules referenced by ID are in its Register,
with the reasoning in [`../docs/CONVENTIONS.md`](../docs/CONVENTIONS.md). One folder per pipeline,
named after its `@pipeline` id; its kind (`snt`, `support`, `bootstrap`) is in
[`registry.json`](registry.json). No `CLAUDE.md` inside a pipeline folder: every `.md` there ships
in the pipeline zip ([ADR 0039](../docs/decisions/0039-docs-placement-rule.md)).

> **Merging a change here deploys nothing** (root rule 2). Live countries run the old
> `snt_development` repo, whose `Pull scripts` = ON pulls notebooks and the shared R library (as
> `code/`) from there, not from here. Say so in every handover.

## Notebook hygiene

- **Strip outputs before every commit** (`nbstripout`) (**R2**). Executed notebooks belong in
  `papermill_outputs/` and `reporting/outputs/` inside the workspace, never in git — they leak
  country data and produce unreviewable diffs.
- Windows `*.ipynb:Zone.Identifier` sidecars are ignored — do not commit them.
- **A notebook change needs a domain reviewer**, not just any reviewer: a change to
  `pipelines/*/code/`, `pipelines/*/utils/` or `shared/r/` should be reviewed by the person responsible
  for that pipeline — [`docs/OWNERSHIP.md`](../docs/OWNERSHIP.md#2-pipeline-responsibilities).
  Convention only: nothing blocks an unreviewed merge
  ([ADR 0005](../docs/decisions/0005-no-codeowners.md)).

## Parameters injected from `pipeline.py` (R11, R12)

- Every parameter injected from `pipeline.py` needs an `if (!exists("X")) X <- <default>` fallback
  cell, so the notebook stays interactively runnable. Change both sides together, spelled
  identically — **case included**. A mismatch is silent: the notebook quietly runs on its
  hardcoded default instead of the operator's choice.
- **Notebook parameter globals are UPPERCASE** — `ROUTINE_DATA_CHOICE`, `SNT_ROOT_PATH`,
  `DEVIATION_IQR`. This distinguishes an injected pipeline parameter from an ordinary R local at a
  glance, and matches the UPPERCASE column convention.
- **Two pipelines predate the rule** and inject lowercase globals: `snt_seasonality_cases` and
  `snt_seasonality_rainfall`. Each is internally self-consistent, so it works — but read the
  pipeline's injected dict before writing the notebook's `exists()` cell. Not a permitted variant:
  logged for migration as [BACKLOG PIPE-3](../docs/BACKLOG.md#pipe-3). New parameters are UPPERCASE
  even when added to one of those two, *unless* that would leave a single notebook mixing both —
  converting a violator is an all-at-once change, not a drive-by. A notebook mixing
  `threshold_for_seasonality` and `THRESHOLD_FOR_SEASONALITY` is worse than either.
- Beware the near-miss in `snt_healthcare_access`: it injects `WORLDPOP_YEAR` into the notebook,
  but its parameters JSON records the same value as `WPOP_YEAR` (`save_pipeline_parameters`
  uppercases the `@parameter` code `wpop_year`). Only the notebook side is governed by R11.

## Editing R notebooks: the VS Code remote-kernel loop

The working loop today:

1. Work in a local clone of this repo, with the `.ipynb` open in VS Code.
2. Connect the Jupyter extension to the OpenHEXA workspace kernel. Code executes **on the OH
   server**, so you get the workspace's files, datasets, connections and globals — exactly as if
   you were in JupyterLab — while keeping VS Code's syntax highlighting, completions, git
   integration and AI tooling.
3. Commit from the local clone as normal.

**The gap — `utils/*.r` helpers.** The notebook `source()`s its helpers from the *workspace*
filesystem, not from your local clone. So changing a helper function means editing it in the OH
workspace, then copying the change back into the local clone to version it — by hand, in that
order, every time. It is the main friction in the R loop and the reason a helper change is easy to
lose. Until it is solved: **make the helper edit in the workspace, test it, then immediately copy
the file back and commit** — do not batch several helper edits before copying back.

Setup for this loop: [`../dev/README.md`](../dev/README.md).

## Country-specific notebook variants

**The mechanism.** A notebook whose filename is the generic name plus an underscore and a country
code — `snt_dhis2_incidence_NER.ipynb` beside `snt_dhis2_incidence.ipynb` — is executed **instead
of** the generic notebook, but only in the workspace whose `SNT_CONFIG.COUNTRY_CODE` matches that
suffix. Everywhere else the generic notebook runs and the variant is inert.

`pipeline.py` never names the variant. It passes `country_code=` to `run_notebook()` /
`run_report_notebook()` alongside the *generic* `nb_path`, and the substitution happens inside
`snt_lib` (`resolve_notebook()`, pinned in each `requirements.txt`):

```python
run_notebook(
    nb_path=pipeline_path / "code" / "snt_dhis2_incidence.ipynb",  # generic name only
    country_code=country_code,                                     # ← enables the swap
    use_custom_notebooks=use_custom_notebooks,                     # ← enables custom/
    ...
)
```

A **hook** is the other kind of country notebook: `<CC>_<name>.ipynb` in `code/`, a country step
that `pipeline.py` calls by name for that country. The only one is
`snt_dhis2_extract/code/NER_pyramid_format.ipynb`, run through papermill inside the extraction
task. `custom/` cannot replace a hook, so it is not listed in `get_notebook_overrides` (R6).

**Custom notebooks, the analyst's escape hatch** ([ADR 0044](../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).
Every run copies the pipeline's own notebooks and `utils/*.r` over the workspace copies, so a hand
edit to any notebook the pipeline version ships, a country variant or hook included, is moved to
`archive/self_sync/<UTC stamp>/…` and replaced, with a `[WARNING]`. To run an edited notebook, put
it in `pipelines/<name>/custom/` under the generic file name (no `_<CC>` suffix) and run with
**Use custom notebooks** (`use_custom_notebooks`) on. Only notebooks: `utils/*.r` always comes from
the pipeline version, and `custom/` is never synced or deleted.

**Which notebook runs**, for each generic notebook, decided once per run:

| `use_custom_notebooks` | Runs, first that exists |
|---|---|
| off (default) | `<generic>_<CC>.ipynb` beside the generic one → the generic one |
| on | `custom/<generic>.ipynb` → `<generic>_<CC>.ipynb` → the generic one |

- Anything but the generic notebook logs a `[WARNING]` naming the file, and is recorded in
  `NOTEBOOK_OVERRIDES` in `{CC}_parameters.json` (`NOTEBOOK`, `SOURCE` = `custom` or
  `country_variant`, `PATH`, `SHA256`). An empty list means every notebook was the pipeline's own.
- A custom notebook's output is named `<stem>_CUSTOM_OUTPUT_<stamp>.ipynb`.
- Switch on but `custom/` holds none of the pipeline's notebooks: `[ERROR]`, and nothing runs.
- Only notebooks listed in `get_notebook_overrides(nb_paths=[...])` are recorded and counted for
  that check ([R6](../docs/CONVENTIONS.md#r6)).

**Why variants exist.** They let a country keep a bespoke analysis that runs on every run without
anyone ticking a switch ([ADR 0003](../docs/decisions/0003-country-variants-outside-pull-scripts.md),
amended by 0044 and 0046).

**Where they live: in this repo, beside the generic notebook**
([ADR 0046](../docs/decisions/0046-country-variants-in-the-repo.md)). A country notebook is
committed in `code/` or `reporting/` and ships in the pipeline version like any other notebook, so
self-sync, the deployer and the templates deliver it. Every workspace receives every country's
notebooks, inert outside their country. The repo is the record of which ones exist:

```bash
git ls-files 'pipelines/*/code/*_[A-Z][A-Z][A-Z].ipynb' 'pipelines/*/reporting/*_[A-Z][A-Z][A-Z].ipynb' 'pipelines/*/code/[A-Z][A-Z][A-Z]_*.ipynb'
```

The checker reports a shipped one like any notebook (`match` or `attributed`, `unknown_content` if
edited by hand). A variant made by hand in a workspace and never committed still reads `untracked`;
the first run of a release that ships a notebook under the same name replaces it and archives the
hand-made copy. Countries on the old `snt_development` repo keep their variants in their workspace,
as before.

**The header and the check.** Each country notebook carries a `snt_variant` key in its notebook
metadata (Jupyter: *Edit → Notebook metadata*): `kind` (`variant` or `hook`), `country`,
`variant_of`, `base_sha256` (the generic notebook's fingerprint when the variant was last aligned
with it, `null` if unknown), `base_ref` (the release or commit to diff the generic against),
`reason` and `tickets`. Field reference: the docstring of
[`tools/check_country_variants.py`](../tools/check_country_variants.py), which CI runs. It
**fails** on a missing or contradicting header, a variant with no generic notebook beside it, a
country notebook in the wrong folder, or any `country_specific/` folder. It **warns**, without
failing, when the generic notebook has changed since `base_sha256`: a pull request that changes a
generic notebook lists the countries that fall behind, and is never blocked by them. After
re-aligning a variant, record the new base:

```bash
python tools/check_country_variants.py --stamp pipelines/snt_dhis2_incidence/code/snt_dhis2_incidence_NER.ipynb --ref v0.3.0
```

**Changing a country notebook:**

- **Normal path:** a pull request, like any notebook. It reaches the country with the next release,
  installed by the deployer or a template update. A country fix waits for a release.
- **Urgent path:** the analyst puts the edited notebook in `custom/` under the *generic* file name
  and switches on `use_custom_notebooks` (a custom notebook wins over a variant), then opens the
  pull request. `custom/` is temporary and unversioned. It cannot replace a hook.
- **Not a path:** editing the variant in the workspace. The next run overwrites it and archives the
  edit, as for a generic notebook.

**Working rules:**

- **Prefer a config-driven branch inside the generic notebook** over creating a variant. A variant
  is a permanent fork: CI says when it has fallen behind, but someone still has to re-align it.
- **A new country notebook** gets its header (with `reason` and `tickets`), `base_sha256` stamped
  from the generic it was copied from, and stripped outputs. Credentials, country data files and
  personal data never go in. Jira links, Google Sheets links and DHIS2 identifiers may, but until
  the PM has ruled ([VAR-1](../docs/BACKLOG.md#var-1)) the repo owner approves each one first.
- **Before changing a generic notebook, list its `_<CC>` siblings in the same folder.** The change
  does not reach those countries unless their variant is re-aligned too; name them in the handover.
  Variants that exist only in a workspace, or in a country still on the old repo, are not in this
  list.
- **Location matters.** A variant only takes effect in the same folder the generic notebook is
  loaded from (`code/` or `reporting/`). A `country_specific/` folder is on no execution path, and
  the check fails on one.
- **A variant may still read the config from disk.** The generic notebooks read `SNT_config.json`
  from the latest version of the `SNT_CONFIGURATION` dataset, through
  `load_snt_config_from_dataset()` ([ADR 0043](../docs/decisions/0043-config-read-from-snt-configuration-dataset.md)).
  A variant written before that reads `configuration/SNT_config.json`, as the NER incidence variant
  does ([VAR-3](../docs/BACKLOG.md#var-3)). In a workspace installed from this repo that file is
  either missing, so the variant fails, or an old copy, so the variant runs on a different config
  from the rest of its pipeline and logs no version. Switch it to `load_snt_config_from_dataset()`
  in the repo before its country moves to this repo.

## Pipeline traps

- **Last run wins — by design.** The five outlier-imputation pipelines all write
  `{CC}_routine_outliers_{detected,removed,imputed}.parquet` to `DHIS2_OUTLIERS_IMPUTATION`; the two
  `reporting_rate_*` variants both write to `DHIS2_REPORTING_RATE`. Downstream consumes whatever ran
  last. Do not rename outputs per method — that breaks the override
  ([ADR 0002](../docs/decisions/0002-alternative-methods-last-run-wins.md)). Which method produced a
  file: check the `{CC}_parameters.json` beside it, or the dataset version.
  - ⚠️ The same runs also overwrite the workspace DB table `outliers_detected`, read by no pipeline
    (its consumer, a Shiny app, is paused) — [PIPE-4](../docs/BACKLOG.md#pipe-4).
- **Missing inputs skip, they do not fail.** `snt_dhis2_formatting` gates its five stages on
  `dataset_file_exists()`; `download_dhis2_analytics` catches per-period errors and continues. A
  partial run looks successful. Adding a stage: decide deliberately between skip and raise, and log
  the choice.
- **Country escape hatches are hardcoded** in `snt_dhis2_extract/pipeline.py`: BFA filters
  `level_4_name` starting `"DS"`; NER rewrites the pyramid through the hook
  `code/NER_pyramid_format.ipynb`. NER is not ready to run from here: the hook leaves 7 facilities
  without an ADM2 ([VAR-2](../docs/BACKLOG.md#var-2)) and the incidence variant fails
  ([VAR-3](../docs/BACKLOG.md#var-3)). Adding a country may mean adding a branch there — check the
  pyramid levels first.
- **The external-source pipelines depend on `snt_dhis2_formatting`.** `snt_era5_climate_data`,
  `snt_map_extracts`, `snt_worldpop_extract` and `snt_healthcare_access` all fetch
  `{CC}_shapes.geojson` from `DHIS2_DATASET_FORMATTED` first.
- **`data/worldpop/rasters/` is a shared filesystem cache** across three pipelines, keyed on
  `{cc_lower}_pop_{year}_*.tif` — *lowercase* country code (the R7 exception). Don't rename them.
- **Three parameter vocabularies for one concept** ("outliers removed") → check the target
  pipeline's `choices=[...]` (R15).
- **"Pregnant Women" in `snt_dhis2_incidence` fails** — confirmed defect: it composes
  `POP_PREGNANT_WOMAN`, producers write `POP_PREGNANT_WOMEN`. Stops loudly; the help text makes it
  read as expected. Fix belongs in `select_population_column()`, not the mapping
  ([PIPE-5](../docs/BACKLOG.md#pipe-5)).
- **Routine-file selection: copy `snt_dhis2_reporting_rate_dataelement`.** Its
  `resolve_routine_source()` maps each choice to dataset *and* filename, raises on an unknown
  choice, and checks `dataset_file_exists()` before running; the notebook just receives
  `DATASET_ID` / `ROUTINE_FILE`. (Its `_dataset` sibling reads no routine data.)
- **`snt_assemble_results` is retired** and was not imported; the Explorer reads the datasets
  directly ([ADR 0006](../docs/decisions/0006-retire-snt-assemble-results.md)). Its `SNT_RESULTS`
  key remains in live workspace configs; nothing reads it.

## Bootstrap pipelines

`snt_workspace_deployer`, `snt_pipeline_deployer` and `snt_workspace_checker` (`kind: bootstrap`)
manage which **release** a workspace runs. Not live in any country workspace. They read **manifest
v2**, the releases of this repo (`BLSQ/snt-stratification`), and refuse a v1 manifest from the old
repo. The first release is `v0.1.0`, a pre-release verified in a test workspace (Phase 4 results in
[`MIGRATION_PLAN.md`](../docs/MIGRATION_PLAN.md#phase-4-results)); no full release exists yet.

- **`snt_workspace_deployer`** installs one GitHub release, whole, from its slim tarball asset: the
  manifest's `filesystem_files` to the workspace filesystem, every `pipelines/<name>/` through the
  OpenHEXA API, each webapp from its `webapp-<name>-<tag>.zip` asset (found by slug, private, its
  scopes; ADR 0048), then `.snt_release` (tag and repo). The only component that changes a workspace.
  Bootstrap pipelines only from the latest full release or newer (ADR 0042).
- **`snt_pipeline_deployer`** deploys **one** named pipeline into a workspace that already holds
  real work: never the shared R library (`shared/r/`), never `.snt_release`. Its shared functions are
  a copy of the deployer's; `tests/test_pipeline_deployer.py` fails when they drift, so change both.
- **`snt_workspace_checker`** is read-only: hashes the workspace and reports, per file, which
  releases it matches. Its report is frozen at `schema_version: 1` (keys may be added).

```bash
pytest tests/ -q     # offline: checker stub, contract fixtures, deployer ↔ single-deployer drift
# after any @parameter edit: the AST parse OpenHEXA runs at deploy time
python -c "from pathlib import Path; from openhexa.sdk.pipelines.runtime import get_pipeline; \
print([p.code for p in get_pipeline(Path('pipelines/snt_workspace_deployer')).parameters])"
```

Nothing tests them against a real workspace: verify by reading, run the stubs, and say what you
could not verify. Their docs are in [`../docs/bootstrap/`](../docs/bootstrap/); `HISTORY.md` is
**never** read by default.

| Read | When |
|---|---|
| [`deployer.md`](../docs/bootstrap/deployer.md), then [`openhexa_deployment.md`](../docs/bootstrap/openhexa_deployment.md) | Changing either deployer, or anything about deployment and tokens |
| [`checker.md`](../docs/bootstrap/checker.md) + [`status_report.schema.json`](../contracts/status_report.schema.json) | Changing the checker or its report (the schema wins over `checker.md` §5.5) |
| [`release_manifest.schema.json`](../contracts/release_manifest.schema.json) (v2) + [`release_manifest.md`](../contracts/release_manifest.md) | Changing how the manifest is read or written (R22) |
| [`snt_release_marker.md`](../contracts/snt_release_marker.md) | Reading or writing `.snt_release` |
| [`context/snt_development.md`](../docs/bootstrap/context/snt_development.md) | What an old-repo release contains |
| [`release_strategy.md`](../docs/bootstrap/release_strategy.md), [`roadmap.md`](../docs/bootstrap/roadmap.md) | Big-picture questions, testing a PR, planning ahead |
| [`decisions.md`](../docs/bootstrap/decisions.md) | Before reopening any choice (`D1–D29`; the architectural ones are ADRs 0026–0035) |
| [`sandbox.md`](../docs/bootstrap/sandbox.md) | The former test bed (manifest v1 fixture releases); releases are now tested as pre-releases of this repo (D-18) |
| [`HISTORY.md`](../docs/bootstrap/HISTORY.md) | Before re-investigating something that seems solved |

**§ references** in these docs keep the numbers of the former bootstrap `PRODUCT_SPEC.md`:
`release_strategy.md` §1, §1.1, §1.3 · `checker.md` §1.2, §2, §3, §3.1, §4–§5, §6, §6.2–§6.6, §7,
§7.2, §7.6, §7.8–§7.11 · `deployer.md` §6.7, §7.5 ·
`openhexa_deployment.md` §7.3, §7.7 · `release_manifest.md` §2.1 · `snt_release_marker.md`
§3.2, §7.4 · `sandbox.md` §6.1 · `decisions.md` §8. A § in `HISTORY.md` is its own unless it names
another file.
