# Things to verify outside this repository

**Ticket:** SNT25-661 · **Opened:** 2026-09-10

Every claim this app relies on that **cannot be checked from inside this repo**. They come from the
SNT pipelines repository, the OpenHEXA platform, or the SNT team — not from anything vendored here.

This exists because the analysis docs are second-hand: they describe upstream code that nobody in
this repo can run. A wrong assumption here does not fail a test, it ships a confidently wrong app.

**How to use it.** Nothing here blocks building the form or the validation engine — that is the
point of writing them down instead of stalling. Each item says what breaks if the assumption is
wrong, so the cost of being wrong is visible before anyone pays it. When you answer one: record the
answer and the date **in place**, fix the doc it affects, and strike the item rather than deleting
it.

| # | Question | Blocks | Status |
|---|---|---|---|
| 1 | All-`NA` guard in `snt_dhis2_incidence` | W4 severity | ❓ open |
| 2 | R gate equivalent to the Python one | §5.1 completeness | ❓ open |
| 3 | Upstream `POP_PREGNANT_WOMEN` fix | CLAUDE.md rule 3 | ❓ open, ongoing |
| 4 | OpenHEXA workspace write mechanism | §7 step 2 | ❓ open |
| 5 | OpenHEXA user identity in the page | §11 q4 | ❓ open |
| 6 | §12.1 paths and symbol names | §12 accuracy | ❓ open |
| 7 | A sixth country config | "fixed" assumptions | ❓ open, ongoing |
| 8 | Enumerating DHIS2 connections from a web app | §4.1 dropdown, §7.1 | ❓ open |
| 9 | `snt_dhis2_extract` connection is a run parameter | §4.1 placement decision | ❓ open |

---

## 1. Does `snt_dhis2_incidence` reject an all-`NA` disaggregation column?

**Where to look:** SNT pipelines repo, `snt_dhis2_incidence` — the code that builds
`{SUSP|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` and raises
`[ERROR] Required columns for disaggregation '{SEL}' are missing`.

**The question.** We know the error fires when a column is **absent**. We also know
([`config_analysis_notes.md`](../../../contracts/snt_config/config_analysis_notes.md) §4.1 trap 3) that an empty list still
creates the column, filled with `NA` (`include_empty_ind = TRUE`). What we do **not** know is
whether there is a **second** guard — an `all(is.na(...))` check, a row-filter that empties the
frame, or a division that propagates `NA` into a hard failure — that turns an empty-but-present
column into a run-time error anyway.

**What hangs on it.** [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §5.2 W4:

- **No second guard** → current text is right. Leaving `TEST_UNDER_5` empty is a silent
  degradation, W4 stays 🔵 info, nothing blocks.
- **There is a second guard** → W4 goes back to 🟠 warning, and the wording must say the run will
  fail. Note this is still *not* the "all four" rule the original text claimed — the composition is
  three columns, with `SUSP`/`PRES` chosen by `N1_METHOD`.

**Cheapest way to answer:** grep the incidence pipeline for `is.na`, `drop_na`, `complete.cases`
and the error string itself, then read the ~30 lines around the column-composition step.

## 2. Is the R gate equivalent to the Python one?

**Where to look:** `validate_required_config_keys()` in the SNT pipelines R helpers, against
`snt_lib.validate_config()` in `snt_utils`.

The analysis docs treat the two as the same contract; [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §12.1
records that as **unverified**. If the R gate is stricter, this app will declare files valid that
the R pipelines refuse — the app's §5.1 rules are a reimplementation of the Python side only.

Answering this is also the cheapest input to the §12.2 decision on how to keep the two
`validate_config()` implementations in agreement, which is still unmade.

## 3. Has `POP_PREGNANT_WOMEN` / `_PREGNANT_WOMAN` been fixed upstream?

**Where to look:** `select_population_column()` in the SNT pipelines repo.

CLAUDE.md rule 3 tells this app to emit the mismatched spellings **on purpose**, because that is
what the pipelines currently expect. The moment someone fixes the defect upstream, that rule becomes
actively harmful and must be reversed here. Nothing will notify us. Re-check whenever the pipelines
repo moves.

## 4. How does an OpenHEXA web app write to the workspace filesystem?

**Where to look:** OpenHEXA docs and the MCP tooling; confirm with the platform team.

[`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §7 asserts that a deployed web app **can** write to
`<workspace>/configuration/`, and stages v1 around it: step 1 download-only, step 2 `WorkspaceStore`.
The assertion is flagged there as not yet confirmed. Needed before step 2 is designed: the exact
mechanism, the permissions required, and whether writes are attributable to the logged-in user.

If it turns out a web app **cannot** write, step 2 needs a workspace-side component instead — which
also reopens §12.2 option 4 (move validation server-side and call the real `validate_config()`).

## 5. Does the OpenHEXA web app context expose the logged-in user to the page?

[`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §11 open question 4. Decides whether `_EDITOR_METADATA.author`
is prefilled (`source: "openhexa"`) or asked for once and remembered (`source: "manual"`). The
metadata already carries `source` to record which, so this does not block — it only decides which
branch gets built. Answer alongside item 4.

## 6. Are the §12.1 paths and symbol names real?

[`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §12.1 carries an explicit warning that every path and symbol in
that table came from the analysis docs, not from reading the pipelines repo. Verify each against the
live repo and **correct the table in place** when you do. Do this once, early — the whole §12 risk
register is worthless if it names things that no longer exist.

## 7. Does a sixth country config break a "fixed" assumption?

[`config_field_matrix.md`](../../../contracts/snt_config/config_field_matrix.md) derives "fixed vs variable" from five configs. The
15 dataset identifiers being identical everywhere is the load-bearing one — the app pre-fills them
and never asks ([`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §8). A sixth country that differs turns a
pre-filled constant into a field. Re-check when a country is added.

## 8. Can a deployed web app enumerate the workspace's connections, filtered by type?

**Where to look:** OpenHEXA docs and MCP tooling; confirm with the platform team. Answer alongside
items 4 and 5 — all three are "what does the web app runtime expose to the page".

[`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §7.1 specifies `WorkspaceContext.listDhis2Connections()`.
Three separate things must be true, and only the first is likely:

1. The page can **list** the workspace's connections at all.
2. Each connection's **type** is exposed, so DHIS2 ones can be filtered from PostgreSQL, S3, GCS and
   IASO. Without this the dropdown would offer an S3 bucket as a DHIS2 instance.
3. A stable **identifier** (slug) is available to record, not just a display name — display names
   get renamed, and the recorded provenance must survive that.

**What hangs on it.** If listing works but type does not, the dropdown needs another
discriminator (a name convention is a poor one — say so rather than shipping it). If listing does
not work, §4.1 degrades to `source: "unavailable"` everywhere and W10 can never fire.

**Note the security boundary while you are there:** the app must read connection *metadata* only.
Confirm that listing connections does not expose their credentials to the page — if it does, that is
worth raising with the platform team independently of this app.

## 9. Is the DHIS2 connection really a run parameter of `snt_dhis2_extract`?

**Where to look:** `snt_dhis2_extract` in the SNT pipelines repo — its parameter declarations.

The §4.1 decision to record the connection as **provenance only** (in `_EDITOR_METADATA` and the
sidecar, never in the config payload) rests on this being true. It matches how `N1_METHOD` works and
on the fact that the skeleton defines no connection field, so it is very likely right — but it was
asserted in conversation, not read from the code.

**What hangs on it.** If some pipeline *does* read a connection identifier out of the config, then
this app is omitting a field those pipelines need, and §4.1 must be reversed: the value moves into
`SNT_CONFIG`, the skeleton is updated **upstream first** (§12.3), and CLAUDE.md rule 6 gets an
explicit exception. The value is already being captured either way, so the reversal is cheap — but
it is a schema change, and those are not this repo's to make.

---

## Also unresolved, but inside this repo

Not external — listed here only so the two sets are not confused:

- **§12.2 — how to keep the JS and Python `validate_config()` in agreement.** Settled: option 2,
  the conformance fixtures in `contracts/snt_config/fixtures/`. The Python side runs; the JS side
  runs them when the validator is built.
- **§11 open question 1 — `REPORTING_RATE_PRODUCT_UID` semantics.** Needs the SNT team, but it is a
  question about intent, not about code that can be read.
- **§11 open questions 2, 3, 5** — import/normalisation, `COUNTRY_NAME` casing, dataset registration.
- **§11 open question 6 — does any country run two DHIS2 instances (SNIS *and* NMDR)?** A question
  for the SNT team about how countries actually work, not something readable from any repo. It is
  the one that could reopen the storage layout (§6.2), so it is worth asking early even though v1
  only warns about it.
