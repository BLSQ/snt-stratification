# MIGRATION PLAN — moving SNT stratification into one public repo, `snt-stratification`

> **This is a plan, not a description of the current system.** Everything else in `docs/` states how
> things *are*; this file states what we *intend* to do and how far we have got. Do not cite it as
> fact about the running pipelines.
>
> **Living document.** It is public so the whole team can follow the migration. Update the checkboxes,
> the Decision log and the Session log at the end of every working session. Status markers:
> `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped.
> New repo: **`BLSQ/snt-stratification`** (D-6). Owner: Giulia.
>
> **Where it lives:** here, `docs/MIGRATION_PLAN.md` in `BLSQ/snt-stratification`, since Phase 1
> (2026-11-05). It was written in `snt_development`, whose copy is frozen at `94cfc38` and becomes a
> one-line pointer to this one (P1-11).
> **For agents:** read it only when working on the migration. It is not part of the routine reading
> path.
>
> **Working rule:** project knowledge lives **in the repo** (CLAUDE.md, docs, ADRs, BACKLOG), never
> only in someone's local Claude memory.

---

## 1. Context

Today, "SNT stratification on OpenHEXA" lives in 4–5 repos that are tightly coupled but versioned
and documented separately:

| Source repo | What | Maturity |
|---|---|---|
| `BLSQ/snt_development` | ~20 SNT pipelines (`pipeline.py` at the root + R notebooks under `pipelines/<name>/`), shared R `code/`, `catalogs/`, `contracts/`, the release-manifest workflow | Docs: high (Register R1–R22, ADRs 0001–0009, BACKLOG, 3 skills). Tests: none |
| `BLSQ/snt_webapp_orchestrator` | Orchestrator static webapp + the `create_pipeline_cards` pipeline | Docs: high (ADRs 0001–0016, R1–R12, BACKLOG). Already a fresh repo built from a snapshot (ADR 0013) |
| `BLSQ/snt_workspace_bootstrap` | `snt_workspace_deployer`, `snt_pipeline_deployer`, `snt_workspace_checker` | Docs: high (D1–D28, contracts, roadmap). pytest exists. No CI |
| `BLSQ/openhexa-webapps-edit-snt-config-json` | Config-editor webapp (ticket SNT25-661) | **Spec stage only**: `docs/PRODUCT_SPEC.md` + schema analysis docs + a throwaway `prototype/index.html`; `app/` is empty. Its own copy of `SNT_config.skeleton.json`. Its spec §12 lists every upstream dependency |
| `BLSQ/snt_utils` (`snt_lib`) | Python helpers: config loading, `pull_scripts_from_repository`, `save_pipeline_parameters` | **External and pinned in the short term** (managed by a colleague); **moves into the monorepo in the long term** (D-3, §10) |

**Problems this solves:**
- Every cross-repo contract (release manifest R22, pipeline ids ↔ orchestrator map, config skeleton
  ↔ editor) needs paired PRs, and the docs and rules (R17/R18/R19 are copied three times) drift apart.
- The release mechanism (tag → `release_manifest.json` → deployer) is designed for one source repo.
  The multi-source roadmap (bootstrap `roadmap.md` §1) disappears once there is one repo.
- A clean start lets us make breaking changes held back to protect live workspaces (config split,
  dataset-key naming, config as a dataset, report-only semantics, retiring Pull scripts).

**Hard constraints:**
- Existing country workspaces keep working **unchanged**: the old repo, the old template CI and the
  old templates published from `snt-development` all stay in place (D-4).
- The new repo starts as a clean snapshot without history. The old repos stay as backups and are
  archived later (orchestrator ADR 0013 is the precedent).
- Public repo: no country data, no secrets.

**Success:**
- A fresh test workspace can be bootstrapped end to end from a GitHub release of the new repo:
  pipelines, R half, webapps, with a version marker, and the checker reports `match`.
- A second fresh workspace can be set up from the **new template set**. Its pipeline codes equal
  `snt-<name>`, so the deployer and checker can take it over later.
- One CLAUDE.md router, one Register, one BACKLOG and one ADR sequence for everything.

---

## 2. Decision log (agreed)

| ID | Decision | Date |
|---|---|---|
| D-1 | One new public monorepo, built as a clean snapshot (no history). Old repos stay as backups and are archived later | 2026-11-02 |
| D-2 | **One release train.** One tag `vX.Y.Z` = one tested combination of pipelines + webapps + bootstrap. Webapps get a `webapps` section in the manifest and a `version.json` stamped at release time. A webapp-only fix = a patch release (the deployer skips unchanged pipelines, D22) | 2026-11-02 |
| D-3 | **Short term:** `snt_lib` (`BLSQ/snt_utils`, managed by a colleague) stays **external, pinned to a real tag** in every `requirements.txt` (closes DEP-1 for it); changes to it are coordinated cross-repo PRs. **Long term:** it moves into `snt-stratification` as `packages/snt_lib/`, with a companion R package next to it (§10) | 2026-11-02 |
| D-4 | Old `snt_development` goes **maintenance-only**: critical fixes for live countries only, ported by hand; all new work happens in the new repo. Archive once no workspace depends on its template CI or Pull scripts | 2026-11-02 |
| D-5 | Co-locate each pipeline's R half with its `pipeline.py` **only if spike S1 passes**. Otherwise use the fallback layout (§4.3). For S2, the preferred outcome is **self-sync** (option b). **Condition met 2026-11-03:** S1 and S2(b) both passed → co-locate + self-sync | 2026-11-02 (confirmed 2026-11-03) |
| D-6 | Repo name **`snt-stratification`** (dash, matching most BLSQ repos). The conda env follows the same name | 2026-11-02 |
| D-7 | The config editor **is included** from the first snapshot, as `webapps/config_editor/`. Its throwaway prototype goes to `webapps/config_editor/design/`; its `ignore/` (NER draft configs) is **not** carried over | 2026-11-02 |
| D-8 | Tag numbering starts from scratch (e.g. `v0.1.0`; first production release `v1.0.0`). The old repo's tags are tests only, so no live workspace's marker can collide | 2026-11-02 |
| D-9 | **Repo path = workspace path** for every file that lands on the workspace filesystem. No mapping layer. The shared R library is renamed `code/` → **`shared/r/`**, in the repo and in the workspace (§4.2) | 2026-11-02 |
| D-10 | **Docs placement rule:** a unit's own docs live with the unit (`webapps/<name>/{docs,design}/`, beside the deployable `app/`; a pipeline's `readme.md`); docs spanning several units live in `docs/`; contract prose lives in `contracts/<name>/` (§4.1) | 2026-11-02 |
| D-11 | **One config skeleton:** the `snt_development` copy becomes the single copy (`contracts/snt_config/`), and every empty single value is written as **`null`**, the pipelines' convention. The editor's `""` for empty strings changes to `null` | 2026-11-03 |
| D-12 | **Report-only fix** (was OD-7): the orchestrator reads the run's own `config.run_report_only` through the proxy (`PIPELINES_READ`, proven by S4) and counts only full runs as "processed". No `RUN_MODE` in `{CC}_parameters.json` | 2026-11-03 |
| D-13 | **Public-import scope:** Jira links and Bluesquare dev-workspace slugs (`snt-development`, `snt-development-sandbox`, `snt-testing`, `snt-app-dev`) are **kept**. **Country-specific notebooks (`*_<CC>.ipynb`, plus the un-suffixed `NER_pyramid_format.ipynb`) are left out.** They stay findable in the old `snt_development` repo at the commit SHA in the provenance table (it stays readable after archiving), and in the country workspaces themselves. How they are versioned in the future is OD-10 | 2026-11-03 |
| D-14 | **One ADR sequence** (was OD-5), in `docs/decisions/`. `snt_development` ADRs keep 0001–0009 (the most cited). The orchestrator's 0001–0016 follow as 0010–0025, then the bootstrap D-entries that record an architectural decision; the new ADRs come after them. Every imported ADR gets an "Originally: `<repo>` ADR NNNN / D<n>" line, and `docs/decisions/README.md` holds the mapping table. Bootstrap D-entries that are only implementation detail stay in `docs/bootstrap/decisions.md` | 2026-11-06 |
| D-15 | **No CODEOWNERS for now** (was OD-8): ADR 0005 stands. Giulia discusses per-area review with the team later; tracked in the BACKLOG | 2026-11-06 |
| D-16 | **Merged Register IDs.** R1–R22 keep their IDs (cited in code and notebooks). Rules the three repos share (git guardrail, `[ERROR]`/`[WARNING]`, Python style) appear once, as R17–R19. Webapp-only rules get `W<n>` in `webapps/CLAUDE.md`. The doc-hygiene rules (bootstrap DOC1–5, orchestrator R12) merge into root rules from R23 on. Rules for the bootstrap pipelines go in `pipelines/CLAUDE.md`: no `CLAUDE.md` inside a pipeline folder, because every `.md` there ships in the pipeline zip. Every renumbered rule keeps its old ID in an "old ID" column | 2026-11-06 |
| D-17 | **Bootstrap pipelines reach a workspace as OpenHEXA templates published on each full release, and the deployer also updates them, never downgrading** (was OD-4). Users never manage a workspace with the `openhexa` CLI (too technical), so templates and the bootstrap pipelines themselves are the only realistic routes (Giulia, 2026-11-12). (1) On a **full** release only (never a pre-release), `release.yaml` pushes `snt_workspace_deployer`, `snt_pipeline_deployer` and `snt_workspace_checker` from the new templates publishing workspace (ADR 0041), which publishes their template versions; a workspace installs them once from the template. So a workspace's deployer is the latest full release, never older than the release it deploys. (2) They are in the release manifest as `kind: bootstrap`. The deployer deploys them **only when the target tag is the latest full release or newer** (an rc); for an older target it skips them with an `[INFO]`, so it never replaces itself with an older, possibly buggy copy. (3) The deployer must read every manifest `schema_version` from 2 on, or refuse an unknown one with a clear `[ERROR]`. (4) ADR 0040's rule ("never the same pipeline from a template and the deployer") is narrowed to `snt` and `support` pipelines, whose R half the deployer installs with them; for bootstrap pipelines both routes deliver the same code from the same tag. Proven by spike S6 ([Phase 3 findings](#phase-3-findings)). Supersedes ADR 0029; ADR 0037 (one release train) stands. Recorded as ADR 0042 (Phase 3, commit 2). Until the publishing workspace exists, maintainers push by hand: there are no users yet, so that is not a gap | 2026-11-12 |
| D-18 | **Releases are tested as pre-releases of this repo** (was OD-6). A test release is a GitHub release of `BLSQ/snt-stratification` marked pre-release (`v0.x.y`, or `vX.Y.Z-rc.N` before a full release), deployed into a test workspace by typing its tag. `snt_development_sandbox` is no longer used for testing releases, and the bootstrap pipelines' `github_repo` default becomes `BLSQ/snt-stratification`. The deployer and the checker already leave pre-releases out unless one is typed or is the target (D27) | 2026-11-13 |

## 3. Open decisions (owner: Giulia unless stated)

**When do they need an answer?** Only when the phase in the "Blocks" column starts. None of them
blocks Phase 0 or Phase 1. Settle each one at the start of the session that begins the phase it
blocks, and move it to the Decision log.

| ID | Question | Recommendation / current leaning | Blocks |
|---|---|---|---|
| OD-9 | Retiring Pull scripts | **S2b passed (2026-11-03):** self-sync works, so Pull scripts can go for both routes. Still open: the S2b sub-questions (§4.3), in particular the per-run escape hatch | Phase 6 |
| OD-10 | **How to version country-specific notebooks, and analyst-edited ones** (raised 2026-11-03). Today nothing versions `_<CC>` variants, and no route delivers them to their country. Analysts also edit notebooks in their workspace, and updates (templates, deployer, self-sync) must not silently overwrite those edits. We need one system that keeps good practice (versioned, reviewable, no country data in the public repo) and still lets users run what they edited | No leaning yet. Constraints so far: country variants are not in the public repo (D-13); self-sync skips `_<CC>` files and archives what it replaces (S2b). Inputs: OD-9's escape hatch, and possibly a private per-country repo or dataset | None (not scheduled). Must be settled before Pull scripts is retired (OD-9) |

---

## 4. Target structure of the new repo

### 4.1 Tree

```
snt-stratification/
├── CLAUDE.md                 ← router: guardrails, Register (merged), Traps, "Where to find things". ≤15 KB
├── README.md                 ← human overview + newcomer path
├── LICENSE                   ← confirm licence (DOC-5)
├── pyproject.toml            ← one ruff + pytest config for all Python (line-length 110, numpydoc)
├── .gitignore                ← allowlist for JSON (see Traps §7)
├── .claude/
│   ├── settings.json         ← R19 hook + permissions.deny (merged from the 3 repos)
│   ├── hooks/                ← block-destructive-git (one implementation)
│   ├── README.md             ← how the guardrail works
│   └── skills/               ← handover, write-pipeline-readme, add-explorer-layer (+ new: release, deploy-webapp)
├── .github/
│   ├── workflows/
│   │   ├── ci.yaml                     ← PR: ruff, pytest, schema validation, link check (TOOL-2/3/5)
│   │   ├── release.yaml                ← on release: build manifest v2, slim release tarball, stamped webapp zips;
│   │   │                                 on a FULL release only: bootstrap pipelines → templates (D-17)
│   │   └── push_templates.yaml         ← SNT + support pipelines → NEW templates workspace; ONE matrix job (replaces 20 copies)
│   └── pull_request_template.md
│
├── pipelines/                ← flat: one folder per pipeline, folder name = @pipeline id (ADR 0015 join key)
│   ├── CLAUDE.md             ← pipeline + notebook rules (lazy-loaded), R11/R12, country variants
│   ├── registry.json         ← name → kind (snt | support | bootstrap) + deploy route. CI fails on an
│   │                           unregistered folder or a registered folder that is missing
│   ├── snt_dhis2_extract/    ← kind: snt (all ~19 SNT pipelines alike)
│   │   ├── pipeline.py   requirements.txt   readme.md
│   │   ├── code/*.ipynb        ┐ co-located R half (D-5, if S1 passes).
│   │   ├── reporting/*.ipynb   │ SAME path in the workspace (D-9):
│   │   └── utils/*.r           ┘ <ws>/pipelines/snt_dhis2_extract/code/…  (= today's workspace layout)
│   ├── create_pipeline_cards/    ← kind: support (also snt_metadata_json_trim, future utility pipelines)
│   ├── snt_workspace_deployer/   ← kind: bootstrap (also snt_pipeline_deployer, snt_workspace_checker)
│   └── …
│
├── shared/
│   └── r/                    ← shared R library (today's code/*.r). SAME path in the workspace: <ws>/shared/r/
│
├── packages/                 ← LONG TERM only (§10), not created now: snt_lib (Python), companion R package
│
├── webapps/
│   ├── CLAUDE.md             ← webapp-wide rules (static bundle, no secrets, proxy scopes)
│   ├── orchestrator/
│   │   ├── CLAUDE.md         ← app-code rules (bundle, i18n, escaping)
│   │   ├── app/              ← THE deployable bundle; release.yaml zips only this folder (+ stamped version.json)
│   │   ├── docs/             ← PRODUCT_SPEC, DEPLOYMENT, research/ (if it passes the public audit)
│   │   └── design/           ← wireframes, grid editor, map preview (not deployed)
│   └── config_editor/
│       ├── CLAUDE.md         ← the editor's rules (from its current CLAUDE.md)
│       ├── app/              ← empty until the editor is built
│       ├── docs/             ← PRODUCT_SPEC, EXTERNAL_CHECKS
│       └── design/           ← the throwaway prototype (prototype/index.html)
│
├── contracts/                ← every cross-unit schema, one README index
│   ├── release_manifest.schema.json   (v2)   status_report.schema.json   snt_release_marker.md
│   ├── snt_config/           ← THE skeleton (one copy, ends the editor's vendored copy) + snt_config.schema.json (CFG-3)
│   │   │                       + the contract prose: config_analysis_notes.md, config_field_matrix.md (from the
│   │   │                       editor repo; they describe what pipelines AND the editor must agree on)
│   │   └── fixtures/         ← conformance cases (valid + one per blocking rule) run by BOTH the editor's JS
│   │                           validator and snt_lib's validate_config() — editor spec §12.2 option 2
│   └── orchestrator/         ← pipeline_map, descriptions, cards schemas
├── catalogs/                 ← universal references shipped per release: SNT_metadata_master.json,
│                               later snt_datasets.json (fixed dataset ids, CFG-1) and the other fixed config parts
│
├── docs/                     ← ONLY docs that span several units (see the placement rule below)
│   ├── ARCHITECTURE.md       ← NEW system map: units, contracts, deploy routes, data flow (1 page + links),
│   │                           incl. "where docs live" (the placement rule)
│   ├── DATA_ARCHITECTURE.md  CONVENTIONS.md  GLOSSARY.md  OWNERSHIP.md  PIPELINE_README_STANDARD.md
│   ├── RELEASES.md           ← release train, tag rules, manifest, how to cut a release, rollback
│   ├── OPENHEXA_WEBAPP_RUNTIME.md ← platform facts used by both webapps AND the bootstrap pipelines
│   ├── BACKLOG.md            ← ONE list, area-prefixed IDs (see §5 Phase 2)
│   ├── MIGRATION_PLAN.md     ← this plan, until the migration is done
│   ├── decisions/            ← ONE ADR sequence + mapping table of imported ADRs
│   └── bootstrap/            ← deployer.md, checker.md, decisions.md (D1–D28 detail): shared by the three
│                               bootstrap pipelines, so not one pipeline's readme
├── reference/openhexa/       ← schema.generated.graphql (used by webapps AND bootstrap; grep it, don't read it whole)
├── tools/                    ← build_manifest.py (from the yaml heredoc), check_links.py, notebook_drift.py
├── tests/                    ← pytest: contracts, manifest builder, deployer/checker helpers
├── dev/                      ← environment.yml (ONE conda env: snt-stratification), setup README
└── ignore/                   ← git-ignored: plans, scratch, spikes
```

**Where docs live (placement rule):** *a unit's own docs live with the unit; docs that span several
units live in `docs/`.*
- **Webapp:** `webapps/<name>/docs/` and `design/`, beside its `app/` bundle. Only `app/` is deployed,
  so docs can never leak into the bundle.
- **Pipeline:** its own doc is `readme.md` (the operator contract, deployed with the zip, ADR 0025).
  Pipelines get **no `docs/` subfolder**: the pipeline zip includes every `.md`, so longer design
  notes go in `docs/<area>/` when they cover several pipelines (as `docs/bootstrap/` does).
- **Contract:** the prose sits next to its schema in `contracts/<name>/`.
- **Several units, or the whole system:** `docs/`.
- No top-level `design/`. The design material of each webapp lives with that webapp.

**Not carried over:** `deprecated/` from every repo (links to it are pinned to the source commit,
like ADR 0022), empty `__pycache__`-only folders (`snt_workspace_check/`, `snt_workspace_manager/`),
and `snt_assemble_results`.

### 4.2 Repo path = workspace path (D-9)

The deployer already copies each file to its repo-relative path, and the checker's model is "workspace
path = repo path". We **keep that model** and choose the repo layout so it holds:

| Repo path | Workspace path | Change vs today's workspaces |
|---|---|---|
| `pipelines/<name>/{code,reporting,utils}/…` | `pipelines/<name>/{code,reporting,utils}/…` | none |
| `shared/r/*.r` | `shared/r/*.r` | **renamed** from `code/` — every notebook's `source(…/code/…)` changes once |
| `pipelines/<name>/` (zip) | pipeline code `<name>` with `_`→`-` | none (ADR 0015 join key kept) |
| `webapps/<name>/*` | not on the filesystem: webapp files (manifest `webapps` section, Phase 7) | — |

That is why `pipelines/` is **flat**: kind folders (`pipelines/snt/<name>/`) would push the kind into
every workspace path and change the layout analysts know. The kind lives in `pipelines/registry.json`
and in the manifest instead.

**Manifest v2** stays close to v1: `schema_version: 2`, `version`, `repo`,
`pipelines: {<name>: {path: "pipelines/<name>", kind, code, zip_files[]}}`, `files: {<path>: sha256}`
(unchanged meaning: path = repo path = workspace path), `filesystem_files: [<path>]` (added
2026-11-12: a notebook now ships in its zip *and* to the filesystem, so the route can't be read from
the path), `webapps: {<name>: {path, files{}, version}}`, `repository_files`. The authority is
[`contracts/release_manifest.schema.json`](../contracts/release_manifest.schema.json). The deployer's `split_manifest()` and the checker's `parts[0]` checks move to
"under `pipelines/<name>/`". The schema, the builder (`tools/build_manifest.py`), the deployer and the
checker change **in the same PR**, which is the monorepo's main benefit.

**Watch for:** anything that hardcodes `code/` as the shared-R path. That includes the notebooks, the
`.r` utils, `snt_lib` (`pull_scripts_from_repository`, and possibly path helpers) and the checker's
scan exclusions. Grep for all of these in Phase 1. If `snt_lib` hardcodes it, a pinned `snt_lib`
release is a prerequisite of the rename (D-3). → **Checked 2026-11-05:** `snt_lib` does not, so no
release is needed. The list of references is under Phase 1, "Facts checked".

### 4.3 R-half layout — spikes first (D-5)

- **S1 — does `openhexa pipelines push` handle a pipeline folder with `code/*.ipynb` + `utils/*.r`
  subfolders?** The bootstrap docs say the SDK's `generate_zip_file()` recurses and keeps
  `.ipynb`/`.r`. Check: push a toy pipeline to a test workspace, then read the version zip (the
  checker already reads `currentVersion.zipfile`). Also check zip size and push time with the real
  notebooks.
- **S2 — can a running pipeline use notebooks from its own bundle?**
  - (a) Does papermill find the R kernel when the notebook path is relative to `__file__`?
  - **(b) ★ PREFERRED** — can `pipeline.py` *self-sync*? On start it copies bundled notebooks and
    `.r` files to the workspace filesystem when they are missing or older (archiving the replaced
    copy, as the deployer does), and never touches `_<CC>` variants.
  - (b) would retire Pull scripts for **both** routes and still leave notebooks on the filesystem for
    the OH UI. Test (b) first; test (a) only if (b) fails.
  - Open sub-questions for (b): how "older" is decided (hash vs the version's own manifest, never
    mtime); whether `shared/r/` travels inside every pipeline zip (duplicated) or is synced by one
    pipeline only; and a per-run escape hatch for an analyst who edited a notebook on purpose.
- **Outcomes:**
  - S1 fails → **fallback layout**: `pipelines/<name>/` holds the Python only, and the R half lives
    in a parallel tree. The parallel tree must still sit at a path equal to its workspace path (D-9),
    which means today's split layout under a new root. Nothing else in this plan changes.
  - S1 passes and S2(b) fails → co-locate. The bundled copy is inert, and the filesystem copy is
    delivered by the deployer (or by Pull scripts for template users).
  - Both pass → co-locate plus self-sync (OD-9).

---

## 5. Phases

Each phase ends in reviewable PRs. Nothing touches a live country workspace. All OpenHEXA work happens
in **new test workspaces** (names TBD, e.g. `snt-mono-test`, `snt-mono-templates`).

### Phase 0 — Read, spike, decide (no new repo yet)
- [x] Read the config editor's docs (2026-11-02): spec stage, no app code. It vendors the skeleton,
      reimplements `validate_config()` in JS, and targets `configuration/SNT_config.json` with
      drafts in `configuration/snt_config_history/`, with a `DatasetStore` (`SNT_CONFIGURATION`) as
      the long-term goal. → see Phase 5 sequencing note.
- [x] Diff the editor's skeleton against `snt_development/contracts/snt_config_json/SNT_config.skeleton.json`
      (`""`/`null` placeholder differences are known). Decide which one becomes the single copy.
      → 2026-11-03, D-11; see [Phase 0 findings](#phase-0-findings).
- [x] Spike S1 (push a nested toy pipeline, inspect the zip). → **passed** 2026-11-03.
- [x] Spike S2: self-sync (b, preferred) first, bundle execution (a) only as a fallback. → **both
      passed** 2026-11-03.
- [x] Spike S3 — **template code derivation.** In a scratch workspace, publish a template, create a
      pipeline from it, and record how the code is derived (from the template name? from the pipeline
      name?). Goal: the new templates produce code `snt-map-extracts`, not `b-2-map-extracts`.
- [x] Spike S4 — can the orchestrator read `PipelineRun.config` (the run's `run_report_only` value)
      through the webapp proxy with `PIPELINES_READ`? Grep `reference/openhexa/schema.generated.graphql`
      first. → **yes**, 2026-11-03.
- [ ] Spike S5 (optional, Phase 7 input) — `updateWebapp(files:)` with a CUSTOM-connection token.
- [x] Pre-publication audit list (first pass done 2026-11-03; second pass **passed** 2026-11-05, P1-7; see findings): which files in the source trees are unfit for a public repo? Known
      candidates: the persona questionnaire (`docs/research/personas/…`, answers from real people),
      country-specific `_<CC>` notebooks with DHIS2 UIDs, workspace slugs, Jira references,
      `ignore/` content (incl. the editor's NER draft configs).

#### Phase 0 findings

Spike code lives in `snt_development/ignore/spikes/` (git-ignored, throwaway); only the results are
recorded here. Test workspaces: `snt-testing` (runs) and `snt-development-sandbox` (template publishing).

**Skeleton diff (2026-11-03).** The editor's copy (`docs/SNT_config.skeleton.json`, 2,180 B) is
**older** than `contracts/snt_config_json/SNT_config.skeleton.json` (2,630 B). Every structural
difference is resolved in favour of the `snt_development` copy by the pipeline code:

| Path | `snt_development` | editor | Which is right |
|---|---|---|---|
| `SNT_DATASET_IDENTIFIERS.SNT_POPULATION_USER_PROVIDED` | present | missing | dev — read by `snt_user_population` |
| `SNT_DATASET_IDENTIFIERS.SNT_RESULTS` | missing | present | dev — retired with `snt_assemble_results` (ADR 0006) |
| `DHIS2_REPORTING_RATES.REPORTING_INDICATORS` | `{ACTUAL_REPORTS, EXPECTED_REPORTS}: null` | missing | dev — read by `snt_dhis2_extract` (`pipeline.py` ~l.375) |
| `DHIS2_REPORTING_RATES.REPORTING_DATASETS` | one example entry (`DATASET: null`, `METRICS`) | `[]` | either; dev's shows the entry shape |
| `SNT_CONFIG.{COUNTRY_CODE, COUNTRY_NAME, DHIS2_ADMINISTRATION_1/2}` | `null` | `""` | known placeholder difference — **convention to settle** |

Key order is otherwise identical. **Decided (D-11):** the `snt_development` copy becomes the single
copy at `contracts/snt_config/` (Phase 1), with `null` for every empty single value. The editor's
"emit `""` for empty strings" rule then changes to `null` (its rule 4 already treats `null` as empty).
The conformance fixtures (Phase 3) confirm `validate_config()` accepts it.

**S1, local half (2026-11-03).** `openhexa` SDK 2.22.7, `openhexa/cli/api.py::generate_zip_file()`:
it recurses (`glob("**/*")`) and keeps relative paths, so `code/`, `reporting/`, `utils/` and deeper
folders all go into the zip. Only files with these extensions are kept: **`.py .ipynb .txt .md .r .sql`**.
Consequences:
- **`.json` never travels in a pipeline zip.** A bundled hash manifest or config for self-sync (S2b)
  must be `.txt`/`.py`, or be computed at run time.
- Only `<dir>/workspace` and virtualenvs are excluded. **`.gitignore` is not respected**: a local
  `ignore/` subfolder with executed notebooks ships if it exists. Example:
  `pipelines/snt_dhis2_formatting/reporting/ignore/` (19 MB locally) made a 12.6 MB zip. CI pushes
  from a clean checkout so it is not affected, but anyone pushing by hand from a working tree is.
- Size, with every real pipeline's R half copied into its folder (clean tree, no `ignore/`): every
  zip is 10–56 KB. Size is not a concern.

**S1 + S2, on OpenHEXA (2026-11-03, `snt-testing`, toy `spike_monorepo_layout`, 4 runs).**
- **S1 passed.** The runner unpacks the whole nested zip at `/home/jovyan/pipeline` (= the folder of
  `__file__`): `code/`, `reporting/`, `utils/` and `_shared/r/`, all 7 files. The cwd is
  `/home/jovyan`, the workspace is `/home/hexa/workspace`, and the bundle folder is writable.
- **S2b (self-sync) passed.**
  - First run: copied the 4 missing files, then ran the **synced** notebook with the `ir` kernel
    (R 4.5.3). The notebook sourced both the pipeline's own `utils/` and the `shared/r` stand-in.
  - Second run, after a simulated analyst edit and a `spike_BFA.ipynb` variant: replaced exactly the
    edited file (hash differed), archived the old copy to `_archive/<stamp>/`, left 3 files unchanged,
    and **left the `_BFA` variant untouched**.
  - The archive stamp is in UTC (container clock).
- **S2a (bundle execution) passed as well.** Papermill ran `/home/jovyan/pipeline/code/spike.ipynb`
  directly, and it sourced the `.r` files from the bundle.
- **Trap for both:** R's working directory is `/home/jovyan`, *not* the notebook's folder. Notebooks
  must build every path from an injected root (as the SNT notebooks already do from
  `SNT_ROOT_PATH`). A `source("utils/x.r")` relative to the notebook's own folder will fail.
- **Still open (S2b sub-questions, settle in Phase 1/6):**
  - "older" was decided by sha256 against the bundle, which works. Consequence: any edit an analyst
    makes to a *generic* notebook is archived and overwritten on the next run, so the per-run escape
    hatch is required. It is implemented (`skip_sync`) but has not been run.
  - `shared/r/`: duplicate it in every zip (as tested) or have one pipeline sync it.

**S4 passed (2026-11-03, orchestrator in `snt-testing`).** The query
`pipelines{runs{id status config}}` through the webapp proxy returns each run's `config`, including
`run_report_only`. `PIPELINES_READ` is enough → OD-7 needs no `RUN_MODE`.

**S3 (2026-11-03, published from `snt-development-sandbox`, installed in `snt-testing`).** The publish
UI has **no code field**. A template named `SNT Spike Template` produced pipeline code
**`spike-monorepo-layout`**. So the code comes from the **source pipeline** (its code
`spike-monorepo-layout`, which here equals the `@pipeline("spike_monorepo_layout")` id), **not from
the template name**. If that code already exists, the new pipeline gets a random suffix:
`spike-monorepo-layout-599458`, `-2ab2b6`, …
- **For the new templates (Phase 6):** the source pipelines in the publishing workspace must
  already have the code `snt-<name>`. The template's display name can be anything.
- **For the deployer/checker:** a template-created pipeline can have the code `snt-<name>-<6 hex>`,
  so matching on the code must accept that suffix (or report it).
- The old `b-2-map-extracts` codes are explained if the source pipelines in `snt-development` carry
  those codes. Not verified.
- Not separated by this test: whether the code comes from the source pipeline's code or from its
  `@pipeline` id. Both were the same here.

**Pre-publication audit (2026-11-03, first pass).** A text scan of the four local source trees.
It found no credentials, `.env` files or raw country data files. The UID scan only catches 11-character
tokens that mix upper case, lower case and digits, so a second pass is needed after the snapshot copy.
**The import is a file copy, so `.gitignore` does not protect it**: the copy step itself must leave out
`ignore/`, `deprecated/`, `.ruff_cache/`, `.pytest_cache/`, `__pycache__/` and `*:Zone.Identifier`.

| Verdict | File(s) | Why |
|---|---|---|
| **leave out** | `snt_development/pipelines/snt_dhis2_extract/code/NER_pyramid_format.ipynb` | NER notebook *without* the `_NER` suffix: 14 org-unit-group UIDs + a Jira link |
| **leave out** | `…/snt_dhis2_formatting/country_specific/snt_dhis2_formatting_pyramid_BDI.ipynb` | Facility UIDs next to facility names |
| **leave out** | `…/pipelines/snt_dhis2_outliers_{detection,removal_imputation}/code/*:Zone.Identifier` | Windows metadata with a personal email in notebook URLs |
| **leave out** | orchestrator `docs/research/personas/persona_questionnaire_answered-20260713.md` | Real people's answers on internal strategy |
| redact | `…/snt_dhis2_extract/utils/snt_dhis2_extract_report.r` | Shared helper with a NER-only fix: 7 facility UIDs + real coordinates → move to a NER-only file that is not imported |
| **leave out** (D-13) | Every `*_<CC>.ipynb`, e.g. `…/snt_dhis2_incidence/country_specific/snt_dhis2_incidence_NER.ipynb`, `…/snt_seasonality_rainfall/code/snt_seasonality_rainfall_NER.ipynb` | Country variants are not imported. These two also held Jira refs, a Google Sheets link, a live workspace URL (`xxx-snt-process`) and 1 UID |
| done | `…/snt_dhs_indicators/code/snt_dhs_vaccination_computation.ipynb` | Had saved outputs in 3 cells (dataset version name, COD shapes size). Stripped on `main`, 2026-11-03 |
| redact | 2 notebooks (`reporting_rate_dataset`, `outliers_imputation_path`), 1 UID each in a comment | Replace with a placeholder |
| redact | editor `docs/{config_field_matrix,config_analysis_notes,PRODUCT_SPEC}.md`, `prototype/index.html` | Real UIDs from country configs used as examples (18 in total), bucket name `snt-xxx-files` |
| redact | Live country workspace slugs: `xxx-snt-process` (`snt_metadata_json_trim/readme.md`), `xxx-snt-process` (orchestrator `BACKLOG.md`, a wireframe) | Live country workspaces |
| ok (D-13) | Jira refs (`bluesquare.atlassian.net/browse/SNT25-*`), about 30 across all four repos | Kept |
| ok (D-13) | Bluesquare dev-workspace slugs (`snt-development`, `snt-development-sandbox`, `snt-testing`, `snt-app-dev`), about 25 mentions | Kept |
| ok (public by choice) | Team-glossary Google Sheets link, shared as "anyone with the link" (`docs/GLOSSARY.md`, `snt_dhis2_incidence.ipynb`) | A public reader can open it. Kept: the sheet may be public (Giulia, 2026-11-03) |
| ok | Owner names (Giulia / `@sPuntinG`) in OWNERSHIP, ADRs; `secrets.OH_TOKEN` references in workflows; dummy `mario.rossi@example.org` | — |

Checked 2026-11-03 (`git ls-files`): the `Zone.Identifier` files are **not tracked** (they exist only
locally). `snt_dhs_vaccination_computation.ipynb` was **tracked with its outputs** (R2 broken on
`main`). It was stripped with `nbstripout` and merged to `main` on 2026-11-03 (branch
`fix/strip-dhs-vaccination-outputs`).

**Second pass (2026-11-05, P1-7): passed.** A scan of the staged `tree/` (289 files), after the
leave-outs and redactions:
- Notebooks with outputs: 0. `snt_seasonality_rainfall_report.ipynb` had only a stray
  `execution_count` on `main`, with no output; stripped on import, no fix needed at the source.
- UID-shaped tokens (mixed case with a digit): 0 outside `orchestrator_wireframe_cockpit_narrative.html`.
  Its 345 hits are all inside embedded assets: 3 gzipped JS bundles (a generated runtime, React,
  ReactDOM; decompressed and scanned: no slug, e-mail or UID) and 12 woff2 fonts. Single-case hits
  are false positives (`dodgerblue4`, `geoalchemy2`, fragments of the encoded assets).
- Editor UIDs: 13 distinct at the source, all redacted. The "18" in the table above adds up
  per-file counts, and the same UID appears in several files.
- E-mail addresses: only `git@github.com` (pip URLs) and the dummy `mario.rossi@example.org`.
- Secrets: none. Live workspace URLs or `<cc>-snt-process` slugs: none left. Google links: only the
  team glossary (kept, see the table).
- Decimals with 6+ places: papermill timestamps in the cell metadata of the 4 reporting-rate
  notebooks, not coordinates and not data.
- The only binary, `webapps/orchestrator/design/pipeline_map_20260625.png`, is a dependency diagram
  of pipeline names.

Residual risk, accepted: a UID made only of letters cannot be told apart from a word by a regex.

### Phase 1 — Snapshot import + layout (behaviour-neutral)

**Outcome:** `BLSQ/snt-stratification` holds every source tree in the §4.1 layout, landed through
**one PR** (branch `phase-1/snapshot-import`), plus one small PR in `snt_development` that turns this
file into a pointer. No pipeline, workflow or workspace behaviour changes. The runbook below was
written on 2026-11-05. Follow it in order and tick each step. **Agents:** run no `git`/`gh` command
yourself (R19). Give Giulia the exact commands.

**Rules for this phase**
- **Export with `git archive <sha>`**, never by copying a working tree. It exports tracked files only,
  so `ignore/`, `__pycache__/`, `*:Zone.Identifier` and executed notebooks under `ignore/` stay out.
  It is read-only: it changes nothing locally or on GitHub (it is unrelated to archiving a repo).
- **Remove everything that must not be public *before* the import commit**: leave-outs, redactions,
  notebook outputs. History is permanent. A later "remove" commit does not unpublish anything.
- **Import no `.github/` folder.** The old `push_snt_*.yaml` deploy to `snt-development`. Phase 3 reads
  `generate_manifest.yaml` at its provenance SHA.
- **Merge the PR with "Create a merge commit"**, not squash. The import commit (files exactly as at
  the source SHA, at their new path) must stay separate from the edits made after it.
- Keep source file names. Renames beyond the mapping below wait for Phase 2.
- If a source repo's `main` moves after P1-5, redo P1-5 → P1-7.

**Facts checked 2026-11-05** (they settle §4.2 "Watch for"):
- `snt_lib` 0.23.0 does **not** hardcode the shared root `code/`. Its only `"code"` is the
  per-pipeline `pipelines/<name>/code/` (`pull_scripts_from_repository`), which does not move. So
  **the rename needs no `snt_lib` release**.
  - ⚠️ **Corrected 2026-11-09: this is wrong for `Pull scripts`.** The `pull_scripts_from_repository`
    Giulia pasted (from `snt_lib`; exact version not recorded, every `requirements.txt` pins
    `@release-v1`) hardcodes the shared files: it copies `<repo>/code/snt_{palettes,report,utils}.r`
    to the workspace's `code/`, creates that folder, and defaults `repo_name` to `snt_development`.
    No pipeline here passes `repo_name`, so `Pull scripts` = ON still pulls notebooks *and* shared
    R from the old repo, which are consistent with each other: nothing breaks today. But pointing
    `Pull scripts` at this repo needs a `snt_lib` release that reads `shared/r/` (→ Phase 6).
- Shared-R references to change (commit 5):
  - About 33 notebooks and `.r` files build `file.path(ROOT_PATH | SNT_ROOT_PATH, "code", …)`, either
    in `source(… "snt_utils.r" | "snt_report.r" | "snt_palettes.r")` or in `CODE_PATH <- …`.
  - `snt_dhis2_extract/pipeline.py` creates the workspace folder `"code"` (`folders_to_create`,
    ~l.1465).
  - `snt_pipeline_deployer` mentions `code/` in docstrings and log messages. Its logic
    (`parts[0] != "pipelines"`) changes in Phase 4.
- The old `snt_development/.gitignore` ignores `**/[Tt]est*`, which would hide `tests/`. It also
  ignores every `*.json`, `*.yaml` and `*.yml`.
- `pipelines/snt_dhis2_outliers_{detection,removal_imputation}/` and the root `snt_workspace_check/`
  and `snt_workspace_manager/` hold only untracked files, so `git archive` drops them.
- Bootstrap tests find the code through `Path(__file__).parents[1] / "snt_<…>"`, so they break after
  the move. Fixed in commit 8.
- LICENSE: all four repos use MIT (Bluesquare). Only the year differs (2026 in the orchestrator).
  DOC-5 is still open.

**Source → target mapping** (implemented by the staging script, P1-6)

| Source (at its SHA) | Target |
|---|---|
| ***snt_development*** | |
| `<name>/` (root folder with `pipeline.py`) + `pipelines/<name>/` | `pipelines/<name>/` (merged) |
| `pipelines/CLAUDE.md` | `pipelines/CLAUDE.md` |
| `code/*.r` | `shared/r/` |
| `contracts/snt_config_json/` | `contracts/snt_config/` |
| rest of `contracts/`, `catalogs/`, `docs/`, `dev/`, `pyproject.toml`, `LICENSE`, `README.md`, `CLAUDE.md` | same path (root `CLAUDE.md` is interim until Phase 2) |
| `.claude/` | already on `main` (P1-3) |
| `.gitignore` | base of commit 1, not imported as is |
| `deprecated/`, `.github/`, `snt_workspace_check/`, `snt_workspace_manager/` | **left out** |
| ***snt_webapp_orchestrator*** | |
| `webapps/orchestrator/CLAUDE.md` | `webapps/orchestrator/CLAUDE.md` |
| rest of `webapps/orchestrator/` (`index.html`, `app.js`, `styles.css`, `*.json`, …) | `webapps/orchestrator/app/` |
| `docs/OPENHEXA_WEBAPP_RUNTIME.md` | `docs/` |
| rest of `docs/` (incl. `decisions/`; `research/` minus the persona questionnaire) | `webapps/orchestrator/docs/` (ADRs and BACKLOG merged in Phase 2) |
| `design/` | `webapps/orchestrator/design/` |
| `contracts/*.schema.json` | `contracts/orchestrator/` |
| `reference/` | `reference/` |
| `pipelines/create_pipeline_cards/` | `pipelines/create_pipeline_cards/` |
| `CLAUDE.md` (repo rules R1–R12) | `webapps/CLAUDE.md` (interim) |
| `README.md` | `webapps/orchestrator/README.md` |
| `.claude/`, `.github/`, `.gitignore`, `LICENSE` | left out (`.gitignore` rules go into commit 1, `.claude/` is merged in Phase 2) |
| ***snt_workspace_bootstrap*** | |
| `snt_workspace_deployer/`, `snt_pipeline_deployer/`, `snt_workspace_checker/` | `pipelines/<same name>/` |
| `docs/contracts/*` | `contracts/` |
| rest of `docs/` (incl. `context/`) | `docs/bootstrap/` |
| `CLAUDE.md` | `docs/bootstrap/CLAUDE.md` (interim) |
| `tests/`, `tools/` | `tests/`, `tools/` |
| `pyproject.toml`, `dev/environment.yml` | merged in commit 4, not imported as is |
| `.claude/`, `.gitignore`, `LICENSE` | left out (as above) |
| ***openhexa-webapps-edit-snt-config-json*** | |
| `CLAUDE.md` | `webapps/config_editor/CLAUDE.md` |
| `docs/PRODUCT_SPEC.md`, `docs/EXTERNAL_CHECKS.md` | `webapps/config_editor/docs/` |
| `docs/config_analysis_notes.md`, `docs/config_field_matrix.md` | `contracts/snt_config/` |
| `prototype/index.html` | `webapps/config_editor/design/index.html` |
| `docs/SNT_config.skeleton.json`, `ignore/`, `LICENSE` | left out (D-11, D-7) |

**Steps**
- [x] **P1-0 Close Phase 0.** Merge `plan/snt-single-repo` into `main`. The local spike code stays in
      `ignore/spikes/` (git-ignored). Optional, not blocking: delete the spike pipelines and the
      template in `snt-testing` and `snt-development-sandbox`.
- [x] **P1-1 Land this runbook** in `snt_development` (branch `plan/phase-1-runbook`, commit
      `plan: Phase 1 runbook`).
- [x] **P1-2 Create the repo** (GitHub UI, Giulia). Name `BLSQ/snt-stratification`, with **no**
      README, `.gitignore` or licence. Recommended visibility: **private until P1-10**, so that the
      second audit pass (P1-7) and DOC-5 come before anything is public. Clone it to
      `~/Bluesquare/snt-stratification`.
- [x] **P1-3 Seed `main`** by a direct push, before protection exists:
  - a `README.md` stub;
  - `.claude/` from `snt_development` (`settings.json`, `hooks/block-destructive-git.py`,
    `README.md`, `skills/`; no `__pycache__/`).

  Test the guardrail as `.claude/README.md` describes. Commit:
  `chore: initialise snt-stratification with the R19 git guardrail`.
- [x] **P1-4 Protect** (GitHub settings):
  - Ruleset on `main`: require a pull request (0 approvals, so Giulia can merge her own PRs), block
    force pushes, block deletion.
  - Tag ruleset on `v*`: restrict updates and deletions, with an empty bypass list.
- [x] **P1-5 Record the source SHAs.** For each of the four source repos, confirm that `main` is clean,
      pushed and holds everything wanted. Then run `git -C ~/Bluesquare/<repo> fetch origin` and
      `git -C ~/Bluesquare/<repo> rev-parse origin/main`. Write the four SHAs into the Session log.
- [x] **P1-6 Stage the export** into `~/Bluesquare/_import_staging/` (outside every repo), using a
      throwaway script `snt_development/ignore/phase1/stage_import.sh` that implements the mapping:
  1. For each repo, `git -C <repo> archive <sha>`, extracted into `src/<repo>/`.
  2. Copy into `tree/` according to the mapping.
  3. Delete the persona questionnaire and the 4 country notebooks (D-13), plus any `country_specific/`
     folder left empty:
     - `snt_seasonality_rainfall/code/snt_seasonality_rainfall_NER.ipynb`
     - `snt_dhis2_extract/code/NER_pyramid_format.ipynb`
     - `snt_dhis2_incidence/country_specific/snt_dhis2_incidence_NER.ipynb`
     - `snt_dhis2_formatting/country_specific/snt_dhis2_formatting_pyramid_BDI.ipynb`
  4. Redact each `redact` row of the Phase 0 audit table. Placeholders: `<DHIS2_UID>`,
     `<country-workspace>`. The NER-only block of `snt_dhis2_extract_report.r` is removed (NER does
     not run from this repo, D-13).
  5. Run `nbstripout` on every `.ipynb` in `tree/`.
  6. Write `import_manifest.tsv` with target path, source repo, source path and sha256, and mark
     every redacted file `modified`.
- [x] **P1-7 Second audit pass** on `tree/`. Grep for:
  - 11-character UID-shaped tokens (`\b[A-Za-z][A-Za-z0-9]{10}\b` that contain a digit; review the
    hits by hand);
  - `-snt-process`;
  - e-mail addresses;
  - `token|secret|password`;
  - long decimal coordinates.

  Fix anything found in the script and rerun P1-6, never by hand. Record the result in the Phase 0
  audit table and close its `[~]` item.
- [x] **P1-8 Build the PR** on `phase-1/snapshot-import`, one commit per row, in this order:

| # | Content | Commit message |
|---|---|---|
| 1 | `.gitignore`: the rules of the three repos, made valid for the new tree. `**/[Tt]est*` dropped. Allowlist: `pipelines/registry.json`, `webapps/*/app/**/*.json`, `tests/fixtures/*.json`, `contracts/**/*.json`, `catalogs/SNT_metadata_master.json`, `.claude/settings.json`, `dev/environment.yml`, `.github/workflows/*.yaml` | `chore: .gitignore allowlist for the monorepo layout` |
| 2 | `tree/` copied in, `git add -A`, nothing else | `import: snapshot of snt_development, snt_webapp_orchestrator, snt_workspace_bootstrap and the config editor` |
| 3 | `README.md` provenance table (repo, SHA, files left out or redacted); `pipelines/registry.json` (`kind`: `snt`; `support` for `create_pipeline_cards` and `snt_metadata_json_trim`; `bootstrap` for the 3 bootstrap pipelines); `webapps/config_editor/app/.gitkeep` | `docs: provenance table and pipelines/registry.json` |
| 4 | One `pyproject.toml` (ruff from `snt_development`, pytest from bootstrap); one `dev/environment.yml` named `snt-stratification` (union of both envs) | `chore: one pyproject.toml and one conda env, snt-stratification` |
| 5 | Every shared-library `"code"` → `"shared", "r"`; `folders_to_create`; deployer wording. Per-pipeline `pipelines/<name>/code/` untouched | `refactor: shared R library path code/ → shared/r/ (D-9)` |
| 6 | Orchestrator `CLAUDE.md` + `docs/DEPLOYMENT.md`: the bundle is `app/`, and drag-and-drop uploads its contents. Editor `CLAUDE.md` links. Any other link broken by the moves | `docs(webapps): paths and links for the app/ + docs/ split (D-10)` |
| 7 | `ruff format .` and `ruff check --fix .`, no manual edits | `style: ruff format and autofix` |
| 8 | Bootstrap test paths (`pipelines/…`, `contracts/`), remaining path breakage, `pytest` green | `fix: test paths and path breakage after the import` |
| 9 | This file: header ("Where it lives"), Phase 1 checkboxes, Session log | `plan: Phase 1 results` |

- [x] **P1-9 Verify** and paste the results into the PR description:
  - `git ls-files --others --ignored --exclude-standard` is empty, or lists only files that should
    be ignored.
  - Each file from commit 2 matches `import_manifest.tsv` (same sha256, or marked `modified`).
  - No notebook has outputs.
  - No `ROOT_PATH, "code"` left in any `.ipynb` or `.r`.
  - `ruff check .` is clean and `pytest` is green.
  - State that nothing was run on OpenHEXA. That happens in Phase 4.
- [x] **P1-10 Merge** the PR with a merge commit. Then make the repo public if P1-7 passed and DOC-5
      is settled. → Public since 2026-11-05. MIT is kept for now; DOC-5 stays open as a later
      review, not a blocker.
- [x] **P1-11 Pointer PR in `snt_development`** (branch `docs/migration-plan-moved`):
  - This file becomes a one-line pointer to the new repo's copy.
  - Drop the MIGRATION_PLAN row from CLAUDE.md "Where to find things", and the README and BACKLOG
    pointers.
  - Commit: `docs: MIGRATION_PLAN moved to BLSQ/snt-stratification`.

  → Done 2026-11-05, with one change: the README and BACKLOG pointers were re-pointed to this repo
  rather than dropped, so `snt_development` readers still learn that the code has moved.

  From then on, plan updates happen in the new repo, and `snt_development` is maintenance-only (D-4).

#### Phase 1 results

P1-0 to P1-11 done on 2026-11-05. Where the work differed from the runbook above, and what was
found on the way:

- **Staging (P1-6).** The throwaway scripts are Python, not shell: `stage_import.py`,
  `audit_tree.py` (P1-7) and `fix_links.py` (commit 6), all in `snt_development/ignore/phase1/`
  (git-ignored). Their outputs (`provenance.txt`, `import_manifest.tsv`, `left_out.tsv`) stay in
  `~/Bluesquare/_import_staging/`.
- **Placeholders (P1-6, step 4).** `REDACTEDUID` (11 characters, like a UID), `xxx-snt-process` and
  `snt-xxx-files`, instead of `<DHIS2_UID>` / `<country-workspace>`: angle brackets break the HTML
  wireframe, where the slug sits inside a JS string of HTML.
- **NER-only block of `snt_dhis2_extract_report.r`.** `apply_ner_manual_geometry_fixes()` has no
  caller in any tracked file, so removing it is behaviour-neutral.
- **Commit 5 (shared R path).** 90 replacements in 60 notebooks, `.r` files and pipeline readmes,
  across 4 forms: `file.path(ROOT_PATH|SNT_ROOT_PATH, "code", …)`, `CODE_PATH <- file.path(…, 'code')`,
  `"~/workspace/code"` (8 occurrences, missing from the facts above) and
  `file.path("~/workspace", "code", …)`. `folders_to_create` now creates `shared/r`.
  - **Not done, unlike the table:** the bootstrap pipelines (`snt_pipeline_deployer`,
    `snt_workspace_deployer`, `snt_workspace_checker`), their readmes and `tests/` still say
    `code/`. They read v1 manifests, where the shared library *is* `code/`, so their wording changes
    in Phase 4 with the manifest-v2 logic.
  - Root `CLAUDE.md` and `docs/*` still say `code/` (Phase 2). `pipelines/registry.json` has `kind`
    only; deploy routes come in Phase 3 (OD-4).
- **Commit 6 (links).** 204 relative links in 41 Markdown files re-pointed through
  `import_manifest.tsv`. The 7 links to material that was not imported (`deprecated/`, old
  workflows) are pinned to the source SHA, and the persona questionnaire link is unlinked (text
  kept). `.claude/` is not in the manifest, so its one broken link was fixed by hand. Orchestrator
  paths now say `webapps/orchestrator/app/…`; the ADRs are left as written. A scan of every `.md`
  file finds 0 broken relative links (777 checked).
- **Commit 7 (ruff).** The env resolved ruff 0.17.3 (floor `>=0.16`). With `preview = true`:
  - RUF201 rewrote the 30 rule codes in `pyproject.toml` to rule names, and RUF105 turned one
    `# noqa` into `# ruff: ignore[…]`. ruff 0.16.5 reads both the same way.
  - `ruff format` also formats Python code blocks in Markdown (3 files). Side effect: the old
    `generate_manifest.py` quoted in `docs/bootstrap/HISTORY.md` is no longer verbatim (quote style
    only).
- **Commit 8 (path breakage).** Besides the test paths:
  - The handover skill's `check_notebook_params.py` looked for `*/pipeline.py` at the root, found
    none and reported "No ERRORs". It now reads `pipelines/*/pipeline.py`. The one ERROR it reports
    in `snt_development` (`snt_seasonality_rainfall_NER.ipynb`) is absent here by design (D-13).
  - The add-explorer-layer skill's `validate_metadata.py` read the skeleton from
    `contracts/snt_config_json/`.
  - The 5 findings left after commit 7 were fixed by hand, except N999 on `malariaAtlasProject`:
    a per-file ignore, not a rename, because it is imported by that name and deployed.

  Result: `ruff check .` and `ruff format --check .` clean, `pytest` 16 passed.

### Phase 2 — Docs and agent setup

**Outcome:** one CLAUDE.md router, one Register, one ADR sequence and one BACKLOG for the whole repo,
landed through **one PR** (branch `phase-2/docs-and-agents`, merged with a merge commit). Docs and
agent setup only: no pipeline, workflow or workspace behaviour changes. One branch because the
renumbering of ADRs, backlog IDs and rules changes links across the whole repo; `main` never holds
a half-renumbered state. Decisions settled at the start: D-14 (was OD-5), D-15 (was OD-8), D-16.
**Agents:** run no `git`/`gh` command yourself (R19). Give Giulia the exact commands, one commit at
a time.

| # | Content | Commit message |
|---|---|---|
| 1 | This file: D-14…D-16, Phase 2 runbook | `plan: open Phase 2, settle OD-5 and OD-8` |
| 2 | Orchestrator ADRs and the architectural bootstrap D-entries moved into `docs/decisions/`, renumbered (D-14), mapping table, links updated | `docs(decisions): one ADR sequence with a mapping table (OD-5)` |
| 3 | The new ADRs listed below | `docs(decisions): ADRs for the monorepo, release train, repo path = workspace path, docs placement and template routes` |
| 4 | One `docs/BACKLOG.md` | `docs: one BACKLOG with area-prefixed IDs` |
| 5 | Root router + merged Register (D-16), `webapps/CLAUDE.md` W-rules, bootstrap rules into `pipelines/CLAUDE.md`, interim CLAUDE.md files retired | `docs: root CLAUDE.md router with the merged Register` |
| 6 | `docs/ARCHITECTURE.md` | `docs: ARCHITECTURE.md system map` |
| 7 | Skill texts | `docs(skills): update the skills for the monorepo paths` |
| 8 | This file: Phase 2 checkboxes, results, Session log | `plan: Phase 2 results` |

The memory and `ignore/` sweep (last item below) runs first, as reading; what it finds lands in
commits 3–5, wherever each item belongs.

**Hand-off for commits 5–8 (2026-11-09), now done.** Kept as the record of what was asked; what
was done is in [Phase 2 results](#phase-2-results).
- **Register IDs (D-16):** R1–R22 keep their IDs. Webapp-only rules become `W1…` in
  `webapps/CLAUDE.md`; its old R1 (git guardrail) is R19 and its old R12 (doc hygiene) merges into
  root rules from R23 on, together with bootstrap DOC1–DOC5 (`docs/bootstrap/CLAUDE.md`). Add an
  "old ID" column, and a `docs/CONVENTIONS.md` section for every new root rule.
- **Retire the interim CLAUDE.md files:** `docs/bootstrap/CLAUDE.md` (its bootstrap-pipeline rules
  go to a "Bootstrap pipelines" section of `pipelines/CLAUDE.md`; its "Read X when Y" table becomes
  routing rows; no `CLAUDE.md` inside a pipeline folder, ADR 0039). `webapps/CLAUDE.md` still
  describes the old orchestrator repo (repo map, "SNT pipeline source" row pointing at
  `snt_development`); rewrite it as the webapp-wide rules file. Root `CLAUDE.md` is 19.9 KB, target
  ≤15 KB, and still says `code/` for the shared R library.
- **R6, now answered** (Giulia pasted `snt_lib`'s `pull_scripts_from_repository`, 2026-11-09):
  notebooks must be listed in `code_scripts` / `report_scripts`. Util files are derived and pulled
  without being listed: `{pipeline_name}.r` (when `code_scripts` is given),
  `{pipeline_name}_report.r` (when `report_scripts` is given) and `{stem}.r` for every listed
  notebook; a missing one is skipped quietly. Any other `.r` name must go in `extra_util_scripts`
  (warning if missing). The three shared files are always pulled. Reword R6 in the root Register and
  in `docs/CONVENTIONS.md#r6` to say this.
- **Sweep items still to place:** the `.gitignore` trap (`git add` silently drops a file matching an
  ignored pattern; `git add --dry-run` is the reliable test, `git check-ignore -v` also exits 0 on a
  `!` negation) → root Traps; `openhexa workspaces add` stores deploy tokens in plain text in
  `~/.openhexa.ini` → `dev/README.md`; the plain-language newcomer explainer from Giulia's local
  notes `snt_development/ignore/DATA_STACK_ORIENTATION.md` (term table) and
  `snt_workspace_bootstrap/ignore/openhexa_deployment_explained.md` §1, 2, 5–7 → commit 6, leaving
  out its claim that a `requirements.txt` in the zip installs nothing (BACKLOG DEP-1 says it does).
- **Deviation to record in commit 8:** the BACKLOG kept every non-colliding ID and renumbered only
  the six orchestrator collisions, instead of area-prefixing every item.

- [x] Root `CLAUDE.md` router (≤15 KB) with the **merged Register**. Rules shared by all three repos
      (git guardrail, `[ERROR]`/`[WARNING]` prefixes, Python style) appear once. Webapp-only rules move
      to `webapps/CLAUDE.md` (prefix `W`); notebook rules stay in `pipelines/CLAUDE.md`.
      → Commit 5.
- [x] `docs/ARCHITECTURE.md` (new): one-page system map. Units, the contracts between them, the
      deploy routes (deployer, new templates, old templates), and the release train.
      → Commit 6.
- [x] Import the ADRs per D-14 (was OD-5). Write the first new ADRs: monorepo (supersedes orchestrator REPO-1),
      release train (D-2), repo path = workspace path (D-9, §4.2), docs placement rule (D-10), templates kept alongside the deployer
      (**supersedes bootstrap D20**), publishing workspace for the new templates (**amends R5 / ADR 0004**).
      → Commits 2–3: ADRs 0010–0035 imported, 0036–0041 new.
- [x] Merge the backlogs into one `docs/BACKLOG.md`. IDs collide (`TOOL-1`, `DOC-2`, `OH-1`… exist
      in several repos), so give each an area prefix (`PIPE-`, `APP-`, `BOOT-`, `CFG-`, `REL-`, `TOOL-`)
      and add an "old ID" column. Drop items this migration resolves: REPO-1/2, the multi-source
      roadmap §1, the CI path-filter typos.
      → Commit 4. The path-filter typos had no backlog item (the old workflows were not imported).
- [x] Update the skills for the new paths. The `release` skill is **moved to Phase 4**: it would
      describe a release process that does not exist yet. (The skills' scripts were fixed in Phase 1,
      commit 8. Their text still says `code/*.r` and `contracts/snt_config_json/`, and
      `validate_metadata.py` still says jsonschema is not in `dev/environment.yml`, which is now wrong.)
      → Commit 7.
- [x] Sweep the local Claude memory and the `ignore/` plans of all source repos. Anything still true
      and useful goes **into the repo** (CLAUDE.md, ADR, BACKLOG, docs). Nothing may rely on local memory.
      → 2026-11-06, memory half done: the notes were Giulia's personal working preferences (moved to
      her global `~/.claude/CLAUDE.md`, as they hold for every repo) and two finished-history notes
      (deleted or marked done). The `ignore/` plans (`snt_development`, `snt_webapp_orchestrator`,
      `snt_workspace_bootstrap`) are still to read. `OpenHEXA-WebApp-Diary` is out of scope.
      → 2026-11-06, `ignore/` half read: 16 items still true and unrecorded. 12 placed in commits 3–4
      (ADR 0039, BACKLOG, OWNERSHIP); the rest are listed in the hand-off above.
      → Commits 5–6 placed the rest: the `.gitignore` trap (root Traps), the `~/.openhexa.ini`
      token (`dev/README.md`) and the newcomer explainer (`docs/ARCHITECTURE.md` Part 2).

#### Phase 2 results

Commits 1–8 on `phase-2/docs-and-agents`, 2026-11-06 → 09. Where the work differed from the runbook
above, and what was found on the way:

- **Commit 4 (BACKLOG).** Every non-colliding ID was kept; only the six orchestrator IDs that
  collided were renumbered, instead of area-prefixing every item.
- **Commit 5 (router and Register).** Root `CLAUDE.md` is 15,227 bytes (15,280 after commit 6's
  routing row: a new row now needs a trim elsewhere). The Register is R1–R26 with an "Old ID"
  column:
  - R17–R19 are the rules all three repos shared, widened to R and Python where needed.
  - Bootstrap DOC5 merged into **R22** (manifest *or* checker report shape → schema in
    `contracts/`), instead of a new number.
  - New: **R23** current truth only (orchestrator R12, bootstrap DOC1–2), **R24** decisions are
    ADRs (DOC3), **R25** one fact one home, open items only in the BACKLOG (orchestrator R12, DOC4),
    **R26** one folder per deployable unit. R26 is the orchestrator's R11, made a root rule rather
    than a W-rule because it covers pipelines too.
  - R5 reworded for both template sets (ADR 0041); R6 reworded as answered above.
  - Orchestrator R2–R10 became **W1–W9** in `webapps/CLAUDE.md`. Their citations in ADRs
    0023–0025, the orchestrator's `DEPLOYMENT.md`, `OPENHEXA_WEBAPP_RUNTIME.md` and one `app.js`
    comment were updated (the comment needs no redeploy).
  - **Root rule 2 rewritten:** merging here deploys nothing (no CI; `Pull scripts` pulls from the
    old repo). It used to say notebooks reach a workspace through `Pull scripts`.
  - **Not in the runbook:** the pipeline-specific Traps moved from the root to
    `pipelines/CLAUDE.md#pipeline-traps`, to fit 15 KB. `docs/bootstrap/CLAUDE.md` was deleted;
    its rules, reading table and § index are in `pipelines/CLAUDE.md#bootstrap-pipelines`.
  - Stale text fixed on the way: `CONVENTIONS.md` (`code/` paths, `deprecated/`, the workflow
    step in "Adding a pipeline"), the config editor's `CLAUDE.md` (it still called the skeleton a
    vendored copy, against D-11), README claims and counts.
- **Commit 6 (ARCHITECTURE.md).** Part 1 is the map, Part 2 the newcomer explainer. **Beyond the
  runbook:** §2.5 also draws on §3, §4 and §8 of `openhexa_deployment_explained.md`, not only §1, 2,
  5–7; accepted by Giulia on 2026-11-09. The `requirements.txt` claim was left out (DEP-1).
  `contracts/README.md` was rewritten to list all eight contracts, and `DATA_ARCHITECTURE.md` §2 now
  says it describes the old repo's routes.
- **Commit 7 (skills).** **Beyond the runbook, agreed with Giulia:** besides the path fixes, the
  handover skill's rows 7, 10 and 11, note steps 4–5 and description were aligned with the commit 5
  rules (R6, R26, R22, rule 2, R5). Without it, the skill told agents to push from
  `snt-development`.
- **Left as they are:** `docs/bootstrap/HISTORY.md` still cites DOC5 (history; the Old ID column
  resolves it). `DATA_ARCHITECTURE.md` §2 still describes the old repo's delivery in full.
  `dev/README.md` still calls `ruff` the only automated check, though `pytest` now exists.

Verification (2026-11-09): 1,007 relative links in all `.md` files, 0 broken; `ruff check .` and
`ruff format --check .` clean; `pytest` 16 passed; the metadata validator returns `OK`. Nothing was
run on OpenHEXA.

### Phase 3 — Tooling and CI

**Branch:** `phase-3/tooling-and-ci`, one PR, merged with a merge commit. OD-4 is settled first
(D-17) and lands as its first two commits. **Agents:** run no `git`/`gh` command yourself (R19).
Give Giulia the exact commands, one commit at a time.

| # | Content | Commit message |
|---|---|---|
| 1 | This file: D-17 (was OD-4), [Phase 3 findings](#phase-3-findings) (spike S6), Phase 3/4/6 items and §4.1 updated, Session log | `plan: settle OD-4 (D-17) with spike S6` |
| 2 | ADR 0042 + current-truth fixes (D-17) | `docs(decisions): ADR 0042, bootstrap pipelines as templates published on release` |
| 3 | `openhexa_deployment.md`: templates stay a deploy route (R23 fix found in commit 2) | `docs(bootstrap): templates stay a deploy route in openhexa_deployment.md` |
| 4 | Manifest v2 schema (v1 kept as `release_manifest.v1.schema.json` until Phase 4); `context/snt_development.md` R23 fix | `contracts: release manifest v2 schema` |
| 5 | `tools/build_manifest.py` + `tests/test_build_manifest.py`; `pythonpath = ["tools"]` in `pyproject.toml` | `tools: build_manifest.py, the release manifest v2 builder` |
| 6 | Config conformance fixtures + `tests/test_config_conformance.py`; `snt_lib` pin for the test; editor §12.2 settled (option 2); DEP-1 facts | `contracts: config conformance fixtures, run through snt_lib validate_config()` |
| 6a | This file: commit 7 hand-off, Session log | `plan: Phase 3 commits 2–6, hand-off for ci.yaml` |
| 7 | `ci.yaml` + `tools/check_links.py`, `tools/check_tracked_files.py`; TOOL-2, 5, 7 closed | `ci: ci.yaml with ruff, pytest, R1/R2, link, registry and Explorer-list checks` |
| 7a | `contracts/snt_config/README.md` brought in line with D-11 (asked in the commit 7 hand-off) | `docs(contracts): snt_config README describes the one skeleton (D-11)` |
| 7b | The old `contracts/snt_config_json/` name replaced outside this file's history | `docs: contracts/snt_config/ everywhere, not the old snt_config_json/` |
| 7c | This file: commit 8 hand-off, Session log | `plan: Phase 3 commit 7, hand-off for release.yaml` |
| 8 | `release.yaml` + `tools/build_release_assets.py` + tests; release assets and `version.json` in `release_manifest.md`; R23 fixes in `contracts/README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `CONVENTIONS.md` | `ci: release.yaml, the release manifest, slim tarball and webapp zips on each release` |
| 8a | This file: commit 9 hand-off, Session log | `plan: Phase 3 commit 8, hand-off for push_templates.yaml` |
| 9 | `push_templates.yaml` (disabled); R23 fixes in `CLAUDE.md`, `ARCHITECTURE.md`, BACKLOG TOOL-8 | `ci: push_templates.yaml, the new SNT template set on each full release (disabled)` |
| 9a | This file: Phase 3 checklist closed, Phase 6 items, closing hand-off, Session log; `ARCHITECTURE.md` bootstrap-templates state | `plan: Phase 3 commit 9, hand-off for closing Phase 3` |

**Phase 3 closed (2026-11-13):** the PR with commits 1–9a is merged into `main`.

#### Phase 3 findings

**Spike S6 (2026-11-12): can the deployer push onto a template-created pipeline? Passed.** Toy
pure-Python pipeline `spike_s6_bootstrap` (code `spike-s6-bootstrap`), published as template
`SNT Spike S6` from `snt-development-sandbox`, installed from it in `snt-testing`. The direct push
used the deployer's own mutation and input (`uploadPipeline`, workspace token). Throwaway code and
runbook: `ignore/spikes/s6/` (git-ignored, local only); the results below are the record.

| Q | Observed |
|---|---|
| Direct push onto a template-created pipeline | **Accepted** (`success: True`); version 2 `s6-B-direct [v2]` |
| Template link after the push | **Kept**: `sourceTemplate` still set, `autoUpdateFromTemplate` still `True` |
| Template publish, same content as the current version | A new version arrives anyway (v3): OpenHEXA does not compare contents |
| Template publish, different content | Arrives within seconds and becomes current (v4), replacing the direct push: **last writer wins** |
| Defaults and names | **`autoUpdateFromTemplate` defaults to `False`** on a template-created pipeline (switched on by hand in the pipeline's settings). Template-delivered versions are named `v<pipeline version number>` (`v1`, `v3`, `v4`), not after the source version or the template version; they have no `user`, and `PipelineVersion.templateVersion` is `null` even on them |

Consequences:
- Auto-update is opt-in, so a workspace that never ticks it keeps its install-time bootstrap
  pipelines; D-17's guarded self-update brings them current whenever the deployer runs at the latest
  release.
- "Last writer wins" is the concrete reason for ADR 0040's rule for `snt`/`support` pipelines: a
  template update would move `pipeline.py` and leave the deployer-installed R half behind.
- The API does not say which template version delivered a pipeline version; content hashing stays
  the only evidence (already the checker's model).
- The checker must read a `v<N>` version name as "no release claimed" (Phase 4).
- `openhexa pipelines push` on a template's source pipeline also publishes a template version: it
  asks interactively, and `--yes` publishes without asking. CI can publish with a plain
  `push --yes`. It also means any push from a publishing workspace publishes, so R5 binds the new
  set as much as the old.

**Checklist**
- [x] Settle OD-4 → D-17, spike S6 (2026-11-12). Commit 1.
- [x] ADR 0042 and the current-truth fixes. Commit 2, see the hand-off above.
- [x] `tools/build_manifest.py` (from the `generate_manifest.yaml` heredoc) emitting **manifest v2**,
      plus pytest coverage and fixtures. Lists `kind: bootstrap` pipelines like any other (D-17).
      Commit 5: validates its own output before writing; stops on a registry ↔ folder mismatch;
      `pytest` imports `tools/` scripts by name (`pythonpath`).
- [x] `contracts/release_manifest.schema.json` v2 (R22 becomes an in-repo rule: schema + builder +
      consumers in one PR). Commit 4: `filesystem_files` added, `webapps` built now (decided
      2026-11-12). v1 moves to `release_manifest.v1.schema.json`, which Phase 4 deletes. The
      consumers switch in Phase 4, a PR later than the schema: harmless, because nothing produces a
      v2 manifest before the first release (`v0.1.0`, Phase 4).
- [x] `ci.yaml`: ruff, pytest, contract validation, metadata validator (`validate_metadata.py`), link check.
      Commit 7: two jobs, `checks` (ruff 0.17.3 pinned, `tools/check_tracked_files.py` for R1/R2,
      `tools/check_links.py` over git's file list so `.claude/` is checked too, the manifest builder,
      the metadata validator) and `pytest` (pinned `snt_lib`, `SNT_LIB_REQUIRED=1`). TOOL-2, 5, 7
      closed; TOOL-6 narrowed to JSON Schemas for `contracts/orchestrator/` (prose today), with
      map ids == description keys now in `pytest`.
- [x] `release.yaml`: on `release: published`, build and attach `release_manifest.json`, a **slim
      release tarball** (only manifest-listed files, so the deployer doesn't download design PNGs and
      docs), and `webapp-<name>-<tag>.zip` with a stamped `version.json`. Plus a job that runs on
      **full releases only** (`release: released`, which skips pre-releases, unlike `published`):
      `openhexa pipelines push --yes` of each registry `kind: bootstrap` pipeline to the new
      templates publishing workspace, which publishes their template versions (D-17). Keep that job
      **disabled** until the publishing workspace exists.
      Commit 8, decided 2026-11-13: `version.json` = `version`, `commit` (full hash), `built_at`
      (UTC); slim tarball `snt-stratification-<tag>.tar.gz` with one top folder of the same name;
      upload with `gh release upload --clobber`; a `workflow_dispatch` run keeps the assets as an
      Actions artifact (7 days), usable once on `main`. Build logic in `tools/build_release_assets.py`
      (hash-checks every file against the manifest, writes nothing on a mismatch). The bootstrap job
      reads `vars.OH_TEMPLATES_WORKSPACE` and `secrets.OH_TEMPLATES_TOKEN`, created when it is
      enabled. Not run yet: no release exists, and the manual run needs the file on `main`.
- [x] `push_templates.yaml`: one matrix job **generated from `pipelines/registry.json`** (kinds `snt` + `support`),
      so typo'd per-pipeline path filters (`readme.txt`, `worlpopclient.py`) can't come back.
      Target = the new templates workspace. Keep it **disabled** until Phase 6.
      Commit 9, decided 2026-11-13: on **full releases only** (`release: released`), the trigger
      ADR 0041 left to Phase 6; its own file, not a job in `release.yaml`; **every** pipeline pushed
      on every full release, changed or not (simpler; costs one template version per pipeline per
      release, S6), which holds for the bootstrap job too. A `pipelines` job lists the names with
      `jq`, then one `push` matrix job per pipeline (`fail-fast: false`) with the bootstrap job's
      flags (`--code`, `--name` = tag, `--description "Release <tag>"`, `--link`, `--yes`), so the
      template route leaves TOOL-8. Not run: disabled (`if: false`), and no release exists.
- [-] `push_bootstrap.yaml`: dropped by D-17. Bootstrap templates publish from `release.yaml` on
      full releases, not on every merge to `main`.
- [x] Config conformance fixtures (`contracts/snt_config/fixtures/`) + a Python runner against the
      **pinned** `snt_lib` `validate_config()` in `ci.yaml`. The JS side runs the same folder when the
      editor's validator exists. Commit 6: 16 cases (3 valid, 13 invalid), runner
      `tests/test_config_conformance.py`, pin `v1.0.2` in `tests/requirements-conformance.txt`
      (`release-v1` is a branch; `v1.0.2` was its head on 2026-11-12). `ci.yaml` must install the pin
      and set `SNT_LIB_REQUIRED=1`.

### Phase 4 — Bootstrap adapted to the monorepo

**Branch:** `phase-4/bootstrap-monorepo`, one PR, merged with a merge commit. OD-6 is settled first
(D-18) and lands as commit 1. **Agents:** run no `git`/`gh` command yourself (R19). Give Giulia the
exact commands, one commit at a time. Every code commit leaves `ruff` and `pytest` green on its own;
the manifest schema, the builder and the three consumers end the PR agreeing (R22). Commit 2 changes
the two deployers together, because `tests/test_pipeline_deployer.py` fails when their shared
functions differ.

| # | Content | Commit message |
|---|---|---|
| 1 | This file: D-18 (was OD-6), Phase 3 closed, this table, Session log | `plan: settle OD-6 (D-18), Phase 4 commit table` |
| 2 | Both deployers read manifest v2: refuse a missing or unknown `schema_version` with an `[ERROR]` (v1 manifests included), copy exactly `filesystem_files`, zip each pipeline from `pipelines.<name>.path`; `github_repo` default `BLSQ/snt-stratification`; tests against the v2 example fixture | `bootstrap: deployers read release manifest v2` |
| 3 | Bootstrap guard (D-17) in both deployers, with tests | `bootstrap: deployers never install bootstrap pipelines from an older release` |
| 4 | `.snt_release` records `repo` and the tag; the checker reads the old and the new marker shape; `snt_release_marker.md` | `bootstrap: .snt_release records the repository` |
| 5 | Checker reads manifest v2: zip members keyed under `pipelines.<name>.path`, filesystem files from `filesystem_files`, the scan's root exclusions checked for `shared/r/`, bootstrap pipelines attributed like any other; `github_repo` default; `tests/test_checker_stub.py` on v2 | `bootstrap: checker reads release manifest v2` |
| 5a | This file: commits 2–5 recorded, hand-off for commit 6, Session log | `plan: Phase 4 commits 2–5, hand-off for commit 6` |
| 6 | Checker: `claimed_release_tag` reads a template-delivered `v<N>` as no claim; template-created codes named (legacy `b-2-…` through a mapping table) | `bootstrap: checker names template-created pipelines` |
| 7 | Delete `release_manifest.v1.schema.json`, its two v1 fixtures and the v1 prose in `release_manifest.md`; current-truth fixes for commits 2–6 and D-18 (`docs/bootstrap/`, the three `readme.md`, `pipelines/CLAUDE.md`) | `contracts: drop release manifest v1` |
| 7a | This file: hand-off for cutting `v0.1.0`, Session log | `plan: Phase 4 commits 2–7, hand-off for v0.1.0` |
| 8 | Cut `v0.1.0` (pre-release, D-18) and verify it in a fresh test workspace; results recorded here | `plan: Phase 4 results, v0.1.0 verified` |
| 9 | `release` skill, from what cutting `v0.1.0` taught | `skills: release, cutting and promoting a release` |

**Questions to ask at the commit that needs them** (not before):
- ~~**Commit 2:** slim tarball or GitHub's source tarball?~~ Slim tarball (decided 2026-11-13).
- ~~**Commit 3:** "latest full release or newer" by `published_at` or by version number?~~
  `published_at` (decided 2026-11-13).
- **Commit 6:** see the hand-off below.
- **Commit 8:** the test workspace, the country config to copy, and the old-repo workspace to
  compare against.

**Hand-off for commit 6 (2026-11-13).** Commits 1–5a are on the branch, CI green through commit 4
(ask Giulia for the result on 5 and 5a first; a failure is fixed first, in its own commit). Start
here, in a new session.

1. **Read first:** this hand-off, the commit 6 row above, the last checklist item about the checker
   below, [ADR 0040](decisions/0040-templates-kept-alongside-the-deployer.md) "Consequences",
   [Phase 0 findings](#phase-0-findings) on spike S3 (`snt-<name>-<6 hex>` collision suffix), and
   [Phase 3 findings](#phase-3-findings) on spike S6 (template-delivered versions are named
   `v<N>`). Code: `claimed_release_tag()`, `name_matches_content()`, `pipeline_report()` and
   `list_unknown_pipelines()` in `pipelines/snt_workspace_checker/pipeline.py`; tests in
   `tests/test_checker_stub.py` (module-level asserts, run at import).
2. **Ask Giulia, one question at a time, before writing** (plain words, file links, a
   recommendation each):
   1. **Legacy template codes.** The list of codes the old templates create (`b-2-map-extracts`,
      …) and the pipeline name each stands for. Only the `snt-development` workspace shows them
      (its pipeline list, or a country workspace installed from it). The mapping table needs the
      real list; do not guess it.
   2. **The `snt-<name>-<6 hex>` suffix.** The checker must recognise it (ADR 0040). Should the
      deployers also find a template-created pipeline by it, instead of creating a second
      pipeline? Not in the checklist; ADR 0040 says "the deployer and the checker". The deployer
      change touches both deployers (shared functions, drift test).
   3. **`+redeploy-` names.** The checklist below says `claimed_release_tag` "still strips `[vN]`
      and `+redeploy-…`", but the code strips only `[vN]`: a `<tag>+redeploy-<date>` name claims
      no release today ([`deployer.md`](bootstrap/deployer.md) "Known consequences", which
      recommends stripping it). Strip it in commit 6 (recommended), or leave it?
3. **Already true, no work needed:** a template-delivered name `v<N>` already claims no release in
   effect (no manifest is named `v3`), but `current_version_claims_tag` reports `"v3"`. Commit 6
   makes it `null` explicitly, per S6.
4. **Commit 6 must keep:** the report's `schema_version` 1 unless a key is renamed or removed
   (`contracts/status_report.schema.json`, R22); a new key in `pipelines[]` (for example the
   legacy name) is an added key, so the schema gets it in the same commit.
5. **After commit 6:** commit 7 (docs and the v1 deletion). Its stale list, found in commits 2–5:
   both deployers' and the checker's `readme.md`; `docs/bootstrap/deployer.md` (slim tarball,
   `filesystem_files`, guard, marker `repo`); `docs/bootstrap/checker.md` (inert copies are now
   zip-only files on the filesystem, `shipped` counts copies, marker `repo`, the report example);
   `pipelines/CLAUDE.md` "Bootstrap pipelines" (still says they read v1); `release_manifest.md` and
   `release_manifest.schema.json` (still say no consumer reads v2, and that the deployers download
   GitHub's source tarball); `docs/bootstrap/release_strategy.md` and `sandbox.md` (D-18: the
   sandbox repository no longer used for testing releases).

**Checklist**
- [~] Deployer and checker read manifest v2 (pipelines under `pipelines/<name>/`, `kind`, ignore
      `webapps` for now; the checker's root exclusions are updated for `shared/r/`). The deployer
      copies exactly `filesystem_files`. Then delete `contracts/release_manifest.v1.schema.json`, its
      two v1 test fixtures, and the v1 prose in `release_manifest.md`.
      Commit 2 (deployers), decided 2026-11-13: they download the release's **slim tarball** asset,
      not GitHub's source tarball; a release without it stops the run with an `[ERROR]`. Commit 5
      (checker): a v1 or unknown manifest makes that release unusable, with a `[WARNING]`; an
      **inert copy** is now a file found on the filesystem at a path releases ship only in a zip
      (`pipeline.py`, …), since notebooks under `pipelines/<name>/` ship by both routes; the
      attribution score's `shipped` counts **copies** (route + path), so a notebook shipped both
      ways counts twice and `present` can't exceed it (same numbers as before for one-route
      paths; `schema_version` stays 1). Root exclusions checked: none names `code/` or `shared/`,
      so nothing changed; an old-layout `code/` folder in a workspace reads `untracked`. Left: the
      v1 deletion, commit 7.
- [x] `github_repo` default = the new repo (no longer `snt_development_sandbox`). Commits 2 and 5.
- [x] `.snt_release` marker records `repo` + tag (closes roadmap §7.4 for this case). Commit 4,
      decided 2026-11-13: the tag keeps its key `snt_release`; the checker uses a marker as its
      target only when it names the repository being checked, or none (an old marker); one naming
      another repository is reported in `declared_release` (which gains `repo`) with a
      `[WARNING]`, and not used.
- [ ] Checker: name pipelines with legacy template codes (`b-2-map-extracts`, …) through a mapping
      table, instead of reporting them as plain `not_in_any_release`.
- [x] **Bootstrap guard (D-17).** `snt_workspace_deployer` deploys `kind: bootstrap` pipelines only
      when the target tag is the latest full release or newer; for an older target it skips them with
      an `[INFO]`. `snt_pipeline_deployer` refuses, with an `[ERROR]`, to deploy a bootstrap pipeline
      from an older release. Both read every manifest `schema_version` from 2 on and refuse an unknown
      one with an `[ERROR]`. Keep the two copies identical (`tests/test_pipeline_deployer.py`).
      Commits 2 (version check) and 3 (guard), decided 2026-11-13: "newer" = published at the same
      time as or after GitHub's latest full release (`published_at`, the checker's order); with no
      full release yet (until `v1.0.0`), every release counts as the newest.
- [~] Checker: bootstrap pipelines are attributed through the manifest like any other (it stops
      reporting itself as `in_any_release: false`); `claimed_release_tag` reads a template-delivered
      version name `v<N>` as no claim (S6), and still strips `[vN]` and `+redeploy-…`.
      Attribution: done in commit 5 (they are in the v2 manifest, so nothing special was needed;
      a stub test proves the checker reports itself `in_any_release: true`). `claimed_release_tag`:
      commit 6, see its hand-off (today it strips only `[vN]`, not `+redeploy-…`).
- [ ] **Release `v0.1.0` (pre-release) = pure move, no behaviour change.** Bootstrap a fresh test workspace,
      run the SNT chain for one country (copy a config), compare outputs with an old-repo workspace,
      and confirm the checker reports `match`. This isolates "did the move break anything" from the
      bold changes.
- [ ] `release` skill (moved from Phase 2), written while cutting `v0.1.0`: checklist, cutting an
      rc, verifying in the test workspace, then promoting.

### Phase 5 — Breaking-change window (before the first production tag)
Batch the held-back breaking changes before any country adopts the new repo; later they would need a
major version. One PR each, each verified on a `v0.x` pre-release.

**Sequencing with the config editor:** the editor has no code yet, and its storage design (spec §6–7)
assumes `configuration/SNT_config.json` plus the current full shape. Settle the config split and the
`SNT_CONFIGURATION` dataset **before** building the editor's write step (`WorkspaceStore`), so it is
built once against the final contract. The form and validation (`LocalStore`, download only) can
proceed in parallel against the new schema.
- [ ] **CFG-1 dataset keys:** key = dataset slug in uppercase (`SNT_DHIS2_EXTRACTS: snt-dhis2-extracts`).
      Move the fixed identifiers out of `SNT_config.json` into `catalogs/snt_datasets.json`. NER's extra
      keys need a deliberate home.
- [ ] **Config split:** `SNT_config.json` keeps only the country-specific parts (`SNT_CONFIG`,
      `DHIS2_DATA_DEFINITIONS`). Write `snt_config.schema.json` (CFG-3) in `contracts/`, used by both
      the config editor and pipelines.
- [ ] **Config as dataset `SNT_CONFIGURATION`** (CFG-4), with a fixed slug by convention (it can't
      be looked up in itself). The editor writes through a validating pipeline. Needs a pinned
      `snt_lib` release (D-3), so sequence this together with CFG-1, since both touch config loading.
- [ ] **Report-only semantics** (OD-7): S4 first; otherwise `RUN_MODE` in `{CC}_parameters.json`;
      the orchestrator only counts full runs as "processed".
- [ ] Clear the `⚠ exceptions` the old repo couldn't touch: R11 (seasonality lowercase globals,
      PIPE-3), R14 (`run_reports_only`), R9 (ERA5 name, healthcare_access `File`), PIPE-5 (pregnant women).
- [ ] Orchestrator: fix `ohName` drift (APP-9) and the `create_pipeline_cards` README raw-URL docs.
      Consider generating `pipeline_map.json` ids from the manifest, so a pipeline can't be added
      without the map knowing.
- [ ] The editor follows each change: its rules 3 and 5 (emit all 15 dataset ids, keep the
      `POP_PREGNANT_WOMEN`/`_PREGNANT_WOMAN` mismatch) **must be reversed** in the same PR as CFG-1 and
      PIPE-5 respectively.
- [ ] Cut **`v1.0.0`** (first production release).

### Phase 6 — New template set (for teams not using the deployer)
- [ ] Create a dedicated publishing workspace for the new templates (it does **not** replace
      `snt-development`, which keeps publishing the old templates from the old repo, D-4).
- [ ] Name the templates according to the S3 result, so template-created codes = `snt-<name>`.
- [ ] Enable `push_templates.yaml` (written in Phase 3 commit 9: full releases only, every pipeline
      on each, decided 2026-11-13).
- [ ] Publish each pipeline as a template by hand once in the publishing workspace, and each
      pipeline added later, before relying on either template workflow (`push_templates.yaml`,
      `release.yaml`'s bootstrap job). A push is expected to publish a template version only onto a
      pipeline that is already a template's source, so a first push only creates a plain pipeline.
      Spike S6 tested only the template-source case: check the first-push behaviour when enabling.
- [ ] Choose the R-half route for template users per OD-9: self-sync, or Pull scripts with `snt_lib`
      (today `snt_lib` hardcodes the shared `code/` path and the `snt_development` repo name; see the
      2026-11-09 correction under Phase 1 "Facts checked")
      accepting repo + ref + path mapping (pinned `snt_lib` release).
- [ ] Bootstrap pipelines as templates (D-17): enable the bootstrap job of `release.yaml` once the
      publishing workspace exists. That solves the chicken-and-egg problem (bootstrap roadmap §3). The
      new-workspace guide must say to switch **auto-update on** for each bootstrap pipeline: it is
      off by default (S6).
- [ ] Verify: a fresh workspace built from the new templates, then the checker run against the
      matching tag, gives `match`. Then switch it to the deployer and check it adopts the pipelines
      without duplicates.

### Phase 7 — Webapps on the release train (D-2)
- [ ] The orchestrator reads `version.json` from its bundle and shows it in the footer (REL-1). The
      release zips carry it since Phase 3 commit 8: `version`, `commit`, `built_at`
      ([`release_manifest.md`](../contracts/release_manifest.md#release-assets-beside-the-manifest)).
- [ ] Manual deploy route documented in `docs/RELEASES.md`: download `webapp-<name>-<tag>.zip` from
      the release and upload it. Never deploy from `main`.
- [ ] Checker: compare the deployed webapp files with the manifest hashes (needs the files to be
      readable; S5).
- [ ] Deployer webapp support (REL-2), gated on S5 / OpenHEXA OH-4. Scopes stay manual (they aren't
      part of the bundle).
- [ ] Keep the runtime contracts unchanged: webapp slug `snt-pipelines-orchestrator-cockpit`, bucket key
      `utils_pipelines/…` (APP-12), template name `Create pipeline_cards.json`, `GENERATOR_KEY_MATCH`.

### Phase 8 — Adoption and sunset
- [ ] New country workspaces start from the new repo (deployer or new templates).
- [ ] Optional migration guide for existing workspaces: it is a re-bootstrap into a **new** workspace,
      not an in-place change.
- [ ] Old repos: README banner "Moved → new repo", then `snt_development` goes maintenance-only (D-4).
      `snt_webapp_orchestrator`, `snt_workspace_bootstrap` and the config editor freeze right after
      Phase 1 (they have no live-country CI, apart from `create_pipeline_cards` publishing from
      `snt-development`; keep that workflow alive until Phase 6).
- [ ] Archive criteria for `snt_development`: no workspace subscribed to the old templates **and**
      none using Pull scripts against it. An archived public repo stays readable, so Pull scripts keeps
      working even after archiving. Confirm the repo's visibility first.

---

## 6. Risks of a single repo for pipelines + webapps (and mitigations)

| Risk | Mitigation |
|---|---|
| A webapp fix has to wait for or ship with pipeline changes (one train) | Patch releases are cheap: the deployer skips unchanged pipelines (D22). Release from `main` only when `main` is green on an rc |
| CI blast radius: one merge triggers unrelated deploys | Path-scoped jobs. Templates publish on release, not on every merge |
| Mixed toolchains (Python, R notebooks, plain JS, pytest) | One conda env, one `pyproject.toml`. JS stays no-build (ADR 0016), so it needs no toolchain |
| Agent context bloat in a bigger repo | Root CLAUDE.md is a router only. Nested CLAUDE.md per area (`pipelines/`, `webapps/`, `webapps/<app>/`) loads lazily |
| Public exposure grows (more docs, research, workspace names) | Phase 0 audit. R1 stays enforced. Public webapps already must not hold secrets (ADR 0022) |
| Deployer downloads the whole repo tarball | Slim release tarball asset (Phase 3) |
| Everyone with write access can change everything | Branch protection. CODEOWNERS per area declined for now (D-15); to be discussed with the team |
| `.gitignore` `*.json` trap silently drops webapp/contract JSON | Allowlist + `git check-ignore` check in Phase 1 |
| Webapp deployment still can't be automated (no CLI/SDK route, OH-4) | Not caused or fixed by the monorepo. Stamped zips make the manual route reproducible |
| Two live systems (old repo/templates + new) for a long period | D-4 maintenance-only + explicit archive criteria |
| `snt_lib` stays external for now: config, Pull-scripts and path changes still need cross-repo PRs | Pin a tag (D-3). Plan `snt_lib` releases as named steps in Phases 1, 5 and 6. Long term: bring it in (§10) |

## 7. Further issues found in the existing docs

- **The deployer can't see template-created pipelines** (it looks up by code only). Covered by S3 and
  the checker mapping.
- **CI drift in the old repo:** `readme.txt` filters, the `worlpopclient.py` typo, and
  `snt_metadata_json_trim` with no push workflow. Discovery-based CI removes this class of bug.
- **Workflow typos aside**, `generate_manifest.yaml`'s depth-1 `*/pipeline.py` anchor was the only
  thing excluding `dev/` and `deprecated/`. The new builder needs explicit roots.
- **ID collisions** across the three backlogs and rule registers. Handled in Phase 2.
- **Webapp scopes are metadata, not bundle files.** Any deploy route has to set them separately.
- **No repo in the release marker**, so tags from different repos would collide. Harmless today (D-8),
  but Phase 4 still adds `repo` to the marker.
- **Config editor ↔ pipelines duplication:** `validate_config()` lives in Python (`snt_lib`) and in
  the editor's JS, and nothing keeps them in agreement. Handled by the conformance fixtures (Phase 3).
  Server-side validation (editor spec §12.2 option 4) arrives naturally with CFG-4's validating pipeline.
- **The editor writes to the workspace, but the orchestrator only has `FILES_READ`.** The write
  mechanism and scopes are unverified (editor EXTERNAL_CHECKS item 4). Fold this into S5.
- **`snt_lib@release-v1` is unpinned** (tag or branch is unverified). D-3 pins it.
- **The tag ruleset is not yet on `BLSQ/snt_development`.** Set it on the new repo from day one.
- **The licence is provisional** (DOC-5). The repo went public under MIT on 2026-11-05; a later
  change applies only to versions released after it, never to copies already taken under MIT.

---

## 8. Verification (end-to-end, per milestone)

- **Every PR:** `ruff check .`, `pytest`, schema validation, link check (CI from Phase 3; run them by
  hand before that).
- **Phase 1:** `git check-ignore` audit. Every imported file traced to the provenance table. Zero
  notebook outputs (`nbstripout --verify`-style check).
- **Phase 4 rc:** fresh test workspace via the deployer, then the checker reports `match` on all
  pipelines and files. One-country SNT chain outputs match an old-repo workspace (same filenames, same
  columns, same row counts).
- **Phase 5:** each breaking change on its own rc, re-running the affected pipelines plus the
  orchestrator in the test workspace.
- **Phase 6:** template-built workspace has codes = `snt-<name>`. The checker reports `match`. The
  deployer takes it over without duplicates.
- **Phase 7:** the footer shows the tag. The checker's webapp hash comparison matches.

## 9. Session log

| Date | Session summary | Next step |
|---|---|---|
| 2026-11-02 | Read md docs of snt_development, orchestrator, bootstrap, config editor. Agreed D-1…D-10 (D-10 = docs placement rule); plan made public in `docs/`; OD-4 has a leaning, not decided; S2(b) self-sync preferred | Phase 0: skeleton diff, spikes S1–S4, public-exposure audit |
| 2026-11-03 | Phase 0, desk half: skeleton diff (dev copy wins; `null` vs `""` to settle), S1 read from the SDK source (recurses; extension allowlist excludes `.json`; ignores `.gitignore`), S3 and S4 schema checks, first-pass public audit. Toy pipeline `spike_monorepo_layout` written for S1/S2. Then on OpenHEXA: **S1, S2a, S2b and S4 passed**. S3 showed that the code comes from the source pipeline, not from the template name, with a random suffix on collision. Decided D-11 (`null`), D-12 (report-only, was OD-7), D-13 (keep Jira links + dev slugs, leave out country notebooks); D-5 confirmed; OD-10 opened (versioning country/analyst-edited notebooks) | Glossary link kept (public by choice); DHS notebook stripped on `main`. Left: delete the spike pipelines + template; second audit pass at the start of Phase 1 |
| 2026-11-05 | Phase 1 prepared: checked the four source trees and `snt_lib` (no hardcoded shared `code/`, so the rename needs no release); wrote the Phase 1 runbook (mapping, steps P1-0…P1-11, commit sequence). Local spike code kept in `ignore/spikes/` | P1-0, then P1-1 (land the runbook), then P1-2 (create the repo) |
| 2026-11-05 | Phase 1 executed, P1-0…P1-8. `BLSQ/snt-stratification` created **private**; `main` seeded with the README stub and `.claude/`, then protected (`main` and `v*` rulesets). Source SHAs (P1-5; full SHAs in the README Provenance table): `snt_development` `94cfc38`, `snt_webapp_orchestrator` `603a831`, `snt_workspace_bootstrap` `abbe8c0`, `openhexa-webapps-edit-snt-config-json` `bd0cbf9`. Second audit pass **passed**. Branch `phase-1/snapshot-import` built as commits 1–9. Deviations: [Phase 1 results](#phase-1-results) | P1-9 (verify, paste results into the PR description), push, open the PR; P1-10 merge with a merge commit, then decide on public (DOC-5); P1-11 pointer PR in `snt_development` |
| 2026-11-05 | **Phase 1 closed.** P1-9 passed (results in the import PR description). Import PR merged with a merge commit. Repo made **public** under MIT; DOC-5 stays open as a later review (P1-10). `snt_development` pointer PR done (P1-11): its plan is now a pointer to this file, and it is maintenance-only (D-4) | Phase 2 — docs and agent setup |
| 2026-11-06 → 09 | Phase 2 started on `phase-2/docs-and-agents`. Settled D-14 (one ADR sequence), D-15 (no CODEOWNERS for now), D-16 (Register IDs); `release` skill moved to Phase 4. Commits 1–4: plan, ADR import (0010–0035), new ADRs 0036–0041, one BACKLOG. Local memory moved to Giulia's global CLAUDE.md; `ignore/` sweep done. R6 answered and a Phase 1 fact corrected (`snt_lib` hardcodes `code/` for `Pull scripts`) | Commit 5 in a new session: see the Phase 2 hand-off |
| 2026-11-09 | Phase 2 commits 5–8: root `CLAUDE.md` router with the merged Register R1–R26, `webapps/CLAUDE.md` W1–W9, bootstrap rules into `pipelines/CLAUDE.md` (interim `docs/bootstrap/CLAUDE.md` retired); `docs/ARCHITECTURE.md`; skills updated; deviations in [Phase 2 results](#phase-2-results) | Push, open the Phase 2 PR, merge it with a merge commit. Then Phase 3: settle OD-4 first |
| 2026-11-12 | Phase 3 opened on `phase-3/tooling-and-ci`. **OD-4 settled as D-17**: bootstrap pipelines as templates published on each full release, plus a guarded deployer self-update (never downgrades), bootstrap in the manifest as `kind: bootstrap`. Options A (templates from `main`) and C (no templates, CLI first push) rejected, reasons in the commit 2 hand-off. Spike S6 passed in `snt-development-sandbox` → `snt-testing`; auto-update is off by default ([Phase 3 findings](#phase-3-findings)). Commit 1 written | Commit 1, then commit 2 (ADR 0042 + current-truth fixes) in a new session |
| 2026-11-12 | Phase 3 commits 2–6: ADR 0042; two R23 fixes (templates are not being retired); manifest v2 schema (`filesystem_files`, `webapps` now, v1 file kept until Phase 4); `tools/build_manifest.py`; config conformance fixtures, `snt_lib` pinned to `v1.0.2` for the test. Order 5–9 chosen. Found: `release-v1` is a branch (DEP-1). `BLSQ/snt_utils` cloned at `~/Bluesquare/snt_utils` for reading `snt_lib` | Commit 6a (this log + hand-off), then commit 7 `ci.yaml` in a new session: see the [Phase 3 hand-off](#phase-3--tooling-and-ci) |
| 2026-11-13 | Phase 3 commit 7: `ci.yaml` (jobs `checks` and `pytest`), `tools/check_links.py` (ported, now over git's file list so `.claude/` is checked), `tools/check_tracked_files.py` (R1/R2); TOOL-2, 5, 7 closed, TOOL-6 narrowed (the orchestrator contracts are prose, not JSON Schema); R1, R2, R18 now `enforced`. Commits 7a–7b: `contracts/snt_config/README.md` aligned with D-11, the old `snt_config_json/` name replaced. CI has not run yet: it runs once the Phase 3 PR is open | Commit 7c (this log + hand-off), then commit 8 `release.yaml` in a new session: step 0 is the first CI result, then four questions — see the [Phase 3 hand-off](#phase-3--tooling-and-ci) |
| 2026-11-13 | Phase 3 commit 8. First CI run on the Phase 3 PR green (`pytest` 98 passed, 0 skipped). Decided: `version.json` = tag, commit, build time; slim tarball `snt-stratification-<tag>.tar.gz` with one top folder; `gh release upload`; a manual-run trigger for testing before `v0.1.0`. `release.yaml` written (assets job; bootstrap-templates job disabled) with `tools/build_release_assets.py` and 17 tests; R23 fixes in `contracts/`, `CLAUDE.md`, `ARCHITECTURE.md`, `CONVENTIONS.md` (approved beyond the plan's scope) | Commit 8a (this log + hand-off), then commit 9 `push_templates.yaml` in a new session: step 0 is the CI result on commit 8, then three questions — see the [Phase 3 hand-off](#phase-3--tooling-and-ci) |
| 2026-11-13 | Phase 3 commit 9. CI green on every commit through 8a; `checks` and `pytest` to become required in the `main` ruleset. Decided for `push_templates.yaml`: full releases only, its own file, every pipeline on each release. Written and disabled, with R23 fixes (`CLAUDE.md`, `ARCHITECTURE.md`; TOOL-8 no longer reaches OpenHEXA from this repo). New Phase 6 item: publish each pipeline as a template by hand once. Phase 3 checklist complete | Commit 9a (this log + hand-off), then close Phase 3: CI on 9a, PR description, merge — see the [Phase 3 hand-off](#phase-3--tooling-and-ci) |
| 2026-11-13 | Phase 3 merged. Phase 4 opened on `phase-4/bootstrap-monorepo`. **OD-6 settled as D-18**: releases are tested as pre-releases of this repo, not in `snt_development_sandbox`. Commit table 1–9 written, with the questions each commit must ask first. Commit 1 written | Commit 1, then commit 2 (deployers read manifest v2): ask the slim-tarball question first — see the [Phase 4 table](#phase-4--bootstrap-adapted-to-the-monorepo) |
| 2026-11-13 | Phase 4 commits 2–5, CI green through commit 4. Deployers read manifest v2 from the **slim tarball**; bootstrap guard by **`published_at`** (no full release yet = every release newest); `.snt_release` records `repo`, and a marker from another repository is not used as the checker's target; checker reads v2 (inert copies = zip-only files on the filesystem, `shipped` counts copies). `pytest` 119 passed, 16 skipped locally | Commit 5a (this log + hand-off), then commit 6 in a new session: three questions first — see the [commit 6 hand-off](#phase-4--bootstrap-adapted-to-the-monorepo) |

---

## 10. Long term: bring `snt_lib` (and a companion R library) into the monorepo

Not scheduled. Start only once Phases 0–5 are done **and** the colleague who maintains
`BLSQ/snt_utils` agrees. Until then D-3 applies (external, pinned).

**Why:** `snt_lib` holds config loading, `validate_config()`, `pull_scripts_from_repository` and
`save_pipeline_parameters`, which are exactly the code the bold changes touch (config split, config
as dataset, dataset-key naming, Pull-scripts retirement, provenance/`RUN_MODE`). As an external repo,
each of those becomes a two-repo, two-release change. Inside the monorepo it is one PR, versioned by
the same release tag as the pipelines that call it.

**Target:**
```
packages/
├── snt_lib/            ← Python package (pyproject.toml, src/snt_lib/, tests/)
│                          installed by pipelines as
│                          snt_lib @ git+https://github.com/BLSQ/snt-stratification@<tag>#subdirectory=packages/snt_lib
└── snt_r/              ← companion R library replacing shared/r/*.r (and duplicated pipelines/*/utils/*.r
                           helpers where they are really shared), e.g. an R package installable with
                           remotes::install_github("BLSQ/snt-stratification", subdir = "packages/snt_r", ref = "<tag>")
```

**Steps:**
1. Agree ownership and review with the `snt_utils` maintainer (record it in `docs/OWNERSHIP.md`).
   List its other consumers outside SNT, if any. They keep using the old repo or switch to the
   subdirectory install.
2. Freeze `BLSQ/snt_utils` at a final tag. Import that snapshot into `packages/snt_lib/`
   (provenance recorded, no history, same as D-1).
3. Add `packages/snt_lib` tests to `ci.yaml`. The conformance fixtures (`contracts/snt_config/fixtures/`)
   then test the real `validate_config()` in-repo.
4. Switch every `requirements.txt` to the subdirectory install at the release tag. The release builder
   must **stamp the tag** into requirements at release time (or the pipelines pin `@main` by
   mistake). Add a CI check for that.
5. Banner + archive `BLSQ/snt_utils`.
6. R companion (separate, later). Decide the delivery route first: a filesystem-synced folder (as
   `shared/r/` is today) vs an R package installed at runtime vs baked into the workspace image
   (OH-3 / DEP-2). Only then migrate `shared/r/` into `packages/snt_r/`. Each notebook's
   `source(...)` becomes `library(snt_r)` in one sweep.

**Risk:** a pip install from a monorepo subdirectory downloads the whole repo archive. Keep the repo
lean (no large binaries) or publish wheels as release assets.
