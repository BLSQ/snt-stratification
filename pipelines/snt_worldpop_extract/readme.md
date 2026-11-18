# SNT WorldPop Extract Pipeline

The **SNT WorldPop Extract** pipeline downloads the WorldPop constrained 100 m population raster of the configured country for each year of a range, sums it per **ADM2** zone of the formatted DHIS2 shapes, and concatenates the years into one ADM2 × YEAR population table. It publishes that table and its parameters file to **`WORLDPOP_DATASET_EXTRACT`** and runs the WorldPop reporting notebook.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

* **`year_start`** (Integer, Required):
  * **Name:** Year start
  * **Description:** First year of the range to extract. Must be between **2015** and **2030**, and not after **`year_end`**; otherwise a full run stops with an error (checked after the report-only branch, so a report-only run does not check it).
  * **Default:** none.
* **`year_end`** (Integer, Required):
  * **Name:** Year end
  * **Description:** Last year of the range to extract, inclusive. Same **2015**–**2030** bounds.
  * **Default:** none.

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version (it has no `code/` notebook) to **`pipelines/snt_worldpop_extract/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_worldpop_extract/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`** and **`*_[COUNTRY_CODE].ipynb`** variants are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose the report notebook (before it runs):** Run **`custom/snt_worldpop_extract_report.ipynb`** if **`use_custom_notebooks`** is on and the file exists, else **`snt_worldpop_extract_report_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. A notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no **`snt_worldpop_extract_report.ipynb`** in **`pipelines/snt_worldpop_extract/custom/`**, the run stops with an `[ERROR]` before anything is downloaded or the report runs.
4. **Validate the years:** Check **`year_start`** and **`year_end`** (see Parameters); an invalid range logs an error and stops the run.
5. **Save parameters:** Write **`[COUNTRY_CODE]_parameters.json`** to **`data/worldpop/`**, before any year is processed.
6. **Per year, from `year_start` to `year_end`:**
   1. **Download:** Find the latest WorldPop release under **`Global_2015_2030/`** and download **`[country_code]_pop_<year>_CN_100m_<release>_v1.tif`** (lowercase country code) to **`data/worldpop/rasters/`**. A file of that name already there is reused, not downloaded again.
   2. **Aggregate:** Fetch **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`**, drop null, empty and invalid geometries (with a `[WARNING]` giving the count), reproject them to the raster CRS, and compute the pixel **sum** and **count** per ADM2 zone. Write **`data/worldpop/aggregations/[COUNTRY_CODE]_worldpop_agg_<year>.parquet`**. An ADM2 with no population logs a warning.
   3. **Format:** Keep **`YEAR`**, **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**, **`POPULATION`** and write **`data/worldpop/population/[COUNTRY_CODE]_worldpop_population_<year>.parquet`**.

   A failed download or aggregation logs a warning and skips that year; the run continues.
7. **Concatenate:** Stack the per-year files into **`[COUNTRY_CODE]_worldpop_population.parquet`** and **`.csv`** in **`data/worldpop/population/`** (ADM2 × YEAR). When no year was processed, log a warning and end the run: nothing is published and the report does not run.
8. **Publish:** Upload the concatenated **`.csv`** and **`.parquet`** and **`[COUNTRY_CODE]_parameters.json`** to **`WORLDPOP_DATASET_EXTRACT`** via **`add_files_to_dataset`**.
9. **Reporting:** Run **`snt_worldpop_extract_report.ipynb`** (or its custom or country version, chosen as in step 3).

With **`run_report_only`**, steps 4–8 are skipped: nothing is downloaded, written to `data/` or published, and no parameters file is written. Steps 1–3 and 9 still run.

## Inputs

* **`[COUNTRY_CODE]_shapes.geojson`** from the latest version of **`DHIS2_DATASET_FORMATTED`** (required for a full run): the ADM2 zones, with **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`** properties. Missing, it skips every year with a warning. **`snt_dhis2_formatting`** must have run first.
* **WorldPop rasters** from **`https://data.worldpop.org/GIS/Population/Global_2015_2030/`** (latest release listed there), or the cached copy in **`data/worldpop/rasters/`**.
* **`data/worldpop/rasters/`** on the workspace filesystem (optional): a raster cache shared with **`snt_map_extracts`** and **`snt_healthcare_access`**, keyed on the lowercase-country-code file name.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`COUNTRY_CODE`** and **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`WORLDPOP_DATASET_EXTRACT`**).
* **Report inputs** (read by the report notebook, report-only included): the **`.parquet`** of the latest **`WORLDPOP_DATASET_EXTRACT`** version, and **`[COUNTRY_CODE]_population.parquet`** and **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`**. A missing one stops the report.
* **`pipelines/snt_worldpop_extract/custom/snt_worldpop_extract_report.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`snt_worldpop_extract_report_[COUNTRY_CODE].ipynb`** beside the generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/worldpop/rasters/[country_code]_pop_<year>_CN_100m_<release>_v1.tif`**, one per year (lowercase country code)
* **`data/worldpop/aggregations/[COUNTRY_CODE]_worldpop_agg_<year>.parquet`**, one per year: the shapes' properties uppercased, plus **`POPULATION`** and **`PIXEL_COUNT`**; not published
* **`data/worldpop/population/[COUNTRY_CODE]_worldpop_population_<year>.parquet`**, one per year; not published
* **`data/worldpop/population/[COUNTRY_CODE]_worldpop_population.parquet`** and **`.csv`**: all processed years
* **`data/worldpop/[COUNTRY_CODE]_parameters.json`**, with **`YEAR_START`**, **`YEAR_END`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **Report outputs** under **`pipelines/snt_worldpop_extract/reporting/outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`** (plus its **`.html`**), or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Synced scripts** under **`pipelines/snt_worldpop_extract/`** (`reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `WORLDPOP_DATASET_EXTRACT`**

* **`[COUNTRY_CODE]_worldpop_population.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

The rasters are not published.

> **Notes for the Data Analyst:**
>
> - **`YEAR`**: the extraction year, stored as a **string** (e.g. `"2020"`), not an integer.
> - **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**: copied from the properties of **`[COUNTRY_CODE]_shapes.geojson`**. ADM2 zones with a null, empty or invalid geometry are dropped, so they have no row.
> - **`POPULATION`**: sum of the WorldPop constrained 100 m raster pixels inside the ADM2 zone, rounded to an integer. Null when no pixel falls inside the zone (logged as a warning).
> - **Grain:** ADM2 × YEAR, one row per valid ADM2 shape per processed year.
> - **Release:** the raster comes from the latest WorldPop release found at run time (e.g. `R2025A`). A cached raster is reused only if its file name, which includes the release, matches.
> - **Guarded execution:** a year whose download or aggregation fails is skipped with a warning, and the published table simply lacks it; the run still succeeds. With no year processed, nothing is published and the report does not run, but **`data/worldpop/[COUNTRY_CODE]_parameters.json`** is still overwritten.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that did not run from this pipeline version, with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means the report notebook was the pipeline's own.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_worldpop_extract/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
