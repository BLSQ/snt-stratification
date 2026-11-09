# 0033. The release manifest is a contract, frozen as a JSON Schema

Date: 2026-10-01
Status: Accepted
Originally: `snt_workspace_bootstrap` D26

## Context

`release_manifest.json` was produced in `snt_development` (`generate_manifest.yaml`) and read in
`snt_workspace_bootstrap` by the deployer and the checker. Its shape existed only implicitly in that
code, across two repos.

## Decision

The manifest is a contract, frozen as a JSON Schema, now
[`contracts/release_manifest.schema.json`](../../contracts/release_manifest.schema.json) (prose:
[`release_manifest.md`](../../contracts/release_manifest.md) §2.1).

- It is derived from the code (the generator, `split_manifest()`/`download_manifest()` in the
  deployer, `load_manifests()`/`build_index()` in the checker), not from prose.
- It is repository-agnostic: no `pipelines/` or `code/` paths in the schema.
- Strict for the producer (`additionalProperties: false`), tolerant for consumers, which ignore
  unknown keys.
- `pipelines` is required, so manifests from before it existed do not validate, and they are not
  supported: they only existed during development.
- Two invariants JSON Schema cannot express (every `<dir>/<zip_file>` is a key of `files`; every
  `zip_files` holds `pipeline.py`) are stated in the schema's description and checked separately.

## Consequences

- A shape change touches the schema, the producer and both consumers together (R22).
- The deployer's fallback for old manifests in `split_manifest()` is to be deleted in a change of
  its own.
