# SNT DHIS2 Formatting Pipeline

The **SNT DHIS2 Formatting** pipeline converts raw DHIS2 extract Parquet files from the extract dataset into analysis-ready **routine**, **population**, **shapes**, **pyramid**, and **reporting** tables and vectors. It publishes the formatted artifacts to **`DHIS2_DATASET_FORMATTED`** and runs the formatting reporting notebook for quality review.

## Parameters

None. `pipeline.py` defines no domain parameters. The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhis2_formatting/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhis2_formatting/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`** and **`*_[COUNTRY_CODE].ipynb`** variants are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`**, resolve **`COUNTRY_CODE`**, and resolve dataset identifiers for extracts and formatted outputs.
3. **Choose each notebook (before any runs):** For each of the six notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhis2_formatting/custom/`** matching any of the six names, the run stops with an `[ERROR]` before any notebook runs.
4. **Shapes (ADM2 geometry):** When **`[COUNTRY_CODE]_dhis2_raw_shapes.parquet`** exists on **`DHIS2_DATASET_EXTRACTS`**, run **`snt_dhis2_formatting_shapes.ipynb`** to produce **`[COUNTRY_CODE]_shapes.geojson`**. Runs first, because the pyramid step validates coordinates against these boundaries.
5. **Pyramid (facility metadata):** When **`[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`** exists, run **`snt_dhis2_formatting_pyramid.ipynb`** to write **`[COUNTRY_CODE]_pyramid.parquet`** and **`.csv`**. If **`[COUNTRY_CODE]_shapes.geojson`** is on the workspace filesystem, facility coordinates are validated against it; when any are invalid, the notebook writes **`[COUNTRY_CODE]_pyramid_invalid_coordinates.csv`**. The same notebook writes two CSV templates (one row per ADM2) to the workspace **`uploads/`** folder: an administrative template listing the ADM1/ADM2 names and IDs, and a blank care-seeking template used as the **`careseeking_file_path`** input of **`snt_dhis2_incidence`**.
6. **Routine (analytics):** When **`[COUNTRY_CODE]_dhis2_raw_analytics.parquet`** exists, run **`snt_dhis2_formatting_routine.ipynb`** to write **`[COUNTRY_CODE]_routine.parquet`** and **`.csv`** (monthly facility-level rows with administrative keys).
7. **Population:** When **`[COUNTRY_CODE]_dhis2_raw_population.parquet`** exists, run **`snt_dhis2_formatting_population.ipynb`** to write **`[COUNTRY_CODE]_population.parquet`** and **`.csv`**. The same notebook writes two blank CSV templates (one row per ADM2) to the workspace **`uploads/`** folder for operators to fill in.
8. **Reporting rates:** When **`[COUNTRY_CODE]_dhis2_raw_reporting.parquet`** exists, run **`snt_dhis2_formatting_reporting_rates.ipynb`** to write **`[COUNTRY_CODE]_reporting.parquet`** and **`.csv`**.
9. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** and upload the formatted files plus the parameters file to **`DHIS2_DATASET_FORMATTED`** via **`add_files_to_dataset`**. A file missing from the filesystem is skipped with a warning.
10. **Reporting:** Run **`snt_dhis2_formatting_report.ipynb`** (or its custom or country version, chosen as in step 3) to refresh the report outputs.

With **`run_report_only`**, steps 4–9 are skipped: nothing is formatted or published. Steps 1–3 and 10 still run.

## Inputs

* **`[COUNTRY_CODE]_dhis2_raw_analytics.parquet`**, **`[COUNTRY_CODE]_dhis2_raw_population.parquet`**, **`[COUNTRY_CODE]_dhis2_raw_shapes.parquet`**, **`[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`**, **`[COUNTRY_CODE]_dhis2_raw_reporting.parquet`** on **`DHIS2_DATASET_EXTRACTS`** (each is optional; a missing input skips its formatting step). The population step also reads **`[COUNTRY_CODE]_dhis2_raw_pyramid.parquet`**, which the pipeline does not check before running it.
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_shapes.geojson`** on the workspace filesystem (optional), read by the pyramid step for coordinate validation; the shapes step of the same run writes it.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`COUNTRY_CODE`** and **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_EXTRACTS`**, **`DHIS2_DATASET_FORMATTED`**).
* **`pipelines/snt_dhis2_formatting/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_routine.parquet`** and **`.csv`**
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_shapes.geojson`**
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_pyramid.parquet`** and **`.csv`**
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_pyramid_invalid_coordinates.csv`**, only when invalid coordinates are found; not published
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_reporting.parquet`** and **`.csv`**
* **`data/dhis2/extracts_formatted/[COUNTRY_CODE]_parameters.json`**, with **`RUN_REPORT_ONLY`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **`uploads/[COUNTRY_CODE]_adm_template.csv`**: ADM1/ADM2 names and IDs (**`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**), sorted by ADM1 and ADM2 name
* **`uploads/[COUNTRY_CODE]_careseeking_template.csv`**: ADM1/ADM2 names and IDs, plus an empty **`CARESEEKING_PCT`** column (no **`YEAR`** column)
* **`uploads/[COUNTRY_CODE]_population_disaggregation_template.csv`**: ADM1/ADM2 names and IDs, plus empty disaggregation columns (**`POP_UNDER_5`**, **`POP_PREGNANT_WOMEN`**, …)
* **`uploads/[COUNTRY_CODE]_population_user_template.csv`**: empty **`YEAR`**, ADM1/ADM2 names and IDs, empty **`POPULATION`**, then the same disaggregation columns
* **Executed notebooks** under **`pipelines/snt_dhis2_formatting/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhis2_formatting/reporting/outputs/`**, named the same way
* **Synced scripts** under **`pipelines/snt_dhis2_formatting/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHIS2_DATASET_FORMATTED`**

* **`[COUNTRY_CODE]_routine.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_population.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_shapes.geojson`**
* **`[COUNTRY_CODE]_pyramid.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_reporting.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **`Routine` resolution**: The formatted routine product is **monthly** at **facility (OU)** level with **`ADM1_ID`**, **`ADM2_ID`**, and **`PERIOD`** / **`YEAR`** / **`MONTH`** as produced by the routine notebook (see that notebook for the authoritative column list).
> - **`Shapes`**: **`[COUNTRY_CODE]_shapes.geojson`** supplies **ADM2** geometries and identifiers used by downstream SNT pipelines.
> - **Upload templates**: The administrative, care-seeking and two population **`uploads/`** templates are workspace files only. They are **not** published to **`DHIS2_DATASET_FORMATTED`**, and a new run overwrites them. Empty cells are written blank, not as `NA`.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the pipeline's own. Entries are resolved for all six notebooks up front, including those of stages that were then skipped.
> - **Guarded execution**: Each formatting stage is gated on **`dataset_file_exists`** for its raw extract; do not expect fresh outputs for stages whose raw Parquet was never published to **`DHIS2_DATASET_EXTRACTS`**. The publish step only checks that each file exists on the filesystem, so a skipped stage's file left from an earlier run is published again.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhis2_formatting/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
