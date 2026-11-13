# Release manifest — the producer ↔ consumer contract

> The authority is the JSON Schema (D26): [`release_manifest.schema.json`](release_manifest.schema.json)
> for **v2**, this repo's releases; [`release_manifest.v1.schema.json`](release_manifest.v1.schema.json)
> for **v1**, the old `snt_development` releases, which the bootstrap pipelines still read until
> Phase 4 of [`MIGRATION_PLAN.md`](../docs/MIGRATION_PLAN.md) (that phase deletes the v1 file). This
> file holds the prose. What `snt_development` ships is in
> [`context/snt_development.md`](../docs/bootstrap/context/snt_development.md).

## Manifest v2 — this repo

**Built on every published release; no consumer reads v2 yet.** The producer is
[`tools/build_manifest.py`](../tools/build_manifest.py), run by
[`release.yaml`](../.github/workflows/release.yaml), which attaches the manifest and the
[release assets](#release-assets-beside-the-manifest) to the release. No release exists yet: the
first is `v0.1.0`, in Phase 4. The deployer, the single-pipeline deployer and the checker switch to
v2 in Phase 4.

How the builder routes each file:

| Route | Rule | Listed in |
|---|---|---|
| Zip | Every file under `pipelines/<name>/` whose suffix (case-insensitive) is `.py .ipynb .txt .md .r .sql`, minus `pipelines/<name>/workspace/`: a mirror of the SDK's `generate_zip_file()`, R half and `country_specific/` included. `<name>` must be in [`registry.json`](../pipelines/registry.json) and hold a `pipeline.py`, or the build stops | `files` + `pipelines.<name>.zip_files` |
| Filesystem | `pipelines/*/code/*.ipynb`, `pipelines/*/reporting/*.ipynb`, `pipelines/*/utils/*.r`, `shared/r/**/*.r` | `files` + `filesystem_files` |
| Fetched at run time | `catalogs/*.json` | `repository_files` |
| Webapp bundle | Every non-hidden file under `webapps/<name>/app/`; an `app/` with none (only `.gitkeep`) gets no entry | `webapps.<name>.files` |

Anything else (docs, `tools/`, `tests/`, design files) is not in the manifest. The builder checks its
output against the schema and the invariants before it writes anything, so a release never carries
an invalid manifest:

```bash
python tools/build_manifest.py --version v0.1.0 --repo BLSQ/snt-stratification   # in a workflow, both come from the env
```

```json
{
  "schema_version": 2,
  "version": "v0.1.0",
  "repo": "BLSQ/snt-stratification",
  "files": {"pipelines/snt_map_extracts/pipeline.py": "<sha256>", "shared/r/snt_utils.r": "<sha256>", "…": "…"},
  "filesystem_files": ["pipelines/snt_map_extracts/code/snt_map_extracts.ipynb", "shared/r/snt_utils.r", "…"],
  "pipelines": {
    "snt_map_extracts": {"path": "pipelines/snt_map_extracts", "kind": "snt", "code": "snt-map-extracts",
                         "zip_files": ["code/snt_map_extracts.ipynb", "pipeline.py", "…"]}
  },
  "repository_files": {"catalogs/SNT_metadata_master.json": "<sha256>"},
  "webapps": {"orchestrator": {"path": "webapps/orchestrator/app", "version": "v0.1.0", "files": {"index.html": "<sha256>"}}}
}
```

What changed from v1, and why:

- **`filesystem_files`, because a file can now take both routes.** In v1 a pipeline's Python
  (`<name>/pipeline.py`) and its R half (`pipelines/<name>/code/…`) lived in different trees, so the
  first path segment told a consumer the route. In this repo both live under `pipelines/<name>/`
  ([ADR 0038](../docs/decisions/0038-repo-path-is-workspace-path.md)), and the SDK zips the R half
  with the Python: a notebook ships inside the zip **and** is copied to the workspace filesystem.
  The manifest therefore lists the filesystem files explicitly, and a consumer derives no route
  from a path (the reasoning of §2.1). `files` keeps its `{path: sha256}` shape and is the union of
  both routes; every key is in `filesystem_files`, in some `zip_files`, or both.
- **`pipelines.<name>.path` and `kind`.** The key is the pipeline name (folder name = `@pipeline`
  id), no longer a top-level folder; `path` is `pipelines/<name>`. `kind` comes from
  [`pipelines/registry.json`](../pipelines/registry.json). Bootstrap pipelines are listed like any
  other, and the deployer deploys them only when the target tag is the latest full release or newer
  ([ADR 0042](../docs/decisions/0042-bootstrap-pipelines-as-templates-on-release.md)).
- **`schema_version` and `repo`.** A consumer reads every `schema_version` from 2 on that it knows
  and refuses an unknown one with an `[ERROR]` (ADR 0042), so a newer manifest never half-deploys.
  `repo` says which repository the tag belongs to.
- **`webapps`.** One entry per `webapps/<name>/app/` bundle that holds a file, with its files hashed
  relative to `app/`. The release attaches each bundle as `webapp-<name>-<tag>.zip` with a stamped
  `version.json` (not listed). No consumer reads the block until Phase 7.

Invariants JSON Schema cannot express are listed in the schema's `description` and checked by
`invariant_errors()` in [`tools/build_manifest.py`](../tools/build_manifest.py).
`repository_files` is unchanged from v1.

## Release assets beside the manifest

[`release.yaml`](../.github/workflows/release.yaml) attaches these to every published release,
pre-releases included:

| Asset | Content | Built by |
|---|---|---|
| `release_manifest.json` | The manifest above | [`tools/build_manifest.py`](../tools/build_manifest.py) |
| `<repo name>-<tag>.tar.gz`, e.g. `snt-stratification-v0.1.0.tar.gz` (the slim tarball) | Exactly the manifest's `files`, at their repository paths, under one top folder `snt-stratification-v0.1.0/` | [`tools/build_release_assets.py`](../tools/build_release_assets.py) |
| `webapp-<name>-<tag>.zip`, one per `webapps` entry | The bundle's files at their paths relative to `app/`, plus a stamped `version.json` at the zip's root | [`tools/build_release_assets.py`](../tools/build_release_assets.py) |

The builder checks every file against its manifest hash before packing it, so the assets cannot
disagree with the manifest they are published with. The deployers still download GitHub's own
source tarball until Phase 4. The slim tarball keeps that tarball's layout (one top folder, repo
paths under it), so their switch to it is a change of URL.

Each webapp zip's `version.json`:

```json
{"version": "v0.1.0", "commit": "<full 40-character git commit hash of the tag>", "built_at": "2026-11-20T10:00:00Z"}
```

`built_at` is when the workflow ran, in UTC. The file is generated at release time, so the
manifest does not hash it, and a bundle must not commit a `version.json` of its own (the builder
refuses one). The orchestrator reads it in Phase 7 to show the version in its footer.

A manual run of the workflow ("Run workflow", offered once the file is on `main`) builds the same
files under a test version name and keeps them on the run's page for seven days. It creates and
changes no release.

## v1: manifest generation in `snt_development` — done

[`.github/workflows/generate_manifest.yaml`](https://github.com/BLSQ/snt_development/blob/main/.github/workflows/generate_manifest.yaml) runs on
`release: published` (and `workflow_dispatch` for manual testing). It hashes every file a release
ships and attaches `release_manifest.json` to the release. The workflow is committed in *this* repo;
the sandbox copy is applied by hand.

The generator has two halves, because a release reaches a workspace by two routes:

1. **Filesystem half** — four glob patterns: `pipelines/**/code/*.ipynb`,
   `pipelines/**/reporting/*.ipynb`, `pipelines/**/utils/*.r`, `code/**/*.r`.
2. **Deployment half** — for each top-level directory holding a `pipeline.py`, walk it recursively
   and keep every file whose suffix is in `{.py, .ipynb, .txt, .md, .r, .sql}`, minus the
   `workspace/` subtree. That is a line-for-line mirror of `generate_zip_file()` in
   `openhexa/cli/api.py`; the constants are commented with that provenance, and the suffix test is
   case-insensitive there and here.

**Why it mirrors the SDK rather than listing globs.** A glob list restates the SDK's rule in a
second, drifting dialect — one pattern per suffix *per depth* — and needs a new line for every
future nesting or suffix. Anchoring on `*/pipeline.py` also excludes `dev/` and `deprecated/`
without naming them: `deprecated/` nests its eight pipelines one level deeper, so `*/pipeline.py`
never matches inside it. Nothing is excluded by a denylist that a new top-level directory could slip
past. (The rejected alternative is recorded in [`HISTORY.md`](../docs/bootstrap/HISTORY.md) §2.1.)

The manifest also carries a `pipelines` block alongside `files` — per pipeline directory, its
OpenHEXA `code` slug and the list of paths inside its zip. Shape and rationale:
§2.1. `files` is byte-compatible with the pre-phase-0 shape, so
the block is purely additive.

**Verified 2026-09-21** against `snt_development` @ `SNT25-670`, by building all 21 deployment zips
with the SDK's *real* `generate_zip_file()` and asserting every zip member resolves to a manifest
entry:

```
manifest files: 156 | zip members: 70 | zip members NOT in manifest: 0
```

The embedded script passes `ruff check` and `ruff format --check` under the repo's `pyproject.toml`.

Two consequences worth knowing:

* `snt_workspace_deployer` is itself a pipeline directory, so the manifest now describes the deployer
  as well. That is wanted — a workspace can be told its deployer is out of date — but it does mean
  the deployer can deploy a new version of itself.
* If the SDK ever changes its suffix list, this generator goes stale silently. The checker's
  `not_covered` status ([`checker.md`](../docs/bootstrap/checker.md) §5.1) is the tripwire for exactly that, which is why the
  spec keeps it after phase 0 rather than deleting it.

A third, optional block, `repository_files`, holds `{path: sha256}` for files a pipeline **fetches
from the repository at run time** instead of receiving them by deployment. In `snt_development`
that is `catalogs/SNT_metadata_master.json` (glob `catalogs/*.json`), which `snt_metadata_json_trim`
downloads at the requested release tag. Releases cut before the folder was renamed record it as
`metadata/SNT_metadata_master.json`. These files must not go in `files`: any `files` path outside
a pipeline directory is synced into the workspace filesystem by the deployer, and the point of the
trim pipeline is to read the master list from the repo, not from the workspace. The block is for
provenance only. Neither the deployer nor the checker reads it, and the schema does not require it,
so older manifests still validate.

Country-specific notebook variants appear in the manifest undistinguished from generic files. That
is intended — telling them apart is the verification pipeline's job, not the generator's.

## 2.1 The manifest's `pipelines` block (v1)

`files` alone does not say *where* an entry lives in a workspace, and
the two answers are not interchangeable: `code/snt_utils.r` is a file on the filesystem, while
`snt_map_extracts/utils.py` exists **only** inside a pipeline's registered version zip and is at no
path on the filesystem at all. Without the block, every consumer has to re-derive that split by
reapplying the generator's rule, and a consumer that gets it wrong reports `missing` for files that
are deployed and correct — a false alarm in the one component whose job is to be trusted.

```json
"pipelines": {
  "snt_map_extracts": {
    "code": "snt-map-extracts",
    "zip_files": ["malariaAtlasProject/__init__.py", "pipeline.py", "readme.md", "utils.py"]
  }
}
```

* The **key** is the repository directory. Prefix it to a `zip_files` entry to get the repository
  path, which is the key into `files` and therefore the expected hash.
* `zip_files` are paths **inside the zip**, so they can be compared directly against the
  `namelist()` of what `get_pipeline` returns.
* `code` is the OpenHEXA pipeline code — the directory name with underscores replaced by hyphens.
  A consumer needs it to look the pipeline up over the API and can get it from nowhere else in the
  manifest. Verified against all 20 `push_snt_*.yaml` `--code` values and against
  `snt_workspace_deployer`'s own derivation.

`files` keeps its exact previous shape, so the block is additive: a reader that ignores `pipelines`
behaves as before. Legacy (pre-phase-0) manifests have no such block and are not supported: a
consumer refuses one. Both consumers name the phase-0 cutover in the error:
`snt_workspace_checker` skips that release with a `[WARNING]`, and `snt_workspace_deployer`
(`download_manifest()`) aborts with `[ERROR] Cannot deploy: …` before writing anything.

**Decided 2026-10-01 (D26): no fallback.** Legacy manifests only ever existed during development
and no live release lacks the block. The contract is
[`release_manifest.v1.schema.json`](release_manifest.v1.schema.json), which requires the
block (it may be empty). The deployer's former fallback, which derived pipeline directories from
`<name>/pipeline.py` entries, is in [`HISTORY.md`](../docs/bootstrap/HISTORY.md) §3.4.

## 7.1 ~~The manifest under-described what is deployed~~ — **closed**

Closed as phase 0. Kept as a numbered heading only so the [`checker.md`](../docs/bootstrap/checker.md) §7.x references elsewhere still line up.
What the problem was, why a wider glob list was rejected, and the consumer it broke:
[`HISTORY.md`](../docs/bootstrap/HISTORY.md) §2.1–2.2. What the generator does now:
this file.

Phase 1 was left blocked only by the token question in [`openhexa_deployment.md`](../docs/bootstrap/openhexa_deployment.md) §7.3, which closed on 2026-09-22. **Phase 1
is unblocked and ready to start.**
