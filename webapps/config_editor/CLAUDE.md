# CLAUDE.md

Web app that produces a valid `SNT_config.json` for the SNT pipelines, aimed at country teams who
know DHIS2 but not JSON. Ticket SNT25-661.

## Read these first, in this order

| File | What it is |
|---|---|
| [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) | **What we are building.** Scope, storage design, validation model, form structure, acceptance criteria. Start here. |
| [`docs/config_analysis_notes.md`](../../contracts/snt_config/config_analysis_notes.md) | **The schema contract.** What "valid" means, per-field rules, traps. Source of truth. |
| [`docs/config_field_matrix.md`](../../contracts/snt_config/config_field_matrix.md) | Field-by-field across the 5 existing countries — what is fixed vs variable. |
| [`docs/SNT_config.skeleton.json`](../../contracts/snt_config/SNT_config.skeleton.json) | The exact shape and key order the app must emit. |

Do not restate schema facts in new files — link to the analysis docs instead. They are maintained;
copies drift.

## Current state

Docs and spec only. No app code yet. `prototype/index.html` is a standalone throwaway prototype for
reviewing the UX — not the codebase.

## Decisions already made — do not relitigate

- **v1 is new configs only.** No import of existing `SNT_config.json`. (Loading back a draft *this
  app wrote* is different and is in scope.)
- **No DHIS2 connection in v1.** No UID → name resolution, no pyramid validation.
- **An OpenHEXA web app CAN write to the workspace filesystem.** v1 ships in two steps: step 1 is
  download-only (proof of concept), step 2 writes into `/configuration`. Both are v1. Spec §7.
- **All persistence goes through the `ConfigStore` interface** (spec §7). No form or validation code
  may touch `localStorage`, `fetch`, or a path directly.
- **`SNT_config.json` is written only when valid.** Drafts live in `snt_config_history/` and
  `snt_config_draft.json`. Spec §6.
- **Metadata placement:** `_EDITOR_METADATA` inline in drafts, stripped on promotion and written to a
  `.log.json` sidecar for valid files. Spec §6.3.
- **Indicator keys:** the skeleton's 18, plus a free-text "other key" escape hatch that warns.
- **DHIS2 instance:** the app asks which instance the UIDs came from (dropdown of the workspace's
  DHIS2-typed connections, step 2 only) and records it in `_EDITOR_METADATA` + the sidecar —
  **never in the config payload.** The pipeline takes its connection as a run parameter; the
  skeleton has no field for one. Provenance, not configuration. Spec §4.1.
- **Checksums:** SHA-256. `config_sha256` (payload without `_EDITOR_METADATA`) in both the metadata
  and the sidecar; `file_sha256` (exact file bytes) in the sidecar only. Spec §6.6.

## Upstream alignment — read before touching validation

This repo shares **no code** with the SNT pipelines; it reimplements their rules. Spec §12 lists
every upstream component relied on and what breaks here if it changes. The critical one:
`validate_config()` now exists twice — Python upstream (unpinned) and JavaScript here — with nothing
keeping them in agreement. Spec §12.2 has the options; **no mitigation is chosen yet.**

Do not edit [`docs/SNT_config.skeleton.json`](../../contracts/snt_config/SNT_config.skeleton.json) to suit the app. It is
a vendored copy of an upstream truth. Spec §12.3.

## Rules the code must not break

1. Every indicator value is a **JSON list**, never a bare string. A string flattens into
   one-character UIDs and passes `validate_config()`. The UI must make this unrepresentable.
2. UID validation is **permissive**: `^[A-Za-z0-9]{11}$` or `^[A-Za-z0-9]{11}\.[A-Za-z0-9]{11}$`.
   A UID **may start with a digit**. Never require a leading letter.
3. Emit `POP_PREGNANT_WOMEN` (plural) under population and `*_PREGNANT_WOMAN` (singular) under
   routine indicators. They disagree on purpose. Do not "fix" it.
4. Emit `_UNDER_5` / `_ABOVE_5` spellings only — never `_UNDER5`.
5. Always emit all 15 dataset identifiers, all 8 population keys, all three top-level sections.
6. Never emit a key the skeleton does not define into a **valid** `SNT_config.json`.
7. Timestamps are UTC ISO 8601. Always.

## Open questions — ask, don't guess

Listed in spec §11. The live one that affects code: `REPORTING_RATE_PRODUCT_UID` semantics are
unresolved (dataset UIDs vs indicator UIDs), so collect it as a free UID list and enforce nothing.

Assumptions that can only be checked **outside this repo** — upstream code, the OpenHEXA platform,
the SNT team — are registered in [`docs/EXTERNAL_CHECKS.md`](docs/EXTERNAL_CHECKS.md) with what
breaks if each is wrong. None of them block building. Add to it rather than guessing.

## Conventions

- Prose docs wrap at 100 columns.
- Reference files as markdown links, not backticked paths.
