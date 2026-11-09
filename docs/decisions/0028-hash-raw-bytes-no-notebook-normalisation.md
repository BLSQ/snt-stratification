# 0028. Hash notebooks as raw bytes; no normalisation

Date: 2026-09-29 (deferred on 2026-09-18 until measured)
Status: Accepted
Originally: `snt_workspace_bootstrap` D9

## Context

The checker compares workspace files with release files by sha256. A notebook can differ only in
metadata or outputs, so normalising notebooks before hashing was considered. On 2026-09-18 the
choice was deferred until real drift had been measured. Measured on one real country workspace: of
31 notebooks present in both the workspace and the repo, 15 were identical, 2 differed in metadata
only, 0 in outputs or formatting, and 14 had real source differences.

## Decision

Do not normalise. Hash raw bytes, for notebooks as for every other file.

## Consequences

- Normalisation would have changed the verdict for 2 of 31 notebooks, at the cost of a second hash
  definition kept in lockstep between the manifest generator and the checker. That cost is avoided.
- A notebook saved with different metadata reads as different. Accepted.
- Measurement tool and detail: `tools/d9_notebook_drift.py`, [`checker.md`](../bootstrap/checker.md) §6.3.
