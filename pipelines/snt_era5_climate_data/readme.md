# SNT ERA5 Climate Data Pipeline

The **SNT ERA5 Climate Data** pipeline downloads **ERA5-Land** reanalysis from the Copernicus Climate Data Store (CDS) over the country's bounding box, aggregates it to **ADM2** zones of the formatted DHIS2 shapes, and writes daily, weekly, epidemic-week and monthly tables. It publishes **only the monthly table** (one per variable, currently **`total_precipitation`** only) and its parameters file to **`ERA5_DATASET_CLIMATE`**, and runs the ERA5 reporting notebook.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)).

* **`start_date`** (String, Required):
  * **Name:** Start date
  * **Description:** Start of the extraction window, **`YYYY-MM-DD`**; another format stops the run. Moved to the **first day of its month** before syncing.
  * **Default:** `2018-01-01`.
* **`end_date`** (String, Optional):
  * **Name:** End date
  * **Description:** End of the extraction window, **`YYYY-MM-DD`**; another format stops the run. Empty: the last day of the month before the current UTC month. Given: kept if it is the last day of its month and before today, otherwise moved to the **last day of the previous month** (`to_last_day_previous_month`).
  * **Default:** none.
* **`cds_connection`** (CustomConnection, Required):
  * **Name:** Climate data store
  * **Description:** OpenHEXA custom connection holding the CDS API key, read from its **`api_key`** field, else **`key`**; neither stops the run. Used for **`https://cds.climate.copernicus.eu/api`**.
* **`force_resync`** (Boolean, Optional):
  * **Name:** Force resync
  * **Description:** On: delete the variable's zarr store under **`data/era5/raw/`** and download the whole window again. Off: keep the store and request only the dates missing from it (see **Guarded execution** for a caveat).
  * **Default:** `True`.

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`reporting/*.ipynb`** of this pipeline version (it has no `code/` notebook and no `utils/*.r`) to **`pipelines/snt_era5_climate_data/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_era5_climate_data/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose the report notebook (before it runs):** Run **`custom/snt_era5_climate_data_report.ipynb`** if **`use_custom_notebooks`** is on and the file exists, else **`snt_era5_climate_data_report_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. A notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no **`snt_era5_climate_data_report.ipynb`** in **`pipelines/snt_era5_climate_data/custom/`**, the run stops with an `[ERROR]` before anything is downloaded or the report runs.
4. **Dates and boundaries:** Check the date formats; load **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`** and derive the CDS request **`area`** (north, west, south, east) from its extent, padded by 0.1° and rounded outward to whole degrees. Normalise **`start_date`** and **`end_date`** (see Parameters).
5. **Download (per variable in `ERA5_VARIABLES`, currently only `total_precipitation`):** Unless **`force_resync`** is off, delete **`data/era5/raw/<variable>.zarr`**. Request the missing dates from the CDS dataset **`reanalysis-era5-land`** in batches of 50 months, and append them to the zarr store. Then check the store: it must hold the variable, a time axis, and at least one non-null value in its first 48 time steps; otherwise the run stops.
6. **Daily ADM2 table:** Reproject the shapes to EPSG:4326, drop null or empty geometries, and mask the ERA5 grid by **`ADM2_ID`**; an ADM2 that covers no ERA5 pixel is dropped with a warning. Per ADM2 and time step take the spatial **mean**, **min** and **max**, then total them per day (accumulated variables such as precipitation) or average them per day (other variables). Precipitation is converted from metres to **millimetres** (× 1,000). Add the DHIS2 week, month (`YYYYMM`) and epidemic week of each day; rows with a null mean are dropped.
7. **Roll-ups:** Group the daily rows by ADM2 × week, ADM2 × epidemic week and ADM2 × month; precipitation is **summed** over the days, other variables are averaged. The run stops if the monthly table has a null **`MEAN`**.
8. **Write:** **`[COUNTRY_CODE]_<variable>_daily.parquet`**, **`_weekly.parquet`**, **`_epi_weekly.parquet`** and **`_monthly.parquet`** under **`data/era5/aggregate/<variable>/`**.
9. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** to **`data/era5/aggregate/`**, then upload each variable's **`_monthly.parquet`** and the parameters file to **`ERA5_DATASET_CLIMATE`** via **`add_files_to_dataset`**. The daily, weekly and epidemic-week tables are not published.
10. **Reporting:** Run **`snt_era5_climate_data_report.ipynb`** (or its custom or country version, chosen as in step 3).

With **`run_report_only`**, steps 4–9 are skipped: the dates are not checked, nothing is downloaded, written to `data/` or published, and no parameters file is written. Steps 1–3 and 10 still run.

## Inputs

* **`[COUNTRY_CODE]_shapes.geojson`** from the latest version of **`DHIS2_DATASET_FORMATTED`** (required for a full run; missing, the run stops): the ADM2 zones, keyed on **`ADM2_ID`**, and the request bounding box. **`snt_dhis2_formatting`** must have run first.
* **ERA5-Land** hourly data from the Copernicus CDS, through **`cds_connection`** (required for a full run).
* **`data/era5/raw/<variable>.zarr`** on the workspace filesystem (optional): the store from earlier runs, reused only when **`force_resync`** is off.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`COUNTRY_CODE`** and **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`ERA5_DATASET_CLIMATE`**).
* **Report inputs** (report-only included): every **`data/era5/aggregate/<variable>/[COUNTRY_CODE]_<variable>_monthly.parquet`** on the **workspace filesystem**, not the dataset (none found stops the report), and **`[COUNTRY_CODE]_shapes.geojson`** from **`DHIS2_DATASET_FORMATTED`** for the maps (missing, the maps are skipped with a warning).
* **`pipelines/snt_era5_climate_data/custom/snt_era5_climate_data_report.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`snt_era5_climate_data_report_[COUNTRY_CODE].ipynb`** beside the generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/era5/raw/<variable>.zarr`**: the downloaded ERA5-Land grid over the bounding box; not published
* **`data/era5/aggregate/<variable>/[COUNTRY_CODE]_<variable>_daily.parquet`**: **`ADM2_ID`**, **`DATE`**, **`MEAN`**, **`MIN`**, **`MAX`**, **`WEEK`**, **`PERIOD`** (`YYYYMM`), **`EPI_WEEK`**; not published
* **`data/era5/aggregate/<variable>/[COUNTRY_CODE]_<variable>_weekly.parquet`**: **`ADM2_ID`**, **`WEEK`**, **`MEAN`**, **`MIN`**, **`MAX`**; not published
* **`data/era5/aggregate/<variable>/[COUNTRY_CODE]_<variable>_epi_weekly.parquet`**: **`ADM2_ID`**, **`EPI_WEEK`**, **`MEAN`**, **`MIN`**, **`MAX`**; not published
* **`data/era5/aggregate/<variable>/[COUNTRY_CODE]_<variable>_monthly.parquet`**: **`ADM2_ID`**, **`PERIOD`** (`YYYYMM`), **`MEAN`**, **`MIN`**, **`MAX`**, **`YEAR`**, **`MONTH`**
* **`data/era5/aggregate/[COUNTRY_CODE]_parameters.json`**, with **`PIPELINE_NAME`** (`snt_era5_aggregate`, see the notes), **`RUN_REPORT_ONLY`**, **`START_DATE`** and **`END_DATE`** (as normalised), **`VARIABLES`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **Report outputs** under **`pipelines/snt_era5_climate_data/reporting/outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`** (plus its **`.html`**), or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook; plots as **`[COUNTRY_CODE]_era5_precipitation_monthly.png`** and **`[COUNTRY_CODE]_era5_precipitation_annual_grid.png`** (and **`[COUNTRY_CODE]_era5_temperature_monthly.png`** if a **`2m_temperature`** monthly file exists)
* **Synced scripts** under **`pipelines/snt_era5_climate_data/`** (`reporting/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `ERA5_DATASET_CLIMATE`**

* **`[COUNTRY_CODE]_total_precipitation_monthly.parquet`** (one **`[COUNTRY_CODE]_<variable>_monthly.parquet`** per variable in **`ERA5_VARIABLES`**)
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** ADM2 × month for the published table (**`PERIOD`**, **`YEAR`**, **`MONTH`**); ADM2 × day, week and epidemic week for the on-disk tables. An ADM2 with no ERA5 pixel has no row.
> - **`MEAN`** (precipitation): the ADM2's average precipitation in **mm**, totalled over the period. **`MIN`** / **`MAX`**: the same totals taken over the smallest / largest ERA5 pixel value of the ADM2 at each time step, so they are not the total of any single pixel.
> - **`PERIOD`**: `YYYYMM` string; **`YEAR`** and **`MONTH`**: integers derived from it.
> - **`WEEK`** / **`EPI_WEEK`**: DHIS2 week strings from the toolbox's `to_dhis2_week`, with `WeekType.WEEK` and `WeekType.WEEK_THURSDAY` respectively.
> - **Variables:** only **`total_precipitation`** is processed. **`2m_temperature`** and **`2m_dewpoint_temperature`** are commented out in **`ERA5_VARIABLES`** in **`pipeline.py`**; no temperature output exists.
> - **`PIPELINE_NAME`** in the parameters file reads **`snt_era5_aggregate`**, the name of the pipeline this one replaced, not **`snt_era5_climate_data`**.
> - **Guarded execution:** the run stops, rather than skipping, on a missing shapes file, a missing CDS key, an empty zarr store, an empty daily table or a null monthly **`MEAN`**. With **`force_resync`** off, the download loop ends at the first 50-month batch that has no missing date, so months in later batches are not requested in that run.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means the report notebook was the generic one.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_era5_climate_data/custom/`** under the same file name and switch on **`use_custom_notebooks`**.
