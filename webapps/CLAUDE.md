# `webapps/` — rules for the OpenHEXA webapps

Loaded by Claude Code only when files under `webapps/` are read; the root
[`../CLAUDE.md`](../CLAUDE.md) still applies in full (guardrails, R1–R26). Each app has its own
`CLAUDE.md` for its code: [`orchestrator/`](orchestrator/CLAUDE.md),
[`config_editor/`](config_editor/CLAUDE.md).

Two webapps, each in `webapps/<name>/` with `app/` (the deployable bundle, the only part deployed),
`docs/` and `design/` (R26):

- **`orchestrator/`** — the SNT Pipelines Orchestrator: one static webapp, identical in every
  workspace, that presents the SNT pipelines as a guided, bilingual (EN/FR) walkthrough where users
  see status, configure and run each one. Its per-workspace catalog (`pipeline_cards.json`) is
  **not in the repo**: it lives in each workspace's bucket, written by
  [`create_pipeline_cards`](../pipelines/create_pipeline_cards/README.md). The repo is the reference
  source for the latest version, **not a record of what is deployed where**.
- **`config_editor/`** — produces a valid `SNT_config.json` (ticket SNT25-661). Spec stage: `app/`
  is empty.

## Working here

- **Hand small, faster-by-hand tasks back to the user** — looking up URLs/paths/IDs in the
  OpenHEXA UI, checking DevTools Console/Network, reading a value off a dashboard, visually
  confirming the running app, and **uploading a full bundle or a wholesale rewrite** (offer
  drag-and-drop from `webapps/<name>/app/` — wording in
  [`DEPLOYMENT.md`](orchestrator/docs/DEPLOYMENT.md#choosing-a-deploy-path)). Give a precise,
  copy-pasteable instruction, then wait; do not proceed on an assumption.
- **Ask which workspace** before any deployment or pipeline operation.
- Work is tracked in Jira (project `SNT25`, epic `SNT25-536`), managed by hand. Do not touch Jira
  unless asked in that session.

## Register

Webapp rules; the repo-wide ones are R1–R26 in the [root Register](../CLAUDE.md#register).
**Status:** `convention` — manual; treat as binding. **Old ID:** the rule's ID in
`snt_webapp_orchestrator` (its R1 is now R19, R11 is R26, R12 is R23 and R25).

| ID | Rule | Status | Why / detail | Old ID |
|---|---|---|---|---|
| W1 | The orchestrator's catalog is never in the repo or the bundle; no `workspaces/` folder | `convention` | [ADR 0011](../docs/decisions/0011-catalog-in-workspace-bucket.md) | R2 |
| W2 | Catalog drift is fixed by re-running `create_pipeline_cards`, never by hand-editing | `convention` | [ADR 0012](../docs/decisions/0012-catalog-parameters-from-deployed-version.md) | R3 |
| W3 | No fallback catalog: a missing catalog fails the boot with a diagnosis | `convention` | [ADR 0011](../docs/decisions/0011-catalog-in-workspace-bucket.md) | R4 |
| W4 | Node `id` = Python function name is the only cross-workspace key; UUIDs/catalogs never cross workspaces | `convention` | [ADR 0015](../docs/decisions/0015-node-id-is-python-function-name.md) | R5 |
| W5 | A bundle is flat, workspace-independent files in `app/`: no build, no CDN, no new script tags without review (sole exception: OpenHEXA's `dev.js`, never with slugs pinned) | `convention` | [ADR 0016](../docs/decisions/0016-multi-file-bundle-no-build.md), [ADR 0023](../docs/decisions/0023-ship-openhexa-dev-js.md) | R6 |
| W6 | Every chrome string in both `I18N.en` and `I18N.fr`; data text edited in both languages; structural fields never translated | `convention` | [ADR 0017](../docs/decisions/0017-one-bilingual-app.md), [app rules](orchestrator/CLAUDE.md#bilingual-text) | R7 |
| W7 | Dynamic values reaching `innerHTML` paths are escaped first | `convention` | [app rules](orchestrator/CLAUDE.md#html-injection-seam) | R8 |
| W8 | The orchestrator stays **private** and has exactly `PIPELINES_READ, PIPELINES_RUN, FILES_READ, USER_READ` | `convention` | [runtime](../docs/OPENHEXA_WEBAPP_RUNTIME.md#allowed_operations-scopes) | R9 |
| W9 | Deployments are resolved live, never recorded in the repo; diff live vs repo before editing a deployed file | `convention` | [ADR 0020](../docs/decisions/0020-repo-is-not-a-deployment-record.md) | R10 |

## Traps

- **Bucket key ≠ repo path.** `utils_pipelines/create_pipeline_cards/pipeline_cards/pipeline_cards.json`
  is a runtime path in every bucket: `CARDS_OBJECT_KEY` (`app.js`) ↔ `OUTPUT_DIR` +
  `WEBAPP_CARDS_PATH` (`config.py`), in lockstep. Do not "fix" it to match `pipelines/`
  ([APP-12](../docs/BACKLOG.md#app-12)). Same for the READMEs next to it: `README_DIR_KEY` (`app.js`)
  ↔ `OUTPUT_DIR` + `README_DIR` (`config.py`).
- **Generator after webapp.** `create_pipeline_cards` curates against the *deployed* map of
  `config.WEBAPP_SLUG` and fails if that webapp is absent.
- **`.io` vs `.org`.** Webapps are served on `*.openhexa.io`; the UI is `app.openhexa.org`. Never
  derive the app host from the webapp hostname.
- **Public webapps cannot call the proxy**; **`FILES_READ` is boot-critical**; the proxy also
  filters **nested fields**: `workspace { connections }` is refused even with `USER_READ`, so
  the connection dropdowns fall back to a text input ([OH-5](../docs/BACKLOG.md#oh-5)).
- **`workspace { pipelines }` does not parse** — use top-level `pipelines(workspaceSlug:)`.
- **`runPipeline.errors` is an enum**, never prose. **`terminating` is not terminal** — keep polling.
  Statuses are lowercase.
- **`.sb-runstatus` is a flex container** — a `<br>` does not break the line.
- **`get_static_webapp` is expensive** (every file inline, `app.js` ~100 KB). Use
  `get_static_webapp_file` for one file, `list_static_webapps` for scopes.

## Session start (orchestrator)

1. **UI work:** read [`PRODUCT_SPEC.md`](orchestrator/docs/PRODUCT_SPEC.md) (scope, v0/v1/v2) and
   the wireframe `orchestrator/design/wireframes/orchestrator_wireframe_cockpit.html`.
2. **Deployment or pipeline work:** ask which workspace; check its catalog with
   `list_files(workspace_slug, prefix="utils_pipelines/create_pipeline_cards/pipeline_cards/")`
   (note `updatedAt`). If missing, the app cannot boot there — ask the user to install and run
   `create_pipeline_cards` (after the webapp exists). Never build a catalog by hand.
3. **Before editing a deployed file:** resolve the webapp live and diff the live file against
   `webapps/orchestrator/app/` (W9).

## Where to find things

| Question | Go to |
|---|---|
| What the orchestrator does, roadmap, PM decisions | [`orchestrator/docs/PRODUCT_SPEC.md`](orchestrator/docs/PRODUCT_SPEC.md) |
| How its pieces fit: catalog, node states, map format, i18n tiers | [`orchestrator/docs/ARCHITECTURE.md`](orchestrator/docs/ARCHITECTURE.md) |
| OpenHEXA webapp know-how: proxy, scopes, queries, run errors, polling, signed URLs, `dev.js` | [`docs/OPENHEXA_WEBAPP_RUNTIME.md`](../docs/OPENHEXA_WEBAPP_RUNTIME.md) |
| Running the app locally against a real workspace | [`DEPLOYMENT.md`](orchestrator/docs/DEPLOYMENT.md#developing-locally) |
| Deploying (a CSS change, a full bundle, a new workspace), scopes, rollback, schema refresh | [`orchestrator/docs/DEPLOYMENT.md`](orchestrator/docs/DEPLOYMENT.md) |
| Field definitions of the orchestrator's JSON files | [`contracts/orchestrator/`](../contracts/orchestrator/) |
| The catalog generator | [`pipelines/create_pipeline_cards/README.md`](../pipelines/create_pipeline_cards/README.md) |
| The config editor's spec and the config contract | [`config_editor/CLAUDE.md`](config_editor/CLAUDE.md) |
| GraphQL types | grep [`reference/openhexa/schema.generated.graphql`](../reference/openhexa/schema.generated.graphql) |
| Pre-cut-over history, the parked Flowchart UI, old spikes | archived repo `BLSQ/OpenHEXA-WebApp-Diary` — [ADR 0022](../docs/decisions/0022-fresh-repo-without-history.md) |
