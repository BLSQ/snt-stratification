# `SNT_config.json` — mechanics, rules and open questions

**Ticket:** SNT25-661 · **Produced:** 2026-09-09
**Companions:** [`SNT_config.skeleton.json`](SNT_config.skeleton.json) ·
[`config_field_matrix.md`](config_field_matrix.md)

Everything a developer or an agent needs to build a web app that emits a **valid
`SNT_config.json` consumable by the existing pipelines with no pipeline-code change**. Section 1 is
the contract; §2–4 the per-field rules; §5 the validation the app can do that the pipelines cannot;
§6 what is unverified; §7 the open questions for the SNT team.

---

## 1. The contract — what "valid" means

### 1.1 One file, one path, one country

Pipelines load exactly `<workspace>/configuration/SNT_config.json` via
`load_configuration_snt()`, then call `validate_config()` (Python) or
`validate_required_config_keys()` (R). One file, one country, one workspace. The committed
`configuration/SNT_config_<CC>.json` copies are **reference only** — in a workspace the file is
renamed by hand to drop the `_<CC>` suffix.

**Consequence for the app:** whatever it stores internally, it must **emit a single merged
document**. Splitting the fixed and variable halves into two files is a sound *storage* idea — the
fixed/variable line falls cleanly between `SNT_DATASET_IDENTIFIERS` and the rest — but two files
cannot be the deliverable without a pipeline change, which is out of scope.

### 1.2 Three top-level sections, no more

```
SNT_CONFIG                 6 fields             — all country-specific
SNT_DATASET_IDENTIFIERS    15 name → slug       — identical in every country
DHIS2_DATA_DEFINITIONS
  POPULATION_INDICATOR_DEFINITIONS   8 fixed keys → {ids: [...], type: "..."}
  DHIS2_INDICATOR_DEFINITIONS        controlled keys → [UID | UID.COC, ...]
  DHIS2_REPORTING_RATES              REPORTING_DATASETS[]  XOR  REPORTING_INDICATORS{}
```

No other top-level key is read anywhere. Extra keys are ignored (readers index by name) — but the
app should not emit any: there is no comment mechanism, and an unknown key looks like a real
setting to the next person.

### 1.3 What is hard-required — `validate_config()` is the gate

**All 20 active pipelines call `snt_lib.validate_config()` immediately after loading the config.**
It collects *every* problem and raises one aggregated `ValueError`, so a config either satisfies the
list below or **no pipeline starts at all**. This is the app's real target — satisfy it and the file
is accepted everywhere.

| Rule | Failure |
|---|---|
| All three top-level sections present | `KeyError: Missing top-level key(s) in config: …` |
| `SNT_CONFIG.COUNTRY_CODE` non-empty after `str().strip()` | `SNT_CONFIG.COUNTRY_CODE is missing or empty` |
| `SNT_CONFIG.DHIS2_ADMINISTRATION_1` non-empty | same shape |
| `SNT_CONFIG.DHIS2_ADMINISTRATION_2` non-empty | same shape |
| `SNT_CONFIG.ANALYTICS_ORG_UNITS_LEVEL` non-empty | same shape (`null` is caught) |
| **All 15** dataset identifiers present and non-empty | one error line per missing key |
| `POPULATION_INDICATOR_DEFINITIONS` non-empty **and** its `POPULATION` key not `None` | `… POPULATION is not configured` |
| `DHIS2_INDICATOR_DEFINITIONS` flattens to **≥ 1 UID overall** | `… has no indicators defined` |

Three consequences worth building on:

- **`COUNTRY_NAME` and `REPORTING_RATE_PRODUCT_UID` are *not* validated.** Both may be absent or
  empty and every pipeline still runs.
- **All 15 dataset identifiers are hard-required** — not just the nine that are read with `[...]`.
  The app must always emit the full block.
- `POPULATION` only has to *exist*: `{"ids": [], "type": "dataElement"}` passes the check, because
  the test is `is None`, not emptiness. The skeleton relies on this.

Beyond `validate_config`, the per-pipeline guards that fire later:

| Field | If it passes validation but is still wrong |
|---|---|
| `DHIS2_ADMINISTRATION_1/2` | Format-checked against `level_(\d+)_` and bounds-checked against `pyramid["level"].max()` at extract — `raise ValueError` |
| `ANALYTICS_ORG_UNITS_LEVEL` | Bounds-checked the same way — `raise ValueError` |
| `POPULATION_INDICATOR_DEFINITIONS` all `ids` empty | `log_warning`, population extract **skipped, run still succeeds** |
| `REPORTING_RATE_PRODUCT_UID` wrong or unmatched | Notebook warns and keeps **all** reporting data unfiltered — silent degradation |
| `DHIS2_REPORTING_RATES` both branches empty | `log_info("No reporting rates to download.")` — legitimate |

**Individual indicator keys are never required to be present.** `indicators_selection()` iterates
over whatever names exist, and `validate_config` only counts UIDs across all keys. So an omitted
optional key is not an error — it just yields no column. The skeleton ships the optional keys for
discoverability, not necessity.

> **One weakness to compensate for.** `validate_config`'s "values must be lists" check is
> `for val in sublist`, which only raises `TypeError` on a non-iterable (`None`, a number). A
> **string** value passes and flattens into individual characters — so
> `"SUSP": "aZwnLALknnj"` (a bare string instead of a list) validates cleanly and then extracts 11
> one-character "UIDs". The app must guarantee every value is a list.

### 1.4 Placeholder convention in the skeleton

`""` for unfilled strings, `null` for the unfilled integer, `[]` / `{}` for unfilled collections.

**Deliberately not sentinel strings** like `"<FILL ME>"`. A sentinel is non-empty, so it passes
`validate_config()` — a half-filled file renamed to `SNT_config.json` would run and produce files
called `<FILL ME>_routine.parquet`. Empty and `null` are caught instead.

The skeleton is therefore **structurally** valid and schema-complete, but **not runnable until
filled** — by design. Handed to a pipeline as-is, `validate_config()` raises exactly this, which
doubles as the checklist of the minimum the app must collect:

```
Configuration validation failed with 5 error(s):
  - SNT_CONFIG.COUNTRY_CODE is missing or empty
  - SNT_CONFIG.DHIS2_ADMINISTRATION_1 is missing or empty
  - SNT_CONFIG.DHIS2_ADMINISTRATION_2 is missing or empty
  - SNT_CONFIG.ANALYTICS_ORG_UNITS_LEVEL is missing or empty
  - DHIS2_DATA_DEFINITIONS.DHIS2_INDICATOR_DEFINITIONS has no indicators defined
```

Note what is *not* in that list: the 15 dataset identifiers (pre-filled), and `POPULATION` — which
passes with `ids: []`, since the check is `is None`. So **five filled fields plus one indicator UID
is the true minimum** for a config that starts. Verified by running `validate_config()` against the
skeleton; the five country configs all pass it unchanged.

---

## 2. `SNT_CONFIG` — the six fields

| Field | Type | Rule | UI |
|---|---|---|---|
| `COUNTRY_CODE` | string | ISO3, **uppercase**. Prefixes every data file (`{CC}_routine.parquet`) | Text + ISO3 validation. **Warn hard on change** — effectively immutable once pipelines have run, since it renames every artefact |
| `COUNTRY_NAME` | string | Free text, display only | Text |
| `DHIS2_ADMINISTRATION_1` | string | Must match `level_(\d+)_name`. The **region** level | Dropdown, **hardcoded list** — see below |
| `DHIS2_ADMINISTRATION_2` | string | Same format. The **district** level — the grain of the final results table, and the join key for population, shapes and reporting rates | Dropdown, **hardcoded list** — see below |
| `ANALYTICS_ORG_UNITS_LEVEL` | integer | 1 ≤ N ≤ pyramid depth. The **facility** level routine data is pulled at | Number picker, 1–8 |
| `REPORTING_RATE_PRODUCT_UID` | array of UID | Filters which reporting product(s) reach downstream. See §4.3 | Multi-select of the UIDs configured in `DHIS2_REPORTING_RATES` |

> ⚠️ **`ANALYTICS_ORG_UNITS_LEVEL` and `DHIS2_ADMINISTRATION_2` are not interchangeable and neither
> can be derived from the other.** In all five current countries the former happens to be the
> latter + 2; that is a coincidence of those pyramids. Ask for both, independently.

**The two `level_N_name` fields: a fixed choice list, not free text.** The app has no pyramid at
this stage, so it cannot offer the country's real level names — but it does not need to. The only
thing that must be right at authoring time is the **format**, and the value space is tiny and
known. Ship a static list:

```
level_1_name  level_2_name  level_3_name  level_4_name
level_5_name  level_6_name  level_7_name  level_8_name
```

That removes the whole class of typo failures (`level3_name`, `Level_3_Name`, `district`) without
needing a DHIS2 connection. The user still has to know *which* level is their district — that is
domain knowledge they have and the app cannot supply. Say so in the help text, and note that the
levels used so far are 2 for ADM1 and 3 or 4 for ADM2.

The remaining risk the app cannot close: a well-formatted but *wrong* level parses fine, passes
every guard, and produces a results table at the wrong administrative grain. Once the pyramid is
available (a later iteration, or a validation step run inside the workspace) these three fields are
the first thing worth checking against it — showing each level's number, DHIS2 name and a couple of
example org units.

---

## 3. `POPULATION_INDICATOR_DEFINITIONS`

Fixed 8-key vocabulary; only the values vary:

```
POPULATION  POP_UNDER_5  POP_PREGNANT_WOMEN  POP_0_1_Y  POP_1_2_Y  POP_5_10_Y  POP_5_36_M  POP_50_PLUS
```

- Shape per key: `{"ids": [<UID>, ...], "type": "dataElement" | "indicator"}`.
- `type` is a **two-value enum** — anything else raises
  `Invalid population indicator type for {name}. Must be 'indicator' or 'dataElement'.` Every entry
  in every current country is `"dataElement"`.
- `ids: []` is the normal "not available in this instance" state: logs
  `No ids defined for population indicator {name}. Skipping.`, then the R side filters the key out
  entirely, so **no column is produced** (unlike the routine indicators, which produce an NA
  column). All 8 keys stay in the file regardless.
- Multiple `ids` are aggregated into the single named column.
- `POP_5_36_M` is **months** (5–36 months), not years — the odd one out. Say so in the UI.
- Only `POPULATION` has a real consumer today (`snt_dhis2_population_transformation`).
  `POP_UNDER_5` and `POP_PREGNANT_WOMEN` are read only through the incidence disaggregation feature.

> 🐛 **Known defect — do not "fix" it in the config.** Selecting "Pregnant Women" in
> `snt_dhis2_incidence` always fails: the indicator suffix is `_PREGNANT_WOMAN` (singular) but the
> population column every producer writes is `POP_PREGNANT_WOMEN` (plural), so
> `select_population_column()` calls `stop()`. It fails loudly — no bad data. The fix belongs in
> `select_population_column()`, **not** in a config rename: the singular value legitimately drives
> the indicator suffix. See `docs/DATA_ARCHITECTURE.md` §6.1.
>
> **App rule:** emit `POP_PREGNANT_WOMEN` (plural) here and `*_PREGNANT_WOMAN` (singular) in the
> routine indicators. Yes, they disagree. That is currently correct.

---

## 4. `DHIS2_DATA_DEFINITIONS` — routine indicators and reporting rates

### 4.1 How to fill `DHIS2_INDICATOR_DEFINITIONS`

The whole block is one flat mapping: **an SNT indicator name → the list of DHIS2 things to add up
to produce it.**

```jsonc
"DHIS2_INDICATOR_DEFINITIONS": {
  "CONF": ["REDACTEDUID", "REDACTEDUID"],              // two data elements, summed
  "CONF_UNDER_5": ["REDACTEDUID.REDACTEDUID"],         // one data element, one age category only
  "ALLADM": []                                          // not available in this instance
}
```

**Left side — the key.** Comes from the controlled vocabulary in §4.2, uppercase. It **becomes a
column name** in `{CC}_routine.parquet`. An unrecognised key is not rejected; it silently produces
a column nothing downstream reads. So the app offers a fixed list and never free text. (The R side
does `toupper()` on the names, so a lowercase key survives there — but the Python extract does not,
so always emit uppercase.)

**Right side — the value. Always a JSON list of strings**, even for a single entry, and even when
empty. `"CONF": "REDACTEDUID"` is **not** a valid substitute: it passes `validate_config()` and
then extracts 11 one-character UIDs (see §1.3).

#### Expected format of each entry

| Form | Pattern | Length | Example |
|---|---|---|---|
| Data element | `^[A-Za-z0-9]{11}$` | exactly **11** | `REDACTEDUID` |
| Data element **.** category option combo | `^[A-Za-z0-9]{11}\.[A-Za-z0-9]{11}$` | exactly **23** (11 + `.` + 11) | `REDACTEDUID.REDACTEDUID` |

That is the standard DHIS2 UID: **11 characters, alphanumeric, case-sensitive.** No other
constraint — in particular a UID **may start with a digit**, so do not require a leading letter.
Every UID in the five current configs happens to start with a letter; that is a coincidence of this
sample, not a rule, and a validator that enforced it would reject legitimate UIDs.

Verified by scanning every UID in all five country configs — 150 distinct bare data elements and
248 distinct dotted pairs: every component exactly 11 alphanumeric characters, and every dotted
value containing exactly **one** dot. **At most one dot** — there is no three-part form.

Keep the pattern permissive. Rejecting a real UID that a country expert pasted correctly is a much
worse failure than accepting an odd-looking one, which the length and character-set checks already
catch in every practical case (truncation, whitespace, a pasted display name, a stray second dot).

Validation the app should apply per entry: trim whitespace, reject anything that is not one of the
two patterns above, and reject duplicates within a list. The pipelines do none of this: a malformed
UID simply matches no column and logs `Indicator '{X}': data points '{uid}' not found` — a
**warning**, not an error, followed by an empty or partial column.

#### What a list does (comma-separated entries) — they are SUMMED

Several entries in one list are **added together into a single column**, per org unit and month:

```jsonc
"TEST": ["REDACTEDUID", "REDACTEDUID"]
```
→ column `TEST` = `REDACTEDUID` + `REDACTEDUID`.

This is how a country whose DHIS2 splits one concept across several data elements (by facility type,
by programme, by RDT vs microscopy) rolls them back into one SNT indicator. `NA` values are ignored
in the sum (`na.rm = TRUE`), **except** that a row where *all* contributing values are `NA` stays
`NA` rather than becoming `0` — a genuinely missing month is preserved as missing, not silently
turned into a zero. Order is irrelevant.

#### What a dot does — it narrows to one disaggregation

A bare data element and a dotted pair differ **only at the formatting stage**; the extract treats
them identically.

**At extract**, `get_unique_data_elements()` does `item.split(".")[0]` — **the COC part is
discarded**. Whatever you write, the whole data element is downloaded with all of its category
option combos. So:

> Adding `.COC` never reduces what is downloaded, and never speeds up an extract. It is purely a
> selector applied afterwards.

**At formatting**, the raw data is pivoted wide with one column per `<dataElement>_<COC>` pair. Then
each configured entry is resolved (`build_indicators()`):

| You write | Matching rule | Result |
|---|---|---|
| `REDACTEDUID` (bare) | regex `^REDACTEDUID(_\|$)` | **every** COC column of that data element, **summed** — i.e. the data element's total across all disaggregations |
| `REDACTEDUID.REDACTEDUID` (dotted) | the `.` becomes `_`, then an exact column-name match | **only** that one data element × category combination |

So the two forms answer two different questions:

- **bare** — "give me the total for this data element" → use for the core indicators (`SUSP`,
  `TEST`, `CONF`, `PRES`, `MALTREAT`, …).
- **dotted** — "give me only the under-5 slice of this data element" → use for the disaggregated
  keys (`TEST_UNDER_5`, `CONF_PREGNANT_WOMAN`, …), where the age or pregnancy split lives in the
  data element's category combination rather than in a separate data element.

#### The three traps this creates

1. **Double counting.** Listing a bare UID *and* one of its own dotted children in the same list
   adds that slice twice: `["REDACTEDUID", "REDACTEDUID.REDACTEDUID"]` counts the under-5s once in
   the total and once again on top. Nothing warns. The app should block it.
2. **Hand-enumerated COC lists drift.** Building `TEST_ABOVE_5` by listing every non-under-5 COC by
   hand (BDI does this with 62 entries) breaks silently the moment the DHIS2 instance adds a
   category option: the new combination is in neither list, so it vanishes from both the under-5 and
   the above-5 columns while still being counted in the bare `TEST` total. Prefer bare + one dotted
   slice over exhaustive enumeration.
3. **An empty list still creates the column**, filled with `NA` (`include_empty_ind = TRUE`) — so
   empty keys are harmless placeholders, which is why the skeleton can ship them. But it also means
   "configured but empty" and "genuinely no data" are indistinguishable downstream: both are an
   all-`NA` column.

#### Filling order that works

1. Pick the indicator key from the list in §4.2.
2. In DHIS2, find the data element(s) that carry that concept. Copy the **UID**, not the name.
3. One data element covers it → single-entry list. Several → list them all; they are summed.
4. Need only an age or pregnancy slice → append `.` + the **category option combo UID**, and put it
   under the matching `*_UNDER_5` / `*_PREGNANT_WOMAN` key, not under the core key.
5. Concept absent from this instance → leave `[]`. Do not delete the key; do not invent a UID.

### 4.2 The controlled vocabulary

**Core — has an active consumer (the skeleton's 10):**

| Key | Consumed by | Required? |
|---|---|---|
| `SUSP`, `TEST`, `CONF` | incidence, quality of care, outlier reports, seasonality | **yes** |
| `PRES` | incidence when `N1_METHOD=PRES`; quality of care | required for that method |
| `MALTREAT` | QoC treatment rate | optional |
| `MALADM`, `MALDTH` | QoC case fatality, `prop_adm_malaria` | optional |
| `ALLOUT`, `ALLADM`, `ALLDTH` | QoC all-cause denominators | optional |

Every optional one degrades **silently**: quality of care guards each derived indicator with
`if ("X" %in% names(qoc))`, so a missing input drops that indicator with no error. The app should
tell the user *which indicators they lose* by leaving a key empty — the pipelines never will.

**Disaggregations — canonical spelling only:**

`snt_dhis2_incidence` composes `{SUSP|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` with
`SEL ∈ {UNDER_5, PREGNANT_WOMAN}`. So the only spellings that work are:

```
SUSP_UNDER_5   TEST_UNDER_5   CONF_UNDER_5   PRES_UNDER_5
SUSP_PREGNANT_WOMAN   TEST_PREGNANT_WOMAN   CONF_PREGNANT_WOMAN   PRES_PREGNANT_WOMAN
```

The columns must be **present**, or the run stops with
`[ERROR] Required columns for disaggregation '{SEL}' are missing`. Two corrections to note, both
made 2026-09-10:

- **It is three columns per set, not four.** `TEST_{SEL}` and `CONF_{SEL}` plus **one** of
  `SUSP_{SEL}` / `PRES_{SEL}`, selected by the `N1_METHOD` **pipeline run parameter** — which is not
  a config field, so the config cannot say which of the two will be needed. An earlier revision of
  this paragraph said "all four", contradicting the composition rule two lines above it.
- **Present, not non-empty.** Per §4.1 trap 3, an empty list still creates the column
  (`include_empty_ind = TRUE`). The error therefore fires on a **missing or misspelled key**
  (BDI's `_UNDER5`), not on an empty one; an empty key yields an all-`NA` column instead. ❓ Whether
  `snt_dhis2_incidence` has a second guard that rejects an all-`NA` column is **unverified** — see
  [`EXTERNAL_CHECKS.md`](../../webapps/config_editor/docs/EXTERNAL_CHECKS.md) item 1.

`_ABOVE_5` variants exist in some configs but **no code consumes them**.

**Extract-only — zero active consumers:** `MALSIMP`, `MALSEV`, `PRESSEV`, `CASRECU`, `CPN`, `CPN1`,
`TPI1`, `TPI3`, `MILDA_CPN`, `MILDA_VAR`, `VAR1`, `UTILISATION`. Downloaded, turned into columns,
read by nothing. Definitions and confidence flags for all of these are in
[`docs/GLOSSARY.md` §2](../../docs/GLOSSARY.md) — four are marked ❓ (meaning unconfirmed). See §7.

### 4.3 `DHIS2_REPORTING_RATES` — XOR, and one overloaded field

Two branches, and the choice is made by the code, not the operator:

```python
if has_reporting_dataset(rep_datasets):  # any entry with a non-empty DATASET
    handle_reporting_datasets(...)
elif has_reporting_indicator(rep_indicators):  # any non-empty value
    handle_reporting_indicators(...)
else:
    log_info("No reporting rates to download.")
```

The dataset branch **wins**. So a config carrying both silently ignores the indicators. → **radio
button in the UI**, three states: *by dataset* / *by indicator* / *none*.

Shapes:

```jsonc
// branch A — by DHIS2 dataset (one entry per dataset)
"REPORTING_DATASETS": [
  { "DATASET": "REDACTEDUID",
    "METRICS": { "ACTUAL_REPORTS": "float", "EXPECTED_REPORTS": "float" } }
],
"REPORTING_INDICATORS": {}

// branch B — by DHIS2 indicator (one UID per metric)
"REPORTING_DATASETS": [],
"REPORTING_INDICATORS": { "ACTUAL_REPORTS": "REDACTEDUID", "EXPECTED_REPORTS": "REDACTEDUID" }

// branch C — none (what the skeleton ships)
"REPORTING_DATASETS": [], "REPORTING_INDICATORS": {}
```

The `METRICS` block is a fixed type declaration — identical in every entry of every country. The
app pre-fills it and never shows it.

> ❓ **`REPORTING_RATE_PRODUCT_UID` needs a decision before the app writes it.** It filters which
> reporting product reaches downstream (`filter(PRODUCT_UID %in% REPORTING_RATE_PRODUCT_UID)`), and
> today it means **different things in different countries**: NER and COD hold DHIS2 *dataset* UIDs;
> BFA holds the two *indicator* UIDs. On no match the notebook **warns and keeps everything
> unfiltered** — silent degradation. Once the intended semantics are settled, the app can derive
> this field as a multi-select over whatever was configured in `DHIS2_REPORTING_RATES`, instead of
> asking for raw UIDs a second time.

---

## 5. What the app can validate that the pipelines cannot

Each of these failures is today a buried log line or an empty column. The first group needs nothing
but the file itself.

**Offline — available now, no DHIS2 connection:**

1. **Reject malformed UIDs on entry** — the 11-alphanumeric-character rule in §4.1 catches
   truncation, pasted whitespace, an accidental second dot, and a display name pasted instead of a
   UID. Keep it permissive: length and character set only, no leading-letter requirement.
2. **Detect double counting** — a bare UID listed alongside its own `UID.COC` children in the same
   list (§4.1).
3. **Report the downstream cost of an empty key**: "leaving `ALLADM` empty means quality of care
   will not produce `prop_adm_malaria`." The pipelines never say this — they just drop the
   indicator.
4. **Enforce the format of the two level fields** from a static choice list (§2).
5. **Run the `validate_config()` rules from §1.3 before the file is exported**, so the user sees the
   five-line error in the app instead of in a workspace run log.
6. **Normalise on import** — `_UNDER5`→`_UNDER_5`, `_ABOVE5`→`_ABOVE_5`, the three "none" spellings
   for reporting rates, uppercase keys, and drop the four dead dataset identifiers.

**Later, if the app ever gets a DHIS2 connection** — highest value, but not needed for a first
version:

7. **Resolve every UID to its display name** beside the field. A typo'd UID today produces
   `data points '{uid}' not found` (a warning) and an empty column.
8. **Flag UIDs that no longer exist** in the instance — the classic decay of a hand-maintained
   config.
9. **List a data element's category-option-combos** when the user wants to pin `UID.COC`, instead of
   hand-transcribing 62 of them (see BDI, §4.2 of the matrix).
10. **Check the three level fields against the real pyramid** — the file's worst remaining
    silent-failure mode, since a well-formatted wrong level passes every existing guard.

---

## 6. Unverified — read before trusting this

1. **`snt_lib.validate_config()` is now confirmed** — its source was supplied and §1.3 reflects it
   exactly, checked by running it against the skeleton and all five country configs, and again on
   2026-11-12 against `snt_lib` `v1.0.2` through the conformance fixtures
   ([`README.md`](README.md#conformance-fixtures--fixtures)). The residual risk is that the
   pipelines install `snt_lib` from the moving branch `@release-v1`
   ([DEP-1](../../docs/BACKLOG.md#dep-1)): its requirements can tighten under any redeploy, with no
   PR in this repo. The conformance test is pinned, so it signals such a change only when its pin is
   bumped.
2. **Only the five committed reference copies were read**, not the live `SNT_config.json` in each
   country workspace. Drift between them is possible and unmeasured. Run a handful of real
   workspace configs through the app's importer early — that is the cheapest way to discover format
   variants this analysis missed.
3. **No pipeline was executed.** Apart from `validate_config()`, every claim here comes from reading
   `pipeline.py`, the notebooks and the `.r` helpers. This repo has no test suite and no CI lint, so
   nothing mechanical corroborates the rest.
4. **`docs/GLOSSARY.md` marks several indicator meanings ❓** — those are genuinely unconfirmed, not
   just undocumented. Do not let the app present a guessed definition as help text.

---

## 7. Open questions for the SNT team

Ordered by how much they block the app.

**Blocking — the app cannot emit a correct field without an answer:**

1. **`REPORTING_RATE_PRODUCT_UID`: dataset UIDs or indicator UIDs?** BFA disagrees with NER and COD.
   (§4.3)
2. **Disaggregation spelling: `_UNDER_5` or `_UNDER5`?** The code requires the underscore; BDI's
   config uses the other. Confirm the app may rewrite BDI on import — it changes column names in
   `{CC}_routine.parquet`, so downstream consumers of that file need checking.
3. **Which indicator keys should the app offer at all?** Ten have consumers; twelve more are
   extracted and read by nothing. Offer them as "extra / ad-hoc", or drop them?

**Non-blocking, but worth asking while the country teams are engaged:**

4. **CMR: `MALADM` and `MALSEV` are the identical two UIDs.** Are severe cases standing in for
   admissions? Both `case_fatality_rate = MALDTH/MALADM` and `prop_adm_malaria = MALADM/ALLADM`
   depend on it. **COD has the same conflation, left half-done** — `MALADM` present but empty,
   `MALSEV` populated.
5. **BFA and COD have no `ALLOUT`, `ALLADM` or `ALLDTH`**, so they silently produce fewer
   quality-of-care indicators. Intended, or an oversight?
6. **COD extracts 3 reporting datasets but selects 1** via `REPORTING_RATE_PRODUCT_UID`. Deliberate
   or stale?
7. **BDI's hand-enumerated COC lists** (`SUSP_ABOVE5` = 62 `UID.COC` pairs, `SUSP_UNDER5` = 16)
   should sum to the same total as bare `SUSP`. Maintained by hand? They will drift the moment the
   DHIS2 instance adds a category option.
8. **BFA sums 5 UIDs into `POPULATION`** while every other country has one. Age bands being
   totalled? If so, should they be in the disaggregation keys instead?
9. **`POP_5_10_Y` and `POP_5_36_M` are empty in all five countries** — retire the keys, or is a
   country expected to fill them?
10. **`COUNTRY_NAME` casing** is inconsistent (`Burundi` vs `BURKINA FASO`). It reaches report
    titles. Pick a convention so the app can enforce it.
11. **Definitions still marked ❓ in the glossary**: `CASRECU`, `MILDA_VAR`, `VAR1`, `UTILISATION`
    (and `CPN` vs `CPN1` — two spellings across countries). Needed only if question 3 keeps them.

---

## 8. Where the authoritative detail lives

| Topic | Source |
|---|---|
| Config schema summary | `docs/DATA_ARCHITECTURE.md` §5.4 |
| Existing validation controls and their behaviour | `docs/DATA_ARCHITECTURE.md` §6 |
| The `POP_PREGNANT_WOMAN` defect, traced | `docs/DATA_ARCHITECTURE.md` §6.1 |
| Indicator vocabulary, French etymology, confidence flags | `docs/GLOSSARY.md` §2 |
| Admin-level rules, naming and schema conventions | `CLAUDE.md` → Schema, Configuration |
| `validate_config()` — the universal gate | external: `github.com/BLSQ/snt_utils`, `snt_pipeline_utils` (unpinned) |
| The five reference configs this analysis is based on | `configuration/SNT_config_<CC>.json` |
