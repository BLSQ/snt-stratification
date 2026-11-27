# 0048. The workspace deployer installs the webapps

Date: 2026-11-27
Status: Accepted (supersedes bootstrap D8 for the deployer; the checker keeps D8)

## Context

Each release carries a stamped zip per webapp ([0037](0037-one-release-train.md)), but nothing
installs it: the orchestrator and the config editor are uploaded by hand, and their scopes are set
by hand. Bootstrap D8 left web apps out of the bootstrap pipelines, and the plan waited for an
OpenHEXA CLI or SDK command ([OH-4](../BACKLOG.md#oh-4)).

The team then agreed that the workspace deployer is the main route into a workspace, for pipelines
and webapps (migration plan D-23). Spike S5, on 2026-11-27, showed that the GraphQL API already does
the job with the token the deployer holds, the CUSTOM connection `openhexa-deploy`
([findings](../MIGRATION_PLAN.md#phase-0-findings),
[`openhexa_deployment.md`](../bootstrap/openhexa_deployment.md#static-webapps-the-same-split)).
`createWebapp` and `updateWebapp` accept the files, set the app private with its scopes, publish an
update at once and keep its commit message. The run's own token is refused for writes. A create
whose name slugs to a slug already taken makes a duplicate with a random suffix, with no error.

Options weighed:

- **Keep the manual route**: download the zip from the release, upload it, set the scopes.
  Rejected as the main route: scopes get forgotten, and nothing records which release an app is at.
  It stays as the fallback.
- **Wait for a CLI or SDK command (OH-4).** Rejected: S5 showed it is not needed.

## Decision

1. **`snt_workspace_deployer` installs every webapp the release manifest lists**, after the
   pipelines, in the same run, with the `openhexa-deploy` token. Both apps; the config editor first
   if only one is ready. `snt_pipeline_deployer` does not install webapps.
2. The files come from the release's `webapp-<name>-<tag>.zip` asset, never from `main`.
3. Each app is **looked up by its slug first**, never created blindly. If absent, it is created as
   a static, **private** app with its scopes. If present, it is updated (`files`, `filesToDelete`)
   with the release tag as the commit message. It is skipped when its served files already hash to
   the manifest's (bootstrap D22).
4. **Slug and scopes are fixed per app and carried by the release manifest**: the orchestrator's
   slug `snt-pipelines-orchestrator-cockpit` and its four scopes (W8), the editor's
   `PIPELINES_READ` and `PIPELINES_RUN` ([0047](0047-config-editor-publishes-to-snt-configuration.md)).
5. A dry run logs what it would do; a webapp that fails to install fails the run like a pipeline.
6. **This ships in `v1.0.0`** (Giulia, 2026-11-27).
7. The checker keeps its webapp blind spot (D8) until its own item; S5 showed it can hash served
   files with no credential.

## Consequences

- One deployer run installs a whole matching release, apps included, with the right scopes; each
  app version names its release.
- Apps and their versions are credited to the member whose key is in the connection, as pipeline
  versions already are.
- `v1.0.0` now also waits for the editor's move into `app/`, the manifest's new webapp fields and
  the deployer step, and its release candidate is verified with both apps installed.
- Settled with the deployer change ([REL-2](../../pipelines/snt_workspace_deployer/readme.md#functionality-overview)): where the name, slug and scopes
  are written down, and what the deployer does with an app it finds under the right slug that it did
  not create (an app uploaded by hand).
- Not verified: whether another workspace member can edit an app the token created.
- Live countries run the old `snt_development` repo; their webapps stay hand-uploaded.

Source: migration plan D-23, spike S5, discussion 2026-11-27.
