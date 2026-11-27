# BACKLOG — open items for `snt-stratification`

The **single list** of open work, unanswered questions and pending decisions for this repository:
pipelines, webapps, bootstrap and contracts alike. Other documents state facts and link here for
anything still open; they do not keep lists of their own. Jira (project `SNT25`) tracks planned
work and is managed by Giulia; this file holds the repo-level items behind it.

> **Interim home.** GitHub issues are the intended future home for these items. Until they move,
> this file is the one place to look.

> **Exceptions.** The migration to this monorepo is tracked in its own plan,
> [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md). Design-level open questions of the bootstrap pipelines
> stay in their specs ([`bootstrap/checker.md`](bootstrap/checker.md) §7,
> [`bootstrap/roadmap.md`](bootstrap/roadmap.md)); actionable bootstrap work is a `BOOT-*` item here.
> Product decisions owned by the PM stay in the orchestrator's
> [`PRODUCT_SPEC.md` §10](../webapps/orchestrator/docs/PRODUCT_SPEC.md#10-open-decisions-for-the-pm-with-recommended-version-placement);
> the `PM-*` items here only point at them.

**How this file works**

- Each item has a stable ID (`META-3`, `PIPE-2`, …). Link to it as `docs/BACKLOG.md#meta-3`. **Do
  not renumber, and do not reuse an ID**: other documents point at these IDs.
- **When an item is resolved, delete it.** There is no "done" section. If a decision settled it,
  write an ADR in [`decisions/`](decisions/README.md). If a fix settled it, the PR is the record.
- **Owner** is who can move the item forward, if known. **Source** is where the item was recorded
  before this file existed. **Blocked on** is set only when something outside the item gates it.
- Facts about the system (pain points, known defects, blind spots) stay in the reference docs. Only
  the *action* lives here, with a link back to the fact.

| Group | IDs |
|---|---|
| [Tooling & CI](#tooling--ci) | `TOOL-*` |
| [Dependencies & reproducibility](#dependencies--reproducibility) | `DEP-*` |
| [Config & contracts](#config--contracts) | `CFG-*` |
| [SNT Explorer metadata](#snt-explorer-metadata) | `META-*` — most are questions for the IASO developers |
| [Pipelines & code](#pipelines--code) | `PIPE-*` |
| [Country variants](#country-variants) | `VAR-*` |
| [Bootstrap pipelines](#bootstrap-pipelines) | `BOOT-*` |
| [Releases & deploy](#releases--deploy) | `REL-*` |
| [Orchestrator webapp](#orchestrator-webapp) | `APP-*`, `UI-*`, `OPS-*`, `GEN-*`, `PLAT-*`, `PM-*` |
| [Documentation](#documentation) | `DOC-*` |
| [Questions for the OpenHEXA developers](#questions-for-the-openhexa-developers) | `OH-*` |
| [Questions for the SNT team (domain)](#questions-for-the-snt-team-domain) | `DOM-*` |

**Imported IDs.** This file merges the backlogs of `snt_development` (IDs unchanged) and
`snt_webapp_orchestrator` (IDs unchanged where they did not collide). The bootstrap repo had no
backlog. Renumbered on import, each with an **Old ID** line:

| Old ID (orchestrator) | New ID |
|---|---|
| `REPO-3` | [`APP-12`](#app-12) |
| `TOOL-1` | [`TOOL-6`](#tool-6) |
| `DOC-2` | [`DOC-7`](#doc-7) |
| `OH-1` · `OH-2` · `OH-3` | [`OH-4`](#oh-4) · [`OH-5`](#oh-5) · [`OH-6`](#oh-6) |
| `REPO-1`, `REPO-2` | resolved by the monorepo: [ADR 0036](decisions/0036-one-monorepo.md), [ADR 0038](decisions/0038-repo-path-is-workspace-path.md) |

---

## Tooling & CI

### <a id="tool-1"></a>TOOL-1 · `nbstripout` as a repo git filter

Install `nbstripout --install` as a git filter and commit a `.gitattributes`, so stripping notebook
outputs (rule R2) stops depending on each developer remembering.

**Source:** CLAUDE.md *Suggestions*.

### <a id="tool-3"></a>TOOL-3 · A `tests/` seed

Pure functions such as `validate_yyyymm`, `validate_period_range`, `get_unique_data_elements`,
`validate_reporting_rates`, `merge_parquet_files` and `raw_reporting_ds_format` have no dependencies
and can be unit-tested today.

**Source:** CLAUDE.md *Suggestions*.

### <a id="tool-4"></a>TOOL-4 · A local loop for the R helpers

A `renv.lock` plus a small `Rscript` harness that sets the `PARAM` globals and sources
`code/snt_utils.r` + `pipelines/<name>/utils/<name>.r` against a tiny fixture would make the R half
testable without a workspace. `pipeline_msg()` already degrades gracefully when the `openhexa` object
is absent, so the helpers are closer to runnable than they look. Pairs with [DEP-2](#dep-2).

**Source:** CLAUDE.md *Suggestions*.

### <a id="tool-6"></a>TOOL-6 · JSON Schemas for the orchestrator contracts

The three files in [`contracts/orchestrator/`](../contracts/orchestrator/) are prose references
(`_description`, `_generation_instructions`), not JSON Schema, so nothing validates
`pipeline_map.json` and `pipeline_descriptions.json` against them, or a workspace's
`pipeline_cards.json`. `pytest` checks only that map node ids equal description keys
(`tests/test_contracts.py`). Write them as JSON Schema (keeping the prose), then validate the two
bundle files in `pytest` like the other contracts.

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `TOOL-1`.

### <a id="tool-8"></a>TOOL-8 · Merge policy for pull requests

Decide which GitHub merge buttons stay enabled. Proposal: squash-only, with the PR title and
description as the commit message, and branches required to be up to date. It no longer reaches
OpenHEXA from this repo: its template pushes
([`push_templates.yaml`](../.github/workflows/push_templates.yaml)) run on full releases or by hand
for a tag, and describe
each version "Release `<tag>`". It still does in the old repo, whose template-push workflows stamp
the head commit's message into each published version
([ADR 0004](decisions/0004-publish-only-from-snt-development.md)), so a merge commit publishes
"Merge pull request #N …". The migration PRs use merge commits on purpose, to keep the import commit
separate. Decide, then set it in the `main` ruleset.

**Owner:** Giulia. **Source:** Giulia's git-practices notes (local), 2026-10; Phase 2, 2026-11.

---

## Dependencies & reproducibility

### <a id="dep-2"></a>DEP-2 · A reproducible local environment for the R half

The Python desk tools are covered (`dev/environment.yml` + `pyproject.toml`). Reproducing the **R**
side is still open. Recommendation: pull the workspace image.

| Option | Verdict |
|---|---|
| **conda / mamba, extended to R** | Adopted for Python, not for R. Conda's `r-base` would drift from what the workspace runs, so "works locally" still would not mean "works in the workspace", and it would not carry the system libraries. |
| **`renv.lock`** | Useful, narrow. Reproducible R *packages* (the image already ships `r-renv`), but not the system libraries (GDAL/PROJ for `sf`, TeX for reports) that usually cause "works there, not here". Pairs with [TOOL-4](#tool-4). |
| **Pull `blsq/openhexa-blsq-r-environment:latest`** | Best value. It *is* the runtime: public on Docker Hub, ~2.5 GB, R 4.5, all R packages, Quarto and the geo stack. A `.devcontainer/` pointing at it gives VS Code an environment identical to production, with no second dependency list. |

Caveat: a local container has no OpenHEXA workspace mounted (`workspace.files_path`, datasets and
connections are absent). It gives a faithful *language* environment for helpers and pure functions,
not a way to run a whole pipeline offline. Depends on [OH-3](#oh-3) for reproducibility.

Also open, and accepted for now: `dev/environment.yml` and `pyproject.toml` carry overlapping
dependency lists ([ADR 0009](decisions/0009-conda-and-pep621-side-by-side.md)). Revisit when the
local-workflow strategy is settled.

**Source:** CLAUDE.md *Suggestions*.

---

## Config & contracts

### <a id="cfg-1"></a>CFG-1 · One key-naming convention for `SNT_DATASET_IDENTIFIERS`

The keys follow no consistent rule. Some carry an `SNT_` prefix (`SNT_HEALTHCARE_ACCESS`,
`SNT_MAP_EXTRACTS`, `SNT_SEASONALITY_*`) and some do not (`DHIS2_INCIDENCE`, `DHIS2_REPORTING_RATE`,
`ERA5_DATASET_CLIMATE`). `DHIS2_DATASET_EXTRACTS` is plural while `WORLDPOP_DATASET_EXTRACT` is
singular. The key often does not resemble the dataset it points at (`DHIS2_INCIDENCE` → the dataset
shown in OpenHEXA as `SNT_DHIS2_INCIDENCE`).

This is not cosmetic. The SNT Explorer resolves a layer by looking its `SOURCE_DATA.DATASET.NAME` up
in this map, so an author who writes the *dataset's* name instead of the *key* produces a layer that
silently fails to load. That already happened: six of the seven entries in the 2026-09-08
`SNT_metadata.json` draft were wrong this way.

**Decided 2026-11-16 (Giulia), not yet implemented.** The convention: **key = the dataset slug in
uppercase, dashes to underscores** (`SNT_DHIS2_EXTRACTS: snt-dhis2-extracts`). The map **stays in
`SNT_config.json`**. Moving it to a repo-shipped file (the plan's `catalogs/snt_datasets.json`
idea) was weighed and **deferred**: too much work for the gain, and it would have to change
`snt_lib`'s loader, every R notebook and the config editor's rule 5. Keep that idea here as a
possible later step; it is not a prerequisite of anything. NER's three extra keys
(`DHIS2_OUTLIERS_DETECTION`, `DHIS2_OUTLIERS_REMOVAL_IMPUTATION`, `SNT_SEASONALITY`) come from an
outdated example config and are **ignored**. Related: [META-5](#meta-5).

**The rename.** Eleven keys change, four already fit (`SNT_HEALTHCARE_ACCESS`,
`SNT_SEASONALITY_RAINFALL`, `SNT_SEASONALITY_CASES`, `SNT_MAP_EXTRACTS`):

| Old key | New key | Slug |
|---|---|---|
| `DHIS2_DATASET_EXTRACTS` | `SNT_DHIS2_EXTRACTS` | `snt-dhis2-extracts` |
| `DHIS2_DATASET_FORMATTED` | `SNT_DHIS2_FORMATTED` | `snt-dhis2-formatted` |
| `DHIS2_POPULATION_TRANSFORMATION` | `SNT_DHIS2_POP_TRANSFORMATION` | `snt-dhis2-pop-transformation` |
| `DHIS2_REPORTING_RATE` | `SNT_DHIS2_REPORTING_RATE` | `snt-dhis2-reporting-rate` |
| `DHIS2_OUTLIERS_IMPUTATION` | `SNT_DHIS2_OUTLIERS_IMPUTATION` | `snt-dhis2-outliers-imputation` |
| `DHIS2_INCIDENCE` | `SNT_DHIS2_INCIDENCE` | `snt-dhis2-incidence` |
| `DHIS2_QUALITY_OF_CARE` | `SNT_DHIS2_QUALITY_OF_CARE` | `snt-dhis2-quality-of-care` |
| `DHS_INDICATORS` | `SNT_DHS_INDICATORS` | `snt-dhs-indicators` |
| `WORLDPOP_DATASET_EXTRACT` | `SNT_WORLDPOP_EXTRACT` | `snt-worldpop-extract` |
| `ERA5_DATASET_CLIMATE` | `SNT_ERA5_CLIMATE` | `snt-era5-climate` |
| `SNT_POPULATION_USER_PROVIDED` | `SNT_POP_USER_PROVIDED` | `snt-pop-user-provided` |

**The blocker: `snt_lib`.** `validate_config()` in `snt_lib/snt_pipeline_utils.py` hard-codes the
15 current key names as required and fails every pipeline at startup if one is missing. Nothing
else in `snt_lib` uses the keys. The validator must change **before** the keys do. `snt_lib` is
maintained by a colleague; the agreed route while they are unavailable: a branch of
`BLSQ/snt_utils` off tag `v2.0.0`, the tag this repo's pipelines pin today
(e.g. `cfg-1-dataset-keys`; names starting with `release-v1` are blocked by the `snt_utils`
ruleset `protect-release-branches`), and this repo's pipelines pin that branch, so the change is
easy to undo. Not off `release-v1`: that would drop the config-from-dataset and self-sync changes.
The branch is never merged into `release-v1`, which live countries install from;
it is tagged instead. `snt_development` is left untouched.

**Where the old keys appear** (84 files mention `SNT_DATASET_IDENTIFIERS`): 20 `pipeline.py`;
about 25 notebooks under `code/` and `.r` files under `utils/` (`config_json$SNT_DATASET_IDENTIFIERS$<KEY>`);
the report notebooks under `reporting/`; every pipeline `readme.md`; `snt_metadata_json_trim`
(checks each Explorer layer's `DATASET.NAME` is a key of the map, by lookup, so no code change);
`catalogs/SNT_metadata_master.json` (every layer's `DATASET.NAME`) and `catalogs/README.md`;
`contracts/snt_config/` (skeleton, the 16 fixtures, README, `config_analysis_notes.md`,
`config_field_matrix.md`); `contracts/snt_metadata_json/` (README, example, schema);
`docs/DATA_ARCHITECTURE.md`, `docs/PIPELINE_README_STANDARD.md`, ADR 0002, `pipelines/CLAUDE.md`,
the `release` skill, `docs/MIGRATION_PLAN.md`; the config editor's `docs/PRODUCT_SPEC.md`,
`docs/EXTERNAL_CHECKS.md` and the `design/*.html` prototypes.

**Commit plan (agreed 2026-11-16), one commit at a time:**

1. **`snt_utils`, new branch off tag `v2.0.0`:** the `required_dataset_keys` list in
   `validate_config()`, and the one expected message in `tests/test_snt_pipeline_utils.py` that
   names `DHIS2_DATASET_EXTRACTS`. Push the branch; note its name and commit SHA.
2. **This repo, the contract:** `SNT_config.skeleton.json`; the 16 fixtures (the
   `invalid_dataset_identifier_*` cases list the key paths); `tests/requirements-conformance.txt`
   pinned to that SHA so CI runs the fixtures against the new validator; the 21
   `pipelines/*/requirements.txt` pinned to the branch (one pins nothing today); the three
   `contracts/snt_config/*.md`.
3. **The pipelines:** a mechanical word-boundary rename over `pipelines/`, then read the diff for
   false hits (a table or variable sharing a name). Notebooks edited as text, then `nbstripout`.
4. **Explorer and docs:** the master list (validate with the `add-explorer-layer` skill),
   `contracts/snt_metadata_json/`, the docs listed above, the editor's spec and external checks.
   The editor's rule 5 ("emit all 15 identifiers") **stays**: it only needed reversing for the
   deferred move. Record the convention as an ADR (R24).

**Verification:** `pytest` and the fixture run locally and in CI; then a pre-release cut with the
`release` skill, a fresh test workspace with a config in the new shape, the previous release's
workspace as baseline (D-19). Live countries are untouched (they run the old repo). Country
configs installed from this repo before the rename need the 11 keys renamed by hand.

**Owner:** Giulia. **Source:** CLAUDE.md *Suggestions*; Phase 5 discussion 2026-11-16.

### <a id="cfg-2"></a>CFG-2 · The shape of `REPORTING_DATASETS[].METRICS`

Every config has `"METRICS": {"ACTUAL_REPORTS": "float", "EXPECTED_REPORTS": "float"}`. The value is
always `"float"`, which looks like a placeholder that only avoids an empty value. It may be used during
extraction: no such use is visible in this repo, but if it exists it is probably in `snt_lib`
(external). A search of this repo cannot settle it, so "no usage found" is not proof that
the value is unused.

**Source:** the `snt_development` version of [`contracts/snt_config/README.md`](../contracts/snt_config/README.md) (formerly `configuration/README.md`).

### <a id="cfg-3"></a>CFG-3 · Write `snt_config.schema.json`

The skeleton records *where* country-specific values go, not *how* to fill them in. That belongs in
a JSON Schema on the model of `contracts/snt_metadata_json/`. Not created yet. Until then, the
per-field rules are in
[`contracts/snt_config/config_analysis_notes.md`](../contracts/snt_config/config_analysis_notes.md).

**Owner:** Giulia. **Source:** the `snt_development` version of [`contracts/snt_config/README.md`](../contracts/snt_config/README.md).

### <a id="cfg-5"></a>CFG-5 · Per-dataset output contracts

Add a contract per OpenHEXA dataset to `contracts/`: files, columns, `YEAR` presence. Needs reading
the code; source material is [`DATA_ARCHITECTURE.md` §3](DATA_ARCHITECTURE.md#3-data-lineage) and
the pipeline readmes. Prerequisite for the filename and column checks in [META-11](#meta-11).

**Source:** `contracts/README.md` ("Planned"); docs restructure plan.

### <a id="cfg-6"></a>CFG-6 · `SNT_config.json` is not tied to a DHIS2 instance

Every UID in `SNT_config.json` (population, routine indicators, reporting rates, product UIDs) is
only meaningful in the DHIS2 instance it was copied from. The file does not say which instance that
is. The DHIS2 connection reaches `snt_dhis2_extract` separately, as its required run parameter
`dhis2_connection`, so nothing checks that the two match.

If a workspace's connection is changed or pointed at another instance (a new server, an HMIS
instead of a malaria registry, a country re-hosting the workspace), the extract runs against UIDs
from a different instance. Depending on the UID, it may fail or quietly return empty or wrong
columns. The config editor records the connection identifier only as provenance (in
`_EDITOR_METADATA` and the `.log.json` sidecar), never in the config, so it does not prevent this.

To discuss with the team before changing anything. Options so far:
- Add a key for the expected connection slug or DHIS2 base URL to `SNT_CONFIG`, and have the
  extract warn or fail on a mismatch. This is a contract change: skeleton,
  [CFG-3](#cfg-3) schema, `validate_config()` in `snt_lib`, and the config editor.
- Keep the config as it is, and have the extract log the connection and the instance URL beside
  `{CC}_parameters.json`, so a mismatch can at least be traced.
- Document the risk in the operator handover only.

**Owner:** Giulia. **Source:** config editor handover for a country-hosted workspace (2026-11-09).

---

## SNT Explorer metadata

Items about `SNT_metadata.json` and the master list. The format is specified in
[`contracts/snt_metadata_json/`](../contracts/snt_metadata_json/README.md). **META-1 to META-10** keep
the numbers they had as that README's *Open questions*. Most need an answer from the **IASO
developers**; that is noted per item.

### <a id="meta-1"></a>META-1 · Empty translations

`""` appears in several fields. Should a consumer fall back to the other language, show the layer
id, or hide the layer? *Until decided: fill both languages where you can, and treat `""` as a
visible to-do.*

**Blocked on:** IASO developers.

### <a id="meta-2"></a>META-2 · Percentage or proportion

The 2026-09-08 draft had `REPORTING_RATE_*` with `SCALE: [0.25, 0.5, 0.75]` (fractions),
`UNIT_SYMBOL: "%"` and `UNITS: "Proportion"`, so a legend would read "0.25 %". Settled in the repo:
the reporting-rate pipelines write a bare 0–1 ratio, so entries take fractional cut points with
`UNIT_SYMBOL: null`, as the master list and the example now do. What remains open is whether the
Explorer ever scales a fraction to a percentage on ingest.

**Blocked on:** IASO developers.

### <a id="meta-3"></a>META-3 · Is `CATEGORY` a controlled vocabulary?

Free text today, so a typo silently creates a new group in the Explorer. A fixed list (an enum in the
schema, a dropdown in the webapp) would prevent that, at the cost of a schema edit whenever a category
is added. All master-list `CATEGORY` values are `""` today and still to be decided.

### <a id="meta-4"></a>META-4 · Which rendering modes does IASO support?

**(a)** Does the Explorer implement `"Ordinal"`, or silently fall back to threshold binning? The
latter would make the `Ordinal` layers in the master list (seasonality flags, block durations and
start months) render wrongly rather than not at all. Confirm before treating `"Ordinal"` as delivered. **(b)** Does a genuinely
**categorical** layer (unordered, or non-numeric values) need a further `TYPE`, since `SCALE` is an
array of numbers and cannot hold labels? **(c)** `"Linear"` is supported by the Explorer but
blocked by an Explorer-side bug. When it is fixed, add `"Linear"` to the `TYPE` enum in
`snt_metadata.schema.json`.

**Blocked on:** IASO developers.

### <a id="meta-5"></a>META-5 · Should `DATASET.NAME` be renamed?

It holds a config *key*, not a name, and that mismatch already caused six wrong pointers in a draft.
`DATASET_KEY` or `IDENTIFIER_KEY` would be self-explanatory. Renaming is a coordinated change with
the IASO developers, so decide **before** the format is adopted. Related: [CFG-1](#cfg-1).

**Blocked on:** IASO developers.

### <a id="meta-6"></a>META-6 · `VERSION: "latest"` versus pinning

`"latest"` means a published Explorer view changes under the user when a pipeline re-runs. That is
usually wanted, but not always (for example, a view cited in a report). Does IASO accept a specific
version id here?

**Blocked on:** IASO developers.

### <a id="meta-7"></a>META-7 · Sub-annual data

For a monthly or epi-week output, does the Explorer aggregate to the year, or can it offer a finer
selector? If so, which column does it expect (`MONTH`, `PERIOD`)? Affects ERA5, which is monthly
(both reporting-rate layers read a yearly table).

**Blocked on:** IASO developers.

### <a id="meta-8"></a>META-8 · No `$schema` key in the data file

The example does not point at its own schema, so an editor does not validate it automatically, and
nothing records which format version a file follows. Worth adding once the shape settles, as a
`$schema` property, a `FORMAT_VERSION` field, or through the `SNT_CONFIGURATION` dataset version
([ADR 0043](decisions/0043-config-read-from-snt-configuration-dataset.md)).

### <a id="meta-9"></a>META-9 · Year-independent layers

Rule R21 and the format assume every layer's table carries `YEAR`. **Seasonality is by construction
a multi-year classification**: `snt_seasonality_rainfall` and `snt_seasonality_cases` decide whether
an `ADM2` is seasonal by how often, across the whole rainfall or confirmed-cases series, a month
starts a concentrated block. Both published tables (`{CC}_rainfall_seasonality` and
`{CC}_cases_seasonality`) are keyed on `ADM2_ID` alone. There is no year to attach, and inventing
one would misrepresent the analysis. The healthcare-access table is the same: it is computed for one
WorldPop year, which is not stored. Options, roughly in order of preference:

- **The Explorer tolerates a table with no `YEAR`** and renders the layer as time-invariant (no year
  selector, or the layer greyed out rather than dropped). Cheapest, and honest about the data. Needs
  confirming that a missing `YEAR` is a supported case and not a load failure.
- **The metadata declares it**, e.g. an optional `TIME: "invariant"` on the layer, so a consumer knows
  not to look for the column. A format change, but it turns a silent failure into a declaration.
- **The table carries its coverage instead of a year**: `YEAR_START` / `YEAR_END`, or a
  `PERIOD_LABEL` like `"2019–2024"`. Useful provenance whatever the Explorer does with it. Costs a
  pipeline change and a new convention.
- **Repeat the value for every year in the range.** Recorded to be rejected: it fabricates a per-year
  result the analysis never produced.

Until this is settled, R21 has a genuine exception. Whichever way it goes, R21's wording in
`CLAUDE.md` should gain the exception, so the next person does not "fix" the seasonality tables by
adding a meaningless `YEAR`.

**Blocked on:** IASO developers.

### <a id="meta-10"></a>META-10 · Data-driven scale limits

For `"Linear"`, the Explorer might compute the end value as max() of the loaded data instead of
reading it from `SCALE`. Population layers need this most: their max() differs too much between
countries for a generic default. How a layer would request it (an omitted value, a sentinel, a flag)
is not decided.

**Blocked on:** IASO developers.

### <a id="meta-11"></a>META-11 · Scripted checks for the master list

`catalogs/SNT_metadata_master.json` is checked by hand today. Estimated at about 1.5–2 days in all;
deferred because the trim pipeline works without it.

| Piece | What it does | Effort |
|---|---|---|
| Filename cross-check | Read the `add_files_to_dataset(...)` calls in every `*/pipeline.py` (AST or regex). Flag layers pointing at a file no pipeline publishes, and published csv/parquet files no layer uses. | ~0.5–1 day |
| Column inventory | Have the trim report list each source's columns, and which ones no layer uses. Combining several workspaces' reports gives candidate new layers. | ~0.5 day |
| Release CI | Run the checks in the release workflow; block a release on schema errors. | ~2 h |
| Column audit | Per release, an agent reviews only the diff of `pipelines/**` since the last tag. | small, recurring |

**Not worth building:** static extraction of *columns* from the R code. Columns come from
`mutate`/`select`, from config-driven names (`POP_*`), from parameter-dependent branches and from NA
fallback columns. A parser would be costly and still wrong.

**Source:** CLAUDE.md *Suggestions*; `catalogs/README.md` *Known open points*.

### <a id="meta-12"></a>META-12 · Per-country tuning of `SCALE` and labels

`SCALE` in the master list is a generic default. If a country hand-tunes scales or labels in its
trimmed file, the next trim run overwrites them. A per-country override mechanism is still to be
decided.

**Source:** `catalogs/README.md` *Known open points*; CLAUDE.md *Suggestions*.

### <a id="meta-13"></a>META-13 · Review the master-list text

`LABEL`, `DESCRIPTION`, `SOURCE` and `UNITS` for all layers are a draft written from the code
(2026-10-15), not yet reviewed by someone with domain knowledge. `CATEGORY` is empty in both
languages ([META-3](#meta-3)). Most `SCALE` values are generic defaults per unit, not drawn from
data; the few reused from earlier catalogues are the population, reporting-rate, incidence and MAP
bins.

**Owner:** SNT team.

### <a id="meta-16"></a>META-16 · Add the quality-of-care rates to the master list

`snt_dhis2_quality_of_care` now writes `TESTING_RATE`, `TREATMENT_RATE`, `CASE_FATALITY_RATE`,
`PROP_ADM_MALARIA` and `PROP_MALARIA_DEATHS` in uppercase (R10). None of them is a layer in
`catalogs/SNT_metadata_master.json` yet. Add them (the `add-explorer-layer` skill traces each one).

**Source:** docs restructure plan, 2026-10 (then lowercase); re-checked in the Phase 2 sweep, 2026-11.

### <a id="meta-17"></a>META-17 · Niger's earlier catalogue versus the master list

Niger's catalogue (converted from its old-format file in 2026-09, archived as
`deprecated/configuration/SNT_metadata_NER.json`) differs from the master list in ways that matter
if Niger already uses those layers in the Explorer:

- **Population layer ids:** `POPULATION_U5` / `POPULATION_FE` in Niger's file, `POP_UNDER_5` /
  `POP_PREGNANT_WOMEN` in the master list. A layer id is what saved Explorer selections refer to, so
  if Niger's ids were ever live, switching to the master list's is a breaking change.
- **Reporting-rate method:** Niger's `REPORTING_RATE` was mapped to the data-element method because
  the old description read *"Taux de rapportage sur base de l'activité des FOSAs"*. Confirm with
  whoever wrote the original which method Niger means: the two give different numbers, and the
  master list offers both.
- **Wording:** Niger's file credits `SNIS` (the national HIS) where the master list says `DHIS2`, and
  says "zone spécifique" where the master list says "unité administrative". If Niger wants its own
  wording, that is country tuning ([META-12](#meta-12)).

**Owner:** NER country team, SNT team.

---

## Pipelines & code

### <a id="pipe-1"></a>PIPE-1 · De-duplicate `worldpopclient.py`

The same client is copied into `snt_worldpop_extract/`, `snt_map_extracts/` and
`snt_healthcare_access/`. Consolidate it, probably into `snt_lib`.

**Source:** CLAUDE.md *Suggestions*; DATA_ARCHITECTURE §9 #10.

### <a id="pipe-2"></a>PIPE-2 · Unify the routine-data-choice vocabulary (R15)

"Routine data with outliers removed" is `raw_without_outliers` in `snt_dhis2_incidence`,
`outliers_removed` in `snt_dhis2_reporting_rate_dataelement`, and `removed` under a differently named
parameter (`data_action`) in `snt_dhis2_quality_of_care`. This is operator-visible, so it needs a
migration rather than a rename. Facts:
[`DATA_ARCHITECTURE.md` §3.2](DATA_ARCHITECTURE.md#32-stages).

**Source:** CLAUDE.md *Suggestions*; DATA_ARCHITECTURE §9 #7.

### <a id="pipe-3"></a>PIPE-3 · Migrate the two lowercase-parameter pipelines to UPPERCASE (R11)

`snt_seasonality_cases` and `snt_seasonality_rainfall` inject `minimum_month_block_size`,
`maximum_month_block_size`, `threshold_for_seasonality`, `threshold_proportion_seasonal_years` and
`use_calendar_year_denominator`. Purely internal: these are notebook globals, not `@parameter`
codes, so no operator-visible name changes, unlike [PIPE-2](#pipe-2). Each pipeline is a contained
three-part edit: the injected dict in `pipeline.py`, the `if (!exists("X"))` fallback cell, and every
use inside the notebook and its `utils/*.r`. It must be atomic per pipeline: a missed use site fails
only at runtime, in a workspace, with "object not found". Check for `_<CC>` variants of the
notebooks too (`snt_seasonality_rainfall_NER.ipynb` exists). `snt_dhis2_quality_of_care` has
already been migrated (`data_action` → `DATA_ACTION`); its operator-facing `@parameter` code is still
`data_action`, which is [PIPE-2](#pipe-2)'s concern, not this item's.

**Source:** CLAUDE.md *Suggestions*.

### <a id="pipe-4"></a>PIPE-4 · Provenance for the `outliers_detected` DB table

The five outlier pipelines overwrite the workspace DB table `outliers_detected`. Unlike the dataset
files, it has no `{CC}_parameters.json` beside it, so once overwritten nothing records which method or
run produced its rows. No pipeline reads it; its consumer is a Shiny app, currently paused and
possibly to be replaced. Before anything depends on it again, decide whether it needs a method/run-id
discriminator column, or append-with-run-id instead of overwrite. The dataset files are fine as they
are ([ADR 0002](decisions/0002-alternative-methods-last-run-wins.md)).

**Blocked on:** whoever resumes the Shiny-app work. **Source:** CLAUDE.md *Suggestions* and
*Traps*; DATA_ARCHITECTURE §9 #5.

### <a id="pipe-5"></a>PIPE-5 · Fix the "Pregnant Women" selection in `snt_dhis2_incidence`

Confirmed defect: the mapped value `PREGNANT_WOMAN` composes `POP_PREGNANT_WOMAN`, while every
producer writes `POP_PREGNANT_WOMEN`, so the selection always stops with an error. The fix belongs in
`select_population_column()` (an explicit disaggregation → population-column mapping), not in the
mapping value, which correctly drives the indicator suffix. Needs a decision on the fix. Facts:
[`DATA_ARCHITECTURE.md` §6.1](DATA_ARCHITECTURE.md#61-confirmed-defect--pop_pregnant_woman-vs-pop_pregnant_women).
Related: [DOM-15](#dom-15).

**Source:** DATA_ARCHITECTURE §9 #4.

### <a id="pipe-6"></a>PIPE-6 · Hardening candidates

[`DATA_ARCHITECTURE.md` §6.2](DATA_ARCHITECTURE.md#62-known-blind-spots) lists known blind spots,
including ERA5 stamping the wrong pipeline name
into its parameters file, and `snt_healthcare_access` storing the `File` object instead of its path.
Each needs a deliberate decision: harden it, or accept it and say so.

**Source:** DATA_ARCHITECTURE §6.2.

### <a id="pipe-8"></a>PIPE-8 · Post-merge review of the `snt_dhis2_incidence` changes from PR #138

[PR #138](https://github.com/BLSQ/snt_development/pull/138) was merged on 2026-10-05, before
its review. It changes the population selection, the care-seeking import, and the yearly `N3`
aggregation in `snt_dhis2_incidence.ipynb`. Things to check:

- **NA instead of 0.** The yearly `N3` aggregation (cell 61 at merge time) now returns NA, not `0`,
  when every month is NA. Before, `INCIDENCE_ADJ_CARESEEKING` showed `0`, which read as "zero
  incidence". Confirm that leaving it empty is correct for a district-year with no usable
  care-seeking value. The readme already documents this behaviour.
- **Blank `CARESEEKING_PCT` is still treated as 100%,** so no adjustment is applied and `N3 = N2`.
  This is inconsistent with the NA rule above. Decide whether a blank value should also give an
  empty result, then document the choice in the readme's `careseeking_file_path` section.
- Validate the rest of the PR's incidence changes: population selection by dataset id, the
  care-seeking import fix, and the stale-dataset guard on error.

**Owner:** Giulia. **Source:** [PR #138 comment](https://github.com/BLSQ/snt_development/pull/138#issuecomment-5956725607)
(2026-10-02) and the merge note (2026-10-05).

### <a id="pipe-9"></a>PIPE-9 · `snt_healthcare_access`: the 5 km buffer assumes UTM zone 30N

`snt_healthcare_access.ipynb` (cell 7) hardcodes `country_epsg_meters <- 32630` (UTM zone 30N,
central meridian 3°W) for every country, and draws the 5 km circles around each health facility in
that projection. The reporting notebook has the same hardcoded value. Distance distortion grows with
distance from 3°W, so the real radius on the ground is smaller than 5 km and `POP_COVERED` /
`PCT_HEALTH_ACCESS` are biased low. Approximate real radius, from the UTM scale factor at the
country's centre: BFA ≈ 5 km, NER ≈ 4.9 km, CMR ≈ 4.8 km, COD ≈ 4.2–4.5 km, BDI ≈ 4.2 km. The
published layers still say "5 km".

Options, roughly in order of preference:

- **Derive the projection from the shapes.** For example, build a transverse Mercator centred on the
  country's centroid (`+proj=tmerc +lon_0=<centroid lon> +k=1 +units=m`), or take the UTM zone of
  the centroid. Nothing to maintain, a new country works without a code change, and a projection
  centred on the country also keeps distortion small in wide countries like COD, which span several
  UTM zones.
- **A per-country value in `SNT_config.json`** (e.g. `SNT_CONFIG.EPSG_METERS`). Explicit and
  reviewable, but it changes the config contract ([CFG-3](#cfg-3)). Every new country also needs
  someone to choose the value correctly, and a missing value needs a fallback.
- **A country-code → EPSG mapping file in the repo.** The same trade-off as the config option, plus
  one more file to keep in step with the list of countries.

Whatever the choice, apply it to both notebooks, log the projection used, and rerun the pipeline in
the affected countries. A workspace running this repo's pipeline picks up the change with the new
pipeline version, which syncs its notebooks on the next run; one still on the old repo needs the fix
ported there and a run with `Pull scripts` = ON.

**Owner:** `snt_healthcare_access` owner (`_TBD_` in [OWNERSHIP.md](OWNERSHIP.md)). **Source:**
master-list check of the healthcare-access layers, 2026-10-29.

### <a id="pipe-10"></a>PIPE-10 · `snt_healthcare_access`: the report ignores `wpop_year`

The computation notebook gets `WORLDPOP_YEAR` from the `wpop_year` parameter, but
`run_report_notebook(...)` in `pipeline.py` passes no parameters, so the report notebook falls back
to `WORLDPOP_YEAR <- current year - 1` (its `exists()` cell). A run with any other year reports on
a different raster from the one the results were computed on, or fails if that raster was never
downloaded. Fix: pass `{"WORLDPOP_YEAR": wpop_year}` to the report. For a report-only run, decide
where the year comes from (the `wpop_year` parameter, or `WPOP_YEAR` in the published
`{CC}_parameters.json`), then update the readme.

**Owner:** `snt_healthcare_access` owner (`_TBD_` in [OWNERSHIP.md](OWNERSHIP.md)). **Source:**
self-sync commit 4 review, 2026-11-18.

### <a id="pipe-11"></a>PIPE-11 · `snt_era5_climate_data`: one up-to-date batch ends the download

`sync_variable()` in `pipeline.py` downloads in batches of 50 months. When a batch has no missing
dates it logs "No missing dates to download." and **returns**, so later batches are never
requested. With **Force resync** on (the default) the zarr store is deleted first and every batch
has missing dates, so it does not show. With it off, an extended period whose first 50 months are
already stored downloads nothing new. Fix: `continue` instead of `return`.

**Owner:** `snt_era5_climate_data` owner (`_TBD_` in [OWNERSHIP.md](OWNERSHIP.md)). **Source:**
self-sync commit 4 review, 2026-11-18.

### <a id="pipe-12"></a>PIPE-12 · `snt_dhis2_extract`: the try/except around its tasks never catches

The population, shapes, pyramid and analytics downloads are OpenHEXA tasks
(`@snt_dhis2_extract.task`). Calling a task in the pipeline body only adds it to the task graph,
so the `try/except` around each call never sees a task's error, and the fallback it sets
(`pop_ready = False`, with a warning) never applies: a failing task fails the run instead. Decide
which is wanted. If a failed download should let the others carry on, handle the error inside the
task and return `False`; otherwise drop the dead `try/except` blocks. Then update
[`DATA_ARCHITECTURE.md` §4.3](DATA_ARCHITECTURE.md#43-in-pipeline-task-orchestration) and the
readme.

**Owner:** `snt_dhis2_extract` owner (`_TBD_` in [OWNERSHIP.md](OWNERSHIP.md)). **Source:**
self-sync commit 4 review, 2026-11-18.

### <a id="pipe-13"></a>PIPE-13 · Two reports stop when the workspace `SNT_metadata.json` is missing

The report notebooks of `snt_dhis2_incidence` (cell 8) and `snt_dhis2_reporting_rate_dataset`
(cell 7) load `configuration/SNT_metadata.json` from the workspace, only to read their map scale
breaks (`INCIDENCE_CRUDE$SCALE`, `REPORTING_RATE$SCALE`). `load_json()` stops with an `[ERROR]` when
the file is missing, and nothing installs it in a workspace set up from this repo (deployer or
templates): only workspaces set up for the old repo have it. So in every new workspace both reports
fail. The run still succeeds, because each `pipeline.py` logs a report failure without failing the
run, but no report is produced. Facts:
[`DATA_ARCHITECTURE.md` §3.2 Stage E](DATA_ARCHITECTURE.md#32-stages).

Both reports already fall back to default breaks when the file has no entry for them (incidence
`c(100, 250, 450, 1000)`, reporting rate `c(0.5, 0.8, 0.9, 0.95, 1.00)`). The smallest fix: use
those defaults when the file is missing too, with a log line saying so. Whether the breaks should
later come from the new-format catalogue (`catalogs/SNT_metadata_master.json`, or the trimmed copy
written by `snt_metadata_json_trim`) instead is a separate decision. Check the `_<CC>` variants of
both report notebooks before editing. Must be fixed before `v1.0.0`: its release test runs every
pipeline in new workspaces.

**Owner:** `_TBD_`. **Source:** DOC-3 check of `DATA_ARCHITECTURE.md`, 2026-11-25.

---

## Country variants

Country-specific notebooks committed beside their generic notebook
([ADR 0046](decisions/0046-country-variants-in-the-repo.md)).

### <a id="var-1"></a>VAR-1 · PM review: what may be public in country notebooks

ADR 0046 lets country notebooks into this public repo. Credentials, country data files, notebook
outputs and personal data never go in. For everything between those lines, the PM decides, per
category, whether it may be public:

- links to internal tools (Jira, Google Sheets);
- names of Bluesquare test workspaces, of live country workspaces, and of storage buckets;
- DHIS2 identifiers of organisation units and organisation-unit groups;
- health-facility names and hand-entered GPS coordinates;
- staff names in comments.

Until then the repo owner approves each such item before it is committed. Approved so far, in
`snt_dhis2_extract/code/NER_pyramid_format.ipynb`: 1 Jira link, 12 organisation-unit-group ids and
a first name. Redacted: the 7 facility ids, names and coordinates ([VAR-2](#var-2)). The import's
redactions (15 DHIS2 ids, 2 live workspace names, 1 bucket name, a Niger helper with facility ids
and coordinates) are kept until this item is settled.

**Owner:** Giulia. **Blocked on:** the PM. **Source:** ADR 0046 discussion, 2026-11-23.

### <a id="var-2"></a>VAR-2 · Restore the redacted coordinates in the NER pyramid notebook

Cell 9 of [`NER_pyramid_format.ipynb`](../pipelines/snt_dhis2_extract/code/NER_pyramid_format.ipynb)
sets the coordinates of 7 Niger health facilities that have none in DHIS2, so that they can be
placed under their district (DS). These lines (DHIS2 id, facility name, latitude and longitude
taken from Google Maps) were redacted before the notebook was published. Until they are back,
every NER run of `snt_dhis2_extract` logs a `[WARNING]` and leaves those facilities without a
district. The original lines are in the same cell of
`pipelines/snt_dhis2_extract/code/NER_pyramid_format.ipynb` in `BLSQ/snt_development` at
`94cfc383c0f8804d2eba264f26a4bd3d372d94da`.

When [VAR-1](#var-1) allows it, restore them, and remove the `[WARNING]` and the "REDACTED" notes
from cells 0, 7 and 9, the `reason` in the notebook's `snt_variant` header, and step 5 of the
[pipeline readme](../pipelines/snt_dhis2_extract/readme.md). If it does not, decide where these
coordinates live instead, for example in DHIS2 itself. Either way, do this before Niger runs
from this repo, and check first whether DHIS2 now has coordinates for these facilities.

**Owner:** Giulia. **Blocked on:** [VAR-1](#var-1). **Source:** ADR 0046, commit 3, 2026-11-23.

### <a id="var-3"></a>VAR-3 · Re-base the NER incidence variant before Niger runs from this repo

[`snt_dhis2_incidence_NER.ipynb`](../pipelines/snt_dhis2_incidence/code/snt_dhis2_incidence_NER.ipynb)
was committed as it stood in `snt_development` (its `country_specific/` folder, at `94cfc38`). It was
forked from an older generic notebook, at a point nobody recorded (`base_sha256: null`, so CI lists
it as stale), and does not fit today's pipeline:

- it loads `snt_utils.r` and `snt_palettes.r` from `code/`, which a workspace installed from this repo
  does not have (shared R is in `shared/r/`, [ADR 0038](decisions/0038-repo-path-is-workspace-path.md));
- it reads `configuration/SNT_config.json` from the filesystem, not the `SNT_CONFIGURATION` dataset
  ([ADR 0043](decisions/0043-config-read-from-snt-configuration-dataset.md));
- it ignores two parameters the pipeline sends, `POPULATION_DATASET_ID` and `CARESEEKING_FILE_PATH`,
  and chooses its population with its own `USE_ADJUSTED_POPULATION` (never sent, default `FALSE`);
- it carries none of the generic notebook's changes since the fork.

It runs automatically wherever `COUNTRY_CODE` is `NER`, so from the first release that contains it, a
Niger run of `snt_dhis2_incidence` is expected to fail at this notebook. Re-base it: compare it with
the generic notebook to list what is Niger-specific (population disaggregation for pregnant women
and children under 5, SNT25-363), move whatever a configuration switch can carry into the generic
notebook, and rewrite the rest on top of the current generic. Then record the new base with
`python tools/check_country_variants.py --stamp <variant> --ref <release>`. Needs Niger data to
test, and the Niger workspace's own copy, which may differ from the repo's.

**Owner:** Giulia. **Source:** ADR 0046, commit 4, 2026-11-23.

### <a id="var-4"></a>VAR-4 · Niger's rainfall variant and `new_parameter.r`, left out: still needed?

`snt_seasonality_rainfall_NER.ipynb` was left out of this repo on purpose: it is probably obsolete.
It is the generic rainfall-seasonality notebook with comments, plus
`compute_month_seasonality_NEW()`, which uses a calendar-year denominator. It `source()`s
`new_parameter.r`, a file that was only ever in the Niger workspace, in no repo. The notebook is
readable at `pipelines/snt_seasonality_rainfall/code/snt_seasonality_rainfall_NER.ipynb` in
`BLSQ/snt_development` at `94cfc383c0f8804d2eba264f26a4bd3d372d94da`.

Before Niger runs from this repo, ask the Niger analysts whether its output is still used. If it
is, get `new_parameter.r` from the workspace, decide whether the calendar-year denominator belongs
in the generic notebook behind a configuration switch, and commit whatever remains as a variant
with its header. If it is not, close this item.

**Owner:** Giulia. **Source:** ADR 0046 discussion (D4), 2026-11-23.

### <a id="var-5"></a>VAR-5 · Burundi's pyramid variant, left out: still needed?

`snt_dhis2_formatting_pyramid_BDI.ipynb` was left out of this repo on purpose. It sat in the old
repo's `country_specific/` folder, so it never ran from there. Its coordinate fix is already in the
generic notebook. What remains is a mapping of old to new communes after Burundi's 2025
administrative reform, and 3 facilities fixed by hand. It is readable at
`pipelines/snt_dhis2_formatting/country_specific/snt_dhis2_formatting_pyramid_BDI.ipynb` in
`BLSQ/snt_development` at `94cfc383c0f8804d2eba264f26a4bd3d372d94da`.

Before Burundi runs from this repo, check whether its DHIS2 pyramid now carries the new communes
and the 3 facilities' fixes. If it does, close this item. If not, commit it as a variant of
`snt_dhis2_formatting/code/snt_dhis2_formatting_pyramid.ipynb`, with its header; its facility ids and names
need the repo owner's approval ([VAR-1](#var-1)).

**Owner:** Giulia. **Source:** ADR 0046 discussion (D9), 2026-11-23.

### <a id="var-6"></a>VAR-6 · Optional: remove Jira and Google Sheets links from country notebooks

ADR 0046 allows Jira and Google Sheets links in this public repo: neither opens without a Bluesquare
login. They are still internal detail. If the PM prefers ([VAR-1](#var-1)), replace each with the
ticket key alone (`SNT25-363`) or a short description, in the country notebooks and in their
`snt_variant` headers. Optional; nothing depends on it.

**Owner:** `_TBD_`. **Source:** ADR 0046 discussion (D1), 2026-11-23.

### <a id="var-7"></a>VAR-7 · `snt_lib`: the sync docstring, and a drift warning at run time

`sync_pipeline_scripts` in `snt_lib/snt_pipeline_utils.py` (`BLSQ/snt_utils`) says country variants
are never touched. Since ADR 0046 that holds only for a variant **not** shipped in the pipeline
version: a shipped one is copied, and a hand edit to it archived, like any notebook. Correct the
docstring in a new `snt_utils` tag, and bump the `snt_lib` pin in the pipelines'
`requirements.txt` to it.

Optional, in the same change: when `resolve_notebook()` picks a variant, compare its
`snt_variant.base_sha256` with the generic notebook's sha256 and log a `[WARNING]` when they differ,
so an analyst sees in the run that the variant lags behind. Today only CI warns, on the pull request.

**Owner:** `snt_lib` owner (`_TBD_` in [OWNERSHIP.md](OWNERSHIP.md)). **Source:** ADR 0046,
2026-11-23.

### <a id="var-8"></a>VAR-8 · PM to review and approve the supported-country list

The [supported countries](../README.md#-supported-countries) (BFA, NER, COD, BDI, CMR) were chosen
by the repo owner and are marked provisional. Each one costs a pair of test workspaces per release,
with that country's DHIS2 connection and configuration
([`release` skill](../.claude/skills/release/SKILL.md) §3). The PM confirms the list, and with it
which countries are told that a pipeline may fail on their data. Once approved, remove
"provisional" from the README.

**Owner:** Giulia. **Blocked on:** the PM. **Source:** ADR 0046 discussion (D5, D11), 2026-11-23.

---

## Bootstrap pipelines

### <a id="boot-2"></a>BOOT-2 · A readable status page from the checker

Besides the JSON report ([ADR 0027](decisions/0027-checker-report-is-a-workspace-file.md)), write a
human-readable HTML status page. In a fresh workspace, a placeholder page would say "run the checker",
linked from the workspace README. Not checked: whether a pipeline can edit the workspace README.

**Source:** Giulia's plan of action (local), 2026-09-30.

### <a id="boot-3"></a>BOOT-3 · Delete the fork `BLSQ/snt_development_test-release`

An abandoned test fork from the release work. A colleague made a commit there; delete it once they
confirm nothing in it is needed. The other sandbox leftovers (probe pipelines in
`snt-development-sandbox`) are already gone.

**Owner:** Giulia. **Blocked on:** the colleague's confirmation. **Source:** Phase 2 sweep, 2026-11.

### <a id="boot-5"></a>BOOT-5 · Deployers and a suffixed template copy whose plain code was deleted

A pipeline created from a template while its code was taken gets `snt-<name>-<6 hex>`
([ADR 0040](decisions/0040-templates-kept-alongside-the-deployer.md)). Both deployers look a
pipeline up by its exact code `snt-<name>` only. While the plain one exists they deploy onto it, and
the checker names the copy in `stands_for`. If someone deletes the plain one, the next deploy creates
a new `snt-<name>` beside the copy, which keeps running old code. Decide whether the deployers should
adopt the copy (and what to do with several), warn, or leave it. Change both deployers together
(`tests/test_pipeline_deployer.py`).

**Source:** Migration Phase 4 commit 6, 2026-11-13 (deferred: the checker only, for now).

### <a id="boot-7"></a>BOOT-7 · The checker reports a missing `SNT_CONFIGURATION` dataset

Every SNT pipeline stops with an `[ERROR]` if the dataset `SNT_CONFIGURATION`
(`snt-configuration`), its latest version or its `SNT_config.json` is missing
([ADR 0043](decisions/0043-config-read-from-snt-configuration-dataset.md)). The checker could
report this before anyone runs a pipeline. It reads no config today and takes no country code; it
would only check that the file exists, not validate it. Changes the checker's report, so its schema
in `contracts/` too (R22).

**Source:** Phase 5 discussion (CFG-4), 2026-11-16.

---

## Releases & deploy

### <a id="rel-1"></a>REL-1 · Release versioning

GitHub releases plus a `version.json` in the bundle, shown in the app footer, so a workspace's
deployed version is one file read. Check first whether git-backed webapps already answer it:
`Webapp.versions` / `GitSource.publishedVersion` may expose the deployed commit without a baked file.

Planned: [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) Phase 7 stamps `version.json` into each
webapp release zip ([ADR 0037](decisions/0037-one-release-train.md)).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="rel-2"></a>REL-2 · Webapp deployer

Likely a "webapps" section in `pipelines/snt_workspace_deployer`'s release manifest,
using `updateWebapp(files: …)`; needs a CUSTOM-connection token like the pipeline deployer. Check
what git-backed webapp versions already give.

Planned: [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) Phase 7, gated on spike S5.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="rel-3"></a>REL-3 · Tested rollback procedure

`UpdateWebappInput.publishedVersionId` can pin the served commit (raw GraphQL / UI only; no MCP
tool). Verify whether a later file update re-publishes HEAD automatically and whether `previewUrl`
serves an unpublished head, then document the procedure in [`DEPLOYMENT.md`](../webapps/orchestrator/docs/DEPLOYMENT.md#version-history-and-rollback).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="rel-4"></a>REL-4 · The manifest should carry the release commit

Add the release commit (`github.sha`) to manifest v2. One releases API call then gives a
tag-to-commit table, and the deployer stops relying on GitHub's undocumented
`<owner>-<repo>-<short_sha>` folder name inside the release tarball. Part of the manifest v2 work
([`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) Phase 3).

**Source:** SNT25-670 GitHub releases primer (local), 2026-10.

### <a id="rel-5"></a>REL-5 · Release notes or a `CHANGELOG.md` (optional)

Decide whether each release gets written notes, and where: GitHub release notes, a `CHANGELOG.md`,
or both. A fix is recorded by its PR ([how this file works](#backlog--open-items-for-snt-stratification)),
so this is about a readable per-release summary for users. Natural place: `release.yaml`
([`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) Phase 3).

**Source:** docs restructure plan, 2026-10.

### <a id="rel-6"></a>REL-6 · `shared/r/` does not reach a template-installed workspace

Self-sync ([ADR 0044](decisions/0044-self-sync-replaces-pull-scripts.md)) copies each pipeline's
own notebooks and `utils/*.r` from its zip, but not the shared R library `shared/r/`, which
almost every notebook `source()`s. Only the deployer installs it. A workspace built from the new
templates (Phase 6) therefore has no `shared/r/`, and its notebooks fail. The same holds for a
pipeline pushed by hand with `openhexa pipelines push` to a workspace the deployer never ran in, or
ran in at an older release: its notebooks get an older `shared/r/`, or none (release `v0.1.0`'s
`snt_utils.r` lacks the `load_snt_config_from_dataset()` the notebooks now call), until someone
uploads `shared/r/` by hand. Options: ship
`shared/r/` in every pipeline zip and sync it (spike S2b tested this; several pipelines then
write the same files), let one pipeline own it, or an R package (migration plan §10). Settle
before relying on the template route ([`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) Phase 6).

**Source:** self-sync discussion, 2026-11-17; self-sync pilot test in `snt-testing`, 2026-11-17.

### <a id="rel-7"></a>REL-7 · Publish `snt_config_publish` as a template before the next full release

`snt_config_publish` is a new support pipeline
([ADR 0047](decisions/0047-config-editor-publishes-to-snt-configuration.md)). Before the next full
release, push it once by hand to `snt-templates` and publish it as a template named after its
`@pipeline` id ([adding a pipeline, step 7](CONVENTIONS.md#adding-or-changing-a-pipeline)). Until
then [`push_templates.yaml`](../.github/workflows/push_templates.yaml) fails on it, because `--code`
only selects a pipeline that already exists there.

**Source:** config editor dataset write, 2026-11-26.

---

## Orchestrator webapp

The SNT Pipelines Orchestrator ([`webapps/orchestrator/`](../webapps/orchestrator/)) and its
catalog generator `create_pipeline_cards`.

### <a id="app-12"></a>APP-12 · Bucket key keeps the old `utils_pipelines/` name

The catalog's bucket key `utils_pipelines/create_pipeline_cards/pipeline_cards/pipeline_cards.json`
no longer matches the repo folder (`pipelines/`). Migrate it deliberately or keep it forever.
Migrating touches `CARDS_OBJECT_KEY` in `app.js`, `config.py`, and every workspace bucket (redeploy
both, re-run the generator everywhere).

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `REPO-3`.

### <a id="ops-1"></a>OPS-1 · Unpublish the live Flowchart webapps?

Flowchart webapps may still be deployed (`snt-app-dev`, `snt-testing`, `xxx-snt-process` as of the
2026-10 cleanup). Decide whether to remove them ([ADR 0018](decisions/0018-cockpit-only-flowchart-parked.md)).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ops-2"></a>OPS-2 · Delete leftover `pipeline_cards.json` inside deployed webapps

Webapps deployed before the catalog moved to the bucket may still carry a `pipeline_cards.json`;
nothing fetches it. Remove with `update_static_webapp(files_to_delete_json=…)`.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ops-3"></a>OPS-3 · Delete leftover spike webapps?

`t0-9-status-proxy-spike` (snt-testing) and `report-embed-probe` (snt-app-dev) may still exist. Their
source is in the archived repo's
[`deprecated/`](https://github.com/BLSQ/OpenHEXA-WebApp-Diary/tree/bbd02388f0104d809e55a81f5b84b29ce6b569bd/deprecated).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="gen-1"></a>GEN-1 · Push the generator to each workspace

The repo's `config.NOTES` fills in the workspace slug, but a generator installed from an older
version still writes a hardcoded "SNT App Dev workspace" note into its catalog until it is
re-pushed and re-run in that workspace.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-13"></a>APP-13 · Hint when a "not installed" step is in fact installed

A step can show "not installed" while a matching pipeline exists in the workspace, because the
catalog is stale. The panel could say "installed; refresh the catalogue" (a hint only, nothing to
run). Open: is there a reliable live key to match on, the node id (Python function name) or the
pipeline `code`? Not the same as [UI-8](#ui-8), which is about version drift.

**Source:** orchestrator install-and-run fixes plan (local), task 5, 2026-10.

### <a id="ui-2"></a>UI-2 · Show run progress

`pipelineRun.progress` is available on every run; the status line shows only the status.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-3"></a>UI-3 · Render `DatabaseTable` outputs

Add the `... on DatabaseTable` fragment if any SNT pipeline starts emitting tables.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-4"></a>UI-4 · Translate parameter labels

Parameter labels, help and choices come from the catalog and are English only. PM decision:
[`PRODUCT_SPEC.md` §10 item 1](../webapps/orchestrator/docs/PRODUCT_SPEC.md#10-open-decisions-for-the-pm-with-recommended-version-placement).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-5"></a>UI-5 · Review the French strings

`I18N.fr` and the `fr` sides of the data files are drafts pending Giulia's review.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-7"></a>UI-7 · Per-type counts in the collapsed Dependencies header

_"Requires (2 pipelines)"_ / _"Unlocks (11 pipelines)"_ — still wanted now that the section starts
collapsed? ([`PRODUCT_SPEC.md` §10 item 9](../webapps/orchestrator/docs/PRODUCT_SPEC.md#10-open-decisions-for-the-pm-with-recommended-version-placement))

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-8"></a>UI-8 · Version drift check

Compare each card's `version_name` / `version_number` with the live
`pipelineByCode.currentVersion` and prompt for a catalog refresh only on real change; optionally pin
runs with `RunPipelineInput.versionId`.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-9"></a>UI-9 · Run notifications and debug logs

`RunPipelineInput.sendMailNotifications` for long runs; `enableDebugLogs` when linking a user to a
failed run.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-10"></a>UI-10 · Catalog read via `readFileContent` (optional)

Instead of `prepareObjectDownload` + `fetch` — only if signed-URL expiry or CORS becomes a problem.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-1"></a>APP-1 · `pipelines(…, perPage: 100)` never paginates

The status and generator-diagnosis queries silently truncate past 100 pipelines. Low risk today;
fix or accept.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-2"></a>APP-2 · DRC-specific connection placeholder

`form.connPlaceholder` (en + fr) reads `e.g. dhis2-nmdr-drc`. Use a neutral example? User-visible
string, so not changed silently.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-3"></a>APP-3 · Verify signed-URL expiry

The `renderReportEmbeds` comment claims ~1 h. Check one `downloadUrl`'s `X-Goog-Expires` in DevTools.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-4"></a>APP-4 · Verify the templates-tab deep link

Check that `/pipelines/?tab=templates` still lands on the templates tab.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-5"></a>APP-5 · Long runs stop being watched after 40 min

Polling ends with "stopped watching — still running in OpenHEXA". Fine, or extend it / pair it with
UI-9? Reloading the page resumes polling with a fresh 40-min budget.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-6"></a>APP-6 · "Refresh the catalogue" button in the run-error drift hint

The not-installed panel runs the generator itself ([ADR 0024](decisions/0024-webapp-may-run-the-generator.md)).
The drift hint under a rejected run (`catalogueRefreshHintHtml`) still only links to it. Reuse the
same control there? The status line is a flex row (`.rs-hint` for a second line).

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-7"></a>APP-7 · "Refresh the catalogue" button in the boot "no catalogue" panel

Same question for the boot panel (`missingCatalogError`, states `neverRun` / `lastRunFailed`). The
app has not booted there, so the control would need to work without `APP` state.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-8"></a>APP-8 · Deep-link step 1 of the not-installed panel to the step's own template

Step 1 links to the templates tab (`/pipelines/?tab=templates`). OpenHEXA also has a page per
template, `/workspaces/<slug>/templates/<encoded template name>` (e.g. `…/templates/A.6%20DHIS2%20Incidence`),
the same shape `generatorTemplateUrl` already uses. The map's `ohName` is now defined as the
template's display name, shown only for a step that is not installed; the five values that had
drifted were corrected on 2026-11-17, the other 13 were not re-checked against the template list.
A wrong name gives a broken page, and the app can't detect that. Options: build the link from
`ohName` and keep it in lockstep with the template names, or add a separate `templateName` field
to the map contract. Either way, fall back to the templates tab when the field is missing.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-10"></a>APP-10 · Should a pipeline that has already run become locked again?

Only an installed, **never-run** pipeline can be locked (`showLocked` = `lockedReason()` and state
`none`, in the rail, the pill and `runRowHtml`). Example: A.2 succeeded last week, then A.1's latest
run failed. A.2 still shows "Succeeded" and its Run button stays enabled. Decide whether "locked"
should apply to an installed pipeline in any state whenever a hard prerequisite's latest run isn't a
success. If yes: how to show it alongside the pipeline's own last-run status (the pill shows one
state), and whether Run is disabled or only warned. Not-installed pipelines stay never-locked either
way.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="ui-11"></a>UI-11 · Confirm the "Queued" colours

`--queue` / `--queue-bg` in `styles.css` (grey text on OpenHEXA's gray-100) are a guess: the queued
badge shows for seconds in OpenHEXA and its colours weren't captured. Replace them once seen.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="app-11"></a>APP-11 · Output dataset links need `DATASETS_READ`

The proxy grants `DatasetVersion` / `Dataset` fields only under `DATASETS_READ`
([runtime](OPENHEXA_WEBAPP_RUNTIME.md#allowed_operations-scopes)), which the app does not have
(R9). So `DATASET_OUTPUTS_QUERY` is refused and the Latest outputs box lists no dataset links;
files and the HTML report are unaffected. Decide: add `DATASETS_READ` (changes R9) and the links
come back with no code change, or drop the query.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### <a id="plat-1"></a>PLAT-1 · Self-hosted OpenHEXA

The front-end base `https://app.openhexa.org` is hardcoded
([ADR 0019](decisions/0019-hardcoded-saas-front-end-base.md)). A self-hosted install needs it from
config, or from `window.OPENHEXA` if the platform ever exposes it.

**Source:** `snt_webapp_orchestrator` BACKLOG.

### Product (PM)

Owned by the PM; full text and recommended version in
[`PRODUCT_SPEC.md` §10](../webapps/orchestrator/docs/PRODUCT_SPEC.md#10-open-decisions-for-the-pm-with-recommended-version-placement).

- <a id="pm-1"></a>**PM-1** · In-app failure help: plain-language summary + run messages/log
  excerpts (v2) — §10 item 2.
- <a id="pm-2"></a>**PM-2** · "Recommend the next step" banner/badge (v2) — §10 item 4.
- <a id="pm-3"></a>**PM-3** · Team run model and "who is running what" (v2) — §10 item 5.
- <a id="pm-4"></a>**PM-4** · Connections and setup ownership (v2) — §10 item 6.
- <a id="pm-6"></a>**PM-6** · Full narrative layer / onboarding tour (v2, parked) — §7 and §9.

---

## Documentation

### <a id="doc-1"></a>DOC-1 · Authoritative pipeline order and dependency map

Giulia holds a mapping of pipeline order and dependencies; it belongs in
[`DATA_ARCHITECTURE.md` §4.2](DATA_ARCHITECTURE.md#42-todo-giulia--authoritative-order--dependency-map).
Expected to resolve the `A.n` numbering used in parameter help text, which stages are mandatory, the
recommended outlier-imputation default and the preferred reporting-rate variant.

**Owner:** Giulia. **Source:** DATA_ARCHITECTURE §9 #1.

### <a id="doc-2"></a>DOC-2 · Stamp readmes with the version they describe

To make readme drift detectable, record at the top of each `readme.md` the version it was verified
against. Blocked on deciding *which* version number counts ([OH-2](#oh-2)). A weaker variant is
available today and needs no OpenHEXA change: the commit SHA of the `pipeline.py` last verified
against. Facts: [`DATA_ARCHITECTURE.md`](DATA_ARCHITECTURE.md) §7.2.

**Blocked on:** [OH-2](#oh-2), for the full version. **Source:** CLAUDE.md *Suggestions*.

### <a id="doc-3"></a>DOC-3 · Doc claims found to be out of step with the repo

One claim left, found during the self-sync work, 2026-11-18: the module docstring of
[`snt_workspace_deployer/pipeline.py`](../pipelines/snt_workspace_deployer/pipeline.py) says its
copy of the R half "Replaces the per-pipeline `Pull scripts` toggle". This repo's pipelines have no
such toggle: each copies its own R half on every run
([ADR 0044](decisions/0044-self-sync-replaces-pull-scripts.md)), and the deployer also installs the
shared R library `shared/r/`. Correct it with that pipeline's next code change, then delete this
item.

**Owner:** Giulia.

### <a id="doc-4"></a>DOC-4 · Fill in the ownership tables

Fill in every `_TBD_` in [`OWNERSHIP.md` §2](OWNERSHIP.md#2-pipeline-responsibilities) and
[§3](OWNERSHIP.md#3-cross-cutting-assets). Decide whether a `Backup` column is worth maintaining.

**Owner:** Giulia. **Source:** OWNERSHIP §4.

### <a id="doc-5"></a>DOC-5 · Confirm the licence

[`LICENSE`](../LICENSE) is **MIT**, added provisionally so a public repository is not left
unlicensed. Rationale: maximally permissive, universally understood, and ministries and national
malaria programmes can adapt the code without legal review. Worth discussing:

- **Apache-2.0**: the same permissions plus an explicit patent grant and contribution terms. The
  usual choice for organisation-backed public projects; slightly more paperwork.
- **Consistency with sibling BLSQ repositories** (`openhexa`, `openhexa-toolbox`, `snt_utils`).
  Matching them is probably the strongest argument either way. Not verified.
- **The documentation.** Some organisations license docs separately (CC-BY-4.0). Simpler to keep one
  licence unless someone objects.
- Confirm the copyright holder string and year in `LICENSE`.

**Owner:** Giulia, with the team. **Source:** OWNERSHIP §4.

### <a id="doc-6"></a>DOC-6 · Link a published reference for the SNT method

Neither the README nor the glossary points to an authoritative external description of the SNT
method (WHO subnational-tailoring guidance, a protocol document, or a paper). External readers, such
as epidemiologists reading the R code without workspace access, currently have only this repository.
Add the link to [`README.md`](../README.md) *Start here* and to
[`GLOSSARY.md` §1.1](GLOSSARY.md#11-what-snt-is).

**Owner:** Giulia. **Source:** OWNERSHIP §4.

### <a id="doc-7"></a>DOC-7 · Fill "not recorded" ADR dates from git history

ADRs 0013–0016 and 0019 (originally orchestrator 0004–0007 and 0010) say "Date: not recorded". `git log` on the old `CLAUDE.md` / `README.md`
in the archived predecessor repo `BLSQ/OpenHEXA-WebApp-Diary` may date them. Needs Giulia's OK to run `git log`; update only the
date line, never the decision.

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `DOC-2`.

---

## Questions for the OpenHEXA developers

### <a id="oh-1"></a>OH-1 · Versioning and propagating the R half of each pipeline

OpenHEXA templates carry `pipeline.py` and `requirements.txt` only. In the old repo, notebooks and
`.r` helpers reach a workspace only when an operator runs with `Pull scripts` = ON, so a workspace
can run the newest Python against months-old R with nothing reporting it. This repo's pipelines
copy their own R half from the pipeline zip on every run
([ADR 0044](decisions/0044-self-sync-replaces-pull-scripts.md)), except `shared/r/`
([REL-6](#rel-6)). Under discussion with the OpenHEXA developers.
Facts: [`DATA_ARCHITECTURE.md` §2.2.1](DATA_ARCHITECTURE.md#221-r-is-outside-this-mechanism--the-core-pain-point).

**Source:** CLAUDE.md rule 2; DATA_ARCHITECTURE §9 #2.

### <a id="oh-2"></a>OH-2 · Three different pipeline version numbers

Source, template and workspace versions disagree routinely (a workspace's v1 may be template v5 and
source v11), so "which version is this country running?" has no single answer. Under discussion with
the OpenHEXA developers. Blocks [DOC-2](#doc-2). Facts:
[`DATA_ARCHITECTURE.md`](DATA_ARCHITECTURE.md) §7.1.1.

**Source:** DATA_ARCHITECTURE §9 #3.

### <a id="oh-3"></a>OH-3 · Workspace image: pin a digest, name two packages

Ask the OpenHEXA developers to (a) pin `blsq/openhexa-blsq-r-environment:latest` to a digest, for
reproducibility, and (b) name `data.table` and `rmapshaper` explicitly in the image. The code uses
both, and both currently arrive only as transitive dependencies. Facts:
[`DATA_ARCHITECTURE.md` §7.4](DATA_ARCHITECTURE.md#74-the-workspace-runtime-image).

**Source:** CLAUDE.md *Suggestions*; DATA_ARCHITECTURE §9 #12.

### <a id="oh-4"></a>OH-4 · Ask OpenHEXA for a CLI/SDK webapp deploy command

The CLI deploys pipelines only and the SDK webapp surface is read-only. A request was said to be in
flight but is not tracked anywhere.

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `OH-1`.

### <a id="oh-5"></a>OH-5 · Ask OpenHEXA to allow `workspace { connections }` through the webapp proxy

The proxy refuses `Workspace.connections` and `Connection.{id,name,slug,type}` even with
`USER_READ` ([runtime](OPENHEXA_WEBAPP_RUNTIME.md#allowed_operations-scopes)), so the
DHIS2/custom connection dropdowns never load and users must type a slug. Ask for those fields (no
secret fields) under `USER_READ` or a new scope. Until then the app's text fallback stands; the
dropdown and the "no connection of this type" note activate on their own once the query passes.

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `OH-2`.

### <a id="oh-6"></a>OH-6 · Ask OpenHEXA to allow `PipelineVersion.files` through the webapp proxy

The app shows each pipeline's README for the version deployed in the workspace
([ADR 0025](decisions/0025-readmes-from-deployed-version.md)). It would rather read it straight
from the version's code:

```graphql
query ($id: UUID!) { pipelineVersion(id: $id) { files { name path content encoding } } }
```

`PIPELINES_READ` unlocks the top-level `pipelineVersion`, but its `SCOPE_GRANTS` entry
(openhexa-app `backend/hexa/webapps/scopes.py`) lists only 16 `PipelineVersion` fields (`id`,
`versionNumber`, `parameters`, `config`, …), not `files` or `zipfile`. `FileNode` is granted to
no scope either, so the proxy refuses the whole query. Ask for `PipelineVersion.files` and
`FileNode` (`name`, `path`, `type`, `content`, `encoding`) under `PIPELINES_READ` or a new
read-only scope. A README is no more sensitive than the parameters and config that are already
granted, but `files` also exposes the pipeline's source code, which is the question to put to the
devs. Until then, `create_pipeline_cards` copies each README into the bucket and the app reads it
with `FILES_READ`. If this is granted, the app could read READMEs directly, the copies could go,
and a README would match the deployed version even before the generator re-runs.

**Source:** `snt_webapp_orchestrator` BACKLOG. **Old ID:** orchestrator `OH-3`.

### <a id="oh-7"></a>OH-7 · Getting the workspace token without the UI

The deployer needs the workspace access token in a CUSTOM connection named `openhexa-deploy`, and
today that is a copy-paste ([`bootstrap/openhexa_deployment.md`](bootstrap/openhexa_deployment.md)
§7.3b). The GraphQL API has two untested mutations: `generateWorkspaceToken(slug)` and
`issueWorkspaceToken(workspaceId or slug)`, which returns a JWT with an expiry. Ask: who may call
them; does generating a new token invalidate the old one (which would break the `openhexa-deploy`
connection); can the JWT deploy a pipeline version?

**Source:** Giulia's OpenHEXA deployment notes (local), 2026-09.

### <a id="oh-8"></a>OH-8 · What may a public webapp call through the GraphQL proxy?

[`OPENHEXA_WEBAPP_RUNTIME.md`](OPENHEXA_WEBAPP_RUNTIME.md#allowed_operations-scopes) says public
webapps cannot call the proxy at all. Two observations suggest the rule is narrower: during the
config editor's dataset-write work a public webapp got an HTTP 403 from the proxy, and openhexa-app
`backend/hexa/webapps/scopes.py` defines a scope set for public webapps. Ask the OpenHEXA developers
what a public webapp may call, then correct the runtime doc. Until then both webapps stay private:
the orchestrator, and the config editor
([ADR 0047](decisions/0047-config-editor-publishes-to-snt-configuration.md)).

**Source:** config editor dataset write, 2026-11-26.

---

## Questions for the SNT team (domain)

Every ❓ in [`GLOSSARY.md`](GLOSSARY.md), plus inconsistencies the glossary sweep turned up. Each
needs a person with the domain knowledge, not another pass over the code. When one is answered,
update the glossary entry and delete the item here. **DOM-1 to DOM-16** keep the numbers they had as
GLOSSARY §7.

**Indicator codes whose meaning is unknown**

- <a id="dom-1"></a>**DOM-1** · `CASRECU`: "cas reçus"? How does it differ from `SUSP`? (Empty in all
  five config copies.)
- <a id="dom-2"></a>**DOM-2** · `UTILISATION`: utilisation of *what*, over *what* denominator?
- <a id="dom-3"></a>**DOM-3** · `VAR1`: measles vaccination dose 1 (*vaccination anti-rougeoleuse*)?
- <a id="dom-4"></a>**DOM-4** · `MILDA_VAR`: LLINs distributed at measles-vaccination contacts? If so,
  `MILDA_CPN` and `MILDA_VAR` are the two routine distribution channels, which is worth saying
  explicitly.
- <a id="dom-5"></a>**DOM-5** · `PRESSEV`, `MALSIMP`, `MALSEV`, `CPN`/`CPN1`, `TPI1`/`TPI3`: the
  glossary's proposed definitions come from standard usage, not from anything in the repo. Confirm or
  correct.
- <a id="dom-6"></a>**DOM-6** · `POP_5_36_M`: confirm the band is 5–36 **months** and not years.

**Method provenance**

- <a id="dom-7"></a>**DOM-7** · How closely does the SNT **MAD15 → MAD10 → seasonal5 → seasonal3**
  chain track [Magic Glasses 2](https://github.com/jpainter/MagicGlasses2)? Were the thresholds taken
  from upstream, or chosen here?
- <a id="dom-8"></a>**DOM-8** · What exactly do the **seasonal5 / seasonal3** passes decompose against?
- <a id="dom-9"></a>**DOM-9** · The **PATH** method needs a fuller write-up: rationale for the
  central-80% trim and the deviation multiplier, the stock-out and epidemic rules in epidemiological
  terms, the low-count floors, and a citable reference if one exists. Itemised in
  [`GLOSSARY.md` §4.1](GLOSSARY.md#41-outlier-detection-and-imputation).

**Definitions that affect how results are read**

- <a id="dom-10"></a>**DOM-10** · **EFT** in `ANTIMALARIAL_EFT_RATE`: "effective treatment"? Its
  `LABEL` in the old `SNT_metadata.json` is the only English one in an otherwise French file, which
  suggests it was never finished.
- <a id="dom-11"></a>**DOM-11** · **CSB vs DHS care-seeking**: is the `N3` care-seeking denominator
  meant to be `PCT_PUBLIC_CARE`, some combination, or always an externally supplied national figure?
- <a id="dom-12"></a>**DOM-12** · `GRAY_INDEX`: what MAP delivers in that band, and whether averaging it
  is meaningful.

**Naming problems found during the sweep** (each is a code question, not just a glossary one)

- <a id="dom-13"></a>**DOM-13** · `NON_MALARIA_ALL_CAUSE_OUTPATIENTS` in `snt_dhis2_quality_of_care` is
  a plain sum of `ALLOUT` with no malaria subtraction. Is the name wrong, or the computation?
- <a id="dom-14"></a>**DOM-14** · `ITN_USE_RATE_RATE`: doubled suffix in the old `SNT_metadata.json`.
  Renaming it is operator-visible, so it needs a migration rather than an edit.
- <a id="dom-15"></a>**DOM-15** · `_PREGNANT_WOMAN` (indicator suffix, singular) vs
  `POP_PREGNANT_WOMEN` (population column, plural): the confirmed defect in
  `select_population_column()` ([PIPE-5](#pipe-5)). Fixing the code would also let the glossary state
  one spelling.
- <a id="dom-16"></a>**DOM-16** · `_UNDER5` vs `_UNDER_5` and `_ABOVE5` vs `_ABOVE_5` vary across
  country configs. Is one canonical, or are both genuinely in use in the respective DHIS2 instances?

**Owner:** SNT team / a malaria epidemiologist. **Source:** GLOSSARY §7.
