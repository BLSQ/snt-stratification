# SNT DHIS2 Incidence Pipeline

The **SNT DHIS2 Incidence** pipeline estimates monthly malaria case metrics and yearly incidence rates from routine DHIS2 data. It supports crude incidence and adjustments for testing gaps, incomplete reporting, and optional care-seeking behaviour, using the population source selected by the operator. It publishes **`[COUNTRY_CODE]_incidence.parquet`** and **`.csv`** to **`DHIS2_INCIDENCE`** and runs the incidence reporting notebook.

---

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

* **`n1_method`** (String, Required):
  * **Name:** Method for N1 calculations
  * **Description:** Defines how **`N1`** (cases adjusted for testing gaps) is derived: from presumed cases or from suspected minus tested cases.
    * `PRES`: **`N1`** uses the **`PRES`** column. The run fails if the routine data has no **`PRES`** column, or if that column contains only missing values. With a **`disaggregation_selection`**, the column checked is **`PRES_[DISAGGREGATION_SELECTION]`**.
    * `SUSP-TEST`: **`N1`** uses **`SUSP`** − **`TEST`**.
  * **Choices:** `PRES`, `SUSP-TEST`.
  * **Default:** `PRES`.
* **`routine_data_choice`** (String, Required):
  * **Name:** Routine data to use
  * **Description:** Which routine dataset variant to use:
    * `raw`: **`[COUNTRY_CODE]_routine.parquet`** from **`DHIS2_DATASET_FORMATTED`**.
    * `raw_without_outliers`: **`[COUNTRY_CODE]_routine_outliers_removed.parquet`** from **`DHIS2_OUTLIERS_IMPUTATION`**.
    * `imputed`: **`[COUNTRY_CODE]_routine_outliers_imputed.parquet`** from **`DHIS2_OUTLIERS_IMPUTATION`**.
  * **Choices:** `raw`, `raw_without_outliers`, `imputed`.
  * **Default:** `imputed`.
* **`population_selection`** (String, Required):
  * **Name:** Population data selection
  * **Description:** Source of the population used as incidence denominator. In every case the file read is **`[COUNTRY_CODE]_population.parquet`**:
    * `DHIS2`: from **`DHIS2_DATASET_FORMATTED`**, produced by **`snt_dhis2_formatting`**.
    * `User-provided`: from **`SNT_POPULATION_USER_PROVIDED`**, produced by **`snt_user_population`**.
    * `Population-transformed`: from **`DHIS2_POPULATION_TRANSFORMATION`**, produced by **`snt_dhis2_population_transformation`**.
  * **Choices:** `DHIS2`, `User-provided`, `Population-transformed`.
  * **Default:** `DHIS2`.
* **`disaggregation_selection`** (String, Optional):
  * **Name:** Analyze by Population Group (only if available)
  * **Description:** Optional demographic subset. Mapped to a suffix (`Children Under 5 Years Old` → `UNDER_5`, `Pregnant Women` → `PREGNANT_WOMAN`); the notebook then uses the routine columns **`CONF_<suffix>`**, **`TEST_<suffix>`** and **`SUSP_<suffix>`** (or **`PRES_<suffix>`**) and the population column **`POP_<suffix>`**. The run fails if any of them is missing. `Pregnant Women` currently always fails (see Notes).
  * **Choices:** `Children Under 5 Years Old`, `Pregnant Women`.
  * **Default:** none (no disaggregation).
* **`careseeking_file_path`** (File, Optional):
  * **Name:** Care seeking behaviour (CSB) data file (.csv)
  * **Description:** User-supplied CSB file. If omitted, or if the file cannot be found or read, the notebook loads DHS-based care-seeking; if neither is available, the care-seeking adjustment is skipped. A file that is read but fails validation (see below) is dropped without falling back to DHS: no care-seeking adjustment is made.
  * **Template:** **`uploads/[COUNTRY_CODE]_careseeking_template.csv`**, written by **`snt_dhis2_formatting`** (pyramid step). It has one row per ADM2 with **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`** and an empty **`CARESEEKING_PCT`** to fill in; it has no **`YEAR`** column, so add one only to provide values per year (see below).
  * **Expected columns:** **`ADM1_ID`** and **`CARESEEKING_PCT`** (numeric, 0–100, or 0–1 which is rescaled), both required; optional **`ADM2_ID`** (joined at ADM2 instead of ADM1) and optional **`YEAR`**.
    * **Without `YEAR`:** each ADM value is applied to **every** year of the routine data.
    * **With `YEAR`:** each year uses its own value, and years absent from the file get **no** care-seeking adjustment (empty **`INCIDENCE_ADJ_CARESEEKING`**, with a warning listing them). A file covering only one year therefore adjusts only that year — leave out **`YEAR`** to apply a single set of values to all years.
    * **Empty `CARESEEKING_PCT` cells** are set to `100` (with a warning), so those units get **`N3`** = **`N2`**.
  * **Default:** none.

---

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_incidence/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_incidence/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. This version ships one variant, **`code/snt_dhis2_incidence_NER.ipynb`**, synced like the other notebooks. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_incidence/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Population check (`pipeline.py`):** Resolve the dataset of the selected **`population_selection`** and check that **`[COUNTRY_CODE]_population.parquet`** exists in its latest version; the run fails before any computation if it does not (or if the dataset identifier is missing from the config).
5. **Parameters:** Save **`N1_METHOD`**, **`ROUTINE_DATA_CHOICE`**, **`POPULATION_DATASET_ID`** (the resolved dataset id), **`DISAGGREGATION_SELECTION`** (the mapped suffix), **`CARESEEKING_FILE_PATH`** and **`ROOT_PATH`** to **`[COUNTRY_CODE]_parameters.json`**, before the computation runs, and inject the same values into the notebook.
6. **Computation:** Run **`snt_dhis2_incidence.ipynb`**:
   1. Load the routine data of the selected variant (fails with an `[ERROR]` if the file cannot be loaded), the population from **`POPULATION_DATASET_ID`**, and the reporting rate.
   2. Apply the optional disaggregation to the routine and population columns. With `PRES`, fail if the **`PRES`** column is missing or empty (see **`n1_method`**).
   3. Load care-seeking data: the uploaded file if provided and readable, else the DHS file, else none.
   4. Compute monthly **`TPR`**, **`N1`**, **`N2`** and (with care-seeking data) **`N3`** at **ADM2 × month** (`group_by(ADM1_ID, ADM2_ID, YEAR, MONTH)`), and write **`[COUNTRY_CODE]_monthly_cases.parquet`**.
   5. Aggregate to **ADM2 × YEAR** (summing **`CONF`**, **`TEST`**, the **`N1`** input column — **`PRES`** or **`SUSP`** — **`N1`**, **`N2`** and **`N3`**), join the population on **`ADM2_ID`** + **`YEAR`**, compute the incidence rates, and write **`[COUNTRY_CODE]_incidence.parquet`** and **`.csv`**.
7. **Output check:** Fail if the incidence parquet or CSV was not written during this run.
8. **Publish:** Upload **`[COUNTRY_CODE]_incidence.parquet`**, **`[COUNTRY_CODE]_incidence.csv`** and **`[COUNTRY_CODE]_parameters.json`** to **`DHIS2_INCIDENCE`** via **`add_files_to_dataset`**.
9. **Reporting:** Run **`snt_dhis2_incidence_report.ipynb`** (or its custom or country version, chosen as in step 3) to refresh the report outputs.

With **`run_report_only`**, steps 4–8 are skipped: nothing is computed or published, and **`[COUNTRY_CODE]_parameters.json`** is not rewritten. Steps 1–3 and 9 still run. The report reads the incidence table and parameters file last published to **`DHIS2_INCIDENCE`**, and the monthly cases file left on the workspace filesystem by the last full run.

---

## Inputs

* **Routine data** (required), per **`routine_data_choice`** — see Parameters for the file and dataset of each choice.
* **Population** (required): **`[COUNTRY_CODE]_population.parquet`** from the dataset of the selected **`population_selection`** — see Parameters.
* **Reporting rate** (required): **`[COUNTRY_CODE]_reporting_rate_dataelement.parquet`** from **`DHIS2_REPORTING_RATE`**, falling back to **`[COUNTRY_CODE]_reporting_rate_dataset.parquet`**; the run fails if neither can be loaded.
* **Care-seeking** (optional): the uploaded **`careseeking_file_path`** CSV (start from **`uploads/[COUNTRY_CODE]_careseeking_template.csv`**, written by **`snt_dhis2_formatting`**), else **`[COUNTRY_CODE]_DHS_ADM2_PCT_CARESEEKING_SAMPLE_AVERAGE.parquet`** from **`DHS_INDICATORS`**, falling back to **`[COUNTRY_CODE]_DHS_ADM1_PCT_CARESEEKING_SAMPLE_AVERAGE.parquet`** (columns **`ADM1_ID`** and **`PCT_PUBLIC_CARE`**, one row per **`ADM1_ID`**; any other column, including **`YEAR`**, is ignored, so the survey value of each ADM1 applies to all its ADM2 units and all years).
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required): **`SNT_CONFIG.COUNTRY_CODE`**, **`SNT_CONFIG.DHIS2_ADMINISTRATION_1`** / **`DHIS2_ADMINISTRATION_2`**, **`DHIS2_DATA_DEFINITIONS.DHIS2_INDICATOR_DEFINITIONS`**, and under **`SNT_DATASET_IDENTIFIERS`**: **`DHIS2_DATASET_FORMATTED`**, **`DHIS2_OUTLIERS_IMPUTATION`**, **`SNT_POPULATION_USER_PROVIDED`**, **`DHIS2_POPULATION_TRANSFORMATION`**, **`DHIS2_REPORTING_RATE`**, **`DHS_INDICATORS`** and **`DHIS2_INCIDENCE`**.
* **Read by the reporting notebook only:** **`[COUNTRY_CODE]_incidence.parquet`** and **`[COUNTRY_CODE]_parameters.json`** from **`DHIS2_INCIDENCE`**; **`[COUNTRY_CODE]_shapes.geojson`** and **`[COUNTRY_CODE]_pyramid.parquet`** from **`DHIS2_DATASET_FORMATTED`**; the file list of **`DHIS2_REPORTING_RATE`**; **`pipelines/snt_dhis2_incidence/intermediate_results/[COUNTRY_CODE]_monthly_cases.parquet`** and **`configuration/SNT_metadata.json`** on the workspace filesystem.
* **`pipelines/snt_dhis2_incidence/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.
* **`code/snt_dhis2_incidence_NER.ipynb`**, shipped with this pipeline version ([ADR 0046](../../docs/decisions/0046-country-variants-in-the-repo.md)): Niger's variant, run instead of **`snt_dhis2_incidence.ipynb`** when **`COUNTRY_CODE`** is `NER`. **It is out of date against this pipeline** ([BACKLOG VAR-3](../../docs/BACKLOG.md#var-3)), so a NER run is expected to fail at that notebook.

---

## Outputs

**Workspace filesystem**

* **`data/dhis2/incidence/[COUNTRY_CODE]_incidence.parquet`** and **`.csv`**
* **`data/dhis2/incidence/[COUNTRY_CODE]_parameters.json`**, with the injected notebook parameters (**`N1_METHOD`**, **`ROUTINE_DATA_CHOICE`**, **`POPULATION_DATASET_ID`**, **`DISAGGREGATION_SELECTION`**, **`CARESEEKING_FILE_PATH`**, **`ROOT_PATH`**), **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. The flags **`run_report_only`** and **`use_custom_notebooks`** are not recorded.
* **`pipelines/snt_dhis2_incidence/intermediate_results/[COUNTRY_CODE]_monthly_cases.parquet`**: intermediate ADM2 × month table, read by the reporting notebook; not published
* **Executed notebooks** under **`pipelines/snt_dhis2_incidence/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_incidence/reporting/outputs/`**, named the same way, plus PNG figures under **`reporting/outputs/figures/`**; not published
* **Synced scripts** under **`pipelines/snt_dhis2_incidence/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHIS2_INCIDENCE`** (not in report-only mode)

* **`[COUNTRY_CODE]_incidence.parquet`**
* **`[COUNTRY_CODE]_incidence.csv`**
* **`[COUNTRY_CODE]_parameters.json`** (records **`POPULATION_DATASET_ID`**, the dataset id, rather than the **`population_selection`** label)

---

> **Notes for the Data Analyst:**
>
> - **Grain:** ADM2 × YEAR. Columns: **`YEAR`**, **`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`**, **`POPULATION`**, the yearly totals **`CONF`**, **`TEST`**, **`N1`**, **`N2`**, **`N3`** (only with care-seeking data), the **`N1`** input column, and the **`INCIDENCE_*`** columns.
> - **`N1` input column:** the case column that entered **`N1`** besides **`CONF`** and **`TEST`**, following **`n1_method`**: **`PRES`** with `PRES`, **`SUSP`** with `SUSP-TEST`. The other one is not published.
> - **Yearly totals:** sums of the monthly values per ADM2 × **`YEAR`**. With `SUSP-TEST`, **`TEST`** is the value capped at **`SUSP`** (see **`N1`**), not the reported one. A month with a missing **`N2`** leaves the yearly **`N2`** and **`INCIDENCE_ADJ_REPORTING`** missing.
> - **With a `disaggregation_selection`:** every published case column (**`CONF`**, **`TEST`**, the **`N1`** input column) and **`POPULATION`** hold the selected group's values.
> - **`TPR`**: Test positivity rate, **`CONF`** / **`TEST`**. If **`TEST`** is zero or missing, **`TPR`** is set to `1` to avoid division by zero.
> - **`N1`**: Testing-adjusted cases. With **`SUSP-TEST`**: **`CONF`** + ((**`SUSP`** − **`TEST`**) × **`TPR`**), capping **`TEST`** at **`SUSP`** when needed. With **`PRES`**: **`CONF`** + (**`PRES`** × **`TPR`**).
> - **`N2`**: **`N1`** / **`REPORTING_RATE`**. If the monthly reporting rate is zero, **`N2`** is set to missing.
> - **`N3`**: **`N2`** / (**`CARESEEKING_PCT`** / 100). If care-seeking percent is zero, **`N3`** is missing.
> - **`INCIDENCE_CRUDE`** / **`INCIDENCE_ADJ_TESTING`** / **`INCIDENCE_ADJ_REPORTING`** / **`INCIDENCE_ADJ_CARESEEKING`**: Yearly rates per 1,000 population from **`CONF`**, **`N1`**, **`N2`** and **`N3`**.
>   - **`INCIDENCE_ADJ_CARESEEKING`** is empty when no care-seeking data is available.
>   - When the care-seeking data has no value for an ADM unit or a **`YEAR`** (a warning lists the missing years), every month of that ADM2 × **`YEAR`** has a missing **`N3`**, and the yearly **`N3`** and **`INCIDENCE_ADJ_CARESEEKING`** are left **empty** (not `0`).
>   - When only some months of an ADM2 × **`YEAR`** have a missing **`N3`** (e.g. zero reporting rate or zero care-seeking percent), the yearly **`N3`** is the sum of the available months only.
> - **Population source:** whichever **`population_selection`** is used, the population file must have one row per **`ADM2_ID`** × **`YEAR`**. A duplicated pair (possible in a user-provided file, where duplicates are only warned about) duplicates that row in the incidence table.
> - **`Pregnant Women`** disaggregation: the mapped suffix composes **`POP_PREGNANT_WOMAN`** (singular), while the population pipelines produce **`POP_PREGNANT_WOMEN`** (plural), so this selection currently fails at the population step ([BACKLOG PIPE-5](../../docs/BACKLOG.md#pipe-5)).
> - **Parameters file written first:** **`[COUNTRY_CODE]_parameters.json`** is saved before the notebook runs, so a failed run leaves a new parameters file on the workspace filesystem; it is published only when the run gets through the output check.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the pipeline's own. Entries are resolved for both notebooks up front.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_incidence/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
