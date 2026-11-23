# SNT Map Extracts Pipeline

The **SNT Map Extracts** pipeline downloads Malaria Atlas Project (MAP) rasters for a fixed set of malaria and intervention indicators, computes per-**ADM2** medians and population-weighted medians for each year of the selected period, and publishes them as one wide table, **`[COUNTRY_CODE]_map_data.parquet`** / **`.csv`**, to **`SNT_MAP_EXTRACTS`**. It then runs the MAP reporting notebook.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 2 and 4 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

* **`year_start`** (Integer, Required):
  * **Name:** Year start
  * **Description:** First year of the extraction. Also the first year for which a WorldPop population raster is used for the population weighting. WorldPop rasters are available for 2015–2030: a year outside that range logs a warning at start, then stops the run when its population raster is downloaded (see **Guarded execution**).
  * **Default:** none.
* **`year_end`** (Integer, Required):
  * **Name:** Year end
  * **Description:** Last year of the extraction, and the year shown in the report's maps. Must be greater than or equal to **`year_start`**, otherwise the run fails before anything else runs, report-only included.
  * **Default:** none.

## Functionality Overview

1. **Validation (every run, report-only included):** Fail if **`year_start`** > **`year_end`**. Log a warning if either year is outside 2015–2030 (WorldPop availability); the run continues.
2. **Sync the R half (every run, report-only included):** Copy each **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version (it has no `code/` notebook) to **`pipelines/snt_map_extracts/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_map_extracts/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
3. **Configuration:** Load and validate **`SNT_config.json`** and read **`COUNTRY_CODE`**.
4. **Choose the report notebook (before it runs):** Run **`custom/snt_map_extracts_report.ipynb`** if **`use_custom_notebooks`** is on and the file exists, else **`snt_map_extracts_report_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. A notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no **`snt_map_extracts_report.ipynb`** in **`pipelines/snt_map_extracts/custom/`**, the run stops with an `[ERROR]` before any shape is loaded.
5. **Shapes (report-only included):** Load **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`** and drop organisation units with a null or empty geometry. The run fails if the file is missing or no shape is left.
6. **Parameters:** Save **`[COUNTRY_CODE]_parameters.json`** under **`data/map/`**.
7. **For each year from `year_start` to `year_end`:**
   1. **Population:** Use the first WorldPop raster found in the cache **`data/worldpop/rasters/`** matching **`[country_code]_pop_[YEAR]_*.tif`** (lowercase country code, any WorldPop release), or download it from WorldPop. The run fails if the download fails, including for a year outside 2015–2030. Write an ADM2 total-population table to **`data/map/aggregated_populations/`**.
   2. **Rasters:** For each indicator, take its latest MAP release (version) and download that release's raster for the target year, over the bounding box of the shapes, into **`data/map/raster_files/[COUNTRY_CODE]/`**; a raster already there is reused. Indicators can come from different releases. An indicator that fails to download, or whose latest release does not cover the year, is logged as an error and skipped.
   3. **Zonal statistics:** For each raster band (**`Data`**, **`LCI`**, **`UCI`**, or **`GRAY_INDEX`** for single-band rasters), compute the ADM2 median, plus the population-weighted median when a population raster is available. **`Data`** and **`GRAY_INDEX`** give the **`MEDIAN`** statistic. An error here is logged and skips the year.
   4. Write the long per-year table **`data/map/formatted/[COUNTRY_CODE]_map_data_[YEAR].parquet`** / **`.csv`**, one row per ADM2 × indicator × **`STATISTIC`** (**`MEDIAN`**, **`LCI`**, **`UCI`**). A year with no raster or no valid statistic writes nothing.
8. **SNT format:** Keep only the **`MEDIAN`** statistic and combine the per-year tables into one wide table, one row per ADM2 × **`YEAR`**, with a value column and a **`_POP_W`** column per indicator. Both columns of each indicator are multiplied by a factor fixed in the pipeline code (**`conversions`** in **`format_map_indicators`**) and rounded to 2 decimals (see **Units** below). The **`LCI`** / **`UCI`** rows stay in the per-year tables only. Write **`data/map/formatted_snt/[COUNTRY_CODE]_map_data.parquet`** / **`.csv`**. The run fails, before publishing or reporting, if no per-year table could be read, or if these files were not written during this run.
9. **Publish:** Upload **`[COUNTRY_CODE]_map_data.parquet`**, **`[COUNTRY_CODE]_map_data.csv`** and **`[COUNTRY_CODE]_parameters.json`** to **`SNT_MAP_EXTRACTS`** via **`add_files_to_dataset`**.
10. **Reporting:** Run **`snt_map_extracts_report.ipynb`** (or its custom or country version, chosen as in step 4). The run fails if the report fails.
    * The report reads **`[COUNTRY_CODE]_map_data.parquet`** and **`[COUNTRY_CODE]_parameters.json`** from the latest version of **`SNT_MAP_EXTRACTS`**, and the shapes from **`DHIS2_DATASET_FORMATTED`**.
    * For each indicator, it draws two ADM2 maps side by side for the **`YEAR_END`** of that published parameters file: the median and the population-weighted median, on a shared colour scale. An indicator with no value that year is not mapped.

With **`run_report_only`**, steps 6–9 are skipped: nothing is downloaded, computed or published, and no parameters file is written. Steps 1–5 and 10 still run, so a report-only run still needs **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`**, and its maps show the **`YEAR_END`** of the last published run, not the **`year_end`** entered.

## Inputs

* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** — required, report-only included; produced by **`snt_dhis2_formatting`**. Its **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`** properties become the table's key columns.
* **MAP rasters** downloaded from the Malaria Atlas Project WCS (**`https://data.malariaatlas.org/geoserver`**), or reused from **`data/map/raster_files/[COUNTRY_CODE]/`** — required per indicator; a missing indicator is skipped. Listing the MAP coverages is not guarded: if the service cannot be reached, the run fails.
* **WorldPop population rasters** (2015–2030) — cached under **`data/worldpop/rasters/`**, a cache shared with **`snt_worldpop_extract`** and **`snt_healthcare_access`**, or downloaded from WorldPop. A failed download stops the run.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required): **`SNT_CONFIG.COUNTRY_CODE`**, and under **`SNT_DATASET_IDENTIFIERS`**: **`DHIS2_DATASET_FORMATTED`** and **`SNT_MAP_EXTRACTS`**.
* **Report inputs:** **`[COUNTRY_CODE]_map_data.parquet`** and **`[COUNTRY_CODE]_parameters.json`** from the latest version of **`SNT_MAP_EXTRACTS`**.
* **`pipelines/snt_map_extracts/custom/snt_map_extracts_report.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`snt_map_extracts_report_[COUNTRY_CODE].ipynb`** beside the generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/map/formatted_snt/[COUNTRY_CODE]_map_data.parquet`** and **`.csv`** — the wide table
* **`data/map/formatted/[COUNTRY_CODE]_map_data_[YEAR].parquet`** and **`.csv`** — one long table per year (not published), with all three statistics (**`MEDIAN`**, **`LCI`**, **`UCI`**), each with its value (**`VALUE`**) and population-weighted value (**`POPULATION_WEIGHTED`**), plus **`METRIC_CATEGORY`**, **`METRIC_NAME`**, **`VERSION`** (MAP release) and **`YEAR`**
* **`data/map/aggregated_populations/[COUNTRY_CODE]_worldpop_population_[YEAR].parquet`** — ADM2 total population per year (not published, not used by the rest of the pipeline)
* **`data/map/[COUNTRY_CODE]_parameters.json`**, with **`YEAR_START`**, **`YEAR_END`**, **`RUN_REPORT_ONLY`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **Cached MAP rasters** under **`data/map/raster_files/[COUNTRY_CODE]/`**, named **`<coverage id>_[YEAR].tif`**, and **WorldPop rasters** under **`data/worldpop/rasters/`**
* **Report outputs** under **`pipelines/snt_map_extracts/reporting/outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`** (plus its **`.html`**), or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook; maps as **`figures/[COUNTRY_CODE]_map_[INDICATOR]_[YEAR].png`**
* **Synced scripts** under **`pipelines/snt_map_extracts/`** (`reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 2)

**Published to `SNT_MAP_EXTRACTS`**

* **`[COUNTRY_CODE]_map_data.parquet`**
* **`[COUNTRY_CODE]_map_data.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** ADM2 × **`YEAR`**, one row each, across all years of the period.
> - **Key columns:** **`YEAR`**, **`ADM1_NAME`**, **`ADM1_ID`**, **`ADM2_NAME`**, **`ADM2_ID`**.
> - **Statistic:** values are the **`MEDIAN`** statistic (from the **`Data`** / **`GRAY_INDEX`** band, the indicator's main estimate); MAP's credible-interval bounds (**`LCI`** / **`UCI`**) are not published, but remain available in the per-year tables under **`data/map/formatted/`**.
> - **Indicator columns:** **`PF_PARASITE_RATE`**, **`PF_INCIDENCE_RATE`**, **`PF_MORTALITY_RATE`**, **`INSECTICIDE_TREATED_NET_ACCESS`**, **`INSECTICIDE_TREATED_NET_USE_RATE`**, **`IRS_COVERAGE`**, **`ANTIMALARIAL_EFFECTIVE_TREATMENT`**, each followed by its **`_POP_W`** column. All fourteen columns are always present; an indicator that was skipped is empty.
>   - **`[INDICATOR]`**: median of the raster pixels covering the ADM2, weighted by the share of each pixel inside the ADM2.
>   - **`[INDICATOR]_POP_W`**: median of the same pixels, weighted by pixel coverage × WorldPop population (resampled onto the MAP grid; pixels without population weigh 0). Empty when the year's population raster has no CRS.
>   - Near borders, a MAP pixel (about 5 km) can extend into a neighbouring country. Those pixels have no WorldPop population in this country, so they affect **`[INDICATOR]`** but not **`[INDICATOR]_POP_W`**. For border ADM2s, prefer **`_POP_W`**.
> - **Units** (same for an indicator and its **`_POP_W`** column), from MAP's native values times a factor fixed in the pipeline code, rounded to 2 decimals:
>   - **`PF_PARASITE_RATE`**, **`INSECTICIDE_TREATED_NET_ACCESS`**, **`INSECTICIDE_TREATED_NET_USE_RATE`**, **`IRS_COVERAGE`**, **`ANTIMALARIAL_EFFECTIVE_TREATMENT`**: percentage (× 100).
>   - **`PF_INCIDENCE_RATE`**: cases per 1,000 people per year (× 1,000).
>   - **`PF_MORTALITY_RATE`**: deaths per 100,000 people per year (× 100,000).
>   - The per-year tables under **`data/map/formatted/`** keep MAP's native, unscaled values.
> - **MAP version:** not stored in the published table (it is in the per-year tables' **`VERSION`**). Indicators of the same year can come from different MAP releases.
> - **Guarded execution:**
>   - A MAP indicator that fails to download, or whose latest release lacks the year, is skipped with an error in the log; its columns stay empty.
>   - A year whose rasters cannot be downloaded or aggregated is skipped; its rows are missing from the table.
>   - A WorldPop raster with no CRS leaves the **`_POP_W`** columns empty for that year. A WorldPop download that fails, including for a year outside 2015–2030, or a cached raster that cannot be opened, stops the run.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means the report notebook was the generic one.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_map_extracts/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
