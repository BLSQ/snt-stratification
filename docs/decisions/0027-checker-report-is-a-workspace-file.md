# 0027. The checker's report is a workspace file, not a dataset or a DB table

Date: 2026-09-18
Status: Accepted
Originally: `snt_workspace_bootstrap` D3

## Context

The checker produces a report per run, and a web app is meant to read the latest one. Datasets and
the workspace database were the other places it could go. The reason for preferring a file was not
written down beyond the decision itself.

## Decision

The report is a workspace file: one timestamped file per run plus a byte-identical
`snt_status/status_latest.json` at a stable path, which is what a web app reads. No dataset, no
DB table.

## Consequences

- The latest report is always at one known path; older reports stay beside it.
- The report's shape is a contract, frozen as `schema_version: 1` in
  [`contracts/status_report.schema.json`](../../contracts/status_report.schema.json)
  ([`checker.md`](../bootstrap/checker.md) §5.5).
