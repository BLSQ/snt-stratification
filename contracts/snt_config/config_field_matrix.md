# `SNT_config.json` — field-by-field, country-by-country

**Ticket:** SNT25-661 · **Produced:** 2026-09-09 · **Scope:** the five reference copies in
[`configuration/`](https://github.com/BLSQ/snt_development/tree/94cfc383c0f8804d2eba264f26a4bd3d372d94da/deprecated/configuration) (`BDI`, `BFA`, `CMR`, `COD`, `NER`), read against the code
that consumes each key.

**Purpose.** Show at a glance which fields are the *same everywhere* (→ the web app pre-fills them,
never asks) and which *differ per country* (→ the app must collect them). The last column flags the
differences worth asking the country teams about.

> ⚠️ These are the committed **reference copies**, not the live `SNT_config.json` in each country
> workspace. Drift between the two is possible and unmeasured. See
> [`config_analysis_notes.md`](config_analysis_notes.md) §6.

Legend: `✅` consistent across all countries · `↔️` varies legitimately (real country difference) ·
`❓` varies and it is not obvious why — **ask** · `—` key absent · `0` key present, empty value.

---

## 1. `SNT_CONFIG` — 6 fields, all variable

| Field | BDI | BFA | CMR | COD | NER | Verdict |
|---|---|---|---|---|---|---|
| `COUNTRY_CODE` | BDI | BFA | CMR | COD | NER | ↔️ ISO3, uppercase. Prefixes every output file |
| `COUNTRY_NAME` | `Burundi` | `BURKINA FASO` | `REPUBLIC OF CAMEROON` | `DEMOCRATIC REPUBLIC OF CONGO` | `NIGER` | ↔️ Display only (report titles). ❓ casing is inconsistent — pick a convention |
| `DHIS2_ADMINISTRATION_1` | `level_2_name` | `level_2_name` | `level_2_name` | `level_2_name` | `level_2_name` | ✅ **level 2 in all five.** Still ask per country — nothing guarantees it |
| `DHIS2_ADMINISTRATION_2` | `level_4_name` | `level_4_name` | `level_3_name` | `level_3_name` | `level_3_name` | ↔️ Genuine pyramid difference. **The grain of the whole results table** |
| `ANALYTICS_ORG_UNITS_LEVEL` | 6 | 6 | 5 | 5 | 6 | ↔️ Facility level. Tracks ADM2 (+2 for BDI/BFA, +2 for CMR/COD… see note) |
| `REPORTING_RATE_PRODUCT_UID` | `[]` | 2 UIDs | `[]` | 1 UID | 2 UIDs | ❓ **Semantically overloaded** — see §5 |

**Note on the two level fields.** `ANALYTICS_ORG_UNITS_LEVEL` = ADM2 level + 2 in every country
here (4→6, 3→5). That is a *coincidence of these five pyramids*, not a rule — the app must not
derive one from the other. They mean different things: ADM2 is the district (population, shapes,
reporting rates), `ANALYTICS_ORG_UNITS_LEVEL` is the facility level routine data is pulled at.

---

## 2. `SNT_DATASET_IDENTIFIERS` — fixed, 15 entries

**Every value is byte-identical in all five countries.** The app pre-fills the whole block.

| Key | Value (identical everywhere) | Present in | Verdict |
|---|---|---|---|
| `DHIS2_DATASET_EXTRACTS` | `snt-dhis2-extracts` | all 5 | ✅ required |
| `DHIS2_DATASET_FORMATTED` | `snt-dhis2-formatted` | all 5 | ✅ required |
| `DHIS2_POPULATION_TRANSFORMATION` | `snt-dhis2-pop-transformation` | all 5 | ✅ required |
| `DHIS2_REPORTING_RATE` | `snt-dhis2-reporting-rate` | all 5 | ✅ required |
| `DHIS2_OUTLIERS_IMPUTATION` | `snt-dhis2-outliers-imputation` | all 5 | ✅ required |
| `DHIS2_INCIDENCE` | `snt-dhis2-incidence` | all 5 | ✅ required |
| `DHIS2_QUALITY_OF_CARE` | `snt-dhis2-quality-of-care` | all 5 | ✅ required |
| `DHS_INDICATORS` | `snt-dhs-indicators` | all 5 | ✅ required |
| `WORLDPOP_DATASET_EXTRACT` | `snt-worldpop-extract` | all 5 | ✅ required |
| `ERA5_DATASET_CLIMATE` | `snt-era5-climate` | all 5 | ✅ required |
| `SNT_HEALTHCARE_ACCESS` | `snt-healthcare-access` | all 5 | ✅ required |
| `SNT_SEASONALITY_RAINFALL` | `snt-seasonality-rainfall` | all 5 | ✅ required |
| `SNT_SEASONALITY_CASES` | `snt-seasonality-cases` | all 5 | ✅ required |
| `SNT_MAP_EXTRACTS` | `snt-map-extracts` | all 5 | ✅ required |
| `SNT_RESULTS` | `snt-results` | all 5 | ✅ required |
| `MIS_INDICATORS` | `snt-mis-indicators` | BDI, NER only | 🗑️ **no active consumer** — drop |
| `DHIS2_OUTLIERS_DETECTION` | `snt-dhis2-outliers-detection` | NER only | 🗑️ deprecated pipeline — drop |
| `DHIS2_OUTLIERS_REMOVAL_IMPUTATION` | `snt-dhis2-outliers-removal-imputation` | NER only | 🗑️ deprecated pipeline — drop |
| `SNT_SEASONALITY` | `snt-seasonality` | NER only | 🗑️ superseded by the two `SNT_SEASONALITY_*` — drop |

"Required" = at least one active `pipeline.py` or notebook indexes the key. Nine of the fifteen are
read with `[...]` (raises `KeyError` if absent); six with `.get()` (degrades). The app should always
emit all fifteen.

---

## 3. `POPULATION_INDICATOR_DEFINITIONS` — fixed 8 keys, variable `ids`

Cell = number of DHIS2 UIDs configured. `0` = key present with `ids: []` (valid; means "not
available in this instance" → warning, download skipped, NA column downstream).

| Key | BDI | BFA | CMR | COD | NER | Verdict |
|---|---|---|---|---|---|---|
| `POPULATION` | 1 | **5** | 1 | 1 | 1 | ↔️ BFA sums 5 UIDs (age bands?) into one total. Every other country has one |
| `POP_UNDER_5` | 0 | 0 | 1 | 0 | 2 | ↔️ Only CMR + NER report it |
| `POP_PREGNANT_WOMEN` | 0 | 0 | 1 | 0 | 1 | ↔️ Only CMR + NER |
| `POP_0_1_Y` | 0 | 0 | 1 | 0 | 0 | ↔️ CMR only |
| `POP_1_2_Y` | 0 | 0 | 1 | 0 | 0 | ↔️ CMR only |
| `POP_5_10_Y` | 0 | 0 | 0 | 0 | 0 | ✅ **empty in all five** — never yet used |
| `POP_5_36_M` | 0 | 0 | 0 | 0 | 0 | ✅ **empty in all five** — never yet used. Note `_M` = *months* |
| `POP_50_PLUS` | 0 | 0 | 1 | 0 | 0 | ↔️ CMR only |

All 8 keys are present in all 5 configs — **the key set is a fixed vocabulary**; only `ids` varies.
Each entry also carries `"type"`, which is `"dataElement"` in **every** entry of **every** country
(`"indicator"` is accepted by the code but unused so far).

> ❓ **Ask:** `POPULATION` is the only population key any pipeline consumes today
> (`snt_dhis2_population_transformation` operates on it alone). The other seven are extracted and
> carried into `{CC}_population.parquet` but only `POP_UNDER_5` / `POP_PREGNANT_WOMEN` are read
> further, and only via the incidence disaggregation feature. Are `POP_0_1_Y`, `POP_1_2_Y`,
> `POP_50_PLUS`, `POP_5_10_Y`, `POP_5_36_M` still wanted?

---

## 4. `DHIS2_INDICATOR_DEFINITIONS` — fixed keys, variable UID lists

Cell = number of DHIS2 UIDs. A value may be a bare `UID` (all its category-option-combos are found
and **summed**) or a pinned `UID.COC_UID`. Multiple values are summed into one column.

**The key becomes a column name in the formatted routine data.** An unrecognised key is not
rejected — it silently produces a column nothing reads. So the app must offer a controlled list.

### 4.1 Core — has an active consumer

| Key | BDI | BFA | CMR | COD | NER | Consumed by | Verdict |
|---|---|---|---|---|---|---|---|
| `SUSP` | 5 | 4 | 4 | 1 | 1 | incidence, QoC, outlier reports | ↔️ **required** |
| `TEST` | 5 | 6 | 4 | 3 | 2 | incidence, QoC, outlier reports | ↔️ **required** |
| `CONF` | 5 | 3 | 7 | 3 | 2 | incidence, QoC, outlier reports, seasonality | ↔️ **required** |
| `PRES` | 1 | 4 | 2 | 1 | 1 | incidence (`N1_METHOD=PRES`), QoC | ↔️ required if `N1_METHOD=PRES` |
| `MALTREAT` | 6 | 4 | 11 | 1 | 1 | QoC (treatment rate), outlier reports | ↔️ optional |
| `MALADM` | 3 | 4 | 2 | **0** | 1 | QoC (case fatality, `prop_adm_malaria`) | ❓ COD has the key but no UIDs |
| `MALDTH` | 3 | 4 | 2 | 1 | 2 | QoC (case fatality, `prop_malaria_deaths`) | ↔️ optional |
| `ALLOUT` | 2 | — | 4 | — | 1 | QoC, outlier reports | ❓ absent in BFA + COD |
| `ALLADM` | 1 | — | 2 | — | 3 | QoC (`prop_adm_malaria`) | ❓ absent in BFA + COD |
| `ALLDTH` | — | — | 2 | — | 1 | QoC (`prop_malaria_deaths`) | ❓ only CMR + NER |

Consequence of the `❓` rows: **BFA and COD silently get fewer quality-of-care indicators.** The
notebook guards each derived indicator with `if ("X" %in% names(qoc))`, so a missing denominator
drops that indicator with no error. Worth confirming this is intended and not an oversight.

### 4.2 Disaggregated — spelling is inconsistent, and it matters

| Key (canonical spelling) | BDI | BFA | CMR | COD | NER |
|---|---|---|---|---|---|
| `SUSP_UNDER_5` | `SUSP_UNDER5` (16) | — | — | — | 1 |
| `TEST_UNDER_5` | `TEST_UNDER5` (16) | — | — | — | 2 |
| `CONF_UNDER_5` | `CONF_UNDER5` (16) | — | — | — | 2 |
| `PRES_UNDER_5` | `PRES_UNDER5` (6) | — | — | — | 1 |
| `SUSP_PREGNANT_WOMAN` | — | — | — | — | 1 |
| `TEST_PREGNANT_WOMAN` | — | — | — | — | 2 |
| `CONF_PREGNANT_WOMAN` | — | — | — | — | 2 |
| `PRES_PREGNANT_WOMAN` | — | — | — | — | 1 |
| `*_ABOVE_5` (SUSP/TEST/CONF/PRES) | `*_ABOVE5` (62/62/62/30) | — | — | — | 1–2 each |
| `MALSEV_UNDER_5` / `_ABOVE_5` | — | — | — | `MALSEV_UNDER5` / `_ABOVE5` (1/1) | 1 / 1 |
| `MALADM_*`, `MALDTH_*`, `MALSIMP_*`, `MALTREAT_*` (`_UNDER_5`/`_ABOVE_5`/`_PREGNANT_WOMAN`) | — | — | — | — | 1–2 each |

> 🐛 **Consequence, verified in the code.** `snt_dhis2_incidence` builds its target column names as
> `{SUSP|PRES}_{SEL}`, `TEST_{SEL}`, `CONF_{SEL}` with `SEL ∈ {UNDER_5, PREGNANT_WOMAN}` — the
> **underscored** spelling. **BDI's `SUSP_UNDER5` / `TEST_UNDER5` / `CONF_UNDER5` will not match**,
> so "Analyze by Population Group → Children Under 5" fails for BDI with
> `[ERROR] Required columns for disaggregation 'UNDER_5' are missing`. Same for COD's
> `MALSEV_UNDER5` / `MALSEV_ABOVE5` (harmless today — nothing consumes `MALSEV`).
>
> **The app should write `_UNDER_5` / `_ABOVE_5` / `_PREGNANT_WOMAN` only**, and offer to rename the
> no-underscore spellings on import.

> ❓ **Ask about BDI's UID counts.** `SUSP_ABOVE5` = 62 UIDs, `SUSP_UNDER5` = 16, and `SUSP` itself =
> 5 bare UIDs. The 62 + 16 are `UID.COC` pairs enumerating the age COCs of the same data elements —
> so `SUSP` (bare, expanding to all COCs) and `SUSP_UNDER5 + SUSP_ABOVE5` should be the same total.
> Is the enumeration maintained by hand? It will drift when the DHIS2 instance adds a COC.

### 4.3 Extracted but consumed by nothing

Present in some configs; **zero active consumers** in `pipelines/`, `snt_*/` or `code/`. They are
downloaded and become columns in the formatted routine data, available for ad-hoc analysis only.

| Key | BDI | BFA | CMR | COD | NER | Verdict |
|---|---|---|---|---|---|---|
| `MALSIMP` | 1 | — | 4 | — | 1 | 🟡 unconsumed |
| `MALSEV` | 1 | — | 2 | 1 | 1 | 🟡 unconsumed |
| `PRESSEV` | — | 0 | 1 | 0 | — | 🟡 unconsumed, and empty in 2 of 3 |
| `CASRECU` | — | 0 | — | 1 | — | ❓ unconsumed + meaning unconfirmed (glossary marks it ❓) |
| `CPN` / `CPN1` | — | 0 | — | 1 | 1 (`CPN`) | ❓ two spellings, unconsumed |
| `TPI1`, `TPI3` | — | — | — | — | 1, 1 | 🟡 NER only, unconsumed |
| `MILDA_CPN`, `MILDA_VAR` | — | — | — | — | 1, 1 | ❓ NER only; `MILDA_VAR` meaning unconfirmed |
| `VAR1` | — | — | — | — | 1 | ❓ NER only, meaning unconfirmed |
| `UTILISATION` | — | — | — | — | **14** | ❓ NER only, 14 UIDs, scope unconfirmed |

> ❓ **Ask:** keep extracting these (they cost download time and add columns), or drop them until a
> consumer exists? The app needs a policy: offer them as "extra / ad-hoc" behind a disclosure, or
> not at all.

### 4.4 Overlapping definitions — worth a domain check

Found by comparing UID sets within a single country:

| Country | Observation | Question |
|---|---|---|
| CMR | `MALADM` and `MALSEV` are the **identical two UIDs** (`REDACTEDUID`, `REDACTEDUID`) | Are severe cases being used as *admissions*? `case_fatality_rate = MALDTH/MALADM` and `prop_adm_malaria = MALADM/ALLADM` both depend on `MALADM` |
| CMR | `CONF` (7) ⊃ `MALSIMP` (4) ∪ `MALSEV` (2), plus one more | Coherent decomposition, or double counting? |
| CMR | `PRESSEV` (`REDACTEDUID`) ⊂ `PRES` | Presumably intended |
| CMR | `ALLOUT` contains `REDACTEDUID`, which also appears in `SUSP` | Intended? |
| COD | `MALADM` present but **empty**, while `MALSEV` is populated | Same conflation as CMR, left unfinished? |

---

## 5. `DHIS2_REPORTING_RATES` — two mutually exclusive branches

The extract pipeline checks the **dataset** branch first and only falls through to indicators if no
entry has a non-empty `DATASET`. Both empty is valid ("No reporting rates to download").

| Country | `REPORTING_DATASETS` | `REPORTING_INDICATORS` | Branch taken | `REPORTING_RATE_PRODUCT_UID` |
|---|---|---|---|---|
| BDI | `[{DATASET: ""}]` (stub) | `{ACTUAL: "", EXPECTED: ""}` | **neither** | `[]` |
| BFA | `[{DATASET: ""}]` (stub) | `REDACTEDUID` / `REDACTEDUID` | **indicators** | ❓ the **same two indicator UIDs** |
| CMR | `[]` | `{}` | **neither** | `[]` |
| COD | 3 UIDs | `{ACTUAL: "", EXPECTED: ""}` | **datasets** | ❓ only 1 of the 3 |
| NER | 2 UIDs | `{ACTUAL: "", EXPECTED: ""}` | **datasets** | 2 UIDs — matches |

Three findings for the app:

1. **`REPORTING_RATE_PRODUCT_UID` means different things in different countries.** NER and COD hold
   DHIS2 **dataset** UIDs; BFA holds **indicator** UIDs. The consuming notebook filters
   `PRODUCT_UID %in% REPORTING_RATE_PRODUCT_UID` and, on no match, **warns and keeps everything** —
   so a wrong value degrades silently rather than failing. ❓ **Needs a decision before the app
   writes this field.**
2. **COD extracts 3 reporting datasets but uses 1.** Deliberate (extract broadly, select one) or
   stale? ❓
3. **Three spellings of "none"** — `[]`, `[{DATASET: ""}]`, `{}` vs `{ACTUAL_REPORTS: "", …}`. All
   equivalent to the code. The app should emit one: `[]` and `{}` (as the skeleton does).

`METRICS: {ACTUAL_REPORTS: "float", EXPECTED_REPORTS: "float"}` is identical in every dataset entry
of every country — a type declaration, **fixed**, pre-filled by the app.

---

## 6. Legacy blocks — read and discard, never write

None of the five current country configs contains either of these, but older files may:

| Block | Status |
|---|---|
| `POPULATION_DEFINITIONS` (`TOTAL_POPULATION_REF`, `GROWTH_FACTOR`, `REFERENCE_YEAR`, `POPULATION_INDICATORS`, `POPULATION_DISAGGREGATIONS`) | **Removed from the config.** These became *pipeline parameters* of `snt_dhis2_population_transformation`, set per run by the operator. No active code reads them from the config. Drop them on import |
| `DHIS2_DATA` as the section name, instead of `DHIS2_DATA_DEFINITIONS` | Historical section name. One display-only cell in `snt_dhis2_formatting_routine.ipynb` still reads it, gets `NULL`, and is harmless. Rename on import |

---

## 7. Summary — what the app asks vs pre-fills

| | Count | Fields |
|---|---|---|
| **Pre-filled, never shown** | 15 + 2 | all `SNT_DATASET_IDENTIFIERS`; each `METRICS` block; every key *name* |
| **Constrained choice (dropdown)** | 3 | `DHIS2_ADMINISTRATION_1/2` (static `level_1_name`…`level_8_name` list — no pyramid needed), `type` (`dataElement`\|`indicator`), reporting-rate branch (datasets \| indicators \| none) |
| **Free user input** | 3 | `COUNTRY_CODE`, `COUNTRY_NAME`, `ANALYTICS_ORG_UNITS_LEVEL` |
| **UID lists — the real work** | 8 population + 10 core indicators + up to 8 disaggregations + reporting rates | see §3, §4, §5 |
