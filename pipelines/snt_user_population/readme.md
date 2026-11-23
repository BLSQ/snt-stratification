# SNT User Population Pipeline

The **SNT User Population** pipeline imports a population file supplied by the operator (a CSV filled in from the **`[COUNTRY_CODE]_population_user_template.csv`** template), validates it against the formatted DHIS2 pyramid, and publishes it as **`[COUNTRY_CODE]_population.parquet`** and **`.csv`** to **`SNT_POPULATION_USER_PROVIDED`**. It then runs the reporting notebook, which maps each population indicator per year at ADM2 level. The published file is the **`User-provided`** population source of **`snt_dhis2_incidence`** and **`snt_dhis2_population_transformation`**.

## Parameters

* **`user_file`** (File, Required):
  * **Name:** Upload user population file (.csv)
  * **Description:** The CSV file to import, based on the population user template. A file must be selected even with **`run_report_only`**, where it is not read. A normal run stops with an error if the selected file does not exist.
  * **Default:** `None`.

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version (it has no `code/` notebook) to **`pipelines/snt_user_population/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_user_population/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`**, resolve **`COUNTRY_CODE`**.
3. **Choose the report notebook (before it runs):** Run **`custom/snt_user_population_report.ipynb`** if **`use_custom_notebooks`** is on and the file exists, else **`snt_user_population_report_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. A notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no **`snt_user_population_report.ipynb`** in **`pipelines/snt_user_population/custom/`**, the run stops with an `[ERROR]` before anything else runs. Then resolve the **`SNT_POPULATION_USER_PROVIDED`** dataset identifier; the run stops if it is missing from the configuration.
4. **Pyramid:** Load **`[COUNTRY_CODE]_pyramid.parquet`** from **`DHIS2_DATASET_FORMATTED`**; stop if it is missing or empty. Then stop if no **`user_file`** is selected or the file does not exist. Extract the unique ADM1/ADM2 names and IDs from the pyramid columns named by **`DHIS2_ADMINISTRATION_1`** / **`DHIS2_ADMINISTRATION_2`** (uppercased, the ID column being the name column with `_NAME` → `_ID`); stop if those columns are not in the pyramid.
5. **Read the user file:** Detect the separator from the header line (comma with decimal point, or semicolon with decimal comma); read as UTF-8 (with or without BOM), falling back to Latin-1. Column names are stripped and uppercased.
6. **Validate** (stops the run only on structural problems):
   * **Stop** if any of **`YEAR`**, **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`POPULATION`** is missing, or if no row has both **`YEAR`** and **`POPULATION`** filled in.
   * **Warn** (the rows are kept as provided) about: columns outside the template (dropped, not published); missing or non-whole-number **`YEAR`**; non-numeric or negative values in **`POPULATION`** / **`POP_*`**; missing **`POPULATION`**; **`ADM2_ID`**s not in the pyramid; pyramid ADM2 units missing for a given **`YEAR`**; ADM1 name/ID or ADM2 name that differ from the pyramid for the same **`ADM2_ID`**; rows sharing the same **`YEAR`** and **`ADM2_ID`**.
   * Round **`POPULATION`** up to an integer.
7. **Save:** Write **`[COUNTRY_CODE]_population.parquet`** and **`.csv`** to **`data/user_population/`** (ADM2 × yearly).
8. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** and upload the parquet, the CSV and the parameters file to **`SNT_POPULATION_USER_PROVIDED`** via **`add_files_to_dataset`**.
9. **Reporting:** Run **`snt_user_population_report.ipynb`** (or its custom or country version, chosen as in step 3). It reads the population back from **`SNT_POPULATION_USER_PROVIDED`**, stops with an `[ERROR]` if any ADM1/ADM2 name + ID combination in it does not match **`[COUNTRY_CODE]_shapes.geojson`**, and otherwise draws one choropleth per non-empty indicator, faceted by **`YEAR`**.

With **`run_report_only`**, steps 4–8 are skipped: nothing is read from the user file, written or published. Steps 1–3 and 9 still run, on the file last published to **`SNT_POPULATION_USER_PROVIDED`**.

## Inputs

* **User population CSV** (the **`user_file`** parameter) — required; not read with **`run_report_only`**. Built from **`uploads/[COUNTRY_CODE]_population_user_template.csv`**, which **`snt_dhis2_formatting`** writes to the workspace.
* **`[COUNTRY_CODE]_pyramid.parquet`** on **`DHIS2_DATASET_FORMATTED`** — required for a normal run; the run stops if it is missing or empty. Not read with **`run_report_only`**.
* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** — read by the reporting notebook only, for the map boundaries and the name check.
* **`[COUNTRY_CODE]_population.parquet`** on **`SNT_POPULATION_USER_PROVIDED`** — read back by the reporting notebook.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`SNT_CONFIG.COUNTRY_CODE`**, **`SNT_CONFIG.DHIS2_ADMINISTRATION_1`**, **`SNT_CONFIG.DHIS2_ADMINISTRATION_2`**, **`SNT_DATASET_IDENTIFIERS.SNT_POPULATION_USER_PROVIDED`** and **`SNT_DATASET_IDENTIFIERS.DHIS2_DATASET_FORMATTED`**.
* **`pipelines/snt_user_population/custom/snt_user_population_report.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`reporting/snt_user_population_report_[COUNTRY_CODE].ipynb`** in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/user_population/[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`data/user_population/[COUNTRY_CODE]_parameters.json`**, with **`USER_FILE`** (the uploaded file path), **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. It does not record **`run_report_only`** or **`use_custom_notebooks`**.
* **Report outputs** under **`pipelines/snt_user_population/reporting/outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook, with their HTML and one PNG per indicator in **`figures/[COUNTRY_CODE]_choropleth_population_user_<INDICATOR>.png`** (not published)
* **Synced scripts** under **`pipelines/snt_user_population/`** (`reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `SNT_POPULATION_USER_PROVIDED`**

* **`[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **`YEAR`**: integer. Rows with a missing or invalid **`YEAR`** are kept and published empty; the report leaves them out of the maps.
> - **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**: text, published exactly as typed by the operator. Differences from the pyramid are only warned about, not corrected.
> - **`POPULATION`**: total population, integer, decimals rounded **up**. May be empty for some rows (warned).
> - **`POP_UNDER_5`**, **`POP_PREGNANT_WOMEN`**, **`POP_0_1_Y`**, **`POP_1_2_Y`**, **`POP_5_10_Y`**, **`POP_5_36_M`**, **`POP_50_PLUS`**: optional disaggregations, published as numeric (decimals kept). Columns absent from the file are not added; empty cells stay empty. The report skips any indicator with no values.
> - **Grain:** ADM2 × yearly, one row per **`ADM2_ID`** and **`YEAR`** as provided. Duplicates and missing ADM2 units are warned about, not removed or filled.
> - **Guarded execution:** Data issues never stop the run; they are logged as warnings and the file is published as provided. The shapes name check in the report runs **after** publication, so a file whose names do not match the shapes is already on **`SNT_POPULATION_USER_PROVIDED`** when the report fails.
> - **`NOTEBOOK_OVERRIDES`**: one entry if the report notebook is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means the generic notebook ran. A run with **`run_report_only`** writes no parameters file, so its override appears only in the run log.
> - **Edited notebooks**: the sync overwrites any hand edit to the notebook in `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_user_population/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
