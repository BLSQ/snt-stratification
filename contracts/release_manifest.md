# Release manifest — the producer ↔ consumer contract

> The authority is the JSON Schema (D26), [`release_manifest.schema.json`](release_manifest.schema.json)
> (v2). This file holds the prose. The manifests of the old `snt_development` releases (v1, no
> `schema_version`) are described in
> [`context/snt_development.md`](../docs/bootstrap/context/snt_development.md); no consumer here
> reads them.

## Manifest v2 — this repo

**Built on every published release, read by the two deployers and the checker.** The producer is
[`tools/build_manifest.py`](../tools/build_manifest.py), run by
[`release.yaml`](../.github/workflows/release.yaml), which attaches the manifest and the
[release assets](#release-assets-beside-the-manifest) to the release. No release exists yet: the
first is `v0.1.0`, in Phase 4 of [`MIGRATION_PLAN.md`](../docs/MIGRATION_PLAN.md).

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
  "filesystem_files": ["pipelines/snt_map_extracts/reporting/snt_map_extracts_report.ipynb", "shared/r/snt_utils.r", "…"],
  "pipelines": {
    "snt_map_extracts": {"path": "pipelines/snt_map_extracts", "kind": "snt", "code": "snt-map-extracts",
                         "zip_files": ["pipeline.py", "reporting/snt_map_extracts_report.ipynb", "…"]}
  },
  "repository_files": {"catalogs/SNT_metadata_master.json": "<sha256>"},
  "webapps": {"orchestrator": {"path": "webapps/orchestrator/app", "version": "v0.1.0", "files": {"index.html": "<sha256>"}}}
}
```

Why the shape is what it is:

- **`filesystem_files`, because a file can take both routes.** A pipeline's Python and its R half
  both live under `pipelines/<name>/` ([ADR 0038](../docs/decisions/0038-repo-path-is-workspace-path.md)),
  and the SDK zips the R half with the Python: a notebook ships inside the zip **and** is copied to
  the workspace filesystem. The manifest therefore lists the filesystem files explicitly, and a
  consumer derives no route from a path (§2.1). `files` is `{path: sha256}`, the union of both
  routes; every key is in `filesystem_files`, in some `zip_files`, or both.
- **`pipelines.<name>.path` and `kind`.** The key is the pipeline name (folder name = `@pipeline`
  id); `path` is `pipelines/<name>`. `kind` comes from
  [`pipelines/registry.json`](../pipelines/registry.json). Bootstrap pipelines are listed like any
  other, and the deployer deploys them only when the target tag is the latest full release or newer
  ([ADR 0042](../docs/decisions/0042-bootstrap-pipelines-as-templates-on-release.md)).
- **`schema_version` and `repo`.** A consumer reads every `schema_version` from 2 on that it knows
  and refuses an unknown one with an `[ERROR]` (ADR 0042), so a newer manifest never half-deploys.
  `repo` says which repository the tag belongs to.
- **`webapps`.** One entry per `webapps/<name>/app/` bundle that holds a file, with its files hashed
  relative to `app/`. The release attaches each bundle as `webapp-<name>-<tag>.zip` with a stamped
  `version.json` (not listed). No consumer reads the block until Phase 7.
- **`repository_files`** holds `{path: sha256}` for files a pipeline **fetches from the repository
  at run time** instead of receiving them by deployment: `catalogs/SNT_metadata_master.json`, which
  `snt_metadata_json_trim` downloads at the requested release tag. They are not in `files`, because
  every `files` path reaches the workspace by a route, and the point of the trim pipeline is to read
  the master list from the repo, not from the workspace. The block is for provenance only: neither
  the deployers nor the checker read it.

Invariants JSON Schema cannot express are listed in the schema's `description` and checked by
`invariant_errors()` in [`tools/build_manifest.py`](../tools/build_manifest.py).

**Why the zip route mirrors the SDK rather than listing globs.** A glob list restates the SDK's rule
in a second, drifting dialect (one pattern per suffix *per depth*) and needs a new line for every
future nesting or suffix. The suffix set and the `workspace/` exclusion are the constants of
`generate_zip_file()` in `openhexa/cli/api.py`, so `zip_files` is exactly what `openhexa pipelines
push` and the deployers put in a version's zip. Two consequences:

* The bootstrap pipelines are pipelines like any other, so the manifest describes the deployer as
  well, and the deployer can deploy a new version of itself; the guard above keeps it from deploying
  an older one.
* If the SDK ever changes its suffix list, the builder goes stale silently. The checker's
  `not_covered` status ([`checker.md`](../docs/bootstrap/checker.md) §5.1) is the tripwire for
  exactly that.

Country-specific notebook variants (none is in this repo, D-13) would appear undistinguished from
generic files. That is intended: telling them apart is the checker's job, not the builder's.

## Release assets beside the manifest

[`release.yaml`](../.github/workflows/release.yaml) attaches these to every published release,
pre-releases included:

| Asset | Content | Built by |
|---|---|---|
| `release_manifest.json` | The manifest above | [`tools/build_manifest.py`](../tools/build_manifest.py) |
| `<repo name>-<tag>.tar.gz`, e.g. `snt-stratification-v0.1.0.tar.gz` (the slim tarball) | Exactly the manifest's `files`, at their repository paths, under one top folder `snt-stratification-v0.1.0/` | [`tools/build_release_assets.py`](../tools/build_release_assets.py) |
| `webapp-<name>-<tag>.zip`, one per `webapps` entry | The bundle's files at their paths relative to `app/`, plus a stamped `version.json` at the zip's root | [`tools/build_release_assets.py`](../tools/build_release_assets.py) |

The builder checks every file against its manifest hash before packing it, so the assets cannot
disagree with the manifest they are published with. Both deployers download the slim tarball, not
GitHub's source tarball, and stop with an `[ERROR]` on a release without it.

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

## 2.1 The manifest's `pipelines` block

`files` alone does not say *where* an entry lives in a workspace, and the answers are not
interchangeable: `shared/r/snt_utils.r` is a file on the filesystem, while
`pipelines/snt_map_extracts/utils.py` exists **only** inside a pipeline's registered version zip and
is at no path on the filesystem at all. Without `filesystem_files` and the `pipelines` block, every
consumer would re-derive that split by reapplying the builder's rule, and a consumer that gets it
wrong reports `missing` for files that are deployed and correct — a false alarm in the one component
whose job is to be trusted.

```json
"pipelines": {
  "snt_map_extracts": {
    "path": "pipelines/snt_map_extracts",
    "kind": "snt",
    "code": "snt-map-extracts",
    "zip_files": ["malariaAtlasProject/__init__.py", "pipeline.py", "readme.md",
                  "reporting/snt_map_extracts_report.ipynb", "utils.py", "utils/snt_map_extracts_report.r", "…"]
  }
}
```

* The **key** is the pipeline name. Prefix `path` to a `zip_files` entry to get the repository
  path, which is the key into `files` and therefore the expected hash.
* `zip_files` are paths **inside the zip**, so they can be compared directly against the
  `namelist()` of a version's zip.
* `code` is the OpenHEXA pipeline code — the name with underscores replaced by hyphens. A consumer
  needs it to look the pipeline up over the API and can get it from nowhere else in the manifest.

**No fallback (D26).** A manifest a consumer cannot read is refused, never half-read: one without
`schema_version` (a v1 manifest from the old `snt_development` repository, whose paths follow that
layout) or with a version it does not know. `snt_workspace_checker` skips that release with a
`[WARNING]` (its report is then `incomplete`), and both deployers abort with
`[ERROR] Cannot deploy: …` before writing anything.
