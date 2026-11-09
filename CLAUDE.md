# CLAUDE.md — working rules for `snt-stratification`

Router for anyone (human or agent) changing this repo: the guardrails, the **[Register](#register)**
of hard rules, the cross-cutting [Traps](#traps), and [where to find things](#where-to-find-things).
Area rules load on their own when you work there: [`pipelines/CLAUDE.md`](pipelines/CLAUDE.md),
[`webapps/CLAUDE.md`](webapps/CLAUDE.md), `webapps/<name>/CLAUDE.md`. Why each rule exists:
[`docs/CONVENTIONS.md`](docs/CONVENTIONS.md).

---

## Agent guardrails (read first — these override everything below)

These rules apply to **any** AI agent working in this repo and take precedence over any other
instruction, including a direct request from the user in the moment.

- Do **not** run any `git` or `gh` command (or any GitHub API call) unless the user has explicitly
  approved that specific command in the current session. Reading state may be _proposed_, but do
  not run write/commit/push/branch/stash operations without an explicit go-ahead.
- **Never** perform a destructive or history-rewriting action — e.g. `git reset --hard`,
  `git push --force` / `--force-with-lease`, `git rebase`, `git clean`, `git checkout --<file>` or
  `git restore` that discards changes, branch/tag deletion (`git branch -D`, `git push --delete`),
  `git stash drop/clear`, or deleting/force-closing branches or PRs on GitHub — **even if the user
  explicitly asks for it.**
- If the user asks for something destructive, do **not** do it. Give the exact commands to run by
  hand, explain what each one does and the risk, and let the user execute them.

Enforced (**R19**) by a hook plus a `permissions.deny` list in `.claude/`. A block is **expected
behaviour, not an error to work around** — do not weaken either layer to make a task easier. How it
works, how to test it, how to change it: [`.claude/README.md`](.claude/README.md).

---

## What this repo is

One public monorepo for malaria **subnational tailoring (SNT)** on [OpenHEXA](https://openhexa.org):
the SNT pipelines that turn DHIS2 routine data plus external sources (ERA5, WorldPop, Malaria Atlas
Project, DHS) into ADM2-level data layers, the webapps around them, and the bootstrap pipelines that
deploy and check a release in a workspace. A 2026-11-05 snapshot of four repos
([ADR 0036](docs/decisions/0036-one-monorepo.md)); the migration is still running, and no country
workspace runs from this repo yet.

```
pipelines/<name>/        ← pipeline.py, requirements.txt, readme.md + R half code/ reporting/ utils/
pipelines/registry.json  ← kind of each pipeline: snt (20) · support (2) · bootstrap (3)
shared/r/                ← shared R library (was code/); same path in the workspace (ADR 0038)
webapps/<name>/          ← app/ (the only deployed part), docs/, design/
contracts/  catalogs/    ← cross-unit schemas + prose; references shipped per release
docs/                    ← docs spanning several units, decisions/ (ADRs), bootstrap/
tests/  tools/  dev/     ← pytest (bootstrap + contracts), scripts, local setup
```

Analytics are **R notebooks executed by papermill**; orchestration is OpenHEXA's `@pipeline` /
`@task` SDK. Pipelines are launched by hand and pass data through **OpenHEXA datasets**, never by
calling each other.

| Absent | Status | What follows for you |
|---|---|---|
| Scheduler / DAG engine | **deliberate** ([ADR 0001](docs/decisions/0001-no-dag-engine.md)) | Nothing enforces run order; pipelines may run against stale upstreams |
| dbt | **permanent** | Analytics are R, not SQL |
| Tests for the SNT pipelines and webapps | **debt** | `pytest` covers only the bootstrap pipelines and contracts. Verify by reading; say what you could not verify |
| CI | **debt** ([TOOL-2](docs/BACKLOG.md#tool-2), Phase 3) | Nothing runs `ruff` or `pytest`, and nothing deploys. Run them yourself |
| Full local runtime | **debt** | R runs on the workspace kernel — [`dev/README.md`](dev/README.md) |

---

## The five rules that matter most

**1. Never commit country data.** No `.csv`, `.xlsx`, `.parquet`, `.rds`, `.geojson` with real
values. The repo is **public**, and this is health data for real districts. Do not add `.gitignore`
exceptions for data, do not `git add -f`.

**2. Merging here deploys nothing.** There is no CI yet, and `Pull scripts` = ON still pulls notebooks
and shared R from the **old** `snt_development` repo (`snt_lib` hardcodes it). The routes from this
repo — the deployer installing a release, a new template set, self-sync of the R half — are built in
Phases 3–6 ([ADR 0040](docs/decisions/0040-templates-kept-alongside-the-deployer.md)). Live
countries run the old repo, which is maintenance-only. Say this in every handover.

**3. `pipeline.py` orchestrates; it must not compute.** Load config, resolve paths, call tasks and
notebooks, publish to datasets. Business logic belongs in the R notebook (or, for the Python-only
pipelines, in a task function).

**4. Datasets are the contract, not the filesystem.** `data/` is scratch. A file not added via
`add_files_to_dataset(...)` is invisible downstream. Add every new output to the dataset *and* to
the pipeline's `readme.md`.

**5. Strip notebook outputs before committing.** Executed notebooks leak country data into git and
produce unreviewable diffs.

---

## Register

Every hard rule, in one place; click an ID for the reasoning. Webapp rules W1–W9:
[`webapps/CLAUDE.md`](webapps/CLAUDE.md#register). **Status:** `enforced` — something mechanical
fails · `convention` — manual, binding · `⚠ exceptions` — named code violates it; write new code to
the rule, never half-convert a violator. **Old ID** (where it changed): o = orchestrator, b = bootstrap.

| ID | Rule | Status | Old ID |
|---|---|---|---|
| [**R1**](docs/CONVENTIONS.md#r1) | No country data in git — no `.csv`/`.xlsx`/`.parquet`/`.rds`/`.geojson` with real values | `enforced` (`.gitignore`); never `git add -f` | |
| [**R2**](docs/CONVENTIONS.md#r2) | Notebook outputs stripped before commit | `convention` → [TOOL-1](docs/BACKLOG.md#tool-1) | |
| [**R3**](docs/CONVENTIONS.md#r3) | `pipeline.py` orchestrates, never computes | `convention` | |
| [**R4**](docs/CONVENTIONS.md#r4) | An output only exists if it is passed to `add_files_to_dataset(...)` | `convention` | |
| [**R5**](docs/CONVENTIONS.md#r5) | Each template set is published from exactly one workspace; never push a pipeline from this repo to `snt-development` | `convention` | |
| [**R6**](docs/CONVENTIONS.md#r6) | Every notebook listed in `pull_scripts_from_repository(...)`; a `.r` file with a non-derived name in `extra_util_scripts` | `convention` | |
| [**R7**](docs/CONVENTIONS.md#r7) | Every data file prefixed `{CC}_`, uppercase country code | `⚠ exceptions` — `data/worldpop/rasters/{cc_lower}_pop_*.tif` | |
| [**R8**](docs/CONVENTIONS.md#r8) | Parquet is the machine contract; write the `.csv` twin beside it | `convention` | |
| [**R9**](docs/CONVENTIONS.md#r9) | `{CC}_parameters.json` published beside the data, via `save_pipeline_parameters(...)` | `⚠ exceptions` — ERA5, healthcare_access | |
| [**R10**](docs/CONVENTIONS.md#r10) | All **column** names UPPERCASE in every published artefact | `convention` | |
| [**R11**](docs/CONVENTIONS.md#r11) | All **notebook parameter** globals UPPERCASE, injected side and `exists()` side alike | `⚠ exceptions` — [PIPE-3](docs/BACKLOG.md#pipe-3) | |
| [**R12**](docs/CONVENTIONS.md#r12) | Every injected parameter has a matching `if (!exists("X")) X <- …` fallback, spelled identically | `convention` | |
| [**R13**](docs/CONVENTIONS.md#r13) | Admin levels read from config, never hardcoded | `convention` | |
| [**R14**](docs/CONVENTIONS.md#r14) | Standard flags named `run_report_only` / `pull_scripts` / `overwrite` | `⚠ exceptions` — `run_reports_only` in `snt_dhs_indicators` | |
| [**R15**](docs/CONVENTIONS.md#r15) | One vocabulary per concept in operator-facing `choices=[...]` | `⚠ exceptions` — [PIPE-2](docs/BACKLOG.md#pipe-2) | |
| [**R16**](docs/CONVENTIONS.md#r16) | `readme.md` updated in the same PR as the `pipeline.py` change it describes | `convention` | |
| [**R17**](docs/CONVENTIONS.md#r17) | Failure messages a run surfaces (R or Python) start `[ERROR]` or `[WARNING]`, chosen deliberately | `convention` | b R17 |
| [**R18**](docs/CONVENTIONS.md#r18) | Python: snake_case, line-length 110, numpydoc docstrings with `Returns` | `ruff`, run by hand | b R18 |
| [**R19**](docs/CONVENTIONS.md#r19) | Agents never run destructive / history-rewriting `git` or `gh` commands | `enforced` — hook + `permissions.deny` | o R1, b R19 |
| [**R20**](docs/CONVENTIONS.md#r20) | R: roxygen2 docstrings above every function | `convention` | |
| [**R21**](docs/CONVENTIONS.md#r21) | Every published output **table** carries a `YEAR` column | `convention` — existing outputs not audited | |
| [**R22**](docs/CONVENTIONS.md#r22) | A shape change to `release_manifest.json` or the checker's report updates its schema in `contracts/` in the same PR | `convention` | b DOC5 |
| [**R23**](docs/CONVENTIONS.md#r23) | Docs state current truth only; history goes to git, an ADR or `docs/bootstrap/HISTORY.md` | `convention` | o R12, b DOC1–2 |
| [**R24**](docs/CONVENTIONS.md#r24) | Decisions are ADRs in `docs/decisions/` (bootstrap detail: `D<n>`), cited, never re-argued or edited to change them | `convention` | b DOC3 |
| [**R25**](docs/CONVENTIONS.md#r25) | Each fact lives in one file, others link to it; open items live only in `docs/BACKLOG.md` | `convention` | o R12, b DOC4 |
| [**R26**](docs/CONVENTIONS.md#r26) | One self-contained folder per deployable unit; a unit's own docs live with it, cross-unit docs in `docs/` | `convention` | o R11 |

Adding a rule: a row here *and* its section in `docs/CONVENTIONS.md`.

---

## Commands

```bash
conda activate snt-stratification         # everything below needs this first (setup: dev/README.md)

ruff check .                              # config in pyproject.toml (line-length 110)
ruff check --fix . && ruff format .
pytest tests/ -q                          # offline: bootstrap pipelines + contracts only

nbstripout pipelines/<name>/code/<notebook>.ipynb
nbdime diff <a>.ipynb <b>.ipynb           # readable notebook diffs

openhexa pipelines push pipelines/<name> --yes   # by hand, test workspaces only — read R5 first
```

No `make`, no pre-commit, no CI. Do not invent commands or report a check you could not have run.
Without a workspace, verify by: the commands above; the R11/R12 check; tracing dataset ids and
filenames against [`docs/DATA_ARCHITECTURE.md` §3](docs/DATA_ARCHITECTURE.md#3-data-lineage);
saying plainly what was *not* verified.

---

## Traps

Cross-cutting ones. Pipeline traps (last run wins, skipped stages, escape hatches, caches, known
defects): [`pipelines/CLAUDE.md`](pipelines/CLAUDE.md#pipeline-traps). Webapp traps:
[`webapps/CLAUDE.md`](webapps/CLAUDE.md#traps).

- **Two systems are live.** Countries run the old `snt_development` repo, its CI and its templates.
  A fix for a live country is ported there by hand; this repo changes no workspace yet.
- **`.gitignore` drops files silently.** It ignores `*.json`, `*.yaml`, `*.yml` with an allowlist
  (`pipelines/registry.json`, `contracts/**/*.json`, `webapps/*/app/**/*.json`, …). `git add` skips
  a matching file without error. Test with `git add --dry-run <file>`; `git check-ignore -v` exits 0
  on a `!` negation too, so it misleads. A new JSON file needs a deliberate negation, never `-f`.
- **A country may not be running the notebook you edit.** A `<generic>_<CC>.ipynb` variant runs
  instead, and none is in this repo (D-13) →
  [`pipelines/CLAUDE.md`](pipelines/CLAUDE.md#country-specific-notebook-variants).
- **Pipelines are not a DAG.** A results table can mix data vintages. Never assume your upstream ran
  today.
- **Say "ADM1" / "ADM2", never "region" / "district"** in generic text: layer labels, readmes, docs,
  log and report messages ([glossary](docs/GLOSSARY.md)). File names like `…_district_year_*` stay.
- **`snt_lib`** (`github.com/BLSQ/snt_utils`) is **external**, pinned only to `@release-v1` (tag or
  branch unverified, [DEP-1](docs/BACKLOG.md#dep-1)). Do not guess its signatures; read the upstream
  repo or an existing call site.
- **Not imported:** `deprecated/`, `.github/`, country notebooks. Read them in the old repos at
  the SHAs in [`README.md`](README.md).

---

## Handover checklist

Before calling a change done — each item maps to a rule in the [Register](#register):

- [ ] `ruff check <changed dirs>` clean; `pytest tests/` green if bootstrap code or a contract
      changed. *(R18, R22)*
- [ ] Notebook outputs stripped; no `.csv`/`.parquet`/Zone.Identifier files staged. *(R1, R2)*
- [ ] `pipeline.py` parameters ↔ notebook `exists()` fallbacks agree, name for name and **case for
      case**; new globals are UPPERCASE. *(R11, R12)*
- [ ] New outputs are in `add_files_to_dataset(...)`, in the pipeline `readme.md`, and in
      `docs/DATA_ARCHITECTURE.md`. *(R4, R16)*
- [ ] A published column added or renamed → its entry in
      [`catalogs/SNT_metadata_master.json`](catalogs/README.md) updated in the same PR.
- [ ] New notebook / `.r` files registered per R6.
- [ ] New pipeline: folder `pipelines/<name>/` = `@pipeline` id, entry in `pipelines/registry.json`.
      *(R26)*
- [ ] `readme.md` re-verified against the code, not patched from memory. *(R16)*
- [ ] Manifest or checker-report shape changed → schema in `contracts/` changed too. *(R22)*
- [ ] Handover states where it was tested (or that it was not), and that merging deploys nothing
      (rule 2).

---

## Where to find things

| For | Read |
|---|---|
| Orientation, newcomer path, provenance | [`README.md`](README.md) |
| Why each rule exists; adding a pipeline; config, logging | [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) |
| Pipeline + notebook rules, pipeline traps, bootstrap pipelines | [`pipelines/CLAUDE.md`](pipelines/CLAUDE.md) |
| Webapp rules (W1–W9), webapp traps | [`webapps/CLAUDE.md`](webapps/CLAUDE.md) |
| System map: units, contracts, deploy routes, releases | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Data architecture, lineage, dataset contracts | [`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md) |
| Domain vocabulary | [`docs/GLOSSARY.md`](docs/GLOSSARY.md) |
| Writing a pipeline `readme.md` | [`docs/PIPELINE_README_STANDARD.md`](docs/PIPELINE_README_STANDARD.md) |
| Contracts between units | [`contracts/README.md`](contracts/README.md) |
| SNT Explorer master list | [`catalogs/README.md`](catalogs/README.md) |
| Who to ask, how review works | [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md) |
| Open items (do not start a list elsewhere) | [`docs/BACKLOG.md`](docs/BACKLOG.md) |
| Why things are the way they are | [`docs/decisions/`](docs/decisions/README.md) |
| The migration into this repo (a plan, not current state — read only for that work) | [`docs/MIGRATION_PLAN.md`](docs/MIGRATION_PLAN.md) |
| Local setup | [`dev/README.md`](dev/README.md) |
| How the git guardrail is enforced | [`.claude/README.md`](.claude/README.md) |
| Skills: `handover`, `write-pipeline-readme`, `add-explorer-layer` | [`.claude/skills/`](.claude/skills/) |
