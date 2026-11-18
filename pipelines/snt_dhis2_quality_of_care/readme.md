# SNT Quality of Care Pipeline

The **SNT Quality of Care** pipeline computes **ADM2 × YEAR** quality-of-care indicators from DHIS2 routine data already processed by an outliers pipeline (outliers imputed or removed). It derives testing, treatment, case-fatality and malaria-share rates plus two absolute counts, publishes the ADM2 × YEAR table to **`DHIS2_QUALITY_OF_CARE`**, and runs the quality-of-care reporting notebook.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

* **`data_action`** (String, Required):
  * **Name:** Data action
  * **Description:** Selects which outliers-processed routine file to read from **`DHIS2_OUTLIERS_IMPUTATION`**, and sets the suffix of the output filenames.
    * `imputed`: routine data with outliers replaced by imputed values (**`[COUNTRY_CODE]_routine_outliers_imputed.parquet`**).
    * `removed`: routine data with outliers set to missing (**`[COUNTRY_CODE]_routine_outliers_removed.parquet`**).
  * **Choices:** `imputed`, `removed` — there is no option to use raw routine data.
  * **Default:** `imputed`.

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_quality_of_care/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_quality_of_care/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`** and **`*_[COUNTRY_CODE].ipynb`** variants are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_quality_of_care/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Parameters:** Save **`[COUNTRY_CODE]_parameters.json`** to **`data/dhis2/quality_of_care/`**, before the computation runs.
5. **Computation notebook:** Run **`snt_dhis2_quality_of_care.ipynb`** with **`DATA_ACTION`**:
   1. **Routine data:** Load **`[COUNTRY_CODE]_routine_outliers_[data_action].parquet`** from the latest version of **`DHIS2_OUTLIERS_IMPUTATION`**; the run stops with an `[ERROR]` if it cannot be loaded.
   2. **Shapes:** Load **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`**; the run stops with an `[ERROR]` if it cannot be loaded.
   3. **Cleaning:** Cast the indicator columns **`TEST`**, **`SUSP`**, **`MALTREAT`**, **`CONF`**, **`MALDTH`**, **`MALADM`**, **`ALLADM`**, **`ALLDTH`**, **`ALLOUT`**, **`PRES`** to numeric (`""` and `"-"` become missing), **`YEAR`** to integer and **`ADM2_ID`** to character. Indicator columns absent from the routine file are skipped.
   4. **Aggregation:** Sum the available indicators **by `ADM2_ID` and `YEAR`**, producing one row per ADM2 × YEAR.
   5. **Indicators:** Compute each rate only when both its numerator and denominator columns are present, and copy the two absolute counts (see Notes).
   6. **ADM2 names:** Join **`ADM2_NAME`** from the shapes by **`ADM2_ID`**.
   7. **Export:** Write **`[COUNTRY_CODE]_quality_of_care_district_year_[data_action].parquet`** and **`.csv`** to **`data/dhis2/quality_of_care/`**.
   8. **Maps:** Save one **ADM2** choropleth PNG per indicator and year to **`pipelines/snt_dhis2_quality_of_care/reporting/outputs/figures/`**. A map that fails is logged as a `[WARNING]` and skipped.
6. **Output check:** Fail the run if the parquet or CSV is missing or was not written during this run, so files left over from a previous run are never published.
7. **Publish:** Upload the parquet, CSV and **`[COUNTRY_CODE]_parameters.json`** to **`DHIS2_QUALITY_OF_CARE`** via **`add_files_to_dataset`**.
8. **Reporting:** Run **`snt_dhis2_quality_of_care_report.ipynb`** (or its custom or country version, chosen as in step 3) to refresh the report outputs.

With **`run_report_only`**, steps 4–7 are skipped: nothing is computed or published, and **`[COUNTRY_CODE]_parameters.json`** is not rewritten. Steps 1–3 and 8 still run. The report reads the most recently modified **`[COUNTRY_CODE]_quality_of_care_district_year_imputed.parquet`** or **`_removed.parquet`** from the workspace filesystem, whatever **`data_action`** is set to.

## Inputs

* **`[COUNTRY_CODE]_routine_outliers_imputed.parquet`** or **`[COUNTRY_CODE]_routine_outliers_removed.parquet`** (per **`data_action`**) on **`DHIS2_OUTLIERS_IMPUTATION`** — required. Produced by whichever outliers imputation pipeline ran last.
* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** — required, read by both notebooks.
* **`data/dhis2/quality_of_care/[COUNTRY_CODE]_quality_of_care_district_year_{imputed|removed}.parquet`** on the workspace filesystem — required by the reporting notebook, which reads the most recently modified one and stops with an `[ERROR]` if there is none.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`SNT_CONFIG.COUNTRY_CODE`** and the dataset identifiers **`DHIS2_OUTLIERS_IMPUTATION`**, **`DHIS2_DATASET_FORMATTED`** and **`DHIS2_QUALITY_OF_CARE`**.
* **`pipelines/snt_dhis2_quality_of_care/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/quality_of_care/[COUNTRY_CODE]_quality_of_care_district_year_[data_action].parquet`** and **`.csv`**
* **`data/dhis2/quality_of_care/[COUNTRY_CODE]_parameters.json`**, with **`DATA_ACTION`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. The flags **`run_report_only`** and **`use_custom_notebooks`** are not recorded.
* **Yearly indicator maps** in **`pipelines/snt_dhis2_quality_of_care/reporting/outputs/figures/`**, named **`[indicator]_[YEAR].png`** (e.g. **`testing_rate_2023.png`**; the outpatient map uses the prefix **`allout_`**). Written, not published.
* **Executed notebooks** under **`pipelines/snt_dhis2_quality_of_care/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_quality_of_care/reporting/outputs/`**, named the same way, plus **`[COUNTRY_CODE]_quality_of_care_summary.parquet`** and **`.csv`** (year-level summary) and **`figures/[COUNTRY_CODE]_quality_of_care_by_year.png`**. Written, not published.
* **Synced scripts** under **`pipelines/snt_dhis2_quality_of_care/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHIS2_QUALITY_OF_CARE`** (not in report-only mode)

* **`[COUNTRY_CODE]_quality_of_care_district_year_[data_action].parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** one row per **`ADM2_ID`** × **`YEAR`**. Columns: **`ADM2_ID`**, **`YEAR`**, the summed indicator columns present in the routine data, the derived indicators below, and **`ADM2_NAME`** (only if the shapes carry it).
> - **Rates are ratios of ADM2 × YEAR sums**, not averages of monthly or facility rates. A rate is missing when its denominator is 0 or missing.
>   - **`TESTING_RATE`**: **`TEST`** / **`SUSP`**.
>   - **`TREATMENT_RATE`**: **`MALTREAT`** / **`CONF`**.
>   - **`CASE_FATALITY_RATE`**: **`MALDTH`** / **`MALADM`** (in-hospital, among malaria admissions).
>   - **`PROP_ADM_MALARIA`**: **`MALADM`** / **`ALLADM`**.
>   - **`PROP_MALARIA_DEATHS`**: **`MALDTH`** / **`ALLDTH`**.
> - **`NON_MALARIA_ALL_CAUSE_OUTPATIENTS`**: ADM2 × YEAR sum of **`ALLOUT`**, copied as is (nothing is subtracted).
> - **`PRESUMED_CASES`**: ADM2 × YEAR sum of **`PRES`**.
> - **Missing values sum to 0:** sums ignore missing values, so an ADM2 × YEAR where an indicator is missing in every record gets **0**, not missing.
> - **Which outliers method?** **`DHIS2_OUTLIERS_IMPUTATION`** holds the output of whichever outliers pipeline ran last; check the **`[COUNTRY_CODE]_parameters.json`** published beside it to know the method.
> - **Parameters file written first:** **`[COUNTRY_CODE]_parameters.json`** is saved before the notebook runs, so a failed run leaves a new parameters file on the workspace filesystem; it is published only when the run gets through the output check.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the pipeline's own. Entries are resolved for both notebooks up front.
> - **Guarded execution:** missing indicator columns are skipped rather than failing the run, so an indicator whose inputs are absent simply does not appear in the output.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_quality_of_care/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
> - Stock-out indicators are not implemented (on hold, pending NMDR data).
