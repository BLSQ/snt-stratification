# Architecture — the system map

How the parts of `snt-stratification` fit together: the units, the contracts between them, how
each reaches a workspace, and how they are released. One page, then links. Part 2 explains the
OpenHEXA words used here for readers new to the platform.

The data side — what each SNT pipeline reads and publishes — is
[`DATA_ARCHITECTURE.md`](DATA_ARCHITECTURE.md). The rules are in the root
[`CLAUDE.md`](../CLAUDE.md#register).

> **Two systems are live during the migration.** Country workspaces run the old `snt_development`
> repo, its CI and its templates. The routes from this repo marked *(not built)* below arrive in
> the phases of [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md). Until then, merging here deploys nothing.

---

## Part 1 — The map

### 1.1 Units

A **unit** is something deployed on its own. Each is one folder (R26).

| Unit | Folder | What it does |
|---|---|---|
| **SNT pipelines** (20, `kind: snt`) | `pipelines/<name>/` | Turn DHIS2 routine data and external sources into ADM2-level data layers, published as OpenHEXA datasets. Python orchestrates; R notebooks compute |
| **Shared R library** | `shared/r/` | `snt_utils.r`, `snt_report.r`, `snt_palettes.r`, sourced by the notebooks |
| **Support pipelines** (2, `kind: support`) | `pipelines/create_pipeline_cards/`, `pipelines/snt_metadata_json_trim/` | Build the orchestrator's catalog; trim the SNT Explorer master list to one workspace |
| **Bootstrap pipelines** (3, `kind: bootstrap`) | `pipelines/snt_workspace_deployer/`, `snt_pipeline_deployer/`, `snt_workspace_checker/` | Install a release (whole, or one pipeline) into a workspace; check which release a workspace matches |
| **Orchestrator webapp** | `webapps/orchestrator/` | Guided, bilingual cockpit: see the status of each SNT pipeline, configure it and run it |
| **Config editor webapp** | `webapps/config_editor/` | Produce a valid `SNT_config.json`. Spec stage, no code yet |

Kinds are recorded in [`pipelines/registry.json`](../pipelines/registry.json), not in the path:
the repo path of every file that lands in a workspace equals its workspace path
([ADR 0038](decisions/0038-repo-path-is-workspace-path.md)).

### 1.2 How they connect

```
                         GitHub release vX.Y.Z  (+ release_manifest.json)
                                       │
                                       ▼  (not built for this repo: Phase 4)
                     ┌─────────── bootstrap pipelines ───────────┐
                     │ deployer: installs     checker: compares  │
                     │ files + pipelines,     workspace ↔ release│
                     │ writes .snt_release    → status report    │
                     └─────────────────────┬─────────────────────┘
                                           ▼
 ┌───────────────────── one OpenHEXA workspace (one country) ─────────────────────┐
 │                                                                                │
 │  configuration/SNT_config.json ◄── operator by hand / config editor (planned)  │
 │          │ read by every pipeline                                              │
 │          ▼                                                                     │
 │  SNT pipelines ── run ──► pipelines/<name>/code/*.ipynb + shared/r/*.r         │
 │          │                                                                     │
 │          ▼ add_files_to_dataset(...)                                           │
 │  OpenHEXA datasets ──► next SNT pipeline (no DAG: a person presses Run)        │
 │          │                                                                     │
 │          ├──────────────────────────────────────────────► SNT Explorer (IASO)  │
 │          │                                                        ▲            │
 │          └──► snt_metadata_json_trim ──► SNT_METADATA dataset ────┘            │
 │                  ▲ catalogs/SNT_metadata_master.json                           │
 │                                                                                │
 │  create_pipeline_cards ── reads deployed pipelines ──► pipeline_cards.json     │
 │                                                        + readmes/ (bucket)     │
 │                                                              │                 │
 │  orchestrator webapp ◄───────────────────────────────────────┘                 │
 │          └── starts runs of the SNT pipelines                                  │
 └────────────────────────────────────────────────────────────────────────────────┘
```

Every arrow that crosses a unit boundary is a **contract**: a file whose shape another unit
depends on. The list, with producer, consumers and schema for each, is
[`contracts/README.md`](../contracts/README.md). The main ones:

- **`SNT_config.json`** — operator or config editor → every pipeline.
- **Datasets and their files** — each SNT pipeline → downstream pipelines and the SNT Explorer
  ([`DATA_ARCHITECTURE.md` §3](DATA_ARCHITECTURE.md#3-data-lineage)).
- **`SNT_metadata.json`** — master list → `snt_metadata_json_trim` → SNT Explorer.
- **`pipeline_map.json`, `pipeline_descriptions.json`, `pipeline_cards.json`** — orchestrator ↔
  `create_pipeline_cards`.
- **`release_manifest.json`, `.snt_release`, the status report** — release ↔ deployer ↔ checker
  (R22).

### 1.3 Deploy routes

How each kind of file reaches a workspace. A Python pipeline and its R half travel separately,
because OpenHEXA runs Python pipelines but not R ([Part 2](#part-2--openhexa-in-plain-words)).

| What | Route | State |
|---|---|---|
| `pipeline.py` + `requirements.txt` | **Old templates**: the old repo's CI pushes to `snt-development`, which publishes a new template version; subscribed countries update automatically (R5) | **Live**, old repo only |
| | **Deployer**: installs every pipeline of a release | Built, not run for this repo (Phase 4) |
| | **New templates**, from their own publishing workspace, codes `snt-<name>` ([ADR 0040](decisions/0040-templates-kept-alongside-the-deployer.md), [0041](decisions/0041-new-templates-publishing-workspace.md)) | Not built (Phase 6) |
| R half: notebooks, `utils/*.r`, `shared/r/` | **`Pull scripts` = ON** in a run: `snt_lib` copies them from GitHub (R6) | **Live**, old repo only (`snt_lib` hardcodes it) |
| | **Deployer**: copies them to the workspace filesystem | Built, not run for this repo (Phase 4) |
| | **Self-sync**: a pipeline copies its bundled R half on start | Proven in a spike; not built (OD-9) |
| Country variants `<name>_<CC>.ipynb` | None: edited in the country's workspace only | By design ([ADR 0003](decisions/0003-country-variants-outside-pull-scripts.md)) |
| Webapp bundle `webapps/<name>/app/` | Uploaded by hand (drag-and-drop or MCP), scopes set separately ([`DEPLOYMENT.md`](../webapps/orchestrator/docs/DEPLOYMENT.md)) | **Live**; release zips in Phase 7 |
| `catalogs/*.json` | Downloaded at run time from a GitHub release by the pipeline that needs it | **Live**, from the old repo |

A workspace must not receive the same pipeline from a template subscription and the deployer at
once.

### 1.4 Release train

**One tag `vX.Y.Z` = one tested combination** of pipelines, webapps and bootstrap
([ADR 0037](decisions/0037-one-release-train.md)). The release carries `release_manifest.json`,
which lists every file it ships with its hash; the deployer installs exactly that list, and the
checker compares a workspace against it. `v0.x.y` are pre-releases for testing; `v1.0.0` is the
first production release. A webapp-only fix is a patch release.

*(Not built: the release workflow, manifest v2 and stamped webapp zips are Phases 3, 4 and 7.)*

### 1.5 Where docs live

A unit's own docs live with the unit; docs that span several units live in `docs/`
([ADR 0039](decisions/0039-docs-placement-rule.md), R26):

| Covers | Lives in |
|---|---|
| One pipeline | its `readme.md` — ships in the zip, so no `docs/` folder and no `CLAUDE.md` there |
| Several pipelines of one area | `docs/<area>/`, e.g. [`docs/bootstrap/`](bootstrap/) |
| One webapp | `webapps/<name>/docs/` and `design/`, beside the deployed `app/` |
| A contract | its folder in `contracts/` |
| The whole system or several units | `docs/`: this file, `DATA_ARCHITECTURE.md`, `CONVENTIONS.md`, `GLOSSARY.md`, ADRs, `BACKLOG.md` |
| Rules for agents and humans | root `CLAUDE.md`, plus `pipelines/CLAUDE.md`, `webapps/CLAUDE.md`, `webapps/<name>/CLAUDE.md` |

---

## Part 2 — OpenHEXA in plain words

For anyone new to OpenHEXA or arriving from other data stacks.

### 2.1 What is not here, and why

Most data teams expect an orchestrator, dbt and a test suite. What each would give you, and what
stands in for it here:

| Term | What it normally gives you | Here |
|---|---|---|
| **Airflow / Dagster** | An *orchestrator*: runs jobs in dependency order, on a schedule, retries failures, keeps a history | A person clicks **Run** in OpenHEXA, one pipeline at a time |
| **DAG engine** | The part that knows "formatting must finish before incidence starts" (a **D**irected **A**cyclic **G**raph) and enforces it | That knowledge lives in people and docs. Nothing enforces it — deliberately ([ADR 0001](decisions/0001-no-dag-engine.md)) |
| **dbt** | SQL transformations with lineage, data tests and docs | Not applicable: the analytics are R |
| **Test suite** | Checks that catch a broken change before a user does | Only for the bootstrap pipelines and contracts (`pytest`); debt for the rest |
| **Local runtime** | Running the code on your laptop | Partial: R runs on the workspace kernel ([`dev/README.md`](../dev/README.md)) |

A DAG engine would fight how SNT is used: pipelines are re-run independently with different
parameters, alternative methods overwrite each other on purpose
([ADR 0002](decisions/0002-alternative-methods-last-run-wins.md)), and an operator may supply their
own input instead of running the upstream pipeline. The run order should still be written down; it
is not yet ([DOC-1](BACKLOG.md#doc-1)).

### 2.2 The parts of a workspace

**The key fact:** OpenHEXA never runs a pipeline from the files you see in the workspace. Deploying
uploads a zipped copy of the pipeline's code into OpenHEXA's database, and a run downloads that zip.

| Part | What it holds | Where you see it |
|---|---|---|
| **Files** (the bucket) | Data, notebooks, R scripts, outputs, `configuration/SNT_config.json` | The Files tab, and Jupyter |
| **Pipelines registry** (a database) | One record per pipeline (e.g. `snt-dhis2-extract`), each with a list of versions | The Pipelines tab |
| **Pipeline version** | One zip of the code, plus its parameters and timeout | A pipeline's version list |
| **Datasets** | Versioned published outputs: the contract between pipelines | The Datasets tab |
| **Connections** | Stored credentials (DHIS2, a workspace token, …) | Settings → Connections |
| **Runner** | A temporary container that runs one pipeline run, then stops | The run logs |

The Files area and the Pipelines registry are separate: copying a new `pipeline.py` into Files does
not change the pipeline that runs.

### 2.3 What happens when you run a pipeline

1. You click **Run** and choose the parameters.
2. OpenHEXA starts a new container, the runner, from the workspace's image.
3. The runner downloads the zip of the pipeline's **current version** and calls its `@pipeline`
   function.
4. The code reads and writes the Files area and publishes to datasets. SNT pipelines run their R
   notebooks **from the Files area**, not from the zip.

So in SNT, the Python comes from the zip and the R comes from the Files area. A deployment has to
update both places, which is why §1.3 has two rows per pipeline.

### 2.4 Images and containers

| Term | Plain meaning | Analogy |
|---|---|---|
| **Image** | A frozen snapshot of a computer: OS, Python, R, installed packages | A recipe with every ingredient included |
| **Container** | A running copy of an image, with its own memory and temporary disk | One meal cooked from the recipe |

Each run gets a fresh container, which is deleted when the run ends. So:

- The packages a run sees come from the image (for SNT,
  [`DATA_ARCHITECTURE.md` §7.4](DATA_ARCHITECTURE.md#74-the-workspace-runtime-image)) plus the
  pipeline's `requirements.txt` (how that is resolved: [DEP-1](BACKLOG.md#dep-1)).
- Anything written outside the Files area is lost when the run ends. The Files area is cloud
  storage that exists without any container; OpenHEXA connects it to a folder inside each
  container, and Jupyter is another container connected to the same storage. That is why pipeline
  outputs show up there.

### 2.5 What "deploying" a pipeline does

1. **Read the parameters.** The tool reads `pipeline.py` as text and finds the `@parameter`
   decorators, without running the code. A bad parameter fails the *deployment*, not the run.
2. **Zip the pipeline folder.** Only `.py .ipynb .txt .md .r .sql` files go in, so a
   `CLAUDE.md` in the folder would ship and a `.json` file would not.
3. **Send the zip to the OpenHEXA API**, which adds a row to the registry: a new pipeline with its
   first version, or a new version that becomes the current one. Old versions stay.

The parameters are stored twice, both from the same `pipeline.py`: the stored list draws the run
form in the UI (the web page cannot run Python), and the decorators inside the zip check the values
in the container.

Three tools start a deployment: the `openhexa` CLI on your computer (`openhexa pipelines push`),
GitHub Actions running that CLI (the old repo's CI), and the deployer pipeline inside OpenHEXA.
Deploying needs a workspace access token; the token each run receives can read code but not
deploy, which is why the deployer needs a connection holding one. Details:
[`bootstrap/openhexa_deployment.md`](bootstrap/openhexa_deployment.md).
