# Roadmap — toward the SNT workspace bootstrap

> What comes after the move: the bootstrap's starting problem, and web apps. Each heading says which
> parts are proposals. §1 and §2 (several release sources) were
> superseded in 2026-11 by the monorepo, §3 is mostly solved by
> [ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md), and §4 is built
> ([ADR 0048](../decisions/0048-workspace-deployer-installs-the-webapps.md)). A choice made from this file becomes an ADR in
> [`../decisions/`](../decisions/README.md) (or, for implementation detail, a `D<n>` in
> [`decisions.md`](decisions.md)), and its text moves to the component's spec. Written 2026-10-02
> (Session 5 of the move plan).

## The goal

Set up an empty SNT workspace from one release of this repository: every pipeline and the R
analytics, the checker, and the two OpenHEXA web apps (pipeline orchestrator, SNT_config editor).
Then move the workspace to newer or older releases on request
([ADR 0037](../decisions/0037-one-release-train.md)).

## 1. Sources replace `github_repo` — superseded

One repo and one release train ([ADR 0036](../decisions/0036-one-monorepo.md),
[ADR 0037](../decisions/0037-one-release-train.md)) leave a workspace with one release source, so the
multi-source proposal is not needed. Its text: [`HISTORY.md` §3.5](HISTORY.md#35-the-multi-source-roadmap--superseded-2026-11-by-the-monorepo).

## 2. This repository as a release source — superseded

The bootstrap pipelines now live in the monorepo, in the same release as everything else (same
history entry). How they reach a workspace is decided by
[ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md): as OpenHEXA templates
published on each full release, plus a deployer self-update that never downgrades. The evaluation
below was an input to it.

### Evaluated: deliver them as OpenHEXA template pipelines

**Settled 2026-11-12 by ADR 0042.** The points below were raised on 2026-10-02 (Giulia).

`snt_workspace_checker` and `snt_workspace_deployer` are pure Python. Unlike the `snt_development`
pipelines, they bring no R analytics to the filesystem, so a release of them may not need the
filesystem half at all. Whether they need *other* files on the filesystem is not known yet.

That raises the option of treating them like the other OpenHEXA template pipelines, instead of as a
release source of their own. Points to evaluate:

* **How the existing template pipelines are versioned.** Colleagues keep them in a dedicated
  repository; find out how it releases and deploys them.
* **Generic or SNT-specific.** Make the two pipelines generic and company-wide, or keep them
  SNT-specific.
* **Context stays with the code.** Both are tightly coupled to other repositories: the SNT pipelines
  now, the web apps next. Whatever delivers them must keep this repository's docs and contracts next
  to the Python code.
* **D20.** The template mechanism is being retired for the `snt_development` pipelines. Weigh whether
  that applies to these two as well, or only to pipelines that ship R alongside their Python.

## 3. The starting problem — solved by ADR 0042, except the `openhexa-deploy` connection

**The bootstrap cannot deploy itself into an empty workspace**: nothing exists there to run it.
[ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md) solves this without the
`openhexa` CLI. A new workspace installs the bootstrap pipelines once from their templates, which
are published on each full release, so it starts on the latest full release rather than on a
working tree. The deployer then deploys everything else, including newer versions of itself
(guarded: never an older release than the latest full one). Not built yet: Phases 3–4 of
[`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md); until then maintainers push them by hand.

One manual step stays:

* **The `openhexa-deploy` connection.** Deploying needs the workspace access token in a CUSTOM
  connection named `openhexa-deploy` ([`openhexa_deployment.md`](openhexa_deployment.md) §7.3b). Today that is a copy-paste.

## 4. Web apps (D8)

**Built (2026-11-27):** `snt_workspace_deployer` installs the web apps from the release
([ADR 0048](../decisions/0048-workspace-deployer-installs-the-webapps.md); how: the deployer's
[readme](../../pipelines/snt_workspace_deployer/readme.md), step 8). What follows is the research it
rests on.

**The API can create and update a static web app from files.** Read in `openhexa-sdk` 2.22.7's
GraphQL schema (`openhexa/graphql/schema.generated.graphql`) on 2026-10-02, and called from a
pipeline run by spike S5 on 2026-11-27 (results:
[`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md#phase-0-findings)).

| Operation | Takes | Notes |
|---|---|---|
| `createWebapp(input: CreateWebappInput!)` | `workspaceSlug`, `name`, `source`, optional `allowedOperations`, `isPublic`, `description`, `icon` | `source` is one of `static: [WebappFileInput!]` (the files), `iframe`, `superset`. Only `static` concerns the bootstrap (below) |
| `updateWebapp(input: UpdateWebappInput!)` | `id`, then optionally `files`, `filesToDelete`, `commitMessage`, `allowedOperations`, `publishedVersionId`, `name`, `subdomain`, … | Incremental: files left out are kept. `commitMessage` is accepted by the live server but missing from the 2.22.7 schema |
| `deleteWebapp(input: DeleteWebappInput!)` | `id` | |
| `webapp(slug, workspaceSlug)`, `webapps(workspaceSlug, …)` | | A `Webapp` has `versions`, `commitDiff(ref)`, `files(ref)` and a `GitSource { repository, publishedVersion }`: OpenHEXA keeps a static app's files in a git repository of its own |

`WebappFileInput` is `{path, content, encoding}`, with `encoding` `TEXT` or `BASE64`. So a release
of a web app's repository could, in principle, be uploaded file by file, like a pipeline zip.

**Every web app the bootstrap deploys is a static app** (Giulia, 2026-10-02): the pipeline
orchestrator, the SNT_config editor, and any later one. It never deploys an `iframe` or `superset`
app, so only the `static` source and the `files` / `filesToDelete` updates matter here.

**Answered by spike S5** (2026-11-27, `snt-app-dev`):

1. Which token may call `createWebapp` / `updateWebapp` from inside a pipeline run? **Only the
   `openhexa-deploy` token**: the run's own `HEXA_TOKEN` gets `PERMISSION_DENIED` on
   `createWebapp`, as for pipelines ([`openhexa_deployment.md`](openhexa_deployment.md#static-webapps-the-same-split)).
2. Can a web app's files be hashed as they are served? **Yes**: `webapp { files(ref) }` and
   `readWebappFile` return the content, with the run's own token, and it hashes to exactly what was
   uploaded.
3. How should a deploy name a version? **By its commit message**: `updateWebapp(commitMessage:)`
   becomes the version's message, so a version can carry the release tag. Each version's id is a git
   commit SHA. An update is published at once (the published version becomes the newest commit), so
   `publishedVersionId` is not needed to deploy.
4. Who decides `allowedOperations` per app, and are they part of a release? **They can be set by the
   deploy**: given at create, they read back exactly, and `updateWebapp` takes them too. The values
   are fixed per app: W8 for the orchestrator, [ADR 0047](../decisions/0047-config-editor-publishes-to-snt-configuration.md)
   for the config editor. A release carries them in each manifest webapp entry, from
   `webapps/<name>/webapp.json` ([`release_manifest.md`](../../contracts/release_manifest.md)).

Also found: there is no slug input, and the slug is the name lower-cased with spaces turned into
hyphens. A second create with a name already used is refused with `ALREADY_EXISTS`, but a different
name whose slug is taken creates a duplicate with a random suffix (`<slug>-fcb549`), with no error.
A deploy must therefore look an app up by slug before creating it.

Also for the devs, already written up elsewhere: deleting or archiving a pipeline from a run
([`deployer.md`](deployer.md) §7.5), and minting the `openhexa-deploy` token
([`openhexa_deployment.md`](openhexa_deployment.md) §7.3b).

## 5. Tracked elsewhere

The move plan's other Session 5 items. They are listed here so the roadmap is complete, and each
is described in its own file:

* ~~Switch the `github_repo` defaults from `BLSQ/snt_development_sandbox` to
  `BLSQ/snt-stratification`~~ Done in Phase 4 of [`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md).
* Finish the deployer's test plan, D21–D24 and `backup_existing` ([`deployer.md`](deployer.md)
  §6.7). Run by hand in a test workspace, against pre-releases of this repo (D-18).
* ~~Delete the pre-phase-0 fallback in `split_manifest()`~~ Deleted 2026-10-02 (D26,
  [`release_manifest.md`](../../contracts/release_manifest.md) §2.1).
