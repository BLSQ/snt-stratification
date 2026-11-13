# Conventions — the reasoning behind each rule

The rules themselves, with their enforcement status and known exceptions, are the **Register** in
[`../CLAUDE.md`](../CLAUDE.md#register). This file holds the *why* and the *how*, one anchor per rule
ID (`#r1` … `#r26`); the webapp rules W1–W9 are in
[`../webapps/CLAUDE.md`](../webapps/CLAUDE.md#register). Decisions with a longer history are in [`decisions/`](decisions/README.md).

Adding a rule: add a row to the Register *and* a section here. A rule that is only here will be
missed; a rule that is only in the Register will be misapplied.

---

## Data and git

<a id="r1"></a>
### R1 — No country data in git

No `.csv`, `.xlsx`, `.parquet`, `.rds`, `.geojson` with real values. This is health data for real
districts. `.gitignore` blocks most of these — do not add exceptions, do not `git add -f`. CI
([`tools/check_tracked_files.py`](../tools/check_tracked_files.py)) fails on any tracked file with
one of these suffixes, real values or not.

<a id="r2"></a>
### R2 — Notebook outputs stripped before commit

Executed notebooks leak country data into git and produce unreviewable diffs. Detail:
[`../pipelines/CLAUDE.md`](../pipelines/CLAUDE.md#notebook-hygiene). CI
([`tools/check_tracked_files.py`](../tools/check_tracked_files.py)) fails on a tracked notebook
with any cell `outputs`. Stripping before the commit, as a local git filter:
[BACKLOG TOOL-1](BACKLOG.md#tool-1).

## Pipeline structure

<a id="r3"></a>
### R3 — `pipeline.py` orchestrates, never computes

Load config, resolve paths, call tasks and notebooks, publish to datasets. Business logic belongs in
the R notebook (or, for the Python-only pipelines, in a task function).

<a id="r4"></a>
### R4 — An output only exists if it is passed to `add_files_to_dataset(...)`

Datasets are the contract, not the filesystem. `data/` is scratch: a file not added to its OpenHEXA
dataset is invisible downstream. When you add an output, add it to the dataset *and* to the
pipeline's `readme.md`.

<a id="r6"></a>
### R6 — Every notebook listed in `pull_scripts_from_repository(...)`; other `.r` names in `extra_util_scripts`

`pull_scripts_from_repository()` (in `snt_lib`) copies only what it is told about:

- **Notebooks** must be listed: `code_scripts=[...]` for `code/`, `report_scripts=[...]` for
  `reporting/`. An unlisted notebook never reaches a workspace.
- **Util files are derived, not listed:** `utils/{pipeline_name}.r` (when `code_scripts` is given),
  `utils/{pipeline_name}_report.r` (when `report_scripts` is given) and `utils/{stem}.r` for every
  listed notebook. A missing derived file is skipped quietly.
- **Any other `.r` name** goes in `extra_util_scripts=[...]`; a listed one that is missing logs a
  warning.
- The three shared files (`snt_utils.r`, `snt_report.r`, `snt_palettes.r`) are always pulled.

Country-specific `_<CC>` variants are deliberately never listed — see
[`../pipelines/CLAUDE.md`](../pipelines/CLAUDE.md#country-specific-notebook-variants). Today the
function pulls from the **old** `snt_development` repo and its `code/` folder, whatever this repo
holds; pointing it here needs a `snt_lib` release (migration plan, Phase 6).

<a id="r16"></a>
### R16 — `readme.md` updated in the same PR as the `pipeline.py` change it describes

The pipeline `readme.md` is its user-facing contract. Follow
[`PIPELINE_README_STANDARD.md`](PIPELINE_README_STANDARD.md), which defines the required sections
and how to verify each one against the code — re-verify, do not patch from memory.

### Adding or changing a pipeline

All in one folder, `pipelines/<name>/`, where `<name>` is the `@pipeline` id (R26,
[ADR 0038](decisions/0038-repo-path-is-workspace-path.md)):

1. `pipeline.py` — `@pipeline("<name>")`, `@parameter(...)`, orchestration only (R3).
2. `requirements.txt` — match the existing two-line pattern unless more is genuinely needed.
3. `readme.md` — the user-facing contract (R16).
4. `{code,reporting,utils}/` — analytics; register the filenames (R6).
5. An entry in [`../pipelines/registry.json`](../pipelines/registry.json) with its `kind`.
6. Add the dataset id to `SNT_DATASET_IDENTIFIERS` in the config, and to the lineage tables in
   [`DATA_ARCHITECTURE.md`](DATA_ARCHITECTURE.md).

There is no deploy workflow to add yet: Phase 3 of the migration generates them from
`registry.json`.

## Publishing and releases

<a id="r5"></a>
### R5 — Each template set is published from exactly one workspace

OpenHEXA ties template publication to the workspace a pipeline is pushed from:

- Push from **`snt-development`** → publishes a **new version of the existing SNT template**, which
  propagates to every country workspace subscribed to auto-update.
- Push from **any other workspace** → creates a **separate new template pipeline**: a duplicate
  nobody is subscribed to, competing with the real one in the template list.

There are two template sets ([ADR 0041](decisions/0041-new-templates-publishing-workspace.md)):

- The **old** set is published from **`snt-development`**, by the old `snt_development` repo's CI
  only. Countries are subscribed to it. **Never push a pipeline from this repo to
  `snt-development`**: it would publish this repo's code to every subscribed country.
- The **new** set (Phase 6, [ADR 0040](decisions/0040-templates-kept-alongside-the-deployer.md))
  is published from its own dedicated workspace, not created yet.

Never run `openhexa pipelines push` for an SNT pipeline from a country or personal workspace. A
manual push from this repo goes to a test workspace only. In the old repo's workflows,
`--description` and `--link` stamp each published version with the commit message and a link to the
commit, which makes the OpenHEXA version list a usable deployment history. Decision record:
[ADR 0004](decisions/0004-publish-only-from-snt-development.md), amended by ADR 0041.

<a id="r22"></a>
### R22 — A shape change to the release manifest or the checker's report updates its schema in the same PR

Two JSON documents are read by code that is not their producer:

- **`release_manifest.json`**, attached to every GitHub release: the deployer installs what it
  lists, and the checker compares a workspace against it. Schema
  [`../contracts/release_manifest.schema.json`](../contracts/release_manifest.schema.json), prose
  [`../contracts/release_manifest.md`](../contracts/release_manifest.md).
- **The checker's status report**, frozen at `schema_version: 1`. Schema
  [`../contracts/status_report.schema.json`](../contracts/status_report.schema.json), which wins
  over the prose in `docs/bootstrap/checker.md` §5.5.

Do not change either shape (a key, a type, or what a value means) without changing its schema in
the same PR. Each schema's `description` says what is breaking: a new key or enum value is not; a
rename, a removal or a change of meaning is. Why the manifest is frozen as a schema:
[ADR 0033](decisions/0033-release-manifest-frozen-json-schema.md).

The manifest's **producer is still in the old repo**:
[`generate_manifest.yaml`](https://github.com/BLSQ/snt_development/blob/94cfc383c0f8804d2eba264f26a4bd3d372d94da/.github/workflows/generate_manifest.yaml)
in `snt_development`, not imported. Until Phase 3 brings it here as `tools/build_manifest.py`
(manifest v2), a shape change there still needs a paired PR here. *Which* paths a release ships is
the producer's choice, not part of the schema, but it changes what the deployer installs and the
checker compares, so say so in the PR.

## Naming

<a id="r7"></a>
### R7 — Every data file prefixed `{CC}_`, uppercase country code

Country code `{CC}` comes from `SNT_CONFIG.COUNTRY_CODE`, uppercase: `{CC}_routine.parquet`,
`{CC}_incidence.csv`, `{CC}_shapes.geojson`. Exception: the WorldPop raster cache
`data/worldpop/rasters/{cc_lower}_pop_{year}_*.tif`, shared by three pipelines — don't rename those
files (see the pipeline traps in
[`../pipelines/CLAUDE.md`](../pipelines/CLAUDE.md#pipeline-traps)).

<a id="r8"></a>
### R8 — Parquet is the machine contract; write the `.csv` twin beside it

The `.csv` twin is for humans. Write both where the existing pipeline does.

<a id="r9"></a>
### R9 — `{CC}_parameters.json` published beside the data

Write run parameters with `save_pipeline_parameters(...)` and always publish the file to the dataset
alongside the data. It is the only provenance record — for example, the only way to tell which
outlier method produced the current files (see *Last run wins* in the
[pipeline traps](../pipelines/CLAUDE.md#pipeline-traps)). Known exceptions: ERA5
stamps `pipeline_name="snt_era5_aggregate"`; `snt_healthcare_access` stores the `File` object, not
`.path`.

<a id="r14"></a>
### R14 — Standard flags named `run_report_only` / `pull_scripts` / `overwrite`

Keep these names and behaviours identical across pipelines — operators rely on the muscle memory:

- `run_report_only` (bool, default `False`) — skip computation, re-run reporting only.
- `pull_scripts` (bool, default `False`) — refresh notebooks from this repo. **Overwrites local
  workspace edits**; the help text must keep saying so.
- `overwrite` (bool) — on extract pipelines, delete existing raw files before download.

Known exception: `run_reports_only` in `snt_dhs_indicators`.

<a id="r15"></a>
### R15 — One vocabulary per concept in operator-facing `choices=[...]`

Today "routine data with outliers removed" is `raw_without_outliers` in `snt_dhis2_incidence`,
`outliers_removed` in `snt_dhis2_reporting_rate_dataelement`, and `removed` under a
differently-named parameter (`data_action`) in `snt_dhis2_quality_of_care`. Check the target
pipeline's `choices=[...]` before assuming. Migration: [BACKLOG PIPE-2](BACKLOG.md#pipe-2).

<a id="r18"></a>
### R18 — Python: snake_case, line-length 110, numpydoc docstrings with `Returns`

pydocstyle and pydoclint are enabled in `ruff` ([`../pyproject.toml`](../pyproject.toml)). CI
([`ci.yaml`](../.github/workflows/ci.yaml)) runs `ruff check` and `ruff format --check` at a pinned
ruff version; run them yourself before pushing.

<a id="r20"></a>
### R20 — R: roxygen2 docstrings above every function

R: snake_case functions, `<-` assignment, roxygen2 docstrings above the function signature
(`#' Title`, blank `#'`, description, `@param` per argument, `@return`, `@export`) — see
[`../shared/r/snt_utils.r`](../shared/r/snt_utils.r) for examples.

## Schema

<a id="r10"></a>
### R10 — All column names UPPERCASE in every published artefact

Python: `df.columns.str.upper()` at the merge boundary. R: `clean_column_names()`. Join keys:
`ADM1_ID` / `ADM2_ID` (+ `_NAME`), `YEAR`, `MONTH`, `PERIOD`. `ADM2_ID` is the grain of the SNT data
layers.

<a id="r11"></a>
### R11 — Notebook parameter globals UPPERCASE

<a id="r12"></a>
### R12 — Every injected parameter has a matching `exists()` fallback

Both are notebook rules; detail and the two known R11 violators are in
[`../pipelines/CLAUDE.md`](../pipelines/CLAUDE.md#parameters-injected-from-pipelinepy-r11-r12).
Migration: [BACKLOG PIPE-3](BACKLOG.md#pipe-3).

<a id="r13"></a>
### R13 — Admin levels read from config, never hardcoded

Read `DHIS2_ADMINISTRATION_1` / `DHIS2_ADMINISTRATION_2` (strings like `"level_3_name"`, parsed with
`re.search(r"level_(\d+)_", …)`) and `ANALYTICS_ORG_UNITS_LEVEL` (integer). They differ per country
and are *not* interchangeable: `ANALYTICS_ORG_UNITS_LEVEL` is the facility level for routine data,
`DHIS2_ADMINISTRATION_2` the ADM2 level for population, shapes and reporting indicators.
Validate against `pyramid["level"].max()` as the existing tasks do.

<a id="r21"></a>
### R21 — Every published output table carries a `YEAR` column

Data points are always attached to a year, so this costs nothing — and the SNT Explorer imports
`YEAR` alongside the layer's value column to let the user choose which year to display. A table
without it cannot be displayed over time, and the omission surfaces only when the layer fails to
load. Applies to tabular outputs (`.parquet` / `.csv`); not to shapes (`{CC}_shapes.geojson`), the
org-unit pyramid, or other genuinely time-independent artefacts. **This rule is newly stated —
existing outputs have not been audited against it.** Bring a table into line when you touch it; do
not assume every current output already complies.

### SNT Explorer metadata

- A published column reaches the SNT Explorer only if a layer in
  [`../catalogs/SNT_metadata_master.json`](../catalogs/README.md) points at it. Adding an indicator
  means adding its layer there too, in the same PR.
- **`SNT_metadata.json` is mid-format-change.** The old-shape copy (archived in
  `snt_development/deprecated/configuration/`, not imported) had one reader,
  `snt_assemble_results`, which is retired, so nothing reads it today. The **target** shape — one
  entry per SNT Explorer data layer, with a `SOURCE_DATA` pointer and bilingual labels — is
  specified in
  [`../contracts/snt_metadata_json/`](../contracts/snt_metadata_json/README.md), with a JSON Schema
  as its source of truth. Write new metadata entries to that schema, and read its open questions
  ([BACKLOG `META-*`](BACKLOG.md#snt-explorer-metadata)) before assuming a field's meaning: the
  format is still being validated with the IASO developers.

## Configuration

- Pipelines read `<workspace>/configuration/SNT_config.json` — one file, one country, one workspace.
  (That is the workspace path — this repo has no `configuration/` folder.)
- The current structure of that file is
  [`../contracts/snt_config/SNT_config.skeleton.json`](../contracts/snt_config/README.md), the one
  copy for the pipelines and the config editor — keep it in sync when a schema key changes. The old
  `SNT_config_<CC>.json` copies (in `snt_development/deprecated/configuration/`, not imported) were
  examples only, never loadable. Do not add logic that reads the `_<CC>` names.
- `.gitignore` blocks `*.json`, `*.yaml` and `*.yml` except an allowlist of negations (see the
  `.gitignore` trap in the root [`CLAUDE.md`](../CLAUDE.md#traps)) — a new JSON file needs a
  deliberate negation, not a force-add. The `.claude/settings.json` negation is load-bearing: without
  it the destructive-git guardrail (R19) is ignored by git and never reaches a colleague's clone.

## Logging

<a id="r17"></a>
### R17 — Failure messages a run surfaces start `[ERROR]` or `[WARNING]`, chosen deliberately

Python: `current_run.log_info / log_warning / log_error / log_debug`. R: `log_msg(msg, level)`, or
`pipeline_msg()` when the code may run outside a pipeline.

**R error severity is carried by a string prefix.** A message starting `[ERROR]` or `[WARNING]` is
mapped to OpenHEXA severity by
`error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"}`. A `[WARNING]`-labelled
failure suppresses HTML report generation but does **not** fail the run — so labelling a real
data-loss condition `[WARNING]` hides it. The same holds for the Python pipelines: the deployer's
`[ERROR] Cannot deploy: …` (bootstrap D24) relies on the prefix.

Keep messages actionable: at minimum, name the missing file — `load_dataset_file()` in
`shared/r/snt_utils.r` (the shared loader most pipelines call to read a dataset file) does this by
default. It has no way to know which upstream pipeline produces a given file, so when that context
is useful, add it in the caller: see the routine-data load cell in
`pipelines/snt_dhis2_incidence/code/snt_dhis2_incidence.ipynb`, which wraps `load_dataset_file()` in
its own `tryCatch` to name the specific upstream pipeline ("DHIS2 Outliers Removal and Imputation")
when the routine file is missing.

## Agents

<a id="r19"></a>
### R19 — Agents never run destructive / history-rewriting `git` or `gh` commands

The rule is in [`../CLAUDE.md`](../CLAUDE.md) → *Agent guardrails*; how it is enforced, tested and
changed is in [`../.claude/README.md`](../.claude/README.md). All three source repos had it; it is
one rule and one hook here.

## Docs and decisions

These four came from the source repos' doc rules (orchestrator R11–R12, bootstrap DOC1–DOC4). Where
a doc goes is [ADR 0039](decisions/0039-docs-placement-rule.md).

<a id="r23"></a>
### R23 — Docs state current truth only

No "verified on DATE", no "this used to be broken", no paragraph about what something *used to be*.
History goes to git, to an ADR, or — for the bootstrap pipelines — to
[`bootstrap/HISTORY.md`](bootstrap/HISTORY.md), leaving a link where the paragraph was. A closed
problem keeps its write-up there: relocated, not deleted. The exception is a document that says it
is a plan or a log, such as [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

<a id="r24"></a>
### R24 — Decisions are ADRs, cited, never re-argued

A decision that shapes how the repo works is an ADR in [`decisions/`](decisions/README.md): one
sequence for the whole repo. Implementation detail of the bootstrap pipelines stays as `D<n>` in
[`bootstrap/decisions.md`](bootstrap/decisions.md), append-only. Cite a decision rather than
re-arguing it. Never edit an accepted ADR to change the decision: write a new one that supersedes
it.

<a id="r25"></a>
### R25 — Each fact lives in one file; open items live only in the BACKLOG

A fact has one canonical home; other docs link to it instead of restating it, because copies
drift. Put a new fact where the routing tables (root `CLAUDE.md` "Where to find things", the nested
`CLAUDE.md` files) send a reader looking for it. Open items, questions and TODOs go to
[`BACKLOG.md`](BACKLOG.md), with a stable ID — never into a new list elsewhere.

<a id="r26"></a>
### R26 — One self-contained folder per deployable unit

Each pipeline is `pipelines/<name>/` (Python and R half together), each webapp `webapps/<name>/`
with the deployable `app/` beside its `docs/` and `design/`
([ADR 0021](decisions/0021-one-folder-per-deployable-unit.md),
[ADR 0038](decisions/0038-repo-path-is-workspace-path.md)). A unit's own docs live with it; docs
spanning several units live in `docs/`. A pipeline gets no `docs/` folder and no `CLAUDE.md`: the
pipeline zip ships every `.md` in it ([ADR 0039](decisions/0039-docs-placement-rule.md)).
