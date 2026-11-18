# SNT DHIS2 Extract Pipeline

The **SNT DHIS2 Extract** pipeline downloads raw routine analytics, population, organisation-unit hierarchy (pyramid), ADM2 geometries (shapes) and reporting-rate data from a DHIS2 instance for a range of months. All processing is in **`pipeline.py`**. It publishes the five merged raw Parquet files and its parameters file to **`DHIS2_DATASET_EXTRACTS`** and runs the extract reporting notebook.

## Parameters

The standard flags **`overwrite`**, **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `overwrite` keeps is described in step 7 and the notes, and what `use_custom_notebooks` changes in steps 2 and 4 ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)). **`overwrite`** defaults to `True` here.

* **`dhis2_connection`** (DHIS2Connection, Required):
  * **Name:** DHIS2 connection
  * **Description:** Workspace connection used for every DHIS2 API call.
  * **Default:** none.
* **`start`** (Integer, Required):
  * **Name:** Period (start)
  * **Description:** First month, **`YYYYMM`**, inclusive. Population is extracted for the years from **`start`**'s year to **`end`**'s year.
  * **Default:** none.
* **`end`** (Integer, Required):
  * **Name:** Period (end)
  * **Description:** Last month, **`YYYYMM`**, inclusive. Must not be before **`start`**.
  * **Default:** none.

## Functionality Overview

1. **Validate the period (every run, report-only included):** **`start`** and **`end`** must be six digits with a month from 01 to 12, and **`start`** ≤ **`end`**; otherwise the run stops with an error.
2. **Sync the R half (every run, report-only included):** Copy each **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version (it has no `code/` notebook) to **`pipelines/snt_dhis2_extract/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_extract/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, **`*_[COUNTRY_CODE].ipynb`** variants and **`NER_transformations/`** are never touched. If the sync fails, the run stops with an `[ERROR]`.
3. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
4. **Choose the report notebook (before it runs):** Run **`custom/snt_dhis2_extract_report.ipynb`** if **`use_custom_notebooks`** is on and the file exists, else **`snt_dhis2_extract_report_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. A notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no **`snt_dhis2_extract_report.ipynb`** in **`pipelines/snt_dhis2_extract/custom/`**, the run stops with an `[ERROR]` before anything is downloaded or the report runs.
5. **Organisation units:** Connect to DHIS2 and download every organisation unit with its parent levels; a failure stops the run. Two country branches are hardcoded:
   * **BFA:** keep only the rows whose **`level_4_name`** starts with `DS`. Every output below is built from this filtered pyramid.
   * **NER:** write the organisation-unit groups to **`data/dhis2/extracts_raw/organisation_unit_groups/`** (**`NER_organisation_unit_groups_raw.parquet`**, and the ownership groups as **`NER_organisation_unit_groups.parquet`** and **`.csv`**), then rewrite the pyramid with **`pipelines/snt_dhis2_extract/NER_transformations/NER_pyramid_format.ipynb`** through papermill. That notebook is not in this repository: the sync does not deliver it, **`use_custom_notebooks`** does not apply to it and **`NOTEBOOK_OVERRIDES`** does not record it. When it is missing or fails, a warning is logged and the pyramid is used untransformed.
6. **Save parameters:** Write **`[COUNTRY_CODE]_parameters.json`** to **`data/dhis2/extracts_raw/`**, before any download below.
7. **Downloads (OpenHEXA tasks):** population, shapes and pyramid start together; analytics starts when population has finished, and reporting rates when analytics has finished, whatever the earlier task returned. All files are under **`data/dhis2/extracts_raw/`**; merged files have their column names uppercased. With **`overwrite`** on, the per-period files of population, analytics and reporting rates are deleted first; off, a per-period file already on disk is kept and its period is not downloaded again.
   1. **Population (ADM2 × year):** For each entry of **`POPULATION_INDICATOR_DEFINITIONS`** (`ids`, `type` `dataElement` or `indicator`) and each year, download the values for the organisation units at the **`DHIS2_ADMINISTRATION_2`** level into **`population_data/indicators_raw/[COUNTRY_CODE]_raw_<name>_<YYYY>.parquet`**, then merge every such file in the folder into **`population_data/[COUNTRY_CODE]_dhis2_raw_population.parquet`**. No entry: a warning, nothing downloaded. An entry with no `ids`: a warning, skipped. An invalid `type`: the run stops. A failed or empty download for a year: a warning, skipped.
   2. **Shapes (ADM2):** The organisation units at the **`DHIS2_ADMINISTRATION_2`** level, with their geometry, parent level ids and names, and the DHIS2 name of each level (**`ORG_LEVEL_<n>_NAME`**), to **`shapes_data/[COUNTRY_CODE]_dhis2_raw_shapes.parquet`**.
   3. **Pyramid (facility level):** The organisation units at the **`ANALYTICS_ORG_UNITS_LEVEL`**, with their parent level ids and names, geometry, opening and closing dates, to **`pyramid_data/[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`**.
   4. **Analytics (facility × month):** For each month, download the data elements of **`DHIS2_INDICATOR_DEFINITIONS`** (the uid before any `.`, so every category option combo) for the organisation units at the **`ANALYTICS_ORG_UNITS_LEVEL`**, add data-element and category-option-combo names and the parent levels, and write **`routine_data/[COUNTRY_CODE]_raw_analytics_<YYYYMM>.parquet`**. Merge every such file in the folder into **`routine_data/[COUNTRY_CODE]_dhis2_raw_analytics.parquet`**. A failed or empty month: a warning, skipped. An **`ANALYTICS_ORG_UNITS_LEVEL`** outside the pyramid's levels, or no data element: the run stops.
   5. **Reporting rates (per month):** Delete **`reporting_data/[COUNTRY_CODE]_dhis2_raw_reporting.parquet`**, then use **`REPORTING_DATASETS`** if any entry has a `DATASET`, else **`REPORTING_INDICATORS`** if any has a value, else download nothing.
      * **Datasets:** entries whose dataset is unknown to DHIS2 or has no `METRICS` are dropped with a warning. For each month, download `<dataset>.<metric>` for the organisation units at the **`ANALYTICS_ORG_UNITS_LEVEL`** into **`reporting_data/datasets/[COUNTRY_CODE]_raw_reporting_ds_<YYYYMM>.parquet`**.
      * **Indicators:** for each month, download the indicators for the organisation units at the **`DHIS2_ADMINISTRATION_2`** level into **`reporting_data/indicators/[COUNTRY_CODE]_raw_reporting_ind_<YYYYMM>.parquet`**.
      * Merge the per-month files of the mode used into **`reporting_data/[COUNTRY_CODE]_dhis2_raw_reporting.parquet`**. A month, or a dataset within a month, that fails is skipped with a warning. Any other error is logged as a warning and ends this step; the run continues.
8. **Publish:** When the five downloads have finished, upload **`[COUNTRY_CODE]_dhis2_raw_analytics.parquet`**, **`_population.parquet`**, **`_shapes.parquet`**, **`_pyramid.parquet`**, **`_reporting.parquet`** and **`[COUNTRY_CODE]_parameters.json`** to **`DHIS2_DATASET_EXTRACTS`** via **`add_files_to_dataset`**, as a version named **`dhis2_level<ANALYTICS_ORG_UNITS_LEVEL>_[COUNTRY_CODE]_<YYYYMMDD_HHMM>`**. A file missing on disk is skipped with a warning. A publication error is logged as an error and the run continues.
9. **Reporting:** When at least one file was published, run **`snt_dhis2_extract_report.ipynb`** (or its custom or country version, chosen as in step 4); otherwise log that reporting is skipped.

With **`run_report_only`**, steps 5–8 are skipped: nothing is downloaded, written to `data/` or published, and no parameters file is written. Steps 1–4 and 9 still run (step 9 always runs the report).

## Inputs

* **DHIS2 instance** reached through **`dhis2_connection`** (required for a full run): organisation units, organisation-unit levels, datasets metadata, analytics, and for NER organisation-unit groups.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required):
  * **`SNT_CONFIG`**: **`COUNTRY_CODE`**, **`ANALYTICS_ORG_UNITS_LEVEL`** (facility level: analytics, pyramid, dataset reporting rates), **`DHIS2_ADMINISTRATION_2`** (`level_<n>_name`; ADM2 level: population, shapes, indicator reporting rates).
  * **`DHIS2_DATA_DEFINITIONS`**: **`DHIS2_INDICATOR_DEFINITIONS`**, **`POPULATION_INDICATOR_DEFINITIONS`**, **`DHIS2_REPORTING_RATES`** (**`REPORTING_DATASETS`**, **`REPORTING_INDICATORS`**).
  * **`SNT_DATASET_IDENTIFIERS`**: **`DHIS2_DATASET_EXTRACTS`**.
* **Per-period files** already under **`data/dhis2/extracts_raw/`** (optional): reused, and merged, when **`overwrite`** is off.
* **`pipelines/snt_dhis2_extract/NER_transformations/NER_pyramid_format.ipynb`** in the workspace (NER only, optional; see step 5).
* **Report inputs** (report-only included): **`[COUNTRY_CODE]_dhis2_raw_analytics.parquet`** and **`[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`** from the latest version of **`DHIS2_DATASET_EXTRACTS`**.
* **`pipelines/snt_dhis2_extract/custom/snt_dhis2_extract_report.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`snt_dhis2_extract_report_[COUNTRY_CODE].ipynb`** beside the generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem** (under **`data/dhis2/extracts_raw/`** unless stated)

* **`routine_data/[COUNTRY_CODE]_dhis2_raw_analytics.parquet`**, and the per-month **`routine_data/[COUNTRY_CODE]_raw_analytics_<YYYYMM>.parquet`** (not published)
* **`population_data/[COUNTRY_CODE]_dhis2_raw_population.parquet`**, and the per-year **`population_data/indicators_raw/[COUNTRY_CODE]_raw_<name>_<YYYY>.parquet`** (not published)
* **`shapes_data/[COUNTRY_CODE]_dhis2_raw_shapes.parquet`**
* **`pyramid_data/[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`**
* **`reporting_data/[COUNTRY_CODE]_dhis2_raw_reporting.parquet`**, and the per-month **`reporting_data/datasets/[COUNTRY_CODE]_raw_reporting_ds_<YYYYMM>.parquet`** or **`reporting_data/indicators/[COUNTRY_CODE]_raw_reporting_ind_<YYYYMM>.parquet`** (not published)
* **`[COUNTRY_CODE]_parameters.json`**, with **`START`**, **`END`**, **`OVERWRITE`**, **`USE_CUSTOM_NOTEBOOKS`**, **`RUN_REPORT_ONLY`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* NER only: **`organisation_unit_groups/NER_organisation_unit_groups_raw.parquet`**, **`NER_organisation_unit_groups.parquet`** and **`.csv`**, and under **`pipelines/snt_dhis2_extract/NER_transformations/`** the notebook's **`input/input_pyramid.parquet`**, **`output/output_pyramid.parquet`** and executed copy in **`papermill_outputs/`** (not published)
* **Report outputs** under **`pipelines/snt_dhis2_extract/reporting/outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`** (plus its **`.html`**), or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook; plots under **`figures/`**
* **Synced scripts** under **`pipelines/snt_dhis2_extract/`** (`reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 2)

**Published to `DHIS2_DATASET_EXTRACTS`**

* **`[COUNTRY_CODE]_dhis2_raw_analytics.parquet`**
* **`[COUNTRY_CODE]_dhis2_raw_population.parquet`**
* **`[COUNTRY_CODE]_dhis2_raw_shapes.parquet`**
* **`[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`**
* **`[COUNTRY_CODE]_dhis2_raw_reporting.parquet`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Raw, not formatted:** these files keep DHIS2's own columns (uppercased in the merged files) and organisation-unit levels (**`LEVEL_<n>_ID`**, **`LEVEL_<n>_NAME`**). **`snt_dhis2_formatting`** turns them into the SNT schema.
> - **Grain:** analytics: facility (**`ANALYTICS_ORG_UNITS_LEVEL`**) × month × data element × category option combo. Population: ADM2 × year × data element or indicator (the configured entry name is only in the per-year file names, not in the merged file). Reporting: facility × month × dataset metric (datasets mode) or ADM2 × month × indicator (indicators mode).
> - **Which months a merged file holds:** every per-period file in its folder. With **`overwrite`** off, files from earlier runs stay, so the merged file can hold periods outside **`start`**–**`end`**.
> - **Guarded execution:**
>   - A month or year that fails or returns no data is skipped with a warning, and the run still succeeds; check the log before assuming the period is complete.
>   - An exception inside the population, shapes, pyramid or analytics task (an invalid level or `type`, a merge failure) stops the run; the `try`/`except` around those calls in the pipeline function does not catch it. The reporting-rates task catches its own errors and only logs a warning.
>   - Publication takes whatever file is on disk. When a step writes no merged file (for example no population definitions, or no month downloaded), a population, analytics, shapes or pyramid file left by an earlier run is published again. The reporting file is deleted at the start of its step, so it is only published if this run wrote it (or if no reporting rate is configured, in which case an old file is not deleted).
> - **Run time:** the pipeline timeout is 12 hours.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means the report notebook was the pipeline's own. The NER pyramid notebook is never recorded.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_extract/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
