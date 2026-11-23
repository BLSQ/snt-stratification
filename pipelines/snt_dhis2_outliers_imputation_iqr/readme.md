# SNT DHIS2 Outliers Imputation (IQR) Pipeline

The **SNT DHIS2 Outliers Imputation (IQR)** pipeline flags outliers in the formatted DHIS2 routine data with a Tukey-style interquartile range (IQR) fence computed over each facility × indicator series. It builds a detection table plus imputed and removed versions of the routine data, publishes them to **`DHIS2_OUTLIERS_IMPUTATION`**, optionally loads the detection table into the workspace database, and runs the IQR reporting notebook.

## Parameters

* **`deviation_iqr`** (float, Optional):
  * **Name:** IQR multiplier
  * **Description:** *m*, the multiplier applied to the interquartile range **Q3 − Q1**. A value outside **[Q1 − *m* × (Q3 − Q1), Q3 + *m* × (Q3 − Q1)]** is flagged as an outlier.
  * **Default:** `1.5`.
* **`push_db`** (bool, Optional):
  * **Name:** Push outliers table to DB
  * **Description:** When true, loads **`[COUNTRY_CODE]_routine_outliers_detected.parquet`** into the workspace database table **`outliers_detected`**, replacing whatever the last outliers pipeline pushed there. No pipeline reads that table.
  * **Default:** `true`.

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_outliers_imputation_iqr/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_outliers_imputation_iqr/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Create **`pipelines/snt_dhis2_outliers_imputation_iqr/`** and **`data/dhis2/outliers_imputation/`** if missing, then load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_outliers_imputation_iqr/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Detection and imputation:** Run **`snt_dhis2_outliers_imputation_iqr.ipynb`** with **`ROOT_PATH`** and **`DEVIATION_IQR`**. The notebook:
   1. Loads **`[COUNTRY_CODE]_routine.parquet`** from **`DHIS2_DATASET_FORMATTED`** and stops with an `[ERROR]` if it cannot be loaded or a configured indicator column is missing.
   2. Reshapes it to long format at **facility (`OU_ID`) × month (`PERIOD`) × `INDICATOR`**, and removes rows duplicated on that key (first row kept; logged).
   3. Computes the ceiling-rounded **Q1** (25th percentile) and **Q3** (75th percentile) of `VALUE` **per `ADM1_ID` × `ADM2_ID` × `OU_ID` × `INDICATOR`, over the whole series** (all months, missing values ignored, zeros included).
   4. Flags values outside **[Q1 − `DEVIATION_IQR` × (Q3 − Q1), Q3 + `DEVIATION_IQR` × (Q3 − Q1)]**; values that cannot be evaluated (missing value or quartiles) are not flagged.
   5. **Imputation:** replaces each flagged value with a centred 3-month moving mean (see Notes). **Removal:** sets each flagged value to missing.
   6. Writes the detected, imputed and removed tables with the standard outliers formatters from **`shared/r/snt_utils.r`** (see Outputs).
5. **Output check:** Stop with an error if any of the three Parquet files is missing or was not rewritten during this run. All outliers imputation pipelines write the same file names, so this prevents publishing a file left by an earlier run of another method.
6. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** and upload the three Parquet files plus the parameters file to **`DHIS2_OUTLIERS_IMPUTATION`** via **`add_files_to_dataset`**. A file that cannot be uploaded is skipped with a warning; the run continues.
7. **Database (only when `push_db`):** Replace the workspace database table **`outliers_detected`** with the contents of **`[COUNTRY_CODE]_routine_outliers_detected.parquet`**.
8. **Reporting:** Run **`snt_dhis2_outliers_imputation_iqr_report.ipynb`** (or its custom or country version, chosen as in step 3) to refresh the report outputs.

With **`run_report_only`**, steps 4–7 are skipped: nothing is computed, published or pushed to the database. Steps 1–3 and 8 still run, and the report reads whatever is in the latest version of **`DHIS2_OUTLIERS_IMPUTATION`**, which may come from another outliers pipeline.

## Inputs

* **`[COUNTRY_CODE]_routine.parquet`** on **`DHIS2_DATASET_FORMATTED`** (required): the notebook stops with an `[ERROR]` if it cannot be loaded or lacks a configured indicator column.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for:
  * **`SNT_CONFIG.COUNTRY_CODE`**, and **`SNT_CONFIG.COUNTRY_NAME`** in the report
  * **`DHIS2_DATA_DEFINITIONS.DHIS2_INDICATOR_DEFINITIONS`**: its keys are the indicators screened
  * **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`DHIS2_OUTLIERS_IMPUTATION`**)
* The reporting notebook reads **`[COUNTRY_CODE]_routine_outliers_detected.parquet`** and **`[COUNTRY_CODE]_routine_outliers_imputed.parquet`** from the latest version of **`DHIS2_OUTLIERS_IMPUTATION`**, and **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`** for its maps.
* **`pipelines/snt_dhis2_outliers_imputation_iqr/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_detected.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_imputed.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_removed.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_parameters.json`**, with **`ROOT_PATH`** and **`DEVIATION_IQR`** (the notebook inputs), **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. **`PUSH_DB`**, **`RUN_REPORT_ONLY`** and **`USE_CUSTOM_NOTEBOOKS`** are not recorded. Not written in report-only runs.
* **Executed notebooks** under **`pipelines/snt_dhis2_outliers_imputation_iqr/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_outliers_imputation_iqr/reporting/outputs/`**, named the same way, with an **`.html`** copy unless the report stops on a `[WARNING]`; figures in **`figures/`**, emptied at the start of each report run
* **Synced scripts** under **`pipelines/snt_dhis2_outliers_imputation_iqr/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

No `.csv` twins are written.

**Published to `DHIS2_OUTLIERS_IMPUTATION`** (not in report-only runs)

* **`[COUNTRY_CODE]_routine_outliers_detected.parquet`**
* **`[COUNTRY_CODE]_routine_outliers_imputed.parquet`**
* **`[COUNTRY_CODE]_routine_outliers_removed.parquet`**
* **`[COUNTRY_CODE]_parameters.json`**

**Workspace database** (only when `push_db`, not in report-only runs)

* Table **`outliers_detected`**, replaced with the detection table.

> **Notes for the Data Analyst:**
>
> - **Last run wins:** all five outliers imputation pipelines publish the same three file names to **`DHIS2_OUTLIERS_IMPUTATION`** ([ADR 0002](../../docs/decisions/0002-alternative-methods-last-run-wins.md)). Downstream uses whichever ran last; check **`OUTLIER_METHOD`** or **`[COUNTRY_CODE]_parameters.json`** to see which method (and which **`DEVIATION_IQR`**) produced the files.
> - **Detection table** (long format, one row per facility × month × indicator of the routine data; rows sorted by `ADM1_ID`, `ADM2_ID`, `OU_ID`, `INDICATOR`, `PERIOD`), columns in order:
>   - **`PERIOD`** (integer, `YYYYMM`), **`YEAR`**, **`MONTH`** (integer), **`DATE`** (date, first day of the month)
>   - **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`OU_ID`**, **`OU_NAME`** (character; names unchanged from the routine data), **`INDICATOR`** (character)
>   - **`VALUE`** (double): original reported value.
>   - **`OUTLIER_DETECTED`** (logical, never missing): `TRUE` if outside the IQR fence. Missing values are never flagged.
>   - **`OUTLIER_METHOD`** (character): `IQR`. The value of *m* is recorded in **`[COUNTRY_CODE]_parameters.json`**, not in the table.
> - **Imputed and removed tables** (wide routine format, one row per facility × month of the routine data, kept even when all values are missing; rows sorted by `ADM1_ID`, `ADM2_ID`, `OU_ID`, `PERIOD`), columns in order: **`PERIOD`**, **`YEAR`**, **`MONTH`** (integer), **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`OU_ID`**, **`OU_NAME`** (character), then one double column per configured indicator (all missing if the indicator has no data).
>   - **Imputed:** only flagged values are replaced, by the ceiling of the mean of the non-flagged, non-missing values of the previous and next month in the same `OU_ID` × `INDICATOR` series, ordered by `PERIOD`. The value becomes missing when both neighbours are flagged or missing, and at the first and last month of a series. Values that were missing in the routine data stay missing.
>   - **Removed:** flagged values are set to missing; every other value, and every row, is kept.
> - **Grain:** facility × month. The quartiles are computed over each facility × indicator's full history, not per year.
> - **Quartiles are ceiling-rounded** (rounded up to whole numbers) before the fence is built, so the fence can differ from a textbook Tukey fence on the raw quartiles. The difference is at most about 1 + *m* and only matters for low-count series.
> - **IQR of zero:** when Q1 and Q3 are equal (typically when more than half of a series' values are identical), the fence collapses to that single value and **every value different from it is flagged**. Series with a very stable reported value are therefore heavily flagged by this method.
> - **Zeros are values:** the notebook does not set zeros to missing, so zeros count in the quartiles and a zero below the lower fence is flagged.
> - **Gaps in `PERIOD`:** the imputation window counts rows, not calendar months, so a series with missing months treats the months on either side of a gap as neighbours.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the generic one. The report notebook is resolved up front too, so its entry is recorded although it runs after publishing.
> - **Guarded execution:** the notebook stops with an `[ERROR]` if the routine file cannot be loaded or a configured indicator column is missing, and the run stops before publishing if any of the three Parquet files was not rewritten during the run. A failed upload does **not** stop the run: the file is skipped with a warning, and the database push and the report still run (the report then reads whatever the latest dataset version holds). A failed database push stops the run after the files are published, before the report.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_outliers_imputation_iqr/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
