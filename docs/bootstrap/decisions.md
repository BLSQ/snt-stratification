# Decisions

> Append-only. A decision is cited by its number rather than re-argued; a new one gets the next
> `D<n>`. Entries that record an architectural decision were promoted to the repo-wide
> ADRs in [`../decisions/`](../decisions/README.md) (D-14 in the migration plan); their row points
> there, and `D<n>` citations stay valid. New bootstrap decisions that shape more than one unit are
> written as ADRs; implementation detail of the bootstrap pipelines still goes here.
> Section references (§) are those of the former `PRODUCT_SPEC.md`; the index in
> [`pipelines/CLAUDE.md`](../../pipelines/CLAUDE.md#bootstrap-pipelines) says which file holds each. D18 names the schema's old path under
> `docs/wip/docs/`; it is now in [`contracts/`](../../contracts/).

## 8. Decisions taken

Recorded so they are not re-litigated. Taken by Giulia in review, 2026-09-18 (D1–D9, D11, D12) and
2026-09-21 (D10), 2026-09-29 (D9 resolved, D13–D17) and 2026-09-30 (D18–D22).

| # | Decision |
|---|---|
| D1 | This spec covers the whole suite, phased: existing `snt_workspace_deployer`, new checker, web app deferred. |
| D2 | **Promoted to [ADR 0026](../decisions/0026-checker-and-deployer-are-separate-pipelines.md)**, the repo-wide record. |
| D3 | **Promoted to [ADR 0027](../decisions/0027-checker-report-is-a-workspace-file.md)**, the repo-wide record. |
| D4 | Release ordering uses GitHub `published_at`. |
| D5 | Country-specific variant override detection is **out of scope for v1**. |
| D6 | Untracked files are **reported** in their own bucket, never acted on. |
| D7 | Both sources — filesystem and pipeline version zips — are read from v1. |
| D8 | Web apps are out of scope for v1, and named as a blind spot in the report. |
| D9 | **Promoted to [ADR 0028](../decisions/0028-hash-raw-bytes-no-notebook-normalisation.md)**, the repo-wide record. |
| D10 | The manifest gap is closed **before** the checker is built (phase 0). |
| D11 | Two modes, driven by whether a target release is given: attribution (factual inventory) and verification (qualitative verdicts). |
| D12 | The status formerly called `mismatch_unknown` is renamed **`unknown_content`**, to stop it reading as a synonym of `untracked`: one is about the bytes at a known path, the other about a path we never shipped ([`checker.md`](checker.md) §5.1.1). |
| D13 | New status **`added_after_target`** (2026-09-29): a present path that only releases newer than the target ship. Without it, a workspace ahead of its target would read as `removed_in_target` ([`checker.md`](checker.md) §5.1). |
| D14 | Attribution representation (2026-09-29, [`checker.md`](checker.md) §7.8): spans `{from, to, count}` in `published_at` order; a single match is a span of one; any release outside the set breaks a span, including one whose manifest is unreadable; in verification mode, carried only on entries that are not `match`. |
| D15 | Attribution scores (2026-09-29, [`checker.md`](checker.md) §7.10), **revised the same day after sandbox run 1** ([`checker.md`](checker.md) §6.5). Each release is judged **only on the paths it ships**. **Agreement** = files here with exactly its bytes ÷ its files found here. **Completeness** = its files found here ÷ its files shipped. Files at paths it does not ship are **extra**, neither for nor against it. A file counts towards every release it matches, so nothing sums to 100%. Best fit = highest agreement, then completeness, then newest. The pool is every entry for a present file except `untracked`, both sources together, and the rule is stated in the report. Files matching no release and unreadable files are also shown on their own. *Superseded form:* one share per release over the whole pool, which counted leftovers of removed files against the release that removed them. |
| D16 | New status **`attributed`** (2026-09-29, [`checker.md`](checker.md) §7.11): attribution mode's "known path, bytes match ≥1 release", with spans over all matching releases and `position: null`. |
| D17 | The reserved `release_tag` value **`none`** (any case) forces attribution mode even when `.snt_release` exists (2026-09-29, [`checker.md`](checker.md) §7.11), so a scheduled attribution check never requires deleting the marker. |
| D18 | Phase 4 (2026-09-30): `schema_version: 1` is **frozen** as a JSON Schema in `docs/wip/docs/status_report.schema.json`, and **`docs/wip/` is treated as a future standalone repository**, so contracts live inside it. Free-text fields (`remediation`, `errors[].message`, `blind_spots[]`, `summary.attribution.rule`) are frozen as keys and types but **display-only**. `checker_version` is renamed **`snt_workspace_check_version`**: the version of the `snt_workspace_checker` pipeline that generated the report; documenting it is enough, and it is `null` today ([`checker.md`](checker.md) §5.5, [`checker.md`](checker.md) §6.6). |
| D19 | **Promoted to [ADR 0029](../decisions/0029-no-deployment-workflow-for-bootstrap-pipelines.md)**, the repo-wide record; superseded by [ADR 0042](../decisions/0042-bootstrap-pipelines-as-templates-on-release.md). |
| D20 | **Promoted to [ADR 0030](../decisions/0030-template-mechanism-being-retired.md)**, the repo-wide record. |
| D21 | **Promoted to [ADR 0031](../decisions/0031-deployer-deploys-the-whole-release.md)**, the repo-wide record. |
| D22 | **Version naming on deploy** (2026-09-30, [`deployer.md`](deployer.md) §6.7). A pipeline whose current version has the release's exact files *and* the tag as its name is skipped (success). Identical files under another name are **registered again under the tag**, so the workspace reads as being at the release, at the cost of one extra version per unchanged pipeline per release (reverses an earlier decision not to redeploy identical versions). A taken tag gets `<tag>+redeploy-<YYYYMMDD>`. `+` in a version name is accepted by OpenHEXA. |
| D23 | **An empty `release_tag` deploys the latest release** (2026-10-01, [`deployer.md`](deployer.md) §6.7). The deployer resolves it through GitHub's `/releases/latest`, i.e. the newest published release that is neither a draft nor a pre-release, so a pre-release must be typed. The resolved tag, never "latest", names the pipeline versions, `archive/<tag>/` and `.snt_release`, so a workspace always records which release it actually got. |
| D24 | **Every deployer failure reaches the run's Messages** (2026-10-01, [`deployer.md`](deployer.md) §6.7). A raised exception alone appears only in the logs, so each anticipated failure is logged as `[ERROR] Cannot deploy: <reason and fix>` before raising, and anything else is logged by a catch-all in the pipeline function. |
| D25 | **Promoted to [ADR 0032](../decisions/0032-one-workspace-per-release.md)**, the repo-wide record. |
| D26 | **Promoted to [ADR 0033](../decisions/0033-release-manifest-frozen-json-schema.md)**, the repo-wide record. |
| D27 | **Promoted to [ADR 0034](../decisions/0034-pre-releases-for-development-only.md)**, the repo-wide record. |
| D28 | **Promoted to [ADR 0035](../decisions/0035-single-pipeline-deployer.md)**, the repo-wide record. |
