# `contracts/snt_config/` — `SNT_config.json`

Reference for the structure of the SNT configuration file. **Nothing in this folder is read by a
pipeline.** In a workspace, the config is the file `SNT_config.json` in the latest version of the
dataset `SNT_CONFIGURATION`: one file, one country, one workspace
([ADR 0043](../../docs/decisions/0043-config-read-from-snt-configuration-dataset.md)). People upload
it by hand ([below](#snt-configuration-dataset)); in future the config editor will write it.

**Switch in progress** ([BACKLOG CFG-4](../../docs/BACKLOG.md#cfg-4)): the notebooks read the
dataset, but each `pipeline.py` still reads `<workspace>/configuration/SNT_config.json`. Until that
is done, a workspace needs both, with the same content.

| File | What it is | Trust it? |
|---|---|---|
| `SNT_config.skeleton.json` | The **fixed part** of `SNT_config.json`, which is the same in every country and workspace. The country-specific values are left empty. The one copy, shared by the pipelines and the config editor. | **Yes.** This is the reference for the current structure. |
| [`config_analysis_notes.md`](config_analysis_notes.md) | What "valid" means, per-field rules and traps, read from the pipeline code. | **Yes**, it is the source of truth for the field rules. |
| [`config_field_matrix.md`](config_field_matrix.md) | Field by field across the five archived country copies: what is fixed, what varies. | As a survey of those copies, which were never verified (below). |
| [`fixtures/`](fixtures/) | Conformance cases: configs with the verdict `validate_config()` must return ([below](#conformance-fixtures--fixtures)). | **Yes**, run in CI. |

Past per-country copies (BDI, BFA, CMR, COD, NER) are archived in
[`deprecated/configuration/`](https://github.com/BLSQ/snt_development/blob/94cfc383c0f8804d2eba264f26a4bd3d372d94da/deprecated/configuration/README.md). They were never checked
against the running workspaces: use them as examples only.

---

## <a id="snt-configuration-dataset"></a>How to provide `SNT_config.json`: the `SNT_CONFIGURATION` dataset

The SNT pipelines and notebooks read `SNT_config.json` from the **latest version** of the
OpenHEXA dataset `SNT_CONFIGURATION`, slug `snt-configuration`. If the dataset, its latest version
or the file is missing, the run stops with an error that links here:

```text
[ERROR] No usable SNT_config.json in the latest version of dataset SNT_CONFIGURATION (snt-configuration): <reason>. Provide a valid SNT_config.json file. See <link to this section>
```

Until the config editor writes the dataset, set it up by hand in the OpenHEXA workspace:

1. **Create the dataset once.** In **Datasets**, create a dataset named exactly
   `SNT_CONFIGURATION`. One per workspace.
2. **Check its slug.** OpenHEXA derives the slug from the name; it must be `snt-configuration`
   (it is in the dataset's URL). The pipelines look the dataset up by this slug, which is fixed and
   not in `SNT_DATASET_IDENTIFIERS`. If it is anything else, for example with a suffix because
   another dataset already holds `snt-configuration`, the pipelines will not find it: sort that out
   before going on.
3. **Upload the config as a new version.** Create a new version of the dataset and add the file,
   named exactly `SNT_config.json` (no `{CC}_` prefix: it is read before the country is known). A
   version name that says what changed helps, since every run logs it (for example
   `2026-11-16 added reporting dataset`).
4. **To change the config, upload a new version** with the whole file. Do not delete old
   versions: runs record the version they read, so an old result can be traced to its config.

Each run reads the version that is latest when it starts reading, and logs its name and id. A
pipeline that publishes `{CC}_parameters.json` will record it there as `SNT_CONFIG_VERSION` and
`SNT_CONFIG_VERSION_ID`. A notebook reads the latest version too, not the one its pipeline read, so
avoid uploading a version while a pipeline is running.

What makes the file valid: the shape of [`SNT_config.skeleton.json`](#snt_configskeletonjson) and
the per-field rules in [`config_analysis_notes.md`](config_analysis_notes.md). Pipelines check it
at startup with `snt_lib`'s `validate_config()` ([below](#conformance-fixtures--fixtures)).

---

## `SNT_config.skeleton.json`

### Why it exists

The per-country copies were never verified against what actually runs in each workspace, so none of
them can be trusted as "the current shape of the config". The skeleton fills that gap. It gives one
place to see the **latest version of the part of `SNT_config.json` that never changes between
countries**:

- the full set of keys and how they are nested;
- the values that are the same everywhere: every `SNT_DATASET_IDENTIFIERS` entry, and
  `"type": "dataElement"` on every `POPULATION_INDICATOR_DEFINITIONS` entry.

Country-specific values are left empty. The skeleton records *where* they go, not *what* goes
there.

### What it deliberately does not do

- **It does not explain how to fill in the country-specific values.** That belongs in a future
  `snt_config.schema.json`, on the same model as the schema for `SNT_metadata.json` in
  [`../snt_metadata_json/`](../snt_metadata_json/README.md). Not created yet:
  [BACKLOG CFG-3](../../docs/BACKLOG.md#cfg-3).
- **It is not a working config.** Copying it into a workspace without filling it in will make the
  pipelines fail or skip steps.

### How empty values are written

| Kind of value | Empty value | Example |
|---|---|---|
| Single value (string or number) | `null` | `COUNTRY_CODE`, `ANALYTICS_ORG_UNITS_LEVEL`, `REPORTING_DATASETS[].DATASET`, `REPORTING_INDICATORS.*` |
| List | `[]` | `REPORTING_RATE_PRODUCT_UID`, every `ids`, every `DHIS2_INDICATOR_DEFINITIONS.*` |

The config editor must write empty values the same way: an empty string is `null`, never `""`
([D-11](../../docs/MIGRATION_PLAN.md#2-decision-log-agreed)).

---

## Where configuration is heading: the config editor

Filling in `SNT_config.json` is moving to an OpenHEXA webapp, the config editor, in
[`webapps/config_editor/`](../../webapps/config_editor/CLAUDE.md) (docs and a design prototype; no
app code yet). It must emit exactly the shape and key order of `SNT_config.skeleton.json`, and keeps
no copy of its own. The skeleton is the pipelines' contract, so a change to it is a pipeline change:
update the skeleton first, then the editor's form
([editor spec §12.3](../../webapps/config_editor/docs/PRODUCT_SPEC.md#123-the-skeleton-is-a-derived-artefact)).
For how to fill in the country-specific values, read [`config_analysis_notes.md`](config_analysis_notes.md).

---

## Conformance fixtures — `fixtures/`

**What "valid" means is decided by `snt_lib.validate_config()`**, the gate every pipeline runs right
after loading the config ([`config_analysis_notes.md`](config_analysis_notes.md) §1.3). The config
editor reimplements it in JavaScript, so the two can drift silently (editor spec §12.2). The
fixtures are the shared yardstick (§12.2 option 2): each file is one case, and both validators must
return the verdict it states.

```json
{
  "description": "Why this case exists, and which rule it exercises",
  "expected": { "valid": false, "fails": ["SNT_CONFIG.COUNTRY_CODE"] },
  "config": { "SNT_CONFIG": { "…": "…" }, "SNT_DATASET_IDENTIFIERS": { "…": "…" }, "DHIS2_DATA_DEFINITIONS": { "…": "…" } }
}
```

- `fails` lists **exactly** the dotted config paths the validator must report: no fewer, no more.
  A valid case has `"fails": []`. The file name starts with `valid_` or `invalid_`.
- The valid cases have exactly the skeleton's keys, so a change to `SNT_config.skeleton.json` makes
  the test fail until the fixtures follow it.
- The cases cover the rules the pipelines and the editor share (editor spec §5.1 rules 1–7), plus
  the documented edge cases. The editor's own stricter rules (8–11) are not here: `validate_config()`
  accepts what they reject, for example a bare string where a list belongs. They get cases, with an
  editor-only verdict, when the editor's validator exists.
- UIDs and the country code (`XYZ`) are made up.

**Python side:** [`tests/test_config_conformance.py`](../../tests/test_config_conformance.py), run in
CI against `snt_lib` pinned in
[`tests/requirements-conformance.txt`](../../tests/requirements-conformance.txt) (`v1.0.2`, the
commit `@release-v1` pointed to on 2026-11-12). Locally the `validate_config()` checks skip unless
`snt_lib` is installed:

```bash
pip install -r tests/requirements-conformance.txt   # heavy: geopandas, polars, papermill
pytest tests/test_config_conformance.py
```

**When `snt_utils` changes `validate_config()`:** bump the pin in its own PR, run the test, and fix
the fixtures, the editor's rules and §1.3 of the notes together. **JS side:** not built; the
editor's validator runs this folder when it exists.

---

## Open questions

- The shape of `REPORTING_DATASETS[].METRICS`, whose value is always `"float"`:
  [BACKLOG CFG-2](../../docs/BACKLOG.md#cfg-2).
- A key-naming convention for `SNT_DATASET_IDENTIFIERS`: [BACKLOG CFG-1](../../docs/BACKLOG.md#cfg-1).
