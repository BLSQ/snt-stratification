# `.snt_release` — the workspace release marker

> Written by the deployer at the workspace root, read by the checker to pick its target (see
> [`checker.md`](../docs/bootstrap/checker.md) §4.2).

## 3.2 `.snt_release`

`snt_workspace_deployer` writes the release it deployed at the workspace root at the end of every
run that is not a dry run:

```json
{"snt_release": "v0.1.0", "repo": "BLSQ/snt-stratification"}
```

* `snt_release` is the release tag. It keeps the key of the first shape, so a checker that predates
  `repo` still reads the tag.
* `repo` is the repository the release belongs to, as `owner/name`, copied from the release
  manifest's `repo`. A tag alone is ambiguous across repositories.

**Older shape.** Markers written before Phase 4 of
[`MIGRATION_PLAN.md`](../docs/MIGRATION_PLAN.md) hold only `{"snt_release": "<tag>"}`. The checker
still reads them and takes them to name the repository it is checking.

**How the checker uses it.** The marker's tag is the target when the `release_tag` parameter is
empty, and only if the marker names the repository being checked (compared without case) or names
none. A marker naming another repository is reported in `declared_release` and logged as a
`[WARNING]`, but not used as the target: checking its tag against this repository would compare the
workspace with an unrelated release that merely shares the name.

One honest limitation, which the report must reflect rather than paper over: the marker is written
after a partial run too, so it states **intent**, not verified fact.

A workspace with no marker is the normal starting state today — every existing country workspace.
That must never be an error.

## 7.4 Enriching `.snt_release`

The repository is recorded since Phase 4. The marker could also record a timestamp and whether the
run completed cleanly, so a checker can tell "deployed to T" from "attempted T, partially".
Changing it means changing `snt_workspace_deployer` and still reading the markers older versions
wrote.
