# SNT Config Editor — product spec

**Ticket:** SNT25-661 · **Drafted:** 2026-09-09 · **Status:** draft, v1 scope agreed
**Reads:** [`config_analysis_notes.md`](../../../contracts/snt_config/config_analysis_notes.md) ·
[`config_field_matrix.md`](../../../contracts/snt_config/config_field_matrix.md) ·
[`SNT_config.skeleton.json`](../../../contracts/snt_config/SNT_config.skeleton.json)

This spec is written for two readers: a human maintainer and a coding agent picking the work up
cold. It says *what to build and why*, and defers every schema fact to the two analysis docs above —
those are the source of truth for field semantics and must not be restated here, only referenced.

---

## 1. Problem

`SNT_config.json` is the single file that every SNT pipeline loads before it will start. Today it is
hand-edited JSON. The failure modes are well understood and all of them are quiet:

- A missing required field fails at `validate_config()` — but only once someone runs a pipeline,
  possibly days later, with an error message far from the person who caused it.
- A malformed UID never fails at all. It logs a warning and yields an empty column.
- A bare UID listed next to its own `UID.COC` child double-counts, silently.
- Leaving an optional key empty silently drops downstream indicators; nothing tells the author which.
- A string where a list belongs (`"CONF": "REDACTEDUID"`) passes validation and then extracts 11
  one-character UIDs.

The people who *have* the domain knowledge to fill this file (country teams, who know their DHIS2
pyramid and data elements) are not the people comfortable hand-editing a 200-line JSON document.

## 2. What we are building

A web app that collects the information needed for a valid `SNT_config.json`, validates it harder
than the pipelines do, and saves it — supporting a workflow that spans **days**, because filling it
requires going away and looking things up in DHIS2.

**Success condition:** a country team member with no JSON experience can produce a config that
`validate_config()` accepts, over several sessions, without ever seeing a brace.

## 3. Users and the real workflow

One primary user: a **country SNT focal point** or a Bluesquare analyst supporting them. Assume
domain knowledge (they know which pyramid level is a district), assume no JSON, assume no DHIS2 API
access from the app in v1.

The workflow this app must fit — and the single most important design input:

1. Session 1 — fills the country identity and the levels. Doesn't know the UIDs yet. **Saves a
   draft.**
2. Goes to DHIS2. Finds the data elements for `SUSP`, `TEST`, `CONF`. Copies UIDs.
3. Session 2 (next day, possibly different browser or machine) — **reopens the draft**, fills what
   they found, saves again. Still incomplete.
4. Session 3 — completes it. The app says it is now valid. **Exports the real thing.**

Steps 1 and 3 are why "just fail on missing mandatory fields" is the wrong behaviour, and why draft
persistence cannot be browser-local-only in the final version.

## 4. Scope

### v1 — in

- Form covering all three top-level sections, driven by the skeleton.
- Live validation: blocking errors, warnings, and informational "you are leaving this empty, here is
  what you lose".
- Save as **draft** at any completeness, repeatedly.
- Save/export as **final** only when validation passes with zero blocking errors.
- A log sidecar recording who saved what, when, and what was missing.
- Reopen a draft and continue.
- **Recording which DHIS2 instance the UIDs were copied from** — chosen from the workspace's
  existing DHIS2 connections. Step 2 only; see §4.1.

v1 ships in two steps (§7). **Step 1** is download-only — a proof of concept that gets the form and
the validation engine right with no platform dependency. **Step 2** writes into the workspace's
`/configuration` folder, which an OpenHEXA web app can do. Step 2 is part of v1, not a later version.

### v1 — out (decided, not forgotten)

- **Import of an existing `SNT_config.json`.** New configs only in v1. The five existing countries
  keep hand-editing for now. *(This is the first v2 feature — see §11.)*
- **Calling DHIS2.** No UID → display-name resolution, no pyramid check, no COC listing. All the
  highest-value validations in `config_analysis_notes.md` §5 items 7–10 are v2+. *(Naming a
  connection is not calling one — see §4.1.)*
- Registering versions in the `SNT_CONFIGURATION` OpenHEXA dataset. Long-term goal, §7.
- Multi-country. One config per app session, one country per file — that is the pipeline contract.
- **Multi-instance.** One config is valid against exactly **one** DHIS2 instance (§4.1). A country
  running two gets two configs, and v1 has nowhere to put the second — out of scope, warned about,
  not solved.

### 4.1 Which DHIS2 instance — naming one is not connecting to one

A country may have more than one DHIS2 holding the same data: a national HMIS (SNIS) and a malaria
registry (NMDR), for instance. **They carry the same indicators under different UIDs.** So a UID
list is only meaningful against the instance it was copied from, and a config that does not say
which instance that was is a config nobody can check.

Three consequences, and they pull in different directions — keep them distinct:

1. **The app should ask.** Step 1 of the form offers a dropdown of the workspace's existing DHIS2
   connections. This is a *label on the work*, not a channel to DHIS2: the app reads the connection
   **list**, never the connection **itself**. No credentials are used, no API call is made, and the
   "out" bullet above still holds in full.
2. **It cannot ask in step 1 of the delivery.** Enumerating connections requires the OpenHEXA
   workspace, which `LocalStore` does not have. See §7 — this is a `WorkspaceContext` capability,
   staged exactly like `WorkspaceStore`.
3. **It changes nothing in the emitted file.** The extraction pipeline receives its connection as a
   **run parameter**, chosen by whoever launches it — the same shape as `N1_METHOD`. Nothing reads a
   connection from `SNT_config.json`, and the skeleton defines no field for one. The selection is
   therefore **provenance**, recorded in `_EDITOR_METADATA` and the sidecar (§6.4), and the live
   `SNT_config.json` keeps not one extra key. CLAUDE.md rule 6 and §10 criterion 2 stand unchanged.

> **Decided 2026-09-10.** Metadata and sidecar only; no new key in `SNT_CONFIG`. Adding one would
> mean editing the vendored skeleton (§12.3 forbids it) to introduce a field no pipeline reads —
> dead configuration that looks live, which is the exact failure W6 and §6.3 exist to prevent. If
> upstream ever adds a real connection field, this decision reverses cheaply: the value is already
> being captured.

## 5. Validation model — three severities

The app must distinguish these clearly in the UI. **This is the core of the product**; the form is
just data entry.

| Severity | Meaning | Blocks final export? | Blocks draft save? |
|---|---|---|---|
| 🔴 **Blocking** | `validate_config()` would reject the file, or the app knows the value is malformed | **Yes** | No |
| 🟠 **Warning** | Valid to the pipelines, but almost certainly a mistake | No — but must be acknowledged | No |
| 🔵 **Info** | Legitimately empty; the user should know the consequence | No | No |

### 5.1 Blocking rules

Sourced from `config_analysis_notes.md` §1.3 — the app reimplements `validate_config()` exactly, so
the user sees the error here instead of in a workspace run log three days later.

> This reimplementation is the app's most important — and most fragile — dependency on the SNT
> codebase. **Read §12.2 before changing anything in this subsection.** Rules 1–7 were checked
> against `snt_lib` `v1.0.2` on 2026-11-12, through the conformance fixtures
> ([`contracts/snt_config/README.md`](../../../contracts/snt_config/README.md#conformance-fixtures--fixtures)).

1. `SNT_CONFIG.COUNTRY_CODE` non-empty after trim. Additionally: ISO3, uppercase, 3 letters.
2. `SNT_CONFIG.DHIS2_ADMINISTRATION_1` non-empty.
3. `SNT_CONFIG.DHIS2_ADMINISTRATION_2` non-empty.
4. `SNT_CONFIG.ANALYTICS_ORG_UNITS_LEVEL` non-empty (`null` counts as empty).
5. All 15 dataset identifiers present and non-empty — pre-filled, so this can only fail if something
   has gone wrong internally. Assert it, don't ask.
6. `POPULATION_INDICATOR_DEFINITIONS` non-empty and its `POPULATION` key not `null`.
7. `DHIS2_INDICATOR_DEFINITIONS` flattens to **≥ 1 UID overall**.

App-added blocking rules the pipelines do not have:

8. Every UID matches `^[A-Za-z0-9]{11}$` or `^[A-Za-z0-9]{11}\.[A-Za-z0-9]{11}$`. Permissive by
   design — a UID **may start with a digit**. Reject on length, character set and dot count only.
9. Every indicator value is a **list**, never a bare string. (Guarantees the §1.3 string-flattening
   defect cannot be produced by this app.)
10. No duplicate UID within a single list.
11. `POPULATION_INDICATOR_DEFINITIONS[*].type` ∈ {`dataElement`, `indicator`}.

### 5.2 Warnings

Each warning below is stated as the implementer needs it (the trigger) *and* as the user needs it
(what actually goes wrong, and what to do instead). **The user-facing wording matters as much as the
rule** — a warning nobody understands is a warning everybody dismisses. The wording in "Tell the
user" is a starting point, not final copy.

---

#### W1 · Double counting a data element with one of its own slices

- **Trigger:** within one indicator key, a bare `UID` appears alongside a `UID.COC` entry whose
  data-element part is that same UID.
- **What actually happens:** a bare UID expands to *every* category-option-combo of that data
  element and sums them — it is already the total. Adding `UID.REDACTEDUID` on top adds the under-5
  slice a second time. The resulting column is inflated by exactly that slice. Nothing in the
  pipelines notices; the number is simply wrong, and plausibly wrong, which is worse.
- **Tell the user:** "`REDACTEDUID` already includes every age group of that data element.
  Adding `REDACTEDUID.REDACTEDUID` counts the under-5s twice. Keep the bare UID for the total, and
  put the slice under `TEST_UNDER_5` instead."
- **Source:** `config_analysis_notes.md` §4.1, trap 1.

#### W2 · Facility level is not below the district level

- **Trigger:** `ANALYTICS_ORG_UNITS_LEVEL` ≤ the number in `DHIS2_ADMINISTRATION_2`.
- **What actually happens:** routine data is extracted at `ANALYTICS_ORG_UNITS_LEVEL`, then
  aggregated up to the ADM2 district. If the extract level is at or above the district level there
  is nothing to aggregate — the results table is built at the wrong grain, or is empty. In the five
  current countries the facility level is 2 below ADM2 (3→5, 4→6).
- **Tell the user:** "Routine data is pulled at level {N} and then rolled up to districts at level
  {M}. Since {N} is not below {M}, there is nothing to roll up. Health facilities are usually 1–3
  levels below the district."
- **Caveat for the implementer:** this is a heuristic, not a rule. Without the country's actual
  pyramid the app cannot know the real depth, which is why it is a warning and not an error.

#### W3 · Region level is not above the district level

- **Trigger:** the number in `DHIS2_ADMINISTRATION_1` ≥ the number in `DHIS2_ADMINISTRATION_2`.
- **What actually happens:** ADM1 is the region, ADM2 the district; a district sits inside a region,
  so ADM1's level number must be the smaller one. Reversed, every regional grouping in the outputs
  is wrong — results aggregate districts into things that are not their parents. It passes every
  pipeline guard, because both values are individually well-formed.
- **Tell the user:** "Region (`level_4_name`) is below district (`level_2_name`) here — these look
  swapped. Region should be the smaller level number. So far ADM1 has been level 2 and ADM2 level 3
  or 4."

#### W4 · A disaggregation set is only partly filled — 🔵 info, not a warning

> **Corrected 2026-09-10.** This rule previously claimed a hard run-time stop and demanded "all
> four" keys. Both were wrong; see "Why this is info" below. One question remains open —
> [`EXTERNAL_CHECKS.md`](EXTERNAL_CHECKS.md) item 1 — and its answer decides whether this rule stays
> info or returns to 🟠 warning. **Do not implement W4 as a blocking or warning rule until it is
> answered.**

- **Trigger:** for `SEL ∈ {UNDER_5, PREGNANT_WOMAN}`, at least one but not all of `TEST_{SEL}`,
  `CONF_{SEL}`, `SUSP_{SEL}`, `PRES_{SEL}` is non-empty.
- **What actually happens:** the disaggregated incidence columns come out **all-`NA`**, not missing.
  Every key the skeleton defines is always emitted by this app, and an empty list still produces a
  column filled with `NA` (`include_empty_ind = TRUE`, `config_analysis_notes.md` §4.1 trap 3). So
  the `[ERROR] Required columns for disaggregation '{SEL}' are missing` failure — which fires on an
  **absent** column, not an empty one — cannot be produced by a file this app writes. It is BDI's
  failure, caused by the `_UNDER5` misspelling putting the column under a name incidence never looks
  for, and the app already prevents that (§5.2 W6, CLAUDE.md rule 4).
- **Which keys are actually needed:** **not four.** `snt_dhis2_incidence` composes
  `{SUSP|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` — that is `TEST` and `CONF` plus **either** `SUSP`
  **or** `PRES`, chosen by `N1_METHOD`. `N1_METHOD` is a **pipeline run parameter, not a config
  field**, so at config-authoring time the app cannot know which of the two is required. Ask for all
  four, require none, and say why.
- **Tell the user:** "You have filled `TEST_UNDER_5` and `CONF_UNDER_5` but not `SUSP_UNDER_5` or
  `PRES_UNDER_5`. Incidence by under-5s also needs one of those two — which one depends on the
  `N1_METHOD` chosen when the pipeline is run. Left as they are, the under-5 incidence columns will
  be empty rather than wrong."
- **Why this is info and not a warning:** the outcome is a silent degradation the user may well
  intend — a partial set is legitimate if nobody runs the disaggregated analysis — and it belongs
  with the other "what you lose" statements in §5.3, not with the mistakes in §5.2.
- **Source:** `config_analysis_notes.md` §4.1 trap 3 and §4.2.

#### W5 · A long hand-enumerated list of `UID.COC` pairs

- **Trigger:** any indicator key with more than ~10 entries, most of them dotted.
- **What actually happens:** this pattern means someone listed the category combos by hand (BDI has
  62 in one key). The moment the DHIS2 instance adds a category option, the new combo is in neither
  the under-5 list nor the above-5 list, so it silently vanishes from both columns — while still
  being counted in the bare total. The two stop reconciling, and nothing reports it.
- **Tell the user:** "62 category combos listed by hand. If DHIS2 adds a new age category, it will
  be missing from this column and nobody will be told. Where possible use the bare data element for
  the total and a single `UID.COC` for the slice you need."
- **Caveat:** sometimes there is no alternative. This is genuinely advisory.

#### W6 · An indicator key outside the controlled vocabulary

- **Trigger:** a key added through the free-text "other key" escape hatch.
- **What actually happens:** the key is extracted and becomes a column in `{CC}_routine.parquet`.
  Nothing reads it. It costs download time on every extract, forever, and it looks like a working
  setting to whoever inherits the file.
- **Tell the user:** "`MALSIMP` will be downloaded and added as a column, but no current pipeline
  reads it. Add it only if you plan to use the routine data directly for ad-hoc analysis."
- **Also check:** if the key is a near-miss of a real one (`SUSP_UNDER5` for `SUSP_UNDER_5`), do not
  warn — **refuse it** and point at the correct key. See §5.1 rule 9 and CLAUDE.md rule 4.

#### W7 · `REPORTING_RATE_PRODUCT_UID` set with no reporting rates configured

- **Trigger:** `REPORTING_RATE_PRODUCT_UID` is non-empty while the reporting-rate branch is "none".
- **What actually happens:** the field filters reporting products *that were downloaded*. With
  nothing downloaded, it filters nothing — it is dead configuration that will confuse the next
  reader into thinking reporting rates are set up.
- **Tell the user:** "You have listed product UIDs to filter on, but reporting rates are set to
  'None', so nothing will be downloaded to filter. Either choose a reporting-rate source above, or
  clear this list."

#### W8 · `POPULATION` has no UIDs

- **Trigger:** `POPULATION_INDICATOR_DEFINITIONS.POPULATION.ids` is empty.
- **What actually happens:** this **passes** `validate_config()` — the check is `is None`, not
  emptiness — so no pipeline refuses to start. But population extraction is skipped with only a log
  line, and `snt_dhis2_population_transformation` has nothing to transform. Every downstream rate
  with a population denominator (incidence above all) is unavailable.
- **Tell the user:** "Leaving `POPULATION` empty is technically accepted, but population data will
  not be extracted and incidence cannot be computed. This is the one population key that is really
  used today."
- **Why a warning and not an error:** the pipelines accept it, and the app must not be stricter than
  the contract in §5.1. It is nonetheless the most consequential warning in the list.

#### W9 · A reporting-rate branch is selected but left incomplete

- **Trigger:** branch "by dataset" with no dataset UID, or branch "by indicator" with
  `ACTUAL_REPORTS` or `EXPECTED_REPORTS` empty.
- **What actually happens:** the extract falls through to `No reporting rates to download.` — the
  same outcome as choosing "None", but the config *looks* configured. A reporting-rate branch that
  is half-filled (one metric UID, not both) yields a reporting-rate calculation with a missing
  numerator or denominator.
- **Tell the user:** "You chose 'by indicator' but only `ACTUAL_REPORTS` is filled. Reporting rates
  need both an actual and an expected count. Fill `EXPECTED_REPORTS`, or switch to 'None'."

#### W10 · The workspace has no DHIS2 connection

- **Trigger:** `listDhis2Connections()` (§7) returns an empty list. Step 2 only — under `LocalStore`
  the list is unknowable, which is not the same as empty, so **do not** raise this warning in step 1.
- **What actually happens:** the config will be exported fine, and then nobody can extract with it.
  `snt_dhis2_extract` takes a DHIS2 connection as a **run parameter**; with none defined in the
  workspace there is nothing to pass, and the pipeline cannot be launched at all. The failure lands
  on whoever tries to run it, days later, and looks like a pipeline problem rather than a
  workspace-setup one.
- **Tell the user:** "This workspace has no DHIS2 connection defined. You can still fill in and save
  this configuration, but the extraction pipeline cannot run without one — someone with workspace
  admin rights needs to add it before the config is usable."
- **Why a warning and not an error:** the config is a *deliverable*, and a perfectly valid one can
  be authored before the workspace is finished being set up — that is a normal order of work. The
  app must not hold a valid file hostage to a condition it does not own. It must, though, be loud:
  this is the one warning about something entirely outside the file.
- **Also:** filter by **type**. A workspace holds connections of many kinds (PostgreSQL, S3, GCS,
  IASO…); only DHIS2-typed ones may appear in the dropdown. A non-empty connection list with no
  DHIS2 entry triggers this warning exactly like an empty one.

#### W11 · The connection changed after UIDs were entered

- **Trigger:** the selected connection differs from the one recorded in the loaded draft's
  `_EDITOR_METADATA.dhis2_connection`, and any UID has been entered.
- **What actually happens:** **the UIDs do not carry over.** Two DHIS2 instances serving the same
  country — a national SNIS and an NMDR, say — hold the same indicators under entirely different
  UIDs. Every UID already entered is now pointing at nothing in the newly selected instance. The
  app cannot detect this, because `^[A-Za-z0-9]{11}$` is satisfied either way (§5.1 rule 8), and
  neither can the pipelines: a UID that does not resolve logs a warning and yields an empty column
  (`config_analysis_notes.md` §2). The result is a config that validates, runs, and produces
  nothing.
- **Tell the user:** "You entered these UIDs against `{old}`. `{new}` is a different DHIS2 instance
  and uses different UIDs for the same data elements — switching will not translate them, and every
  UID here will need to be looked up again. Keep them anyway, or clear them and start over?"
- **Offer both actions.** Keeping is legitimate: someone may be correcting a connection they picked
  wrongly at the start, before entering anything meaningful. Clearing is destructive and must never
  be the default.
- **Note for the implementer:** this is the only place the app knows about the two-instance problem.
  It does **not** solve it — a country genuinely using both instances needs two configs, and §6.1
  allows one. See §11 open question 6.

### 5.3 Info — the "what you lose" table

This is the feature the pipelines can never provide, and the reason the app is worth building.
For every empty optional key, state the concrete consequence. Non-exhaustive, from
`config_field_matrix.md` §4.1:

| Left empty | Consequence to show the user |
|---|---|
| `MALTREAT` | Quality of care will not produce the treatment rate |
| `MALADM` | No `case_fatality_rate`, no `prop_adm_malaria` |
| `MALDTH` | No `case_fatality_rate`, no `prop_malaria_deaths` |
| `ALLADM` | No `prop_adm_malaria` (needs both `MALADM` and `ALLADM`) |
| `ALLDTH` | No `prop_malaria_deaths` |
| `ALLOUT` | Quality of care loses its all-cause outpatient denominator |
| `PRES` | Incidence cannot run with `N1_METHOD = PRES` |
| population keys other than `POPULATION` | No column is produced at all (the key is filtered out) |
| any of `{SUSP\|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` | Incidence disaggregated by `{SEL}` yields empty columns — see W4 |

Also list, plainly, every non-mandatory field left empty — the user asked for this explicitly. Info
severity, never blocking, always visible in the summary panel before saving.

### 5.4 Fields deliberately *not* validated

`COUNTRY_NAME` and `REPORTING_RATE_PRODUCT_UID` are not checked by `validate_config()`. Keep them
optional here too. `REPORTING_RATE_PRODUCT_UID` in particular has **unresolved semantics** (§11 open
question 1) — do not enforce a rule the team has not agreed.

## 6. Storage design

### 6.1 The principle

> **`SNT_config.json` is a deliverable, not a workspace.** It exists at
> `<workspace>/configuration/SNT_config.json` only when it is valid. Incomplete work lives elsewhere
> and is never mistaken for it.

This is non-negotiable: `load_configuration_snt()` reads exactly that path, and a draft sitting there
either crashes every pipeline or, worse, runs with a wrong value.

### 6.2 Layout

```
<workspace>/configuration/
  SNT_config.json                                  # live. Written ONLY on a valid save. Pure schema.
  snt_config_history/
    2026-09-09T14-32-05Z__NER__DRAFT.json          # snapshot, carries _EDITOR_METADATA
    2026-09-09T14-32-05Z__NER__DRAFT.log.json      # sidecar
    2026-09-09T16-01-11Z__NER__VALID.json          # snapshot of what was promoted to live
    2026-09-09T16-01-11Z__NER__VALID.log.json
  snt_config_draft.json                            # the single resumable working draft (latest)
```

Timestamp-first names sort chronologically. `Z` is UTC — always UTC, never local time, because
authors are in different timezones from reviewers. Colons are replaced with `-` for filesystem
safety.

`snt_config_history/` is a subfolder, so `load_configuration_snt()` never sees it.

### 6.3 Where the metadata lives — the combination

You liked both "timestamped history + sidecar log" and "status field inside the JSON". They combine
cleanly, and the combination is better than either alone, because the two file kinds have different
audiences:

| File | Carries `_EDITOR_METADATA`? | Why |
|---|---|---|
| `snt_config_draft.json` and `*__DRAFT.json` | **Yes, inline** | A draft is never fed to a pipeline. Inline metadata makes it self-describing: pick the file up anywhere — email, a colleague's machine, a bucket listing — and you know who saved it, when, and what was missing. No second file to keep paired. |
| `SNT_config.json` (live) and `*__VALID.json` | **No** | This is the pipeline's file. `config_analysis_notes.md` §1.2 is explicit: emit no key the schema doesn't define, because an unknown key looks like a real setting to the next person. Its metadata goes to the `.log.json` sidecar. |

So: **metadata inline while it is work in progress, metadata alongside once it is a deliverable.**
The promotion from draft to valid is exactly the moment `_EDITOR_METADATA` is stripped out and
written to the sidecar instead.

> Technical note: an extra top-level key would *not* break the pipelines — readers index by name and
> ignore the rest. This is a cleanliness decision, not a compatibility one. If it ever becomes
> inconvenient, keeping `_EDITOR_METADATA` in the live file is safe.

### 6.4 `_EDITOR_METADATA` shape

```jsonc
"_EDITOR_METADATA": {
  "editor_version": "0.1.0",
  "schema_source": "SNT_config.skeleton.json",
  "status": "DRAFT",                       // DRAFT | VALID
  "saved_at": "2026-09-09T14:32:05Z",      // UTC, ISO 8601
  "author": { "name": "…", "email": "…", "source": "openhexa | manual" },
  "country_code": "NER",
  "dhis2_connection": {                    // §4.1 — which instance the UIDs were copied from
    "slug": "snis-ner",                    //   the workspace connection identifier
    "name": "SNIS Niger",                  //   display name at the time of saving
    "source": "openhexa | unavailable"     //   "unavailable" under LocalStore — see below
  },
  "note": "free text from the author, e.g. 'still need the ALLADM UIDs'",
  "config_sha256": "9f2b…"                 // see §6.6 — hash of the config payload only
}
```

**On `dhis2_connection`.** This is the whole of the §4.1 decision: the instance is recorded here and
in the sidecar, and **nowhere in the config payload**. Three properties follow, and each is the
reason to prefer this placement:

- `config_sha256` **does not cover it** (§6.6 strips `_EDITOR_METADATA` before hashing). Correct: the
  hash answers "is this the same configuration?", and the same UIDs are the same configuration
  whoever labelled their origin. Re-selecting the connection does not invalidate a hash.
- A valid `SNT_config.json` gains **no key** — CLAUDE.md rule 6 and §10 criterion 2 hold.
- Under `LocalStore` there is no connection list to choose from, so the field is written as
  `{"source": "unavailable"}` with no slug. A draft authored in step 1 and reopened in step 2 must
  then **prompt for the instance**, not silently leave it blank — that draft's UIDs came from
  somewhere, and only the author knows where.

### 6.5 `.log.json` sidecar shape

Everything in `_EDITOR_METADATA`, plus the validation state **at the time of saving** — a frozen
record, not something recomputed on read:

```jsonc
{
  "…": "all _EDITOR_METADATA fields, including config_sha256",
  "file_sha256": "1c07…",        // §6.6 — hash of the exact bytes of the file this log describes
  "file_name": "SNT_config.json",
  "validation": {
    "is_valid": false,
    "blocking":  [ { "path": "SNT_CONFIG.ANALYTICS_ORG_UNITS_LEVEL", "message": "…" } ],
    "warnings":  [ { "path": "DHIS2_INDICATOR_DEFINITIONS.TEST",     "message": "…" } ],
    "empty_optional": ["SNT_CONFIG.COUNTRY_NAME", "DHIS2_INDICATOR_DEFINITIONS.ALLADM", "…"],
    "lost_capabilities": ["quality-of-care: prop_adm_malaria", "…"]
  },
  "diff_from_previous": { "changed": ["…"], "previous_file": "2026-09-09T14-32-05Z__NER__DRAFT.json" }
}
```

`diff_from_previous` is the audit trail: over a multi-day fill, it answers "what did they actually
add on Tuesday?" without diffing 200-line JSON by hand. Nice-to-have; drop it if it costs too much.

#### 6.6 Checksums — pairing a file with its log

Yes, worth doing. It is cheap, and it answers a question that will otherwise be unanswerable during
support: *"is this `SNT_config.json` the one that log describes?"* Timestamps in filenames are a
convention; a hash is evidence. Concretely it settles:

- **Is the live file still what we exported?** Someone hand-edited `SNT_config.json` after the app
  wrote it — very likely, during the transition period when not everyone uses the app. The hash in
  the sidecar no longer matches. That is the first thing to check when a pipeline behaves oddly and
  the log says the config was valid.
- **Which history snapshot is the live file?** Hash the live file, look for the matching snapshot.
  Now you know exactly which save produced what is running, without diffing.
- **Was this draft modified outside the app?** A draft carries its own hash; on load, recompute and
  compare.
- **Is a file the user emailed us the one they think it is?** Compare hashes, not filenames.

**Algorithm:** SHA-256, lowercase hex. Standard, available in every language the team uses, and
available in the browser via `crypto.subtle.digest` (a small pure-JS fallback keeps it working on
`file://` origins, where secure-context rules vary by browser).

**Two hashes, because a file cannot contain its own hash.** This is the one subtlety, and getting it
wrong makes the whole thing useless:

| Field | Hashes what | Lives in | Why |
|---|---|---|---|
| `config_sha256` | The **config payload alone** — the document with `_EDITOR_METADATA` removed, serialised canonically | `_EDITOR_METADATA` *and* the sidecar | Self-reference is impossible: adding a hash to a file changes the file. Excluding the metadata block breaks the cycle. It also makes the hash **stable across draft→valid promotion** — the same config content hashes identically whether saved as a draft or exported as final, so you can prove "this is the same configuration" across the whole history. |
| `file_sha256` | The **exact bytes** of the file on disk | the sidecar only | This is the tamper check. It covers the file as it actually exists, and only a separate file can hold it. |

**Canonical serialisation for `config_sha256`** — must be identical everywhere or the hashes will
not reproduce:

1. Remove `_EDITOR_METADATA` if present.
2. Serialise with the skeleton's key order preserved (not sorted — key order is part of the
   contract, §10 criterion 2), 2-space indent, `\n` line endings, UTF-8, no trailing newline.
3. Hash the resulting bytes.

Write this rule down in the implementation as a single shared function used by every backend. Two
implementations of "canonical JSON" is the classic way to end up with hashes that never match.

**UI treatment:** none by default. You are right that users will not use this. Show the first 8 hex
characters in a small monospace line at the bottom of the review step and in the history list, with
a copy button. That is enough to be useful in a support conversation and invisible enough not to
worry anyone.

**Verification on draft load:** recompute `config_sha256` from the loaded payload and compare with
the stored value. On mismatch, do not refuse the file — load it and show an informational note:
*"This draft was modified outside the editor."* It may be entirely legitimate (someone fixed a UID
by hand), and blocking would be worse than telling.

### 6.7 Retention

Keep every history entry. These files are a few KB; a country will produce tens, not thousands. The
history *is* the versioning until the OpenHEXA dataset takes over — and when it does, the same
snapshots become dataset file versions with no change to their shape.

## 7. Save layer — one interface, staged backends

**An OpenHEXA web app deployed in a workspace can write to the workspace filesystem.** So
`/configuration` is reachable, and the download-only first step is a deliberate staging choice, not
a platform limit. *(To be verified against the OpenHEXA MCP tools when the writing step is built —
the exact mechanism and permissions are not yet confirmed here.)*

Staging the work this way keeps the first milestone free of any platform dependency: the form and
the validation engine — which are the whole product — get built and reviewed before anything touches
a filesystem.

| Stage | `saveDraft` | `publishValid` | Status |
|---|---|---|---|
| `LocalStore` | `localStorage` + a Download button | Download `SNT_config.json` + `.log.json` | **v1 step 1 — proof of concept** |
| `WorkspaceStore` | Writes `snt_config_draft.json` + a history snapshot into `/configuration` | Writes live `SNT_config.json` + history snapshot + `.log.json` sidecar | **v1 step 2 — the real target** |
| `DatasetStore` | — | Also registers a new version in the `SNT_CONFIGURATION` OpenHEXA dataset | long-term goal |

```ts
interface ConfigStore {
  saveDraft(doc, meta): Promise<SaveResult>        // snt_config_draft.json + history snapshot
  loadDraft(): Promise<{doc, meta} | null>
  publishValid(doc, meta, log): Promise<SaveResult> // live SNT_config.json + history + sidecar
  listHistory(): Promise<HistoryEntry[]>
}
```

**Design rule:** no form or validation code may reference `localStorage`, `fetch`, or a file path
directly. All of it goes through `ConfigStore`. This is what makes step 2 an addition rather than a
rewrite — and what lets `DatasetStore` arrive later without touching the form at all.

### 7.1 `WorkspaceContext` — what the app knows about where it is running

The connection dropdown (§4.1) and the author prefill (§11 q4) both need something `ConfigStore`
does not provide: facts about the *environment*, not the document. Keep them in a second, separate
interface — persistence and environment are different concerns, and conflating them would make the
step-1 stub awkward in both.

```ts
interface WorkspaceContext {
  listDhis2Connections(): Promise<Dhis2Connection[] | null>  // null = cannot know (see below)
  currentUser(): Promise<Author | null>                      // §11 q4
}

type Dhis2Connection = { slug: string; name: string }
```

| Stage | `listDhis2Connections()` | Effect on the form |
|---|---|---|
| `LocalContext` (v1 step 1) | `null` | No dropdown. Show a disabled field reading "Available when running in OpenHEXA". **No W10.** |
| `WorkspaceContext` (v1 step 2) | The workspace's DHIS2-typed connections | Dropdown. Empty list ⇒ W10. |

**`null` and `[]` mean different things and must not be collapsed.** `null` is "this build cannot
see the workspace"; `[]` is "the workspace has no DHIS2 connection" — a real, warnable problem
(W10). A stub returning `[]` would fire W10 at every step-1 user, about a workspace they are not
even in. This is the single easiest mistake to make here.

**Filter by type, in the adapter.** Only DHIS2-typed connections may be returned. The workspace will
hold PostgreSQL, S3, GCS and IASO connections too, and a dropdown offering an S3 bucket as a DHIS2
instance would be actively misleading. The form must not be the thing doing the filtering — it
receives a list that is already correct by construction.

**Still no DHIS2 call.** `WorkspaceContext` reads connection *metadata* from the platform. It never
uses a connection's credentials and never contacts a DHIS2 server; §4 "out" holds. *(How to
enumerate connections from an OpenHEXA web app, and whether the type is exposed for filtering, is
[`EXTERNAL_CHECKS.md`](EXTERNAL_CHECKS.md) item 8 — unverified.)*

**Known limitation of `LocalStore`, to state plainly in the UI while it is the only backend:**
drafts are per-browser. A user who switches machines loses them unless they downloaded the draft
file — so Download-draft is not a convenience, it is the portability mechanism. `WorkspaceStore`
removes this limitation entirely, which is the main reason step 2 matters.

The app must also accept a previously downloaded draft file being loaded back in. *(This is a
narrow, well-defined form of file loading, not the §4 "import an existing config" feature — a draft
is a file this app wrote, whose `_EDITOR_METADATA` and checksum it can verify. See §6.6.)*

## 8. Form structure

Four steps, freely navigable — **not a locked wizard.** The user works in the order DHIS2 gives them
answers, not the order we imagined. Every step shows its own completeness state; a persistent summary
panel shows the whole document's state and both save actions.

**Step 1 — Country and instance.** `COUNTRY_CODE` (text, ISO3 uppercase, with a hard "changing this
renames every downstream artefact" warning once other data exists), `COUNTRY_NAME` (text, optional),
`DHIS2_ADMINISTRATION_1` and `_2` (dropdowns, static `level_1_name`…`level_8_name`),
`ANALYTICS_ORG_UNITS_LEVEL` (number 1–8).

Help text must carry the two things the app cannot check: ADM2 is the district and the grain of the
whole results table; `ANALYTICS_ORG_UNITS_LEVEL` is the facility level and is **not** derivable from
ADM2 — the +2 relationship in the five current countries is a coincidence. Mention that ADM1 has
been level 2 and ADM2 level 3 or 4 so far.

**Plus the DHIS2 instance** (§4.1) — a dropdown of the workspace's DHIS2-typed connections, from
`WorkspaceContext.listDhis2Connections()` (§7.1). It belongs *first on this step*, above
`COUNTRY_CODE`, for one reason: **it frames every UID entered afterwards.** A user who reaches step
3 without having said which instance they are copying from has been allowed to do the work in the
wrong frame of reference.

- **Never blocking.** It is not part of the emitted config and cannot make a file invalid (§5.1 is
  the exhaustive list). Empty list ⇒ W10; changing it after UIDs exist ⇒ W11.
- **Show the consequence, not just the label.** Under the dropdown: "UIDs are specific to the
  instance they come from. Data elements in a national HMIS and in a malaria registry have different
  UIDs even when they hold the same data." This sentence is the reason the field exists.
- **Echo it on step 3.** Routine indicators is where UIDs are actually pasted, often days later in a
  different session. A quiet line — "Entering UIDs from **SNIS Niger**" — at the top of that step
  costs nothing and catches the case where someone resumed a draft without noticing the instance.
- **Step 1 of the delivery has no dropdown at all** — `listDhis2Connections()` returns `null`, and
  the field renders disabled with "Available when running in OpenHEXA". Do not fake it with a
  free-text box: an unverifiable connection name recorded as provenance is worse than a recorded
  "unavailable", because it looks checked.

**Step 2 — Population.** The fixed 8 keys, each a UID list + a `dataElement`/`indicator` selector.
Label `POP_5_36_M` as **months**, not years. Note that only `POPULATION` has a real consumer today,
and that an empty population key produces no column at all.

**Step 3 — Routine indicators.** The skeleton's 18 keys grouped as: core-required (`SUSP`, `TEST`,
`CONF`), core-optional (`PRES`, `MALTREAT`, `MALADM`, `MALDTH`, `ALLOUT`, `ALLADM`, `ALLDTH`), and
the 8 canonical disaggregations. Plus a free-text **"other key"** escape hatch (your choice) — accepts
an uppercase key, warns that no active consumer exists, and never offers the non-underscored
spellings (`_UNDER5`) even as a suggestion.

UID entry is a chip/tag input, one UID per chip, validated on entry, with a visible reminder that
several UIDs in one key are **summed**, and that `UID.COC` narrows to one disaggregation.

**Step 4 — Reporting rates.** A three-state radio: *by dataset* / *by indicator* / *none*. The code
takes the dataset branch whenever any entry has a non-empty `DATASET`, so the UI must make the two
mutually exclusive rather than letting a user fill both. `METRICS` is pre-filled and never shown.

`SNT_DATASET_IDENTIFIERS` has no step: all 15 values are identical in every country. Pre-fill,
display read-only behind a disclosure, never ask.

## 9. Non-goals

- Not a DHIS2 browser. v1 never contacts a DHIS2 server; do not build a fake one. Listing the
  workspace's connections by name (§4.1) is not contacting one — but it is the whole of what the app
  may do with them.
- Not a connection manager. The app reads the workspace's DHIS2 connections; it never creates,
  edits, tests or repairs one. W10 tells the user to go and get one added, and stops there.
- Not a JSON editor. If someone wants to edit raw JSON, they already can.
- Not a multi-country manager.
- Does not attempt to fix the known `POP_PREGNANT_WOMEN` / `_PREGNANT_WOMAN` mismatch. Emit
  `POP_PREGNANT_WOMEN` (plural) in population and `*_PREGNANT_WOMAN` (singular) in routine
  indicators. They disagree; that is currently correct. See `config_analysis_notes.md` §3.

## 10. Acceptance criteria for v1

1. Filling only `COUNTRY_CODE`, `DHIS2_ADMINISTRATION_1`, `DHIS2_ADMINISTRATION_2`,
   `ANALYTICS_ORG_UNITS_LEVEL` and one indicator UID produces a file that `validate_config()`
   accepts. *(The five-field minimum from `config_analysis_notes.md` §1.3.)*
2. The exported valid file is byte-comparable in structure to `SNT_config.skeleton.json` — same
   sections, same key order, no extra keys.
3. With nothing filled, the app reports exactly the 5 blocking errors listed in §1.3 of the analysis
   notes, in the app, before any export.
4. A draft saved, the browser closed, and the app reopened restores every entered value.
5. A downloaded draft loaded back in restores every entered value.
6. Every export produces a paired `.log.json` whose `empty_optional` list is complete.
7. `"CONF": "REDACTEDUID"` (bare string) is unrepresentable — the UI cannot produce it.
8. Entering a bare UID and its own `UID.COC` child in one key raises the double-counting warning.
9. **Selecting a DHIS2 connection changes the emitted `SNT_config.json` not at all**, and its
   `config_sha256` not at all. The slug appears in `_EDITOR_METADATA` and the `.log.json` only.
   *(Guards §4.1 against being quietly widened into a schema change.)*
10. In a workspace with no DHIS2 connection, W10 fires and a valid config can still be exported.
    In a step-1 build, W10 does **not** fire. *(The `null`-vs-`[]` distinction, §7.1.)*
11. A dropdown offering a non-DHIS2 workspace connection is a defect. Only DHIS2-typed ones appear.

## 11. Open questions carried forward

Blocking a *correct* app, not a *working* one. From `config_analysis_notes.md` §7:

1. **`REPORTING_RATE_PRODUCT_UID` — dataset UIDs or indicator UIDs?** BFA disagrees with NER and COD.
   Until answered, the app collects it as a free UID list with a note, and does not enforce a
   relationship to `DHIS2_REPORTING_RATES`.
2. **Import + normalisation of the 5 existing configs** — the first v2 feature. Needs a decision on
   whether the app may rewrite BDI's `_UNDER5` → `_UNDER_5`, which changes column names in
   `{CC}_routine.parquet` and so needs downstream consumers checked.
3. **`COUNTRY_NAME` casing convention** — inconsistent today, reaches report titles. Once agreed the
   app can normalise on entry.
4. **Author identity source.** Does the OpenHEXA webapp context expose the logged-in user to the
   page? If yes, prefill `author`; if not, the app asks for a name once and remembers it.
   `source: "openhexa" | "manual"` in the metadata exists to record which.
5. **Retention/registration in the `SNT_CONFIGURATION` dataset** — one dataset per country, or one
   dataset with per-country files? Affects nothing in v1 but shapes `DatasetStore`.
6. **Does any country actually run two DHIS2 instances for SNT — and if so, how?** A national SNIS
   and an NMDR hold the same indicators under different UIDs, so each needs its own config, while
   `load_configuration_snt()` reads exactly one path (§6.1). None of the five current configs
   exposes this, because none records an instance at all. v1 warns (W11) and does nothing else.
   Needed before it can be solved: whether this is hypothetical or live, and whether the intended
   answer is two workspaces, two config files with a run-parameter switch, or one config carrying
   both UID sets. **Ask the SNT team** — this shapes storage (§6.2), not just the form.

Non-blocking questions 4–11 from the analysis notes are country-data questions, not app questions.
They do not gate this build.

---

## 12. Relationship to the existing SNT codebase

This app is a **separate repository that shares no code** with the SNT pipelines. It reuses their
*rules*, not their implementation. That is a deliberate consequence of the runtime split — the
pipelines are Python and R; this is a browser app — but it creates a real long-term risk, and this
section exists so that risk is managed rather than discovered.

> ⚠️ Paths and symbol names below come from
> [`config_analysis_notes.md`](../../../contracts/snt_config/config_analysis_notes.md) and
> [`config_field_matrix.md`](../../../contracts/snt_config/config_field_matrix.md), not from reading the pipelines repository
> directly. **Verify each one against the live repo before relying on it**, and correct this table
> in place when you do.

### 12.1 What is reused, and what breaks if it moves

| Upstream component | Where it lives | How this app uses it | What breaks here if it changes |
|---|---|---|---|
| **`snt_lib.validate_config()`** | `github.com/BLSQ/snt_utils` → `snt_pipeline_utils`. The pipelines install the **moving branch** `@release-v1` (DEP-1); the conformance test pins tag `v1.0.2` | **Reimplemented in JavaScript** as spec §5.1 rules 1–7. The single most important reuse. | The app declares a file valid that the pipelines reject, or blocks a file they would accept. **Silent** — nothing tells us. See §12.2 |
| **`validate_required_config_keys()`** (R side) | SNT pipelines repo, R helpers | Assumed equivalent to the Python gate. **Unverified** — the analysis docs treat them as the same contract | If the R gate is stricter, R pipelines reject files this app calls valid |
| **`load_configuration_snt()`** | SNT pipelines repo | Defines the path contract: exactly `<workspace>/configuration/SNT_config.json`. This is why §6.1 exists and why history goes in a subfolder | If it starts globbing, or reads a different path, the whole draft-isolation design needs revisiting |
| **`SNT_config.skeleton.json`** | [`docs/`](../../../contracts/snt_config/SNT_config.skeleton.json) in *this* repo | Drives the form: section order, key order, key sets, placeholder conventions. Acceptance criterion §10.2 compares against it | It is a **derived artefact** — see §12.3 |
| **The 5 reference configs** `configuration/SNT_config_<CC>.json` | SNT pipelines repo | Source of the fixed-vs-variable analysis: the 15 identical dataset identifiers, the 8 population keys, observed level values | A sixth country with a different shape invalidates a "fixed" assumption — most likely the dataset identifiers |
| **`indicators_selection()`, `build_indicators()`, `get_unique_data_elements()`** | SNT pipelines repo (extract + formatting) | Define UID semantics: bare = sum all COCs, dotted = one COC, `.split(".")[0]` at extract, lists are summed. All of §5.2 W1 and W5 rest on this | The double-counting warning becomes wrong — actively misleading, worse than absent |
| **`has_reporting_dataset()` / `has_reporting_indicator()`** | SNT pipelines repo (reporting-rate extract) | Define the XOR and that **datasets win**. This is why step 4 is a radio, not two independent sections | If the precedence flips, the UI teaches the wrong mental model |
| **`snt_dhis2_incidence` column composition** | SNT pipelines repo | Composes `{SUSP\|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` — **three** columns, not four; which of `SUSP`/`PRES` depends on the `N1_METHOD` **run parameter**, not on the config. Forces `_UNDER_5` spelling. Drives W4 and CLAUDE.md rule 4 | New disaggregation, or renamed spelling, silently unsupported by the form. If the all-`NA` behaviour changes ([`EXTERNAL_CHECKS.md`](EXTERNAL_CHECKS.md) item 1), W4's severity is wrong |
| **`select_population_column()`** | SNT pipelines repo | The `POP_PREGNANT_WOMEN` / `_PREGNANT_WOMAN` mismatch (CLAUDE.md rule 3). We deliberately emit both spellings | **If this is ever fixed upstream, rule 3 must be reversed here.** Track it |
| **`docs/DATA_ARCHITECTURE.md`, `docs/GLOSSARY.md`** | SNT pipelines repo | Source of the "what you lose" copy in §5.3 and of indicator help text. Four glossary entries are marked ❓ — do not present those as definitive | Help text drifts from reality; low severity, but it is user-facing |
| **`snt_dhis2_extract` connection parameter** | SNT pipelines repo | The extraction pipeline takes a DHIS2 connection as a **run parameter**, not from the config. This is why §4.1 records the instance as provenance only, and why W10 is a warning about the workspace rather than about the file | If a connection field is ever added to the config schema, §4.1 reverses — record it in `SNT_CONFIG` instead of `_EDITOR_METADATA`. The value is already captured, so the change is small |
| **OpenHEXA workspace connections** | OpenHEXA platform | `WorkspaceContext.listDhis2Connections()` (§7.1) enumerates them and filters to DHIS2 type. Metadata only — never the credentials, never a DHIS2 call | No enumeration API, or no type exposed ⇒ the dropdown cannot be built as specified and §4.1 falls back to "unavailable". [`EXTERNAL_CHECKS.md`](EXTERNAL_CHECKS.md) item 8 |
| **The `SNT_CONFIGURATION` OpenHEXA dataset** | OpenHEXA workspace | Long-term destination (§7 `DatasetStore`). Not touched in v1 | — |

### 12.2 The duplication problem — say it plainly

**`validate_config()` exists twice: in Python upstream, and reimplemented in JavaScript here.** There
is no mechanism today that keeps them in agreement, and the upstream dependency is unpinned, so it
can tighten under any redeploy with no PR in either repo and no CI signal.

The failure is silent in both directions. The worse one: upstream adds a required field, this app
keeps exporting files without it, and every country the app touched produces a config that no
pipeline will start.

**Settled: option 2** (migration plan, Phase 3). The fixtures are in
[`contracts/snt_config/fixtures/`](../../../contracts/snt_config/README.md#conformance-fixtures--fixtures);
the Python side runs them in CI against a pinned `snt_lib`, and this app's JS validator must run the
same folder when it is built. The options as they were weighed, cheapest first:

1. **Do nothing; re-check manually when `snt_utils` moves.** What §6 of the analysis notes already
   recommends. Zero cost, relies entirely on someone remembering.
2. **A conformance fixture set (recommended).** Keep a folder of small JSON cases — valid, and one
   per blocking rule — with the expected verdict. The JS validator runs them in this repo's tests; a
   short Python script runs the same folder through the real `validate_config()`. Any disagreement
   is a test failure. Catches drift the first time anyone runs either suite, and costs a day.
3. **Pin `snt_utils` to a ref upstream and record that ref here** in `_EDITOR_METADATA` as
   `validated_against`. Makes the coupling explicit and auditable, but the pin is a change to the
   pipelines repo, not this one.
4. **Move validation server-side** and call the real `validate_config()` — only possible once the
   app has a workspace-side component (§7 step 2). Eliminates the duplication entirely, at the cost
   of losing instant client-side feedback. **Worth revisiting when step 2 is built.**

Whatever is chosen, §5.1 must carry a note saying which upstream version it was checked against, and
when.

### 12.3 The skeleton is a derived artefact

[`docs/SNT_config.skeleton.json`](../../../contracts/snt_config/SNT_config.skeleton.json) lives in this repo but is not authored
here — it was derived from the five country configs and the code that reads them. It is the app's
schema source, so if it drifts from upstream reality the app drifts with it, confidently.

Treat it as a **vendored copy**: never edit it to suit the app. When a country config changes shape
upstream, update the skeleton first, then the form. Ideally the skeleton moves into the pipelines
repo alongside the configs it describes, and this repo vendors it with a recorded source commit —
worth proposing to the SNT team.
