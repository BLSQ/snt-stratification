# SNT Healthcare Access Pipeline

The **SNT Healthcare Access** pipeline estimates, for each **ADM2**, the share of the population living within a **5 km straight-line buffer** of at least one health facility (**FOSA**, *formation sanitaire*). It overlays facility buffers on a WorldPop population raster for one year, sums total and covered population per ADM2, publishes **`[COUNTRY_CODE]_population_covered_health`** to **`SNT_HEALTHCARE_ACCESS`**, and runs the healthcare access reporting notebook.

## Parameters

* **`input_fosa_file`** (File, Optional):
  * **Name:** Optional FOrmation SAnitaire (FOSA) location file (.csv)
  * **Description:** Health facility coordinates to use instead of the DHIS2 pyramid. The notebook uses it only if it exists, has a **`.csv`** extension, is readable, and has numeric **`LATITUDE`** and **`LONGITUDE`** columns (names matched case-insensitively); otherwise it logs the reason and uses **`[COUNTRY_CODE]_pyramid.parquet`** from **`DHIS2_DATASET_FORMATTED`**.
  * **Default:** `None` (use the DHIS2 pyramid).

* **`wpop_year`** (Integer, Required):
  * **Name:** Year
  * **Description:** Reference year of the WorldPop population raster. Must be between 2015 and 2030; the run stops otherwise. Required even with **`run_report_only`**, although the report does not use it (see step 10).
  * **Default:** none.

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 2 and 4 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

## Functionality Overview

1. **Validate the parameters:** If **`input_fosa_file`** is given and does not exist or is not a **`.csv`**, log a warning and continue (the notebook then falls back to the DHIS2 pyramid). Stop the run if **`wpop_year`** is outside 2015–2030.
2. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_healthcare_access/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_healthcare_access/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
3. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
4. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_healthcare_access/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
5. **Check the shapes:** Load **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`**, drop units with missing or empty geometry, and stop the run if none remain.
6. **Save the parameters:** Write **`[COUNTRY_CODE]_parameters.json`** to **`data/healthcare_access/`**, before the computation runs.
7. **Population raster:** Use **`data/worldpop/rasters/[country_code]_pop_[wpop_year]_CN_100m_*.tif`** (lowercase country code) if present, else download it from WorldPop into that folder. Stop the run if it cannot be retrieved.
8. **Compute:** Run **`snt_healthcare_access.ipynb`** with **`INPUT_FOSA_FILE`** (the upload's path, or `None`) and **`WORLDPOP_YEAR`**. The notebook:
   * loads the ADM2 polygons and the facility points (fallback rules under **`input_fosa_file`**), drops facilities with a **`CLOSED_DATE`** (when the column exists), without coordinates, or outside the country;
   * for **NER** only, also drops facilities whose name contains "clôture"/"fermé", and, if **`data/dhis2/extracts_raw/organisation_unit_groups/NER_organisation_unit_groups.parquet`** exists, those in the "Structures Clôturées" group;
   * draws a 5 000 m buffer around each facility in **EPSG:32630** and dissolves them into one coverage area;
   * marks the raster cells inside it, multiplies by population, and sums total and covered population per **`ADM2_ID`** (zonal sums over the ADM2 polygons rasterized on the population grid);
   * writes **`[COUNTRY_CODE]_population_covered_health.parquet`** and **`.csv`**.
9. **Publish:** Upload the parquet, the CSV and the parameters file to **`SNT_HEALTHCARE_ACCESS`** via **`add_files_to_dataset`**; the run fails if that dataset identifier is missing from the configuration.
10. **Reporting:** Run **`snt_healthcare_access_report.ipynb`** (or its custom or country version, chosen as in step 4). It receives no parameters: it reads the raster of **the year before the current calendar year** (its default **`WORLDPOP_YEAR`**), not **`wpop_year`**, and labels its maps with that year. It fails if that raster is not in **`data/worldpop/rasters/`**.

With **`run_report_only`**, steps 6–9 are skipped: nothing is computed, saved or published. Steps 1–5 and 10 still run, and the report reads the files of the last full run.

## Inputs

* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** (required; written by **`snt_dhis2_formatting`**): the ADM2 polygons, read by `pipeline.py`, the computation and the report notebook.
* **Facility coordinates** (required, one of): the **`input_fosa_file`** upload, or **`[COUNTRY_CODE]_pyramid.parquet`** on **`DHIS2_DATASET_FORMATTED`** (columns **`LATITUDE`**, **`LONGITUDE`**, and **`CLOSED_DATE`** if present).
* **`data/worldpop/rasters/[country_code]_pop_[YEAR]_CN_100m_*.tif`** on the workspace filesystem: a raster cache shared with **`snt_worldpop_extract`** and **`snt_map_extracts`**. Downloaded from WorldPop when missing (computation only; the report never downloads).
* **`data/dhis2/extracts_raw/organisation_unit_groups/NER_organisation_unit_groups.parquet`** on the workspace filesystem (optional, **NER** only).
* **`[COUNTRY_CODE]_parameters.json`** on **`SNT_HEALTHCARE_ACCESS`** (optional), read by the report to label the facility source ("DHIS2" when it has no **`INPUT_FOSA_FILE`**).
* **`data/healthcare_access/[COUNTRY_CODE]_population_covered_health.parquet`** and the two **`.gpkg`** files under **`pipelines/snt_healthcare_access/intermediate_results/`** on the workspace filesystem, read by the report.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`SNT_CONFIG.COUNTRY_CODE`**, **`SNT_CONFIG.ANALYTICS_ORG_UNITS_LEVEL`** (NER filters only) and **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`SNT_HEALTHCARE_ACCESS`**).
* **`pipelines/snt_healthcare_access/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/healthcare_access/[COUNTRY_CODE]_population_covered_health.parquet`** and **`.csv`**
* **`data/healthcare_access/[COUNTRY_CODE]_parameters.json`**, with **`INPUT_FOSA_FILE`**, **`WPOP_YEAR`**, **`RUN_REPORT_ONLY`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **`data/worldpop/rasters/[country_code]_pop_[wpop_year]_CN_100m_*.tif`**, when downloaded (step 7)
* **Intermediate files** under **`pipelines/snt_healthcare_access/intermediate_results/`**: **`[COUNTRY_CODE]_FOSA_filtered.gpkg`** (facility points kept), **`[COUNTRY_CODE]_health_coverage_buffers.gpkg`** (dissolved buffers) and **`.pop_covered_healthcare.tif`** (covered population raster); not published
* **Executed notebooks** under **`pipelines/snt_healthcare_access/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_healthcare_access/reporting/outputs/`**, named the same way, with the map PNGs in its **`figures/`** subfolder
* **Synced scripts** under **`pipelines/snt_healthcare_access/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 2)

**Published to `SNT_HEALTHCARE_ACCESS`**

* **`[COUNTRY_CODE]_population_covered_health.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** one row per **ADM2**, for the single WorldPop year **`wpop_year`**. Columns: **`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`** (from the shapes), **`POP_TOTAL`**, **`POP_COVERED`**, **`PCT_HEALTH_ACCESS`**. There is **no `YEAR` column**: the year is recorded only as **`WPOP_YEAR`** in **`[COUNTRY_CODE]_parameters.json`**.
> - **`POP_TOTAL`** / **`POP_COVERED`**: sums of the raster cells of the ADM2, all cells / cells inside the coverage area. **`PCT_HEALTH_ACCESS`** = **`POP_COVERED`** × 100 ÷ **`POP_TOTAL`** (0–100).
> - **Spatial resolution:** results inherit the grid of the WorldPop raster (100 m). Each cell is assigned whole to one ADM2 and counted as covered or not, by `terra::rasterize()` on that grid.
> - **Radius:** a Euclidean 5 km buffer, not a travel time. It is drawn in **EPSG:32630** (UTM zone 30N) for every country, so the real radius on the ground is smaller than 5 km away from 3°W ([PIPE-9](../../docs/BACKLOG.md#pipe-9)).
> - **`INPUT_FOSA_FILE`** in the parameters file is the text form of the uploaded `File` object, not its path, or `null` when no file was given. It records what was selected, not what was used: the notebook may have fallen back to the DHIS2 pyramid.
> - **Parameters file timing:** it is written before the computation runs, so a failed run leaves an updated **`[COUNTRY_CODE]_parameters.json`** on the filesystem that does not match the data beside it. Only a successful run publishes it.
> - **Report year:** the report maps the raster of the year before the current calendar year, whatever **`wpop_year`** was (step 10).
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the generic one. Entries are resolved for both notebooks up front.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_healthcare_access/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
