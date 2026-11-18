# SNT DHIS2 Reporting Rate (Dataset) Pipeline

The **SNT DHIS2 Reporting Rate (Dataset)** pipeline computes **monthly** and **yearly** DHIS2 reporting rates at **ADM2** resolution as **`ACTUAL_REPORTS / EXPECTED_REPORTS`**, from the reporting extract formatted by the DHIS2 formatting pipeline. It publishes **`[COUNTRY_CODE]_reporting_rate_dataset`** (monthly) and **`[COUNTRY_CODE]_reporting_rate_dataset_yearly`** (yearly) to **`DHIS2_REPORTING_RATE`** and runs the reporting notebook.

## Parameters

None. `pipeline.py` defines no domain parameters. The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_reporting_rate_dataset/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_reporting_rate_dataset/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`** and **`*_[COUNTRY_CODE].ipynb`** variants are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`**, read **`COUNTRY_CODE`** and the dataset identifiers.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_reporting_rate_dataset/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Input check:** Verify that **`[COUNTRY_CODE]_reporting.parquet`** exists on **`DHIS2_DATASET_FORMATTED`**. If it is missing, log a warning and **stop without failing**: nothing is computed, published or reported.
5. **Product UID check:** Fail the run with an error if **`SNT_CONFIG.REPORTING_RATE_PRODUCT_UID`** is missing, empty or holds only blank values.
6. **Parameters:** Save **`[COUNTRY_CODE]_parameters.json`** in **`data/dhis2/reporting_rate/`**, before the notebook runs (see Outputs for its keys).
7. **Computation notebook:** Run **`snt_dhis2_reporting_rate_dataset.ipynb`**:
   1. **Load** **`[COUNTRY_CODE]_reporting.parquet`** from **`DHIS2_DATASET_FORMATTED`** and detect its grain: **facility level** when an **`OU_ID`** column is present (dataset-based extract), **already ADM2** when it is absent (indicator-based extract).
   2. **Filter by product:** Keep only the rows whose **`PRODUCT_UID`** is listed in **`REPORTING_RATE_PRODUCT_UID`**, when all the listed UIDs are present in the data; otherwise log a warning and keep all products.
   3. **Pivot** **`PRODUCT_METRIC`** into **`ACTUAL_REPORTS`** and **`EXPECTED_REPORTS`** columns.
   4. **Deduplicate (facility level only):** When a facility appears in several datasets for the same period, keep the row with the highest **`ACTUAL_REPORTS`**, provided all duplicated values are 0 or 1; otherwise log a warning and keep the duplicates. Skipped for ADM2-level data.
   5. **NER only, facility level only:** Convert **`ACTUAL_REPORTS`** and **`EXPECTED_REPORTS`** values above 1 to 1 (pre-aggregated HOP hospital datasets). Skipped, with a warning, for ADM2-level data.
   6. **Aggregate:** Sum **`ACTUAL_REPORTS`** and **`EXPECTED_REPORTS`** **by `ADM2_ID` and `PERIOD`**, then compute **`REPORTING_RATE`**.
   7. **Yearly:** Sum the ADM2 × month **`ACTUAL_REPORTS`** and **`EXPECTED_REPORTS`** **by `ADM2_ID` and `YEAR`**, then compute **`REPORTING_RATE`**.
   8. **Export** **`[COUNTRY_CODE]_reporting_rate_dataset.parquet`** / **`.csv`** (monthly) and **`[COUNTRY_CODE]_reporting_rate_dataset_yearly.parquet`** / **`.csv`** (yearly) to **`data/dhis2/reporting_rate/`**.
8. **Output check:** Fail the run if any of the monthly or yearly parquets or CSVs is missing or was not written during this run, so files left over from a previous run are never published.
9. **Publish:** Upload the monthly and yearly parquets and CSVs, and **`[COUNTRY_CODE]_parameters.json`**, to **`DHIS2_REPORTING_RATE`** via **`add_files_to_dataset`**.
10. **Reporting:** Run **`snt_dhis2_reporting_rate_dataset_report.ipynb`** (or its custom or country version, chosen as in step 3), which reads the published monthly and yearly tables back from **`DHIS2_REPORTING_RATE`**. The yearly map shows the published yearly **`REPORTING_RATE`**.

With **`run_report_only`**, steps 4–9 are skipped: nothing is checked, computed or published, and no parameters file is saved. Steps 1–3 and 10 still run.

## Inputs

* **`[COUNTRY_CODE]_reporting.parquet`** on **`DHIS2_DATASET_FORMATTED`** — required; produced by the DHIS2 formatting pipeline from the extract's reporting data; when missing, the run ends early (step 4). Its grain depends on how reporting rates are configured for extraction (**`DHIS2_DATA_DEFINITIONS.DHIS2_REPORTING_RATES`**):
  * **`REPORTING_DATASETS`**: one row per facility (**`OU_ID`**) × period × dataset metric.
  * **`REPORTING_INDICATORS`**: one row per ADM2 (**`ADM2_ID`**) × period × indicator, already aggregated by DHIS2; no **`OU_ID`** / **`OU_NAME`** columns.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`SNT_CONFIG.COUNTRY_CODE`**, **`SNT_CONFIG.REPORTING_RATE_PRODUCT_UID`** (required) and the dataset identifiers **`DHIS2_DATASET_FORMATTED`** and **`DHIS2_REPORTING_RATE`**.
* Reporting notebook only: **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** (maps), and **`configuration/SNT_metadata.json`** on the workspace filesystem for the **`REPORTING_RATE.SCALE`** breaks (colour categories; default breaks with a warning when the key is absent, the report fails when the file is missing).
* **`pipelines/snt_dhis2_reporting_rate_dataset/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/reporting_rate/[COUNTRY_CODE]_reporting_rate_dataset.parquet`** and **`.csv`** (monthly)
* **`data/dhis2/reporting_rate/[COUNTRY_CODE]_reporting_rate_dataset_yearly.parquet`** and **`.csv`** (yearly)
* **`data/dhis2/reporting_rate/[COUNTRY_CODE]_parameters.json`**, with the notebook parameter **`ROOT_PATH`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. The **`run_report_only`** and **`use_custom_notebooks`** flags are not recorded.
* **Executed notebooks** under **`pipelines/snt_dhis2_reporting_rate_dataset/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_reporting_rate_dataset/reporting/outputs/`**, named the same way
* **Report figures** in **`pipelines/snt_dhis2_reporting_rate_dataset/reporting/outputs/figures/`**: line-point plot, heatmap, monthly map and yearly map, named **`[COUNTRY_CODE]_reporting_rate_dataset_adm2_{linepoint|heatmap|map|map_year}_[PRODUCT_UIDs].png`**. Written, not published.
* **Synced scripts** under **`pipelines/snt_dhis2_reporting_rate_dataset/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHIS2_REPORTING_RATE`**

* **`[COUNTRY_CODE]_reporting_rate_dataset.parquet`** and **`.csv`** (monthly)
* **`[COUNTRY_CODE]_reporting_rate_dataset_yearly.parquet`** and **`.csv`** (yearly)
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:**
>   - **`[COUNTRY_CODE]_reporting_rate_dataset`**: one row per **`ADM2_ID`** × **`YEAR`** × **`MONTH`**, for the ADM2-months present in the reporting extract. Columns: **`YEAR`**, **`MONTH`**, **`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`**, **`REPORTING_RATE`** (no **`PERIOD`**).
>   - **`[COUNTRY_CODE]_reporting_rate_dataset_yearly`**: one row per **`ADM2_ID`** × **`YEAR`**, for the ADM2-years present in the reporting extract. Columns: **`YEAR`**, **`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`**, **`REPORTING_RATE`**.
> - **`REPORTING_RATE`** (monthly): ADM2-month **`sum(ACTUAL_REPORTS) / sum(EXPECTED_REPORTS)`**, a proportion — a ratio of sums, not an average of facility rates.
> - **`REPORTING_RATE`** (yearly): the same ratio over the ADM2's months in the year, **`sum(ACTUAL_REPORTS) / sum(EXPECTED_REPORTS)`**, so months with more expected reports count more. The first and last years can be partial; their rate covers only the months in the extract, and the table does not flag them.
> - For both tables:
>   - There is no guard on the denominator: a row with **`EXPECTED_REPORTS` = 0** gets **`NaN`** (or **`Inf`** if actual reports are positive).
>   - Values above 1 are kept; the notebook logs a warning when any monthly value falls outside [0, 1] (the yearly values are not checked).
> - **`REPORTING_RATE_PRODUCT_UID`** must list UIDs from the extraction mode actually used: dataset UIDs for **`REPORTING_DATASETS`** (it may be a subset of the extracted datasets), or both indicator UIDs (actual and expected reports) for **`REPORTING_INDICATORS`**. If a listed UID is absent from the data, no filtering is applied and all products are kept.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the pipeline's own. Entries are resolved for both notebooks up front.
> - **Guarded execution:** a missing **`[COUNTRY_CODE]_reporting.parquet`** ends the run early as a success, with only a warning in the log; the sync and the notebook choice (steps 1–3) have already run, the report has not. Facility-level steps (deduplication, NER HOP conversion) are skipped when the data has no **`OU_ID`**. The parameters file is written before the notebook runs, so after a failed run the workspace copy describes that run while **`DHIS2_REPORTING_RATE`** still holds the previous one.
> - **Last run wins:** **`snt_dhis2_reporting_rate_dataelement`** also publishes to **`DHIS2_REPORTING_RATE`**, and the dataset holds only the files of the last successful run, so it contains either this pipeline's tables or the data-element ones, never both. Check the **`[COUNTRY_CODE]_parameters.json`** beside them to see which pipeline produced them. A report-only run fails when the data-element pipeline was the last to publish, since the report cannot find this pipeline's tables.
> - **Downstream use:** **`snt_dhis2_incidence`** left-joins this table onto its own routine ADM2-months by **`ADM2_ID`**, **`YEAR`**, **`MONTH`**, so ADM2-months missing here get a missing reporting rate there.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_reporting_rate_dataset/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
