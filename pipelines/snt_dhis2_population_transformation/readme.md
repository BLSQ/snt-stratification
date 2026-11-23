# SNT DHIS2 Population Transformation Pipeline

This pipeline takes a population table — either the formatted DHIS2 population from **`DHIS2_DATASET_FORMATTED`** or a user-provided population table from **`SNT_POPULATION_USER_PROVIDED`** — and applies three optional transformation stages: (1) scaling the population columns to a national reference total, (2) creating disaggregated population columns from proportion parameters and/or an uploaded CSV, and (3) projecting population figures across years using a growth rate. It publishes the transformed population Parquet and CSV to **`DHIS2_POPULATION_TRANSFORMATION`** and runs the population transformation reporting notebook.

All columns of the source table are kept. **`POPULATION`** is the basis for the scaling factor and for all computed disaggregations; population indicators already present in the source (e.g. disaggregations in a user-provided table) are carried through and scaled with it.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

### Population source

* **`pop_source`** (str, Required):
  * **Name:** Population source
  * **Description:** Source of the population data to transform.
    * `DHIS2`: **`[COUNTRY_CODE]_population.parquet`** from **`DHIS2_DATASET_FORMATTED`**.
    * `User-provided`: **`[COUNTRY_CODE]_population.parquet`** from **`SNT_POPULATION_USER_PROVIDED`**.
  * **Choices:** `DHIS2`, `User-provided`.
  * **Default:** `DHIS2`.

### Part 1 — Population adjustment

* **`tot_pop_reference`** (int, Optional):
  * **Name:** Part 1: Population reference
  * **Description:** Total national population used to scale the population data. When provided, all population columns are multiplied by **`tot_pop_reference` / total `POPULATION` of the reference year**, so that the reference year total matches this value (e.g. `1000000` for a total population of 1 million).
  * **Default:** `None` (no adjustment applied).
* **`tot_pop_reference_year`** (int, Optional):
  * **Name:** Part 1: Population year reference
  * **Description:** Year in the population data to which **`tot_pop_reference`** applies (e.g. `2025`). Must be available in the data. If omitted or not available, the latest available year is used (with a warning). Ignored when **`tot_pop_reference`** is not set.
  * **Default:** `None` (latest available year used).

### Part 2 — Disaggregation

Each proportion is applied to **`POPULATION`** (after scaling) and written to the column of the same name in uppercase, rounded to the nearest whole number. The same proportion is used for every ADM2 and every year. Each one is a float, Optional, with default `None` (column not computed).

* **`pop_under_5`** — **Name:** Part 2: Proportion population under 5. Proportion of the total population aged under 5 (e.g. `0.17` for 17%). Column **`POP_UNDER_5`**.
* **`pop_pregnant_women`** — **Name:** Part 2: Proportion population pregnant women. Proportion of the total population that are pregnant women (e.g. `0.05` for 5%). Column **`POP_PREGNANT_WOMEN`**.
* **`pop_0_1_y`** — **Name:** Part 2: Proportion population 0-1 years. Proportion aged 0–1 years (e.g. `0.04`). Column **`POP_0_1_Y`**.
* **`pop_1_2_y`** — **Name:** Part 2: Proportion population 1-2 years. Proportion aged 1–2 years (e.g. `0.03`). Column **`POP_1_2_Y`**.
* **`pop_5_10_y`** — **Name:** Part 2: Proportion population 5-10 years. Proportion aged 5–10 years (e.g. `0.06`). Column **`POP_5_10_Y`**.
* **`pop_5_36_m`** — **Name:** Part 2: Proportion population 5-36 months. Proportion aged 5–36 months (e.g. `0.06`). Column **`POP_5_36_M`**.
* **`pop_50_plus`** — **Name:** Part 2: Proportion population 50 plus years. Proportion aged 50 years and above (e.g. `0.06`). Column **`POP_50_PLUS`**.
* **`disaggregation_file`** (File, Optional):
  * **Name:** Part 2: Use disaggregation proportions (.csv)
  * **Description:** User-uploaded CSV (comma- or semicolon-separated) with ADM2-level disaggregation proportions, based on **`uploads/[COUNTRY_CODE]_population_disaggregation_template.csv`**. Must contain **`ADM2_ID`** and must not contain **`YEAR`** or **`POPULATION`**. Each non-empty column is computed as **`POPULATION`** × the ADM2 proportion; a column matching a parameter-derived disaggregation **overwrites** it, other columns are added.
  * **Default:** `None` (no file).

### Part 3 — Projections

* **`growth_factor`** (float, Optional):
  * **Name:** Part 3: Projection growth rate
  * **Description:** Annual growth rate used to project all population columns 6 years backward and 6 years forward from the reference year (e.g. `0.03` for 3%).
  * **Default:** `None` (no projection applied).
* **`growth_reference_year`** (int, Optional):
  * **Name:** Part 3: Projection reference year
  * **Description:** Base year from which projections are calculated. Must be available in the population data. If omitted or not available, the latest available year is used (with a warning). Ignored when **`growth_factor`** is not set.
  * **Default:** `None` (latest available year used).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Create `pipelines/snt_dhis2_population_transformation/` and `data/dhis2/population_transformed/` if missing, then copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_population_transformation/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_population_transformation/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_population_transformation/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Population source:** Load the population table of the selected **`pop_source`** from the latest version of its dataset; abort with an error if the dataset identifier, the dataset, its latest version or the file cannot be found or downloaded.
5. **Disaggregation file check:** If a **`disaggregation_file`** is supplied, abort if the file does not exist on disk, and validate its header — abort if **`ADM2_ID`** is missing or **`YEAR`** / **`POPULATION`** are present.
6. **Reference years:** Read the years in the **`YEAR`** column of the population table (abort if the column is missing or empty), then resolve **`tot_pop_reference_year`** (only if **`tot_pop_reference`** is set) and **`growth_reference_year`** (only if **`growth_factor`** is set) against them.
7. **Parameters:** Save **`[COUNTRY_CODE]_parameters.json`** to **`data/dhis2/population_transformed/`**, before the computation runs. The source is recorded as **`POPULATION_DATASET_SOURCE`**, the dataset id resolved from **`pop_source`**; the reference years are the resolved values from step 6.
8. **Transformation:** Run **`snt_dhis2_population_transformation.ipynb`** (through the helper `dhis2_population_transformation()` in `pipeline.py`) with the parameters of step 7 plus **`SNT_ROOT_PATH`**:
   1. Load **`[COUNTRY_CODE]_population.parquet`** from **`POPULATION_DATASET_SOURCE`**, keeping all columns.
   2. **Part 1 — Adjustment:** if **`tot_pop_reference`** is set, multiply **`POPULATION`** and every existing non-empty numeric population column by **`tot_pop_reference` / total `POPULATION` of the reference year**, for all years.
   3. **Part 2 — Disaggregation (parameters):** for each proportion parameter provided, compute its column as **`POPULATION`** × proportion.
   4. **Part 2 — Disaggregation (file):** if **`disaggregation_file`** is set, join the proportions on **`ADM2_ID`** and compute each valid column as **`POPULATION`** × proportion (see Notes for the validation rules).
   5. **Part 3 — Projection:** if **`growth_factor`** is set, project all population columns backward and forward 6 years from the reference year.
   6. Convert all population columns to integer and write **`[COUNTRY_CODE]_population.parquet`** and **`[COUNTRY_CODE]_population.csv`** to `data/dhis2/population_transformed/`.
9. **Output check:** Abort with an error if the Parquet or the CSV is missing or was not written during this run (guards against publishing stale files).
10. **Publish:** Upload the Parquet, the CSV and **`[COUNTRY_CODE]_parameters.json`** to **`DHIS2_POPULATION_TRANSFORMATION`** via **`add_files_to_dataset`**.
11. **Reporting:** Run **`snt_dhis2_population_transformation_report.ipynb`** (or its custom or country version, chosen as in step 3) to refresh the report outputs. It draws one choropleth per population column, faceted by **`YEAR`**, with a subtitle naming the source read from **`POPULATION_DATASET_SOURCE`** in the published parameters JSON (`DHIS2` or `population fournie par l'utilisateur`).

With **`run_report_only`**, steps 4–10 are skipped: nothing is computed or published, and **`[COUNTRY_CODE]_parameters.json`** is not rewritten. Steps 1–3 and 11 still run, and the report reads the population and parameters file last published to **`DHIS2_POPULATION_TRANSFORMATION`**.

## Inputs

* **`pop_source` = `DHIS2`:** **`[COUNTRY_CODE]_population.parquet`** from **`DHIS2_DATASET_FORMATTED`**, produced by **`snt_dhis2_formatting`** (required).
* **`pop_source` = `User-provided`:** **`[COUNTRY_CODE]_population.parquet`** from **`SNT_POPULATION_USER_PROVIDED`**, produced by **`snt_user_population`** (required).
* **`disaggregation_file`** (optional): operator-uploaded CSV with ADM2-level proportion columns. Start from **`uploads/[COUNTRY_CODE]_population_disaggregation_template.csv`**, written by **`snt_dhis2_formatting`**.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required): **`SNT_CONFIG.COUNTRY_CODE`** (and **`SNT_CONFIG.COUNTRY_NAME`** in the report) and the dataset identifiers **`DHIS2_DATASET_FORMATTED`**, **`SNT_POPULATION_USER_PROVIDED`** and **`DHIS2_POPULATION_TRANSFORMATION`** under **`SNT_DATASET_IDENTIFIERS`**.
* **Read by the reporting notebook only:** **`[COUNTRY_CODE]_population.parquet`** and **`[COUNTRY_CODE]_parameters.json`** from **`DHIS2_POPULATION_TRANSFORMATION`**, and **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`**. A missing file is logged as a warning, not an error.
* **`pipelines/snt_dhis2_population_transformation/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/population_transformed/[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`data/dhis2/population_transformed/[COUNTRY_CODE]_parameters.json`**, with the notebook parameters (**`POPULATION_DATASET_SOURCE`**, **`TOT_POP_REFERENCE`**, **`TOT_POP_REFERENCE_YEAR`**, **`GROWTH_FACTOR`**, **`GROWTH_REFERENCE_YEAR`**, **`POP_UNDER_5`**, **`POP_PREGNANT_WOMEN`**, **`POP_0_1_Y`**, **`POP_1_2_Y`**, **`POP_5_10_Y`**, **`POP_5_36_M`**, **`POP_50_PLUS`**, **`DISAGGREGATION_FILE`**), **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. **`SNT_ROOT_PATH`** and the flags **`run_report_only`** and **`use_custom_notebooks`** are not recorded.
* **Report maps** under **`pipelines/snt_dhis2_population_transformation/reporting/outputs/figures/`**, named **`[COUNTRY_CODE]_choropleth_poptransformed_<INDICATOR>.png`**; not published
* **Executed notebooks** under **`pipelines/snt_dhis2_population_transformation/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_population_transformation/reporting/outputs/`**, named the same way
* **Synced scripts** under **`pipelines/snt_dhis2_population_transformation/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHIS2_POPULATION_TRANSFORMATION`** (not in report-only mode)

* **`[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** one row per ADM2 × **`YEAR`**, with **`YEAR`**, **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`POPULATION`** and any disaggregation columns.
> - **Data types:** all numeric population columns (**`POPULATION`** and disaggregations) are integers, whichever steps ran.
> - **Source columns:** all columns of the source table are kept, including population indicators already present in a user-provided table.
> - **Part 1 scaling:** the scaling factor is computed from the reference year and applied to all years, so the year-to-year trend is preserved. **`POPULATION`** and every existing disaggregation column with values are scaled by the same factor, so their proportions are preserved. Empty or non-numeric columns are left unchanged and listed in a warning.
> - **Part 2 precedence:** parameter-based disaggregations are computed first; columns from **`disaggregation_file`** then overwrite any matching column. A disaggregation already in the source table is overwritten (with a warning) when a parameter or file column of the same name is provided.
> - **Part 2 file validation:**
>   - A column left completely blank is ignored.
>   - A column with any value outside [0, 1] is reported as an error and ignored — proportions must be written as e.g. `0.17`, not `17`.
>   - A duplicated **`ADM2_ID`** is reported as an error and only its first row is used.
>   - ADM2 units missing from the file get empty values for the file's columns.
> - **Proportion parameters are not range-checked:** unlike the columns of **`disaggregation_file`**, the Part 2 parameters are applied as given — enter `0.17`, not `17`, or the column is 17 times the population.
> - **Part 3 projections:** the output contains only the reference year and the 6 years before and after it. Existing years in that window are overwritten by the projections (a warning lists the overwritten years); existing years outside it are dropped.
> - **Reference year fallback:** **`tot_pop_reference_year`** and **`growth_reference_year`** fall back to the latest available year when omitted or not available, with a warning — check the run logs, or the resolved years in **`[COUNTRY_CODE]_parameters.json`**, to confirm which year was used.
> - **Parameters file written first:** **`[COUNTRY_CODE]_parameters.json`** is saved before the notebook runs, so a failed run leaves a new parameters file on the workspace filesystem; it is published only when the run gets through the output check.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the generic one. Entries are resolved for both notebooks up front.
> - **Guarded execution:** a missing population source, a missing or invalid **`disaggregation_file`**, or a notebook run that does not write both outputs all **fail** the run; nothing is skipped silently, and stale files are never published.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_population_transformation/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
