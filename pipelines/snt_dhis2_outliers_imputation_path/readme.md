# SNT DHIS2 Outliers Imputation (PATH) Pipeline

The **SNT DHIS2 Outliers Imputation (PATH)** pipeline flags unusually high values in the formatted DHIS2 routine data against a trimmed mean + *k* × SD threshold computed over each facility × indicator series, then un-flags likely stock-out periods and replaces the remaining outliers with the trimmed mean. It builds a detection table plus imputed and removed versions of the routine data, publishes them to **`DHIS2_OUTLIERS_IMPUTATION`**, optionally loads the detection table into the workspace database, and runs the PATH reporting notebook.

## Parameters

* **`deviation_mean`** (int, Optional):
  * **Name:** Number of SD around the mean
  * **Description:** *k*, the number of standard deviations above the trimmed mean (`MEAN_80`) beyond which a value is flagged: a value above **`MEAN_80` + *k* × `SD_80`** is an outlier. Only high values are flagged. The same *k* sets the **`TEST`** threshold used by the stock-out exception.
  * **Default:** `10`.
* **`push_db`** (bool, Optional):
  * **Name:** Push outliers table to DB
  * **Description:** When true, loads **`[COUNTRY_CODE]_routine_outliers_detected.parquet`** into the workspace database table **`outliers_detected`**, replacing whatever the last outliers pipeline pushed there. No pipeline reads that table.
  * **Default:** `true`.

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_outliers_imputation_path/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_outliers_imputation_path/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`** and **`*_[COUNTRY_CODE].ipynb`** variants are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Create **`pipelines/snt_dhis2_outliers_imputation_path/`** and **`data/dhis2/outliers_imputation/`** if missing, then load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_outliers_imputation_path/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Detection and imputation:** Run **`snt_dhis2_outliers_imputation_path.ipynb`** with **`ROOT_PATH`** and **`DEVIATION_MEAN`**. The notebook:
   1. Loads **`[COUNTRY_CODE]_routine.parquet`** from **`DHIS2_DATASET_FORMATTED`** and stops with an `[ERROR]` if it cannot be loaded or a configured indicator column is missing.
   2. Reshapes it to long format at **facility (`OU_ID`) × month (`PERIOD`) × `INDICATOR`**, completing every facility with all periods and indicators present in the data (added combinations have a missing `VALUE`), and removes rows duplicated on that key (first row kept; logged as a warning).
   3. Computes, **per `ADM1_ID` × `ADM2_ID` × `OU_ID` × `INDICATOR`, over the whole series**, the ceiling-rounded mean (**`MEAN_80`**) and SD (**`SD_80`**) of the positive values, after dropping the lowest 10% (rounded down) and the highest 10% (rounded up) of them (zeros and missing values are excluded, as more likely non-reporting than true zeros).
   4. **Flags** values above **`MEAN_80` + `DEVIATION_MEAN` × `SD_80`**. Values that cannot be evaluated (missing value or `SD_80`) are not flagged, nor are low counts: **`TEST`** or **`PRES`** below 50, **`CONF`** below 10.
   5. **Stock-out exception:** un-flags a flagged **`PRES`** value when, in the same facility and month, **`TEST`** is below its own `MEAN_80` and the `PRES` value is below the `TEST` threshold (`TEST` `MEAN_80` + `DEVIATION_MEAN` × `SD_80`), since a sudden rise in presumed cases with low testing suggests an RDT stock-out.
   6. **Epidemic check:** marks facility-months where **`CONF`** is flagged and either **`TEST`** is flagged or `TEST` ≥ `CONF`. It does not change any flag (see Notes).
   7. **Imputation:** replaces each flagged value with its series' **`MEAN_80`**, then applies the **TEST/CONF reversal**: when the imputed `TEST` is below the imputed `CONF` of the same facility-month while the reported `TEST` was above the reported `CONF`, both are restored to their reported values and un-flagged, so they are not outliers in any output table (the number of reverted values is logged). **Removal:** sets the values still flagged after the reversal to missing.
   8. Writes the detected, imputed and removed tables with the standard outliers formatters from **`shared/r/snt_utils.r`** (see Outputs).
5. **Output check:** Stop with an error if any of the three Parquet files is missing or was not rewritten during this run. All outliers imputation pipelines write the same file names, so this prevents publishing a file left by an earlier run of another method.
6. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** and upload the three Parquet files plus the parameters file to **`DHIS2_OUTLIERS_IMPUTATION`** via **`add_files_to_dataset`**. A file that cannot be uploaded is skipped with a warning; the run continues.
7. **Database (only when `push_db`):** Replace the workspace database table **`outliers_detected`** with the contents of **`[COUNTRY_CODE]_routine_outliers_detected.parquet`**.
8. **Reporting:** Run **`snt_dhis2_outliers_imputation_path_report.ipynb`** (or its custom or country version, chosen as in step 3). The notebook is a placeholder: it prints a line and reads no data.

With **`run_report_only`**, steps 4–7 are skipped: nothing is computed, published or pushed to the database. Steps 1–3 and 8 still run.

## Inputs

* **`[COUNTRY_CODE]_routine.parquet`** on **`DHIS2_DATASET_FORMATTED`** (required): the notebook stops with an `[ERROR]` if it cannot be loaded or lacks a configured indicator column.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for:
  * **`SNT_CONFIG.COUNTRY_CODE`**
  * **`DHIS2_DATA_DEFINITIONS.DHIS2_INDICATOR_DEFINITIONS`**: its keys are the indicators screened. They must include **`TEST`** and **`CONF`** (used by the epidemic check and the reversal; the notebook fails without them); **`PRES`** is used by the stock-out exception.
  * **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`DHIS2_OUTLIERS_IMPUTATION`**)
* **`pipelines/snt_dhis2_outliers_imputation_path/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_detected.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_imputed.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_routine_outliers_removed.parquet`**
* **`data/dhis2/outliers_imputation/[COUNTRY_CODE]_parameters.json`**, with **`ROOT_PATH`** and **`DEVIATION_MEAN`** (the notebook inputs), **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. **`PUSH_DB`**, **`RUN_REPORT_ONLY`** and **`USE_CUSTOM_NOTEBOOKS`** are not recorded. Not written in report-only runs.
* **Executed notebooks** under **`pipelines/snt_dhis2_outliers_imputation_path/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_outliers_imputation_path/reporting/outputs/`**, named the same way, with an **`.html`** copy unless the report stops on a `[WARNING]`
* **Synced scripts** under **`pipelines/snt_dhis2_outliers_imputation_path/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

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
> - **Last run wins:** all five outliers imputation pipelines publish the same three file names to **`DHIS2_OUTLIERS_IMPUTATION`** ([ADR 0002](../../docs/decisions/0002-alternative-methods-last-run-wins.md)). Downstream uses whichever ran last; check **`OUTLIER_METHOD`** or **`[COUNTRY_CODE]_parameters.json`** to see which method (and which **`DEVIATION_MEAN`**) produced the files.
> - **Detection table** (long format, one row per facility × month × indicator, including the combinations added when completing the series; rows sorted by `ADM1_ID`, `ADM2_ID`, `OU_ID`, `INDICATOR`, `PERIOD`), columns in order:
>   - **`PERIOD`** (integer, `YYYYMM`), **`YEAR`**, **`MONTH`** (integer), **`DATE`** (date, first day of the month)
>   - **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`OU_ID`**, **`OU_NAME`** (character; names unchanged from the routine data), **`INDICATOR`** (character)
>   - **`VALUE`** (double): original reported value.
>   - **`OUTLIER_DETECTED`** (logical, never missing): `TRUE` if flagged after the stock-out exception and the TEST/CONF reversal, i.e. exactly the values replaced in the imputed table and set to missing in the removed table. Missing values are never flagged.
>   - **`OUTLIER_METHOD`** (character): `PATH`. The value of *k* is recorded in **`[COUNTRY_CODE]_parameters.json`**, not in the table.
> - **Imputed and removed tables** (wide routine format, one row per facility × month of the routine data, kept even when all values are missing; rows sorted by `ADM1_ID`, `ADM2_ID`, `OU_ID`, `PERIOD`), columns in order: **`PERIOD`**, **`YEAR`**, **`MONTH`** (integer), **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`OU_ID`**, **`OU_NAME`** (character), then one double column per configured indicator (all missing if the indicator has no data).
>   - **Imputed:** flagged values are replaced by the series' **`MEAN_80`** (a whole number, as it is ceiling-rounded). Every other value is unchanged.
>   - **Removed:** flagged values are set to missing; every other value, and every row, is kept.
> - **TEST/CONF reversal:** a TEST or CONF value flagged by the rule but restored by the reversal is not an outlier in any of the three tables. Its reported value is kept; the number of such values appears only in the run log.
> - **Epidemic check has no effect:** the rule is evaluated, but it only sets to `TRUE` flags that are already `TRUE`, so no value is un-flagged (or flagged) because of a possible epidemic.
> - **Grain:** facility × month. `MEAN_80` and `SD_80` are computed over each facility × indicator's full history, not per year.
> - **Small series:** a series with two or fewer positive values keeps fewer than two after trimming, so it has no `SD_80` and none of its values is flagged.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the pipeline's own. The report notebook is resolved up front too, so its entry is recorded although it runs after publishing.
> - **Guarded execution:** the notebook stops with an `[ERROR]` if the routine file cannot be loaded or a configured indicator column is missing, and the run stops before publishing if any of the three Parquet files was not rewritten during the run. A failed upload does **not** stop the run: the file is skipped with a warning, and the database push and the report still run. A failed database push stops the run after the files are published, before the report.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_outliers_imputation_path/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
