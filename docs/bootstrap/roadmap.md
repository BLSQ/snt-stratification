# Roadmap — toward the SNT workspace bootstrap

> What comes after the move: the bootstrap's starting problem, and web apps. Nothing here is built;
> each heading says which parts are proposals. §1 and §2 (several release sources) were
> superseded in 2026-11 by the monorepo, and §3 is mostly solved by
> [ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md). A choice made from this file becomes an ADR in
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

## 3. The starting problem — solved by ADR 0042, except the `oh` connection

**The bootstrap cannot deploy itself into an empty workspace**: nothing exists there to run it.
[ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md) solves this without the
`openhexa` CLI. A new workspace installs the bootstrap pipelines once from their templates, which
are published on each full release, so it starts on the latest full release rather than on a
working tree. The deployer then deploys everything else, including newer versions of itself
(guarded: never an older release than the latest full one). Not built yet: Phases 3–4 of
[`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md); until then maintainers push them by hand.

One manual step stays:

* **The `oh` connection.** Deploying needs the workspace access token in a CUSTOM connection named
  `oh` ([`openhexa_deployment.md`](openhexa_deployment.md) §7.3b). Today that is a copy-paste.

## 4. Web apps (D8)

**The API can create and update a static web app from files. Read in `openhexa-sdk` 2.22.7's
GraphQL schema (`openhexa/graphql/schema.generated.graphql`) on 2026-10-02; never called.**

| Operation | Takes | Notes |
|---|---|---|
| `createWebapp(input: CreateWebappInput!)` | `workspaceSlug`, `name`, `source`, optional `allowedOperations`, `isPublic`, `description`, `icon` | `source` is one of `static: [WebappFileInput!]` (the files), `iframe`, `superset`. Only `static` concerns the bootstrap (below) |
| `updateWebapp(input: UpdateWebappInput!)` | `id`, then optionally `files`, `filesToDelete`, `allowedOperations`, `publishedVersionId`, `name`, `subdomain`, … | Incremental: files left out are kept |
| `deleteWebapp(input: DeleteWebappInput!)` | `id` | |
| `webapp(slug, workspaceSlug)`, `webapps(workspaceSlug, …)` | | A `Webapp` has `versions`, `commitDiff(ref)`, `files(ref)` and a `GitSource { repository, publishedVersion }`: OpenHEXA keeps a static app's files in a git repository of its own |

`WebappFileInput` is `{path, content, encoding}`, with `encoding` `TEXT` or `BASE64`. So a release
of a web app's repository could, in principle, be uploaded file by file, like a pipeline zip.

**Every web app the bootstrap deploys is a static app** (Giulia, 2026-10-02): the pipeline
orchestrator, the SNT_config editor, and any later one. It never deploys an `iframe` or `superset`
app, so only the `static` source and the `files` / `filesToDelete` updates matter here.

**Not known yet: test first in the sandbox, ask the OpenHEXA devs only if a test hits a wall.**

1. Which token may call `createWebapp` / `updateWebapp` from inside a pipeline run: the run's own
   `HEXA_TOKEN`, or only the `oh` workspace token? The same question for pipelines had a non-obvious
   answer ([`openhexa_deployment.md`](openhexa_deployment.md), Authentication), and was settled the
   same way, by trying both.
2. Can a web app's files be hashed as they are served (through `files(ref)`)? The checker needs that
   to tell which release an app is at, the way it reads a pipeline version's zip.
3. How should a deploy name a version? `updateWebapp` takes a `publishedVersionId`. Can a version
   carry the release tag, the way pipeline versions do (D22)?
4. `allowedOperations` grants the app's own GraphQL scopes. Who decides those per app, and are they
   part of a release?

Also for the devs, already written up elsewhere: deleting or archiving a pipeline from a run
([`deployer.md`](deployer.md) §7.5), and minting the `oh` token
([`openhexa_deployment.md`](openhexa_deployment.md) §7.3b).

## 5. Tracked elsewhere

The move plan's other Session 5 items. They are listed here so the roadmap is complete, and each
is described in its own file:

* Switch the `github_repo` defaults from `BLSQ/snt_development_sandbox` to
  `BLSQ/snt-stratification` ([`MIGRATION_PLAN.md`](../MIGRATION_PLAN.md) Phase 4).
* Finish the deployer's test plan, D21–D24 and `backup_existing` ([`deployer.md`](deployer.md)
  §6.7). Run by hand in the sandbox.
* ~~Delete the pre-phase-0 fallback in `split_manifest()`~~ Deleted 2026-10-02 (D26,
  [`release_manifest.md`](../../contracts/release_manifest.md) §2.1).
