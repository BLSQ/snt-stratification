# SNT Seasonality Cases Pipeline

The **SNT Seasonality Cases** pipeline classifies each **ADM2** as seasonal or not for malaria cases, from **monthly** confirmed cases (**`CONF`**) in the formatted DHIS2 routine data, and gives the length and usual onset month of its high-transmission season. It publishes **`[COUNTRY_CODE]_cases_seasonality`** (one row per ADM2) to **`SNT_SEASONALITY_CASES`** and runs the case seasonality reporting notebook.

## Parameters

The standard flags **`run_report_only`** and **`use_custom_notebooks`** are omitted per project conventions; what `use_custom_notebooks` changes is described in steps 1 and 3 below ([ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)). The parameters below are used only by full runs. `pipeline.py` drops their **`get_`** prefix and injects them as **lowercase** notebook globals (an R11 exception, [BACKLOG PIPE-3](../../docs/BACKLOG.md#pipe-3)).

* **`get_minimum_month_block_size`** (Integer, Required):
  * **Name:** Minimum number of months per block
  * **Description:** Shortest seasonal block (in months) tested. Notebook global **`minimum_month_block_size`**.
  * **Choices:** `3`, `4`, `5`.
  * **Default:** `3`.

* **`get_maximum_month_block_size`** (Integer, Required):
  * **Name:** Maximum number of months per block
  * **Description:** Longest seasonal block (in months) tested; every block size from the minimum to the maximum is tested. Must not be smaller than the minimum, or the run fails. Notebook global **`maximum_month_block_size`**.
  * **Choices:** `3`, `4`, `5`.
  * **Default:** `5`.

* **`get_threshold_for_seasonality`** (Float, Required):
  * **Name:** Minimal proportion of cases for seasonality
  * **Description:** Share of the annual cases that the block starting in a month must hold for that month to be flagged as a season start (e.g. `0.6` = 60%). Must be between 0 and 1, or the run fails. Notebook global **`threshold_for_seasonality`**.
  * **Default:** `0.6`.

* **`get_threshold_proportion_seasonal_years`** (Float, Optional):
  * **Name:** Minimal proportion of seasonal years
  * **Description:** Share of years in which the same calendar month must be flagged as a season start for the ADM2 to be seasonal for that block size. Must be between 0 and 1, or the run fails. Notebook global **`threshold_proportion_seasonal_years`**.
  * **Default:** `0.5`.

* **`use_calendar_year_denominator`** (Boolean, Optional):
  * **Name:** Use calendar year as denominator
  * **Description:** Defines the "annual cases" a block is compared with.
    * `false`: the 12 months starting at the block's first month (forward-looking sliding window, WHO approach).
    * `true`: the calendar year (January–December) of the block's first month.
  * Notebook global **`use_calendar_year_denominator`**.
  * **Default:** `false`.

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_seasonality_cases/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_seasonality_cases/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the two notebooks below, run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_seasonality_cases/custom/`** matching either name, the run stops with an `[ERROR]` before any notebook runs.
4. **Validate parameters:** Fail the run if a value is negative, a block size is not an integer, a proportion is above 1, or the minimum block size is larger than the maximum.
5. **Computation:** Run **`snt_seasonality_cases.ipynb`**:
   1. Load **`[COUNTRY_CODE]_shapes.geojson`** and **`[COUNTRY_CODE]_routine.parquet`** from **`DHIS2_DATASET_FORMATTED`**.
   2. Sum **`CONF`** by **`ADM2_ID` × `YEAR` × `MONTH`**, and complete the grid of every ADM2 × every month from the first to the last month in the data.
   3. **Data checks**, each stopping the run with an error: fewer than **36** months in the range; more than **10%** of the ADM2-months missing overall; any ADM2 missing more than **20%** of the months.
   4. **Impute** the missing ADM2-months with a seasonal ARIMA per ADM2, and write the imputed table (only when something was imputed).
   5. **Flag season starts** (ADM2 × month, for each block size): the month is a start when the cases of the block starting there, divided by the annual cases (see **`use_calendar_year_denominator`**), reach **`threshold_for_seasonality`**. Written as **`[COUNTRY_CODE]_cases_row_seasonality`**.
   6. **Classify** (ADM2, for each block size): the ADM2 is seasonal when at least one calendar month is flagged as a start in a share of years reaching **`threshold_proportion_seasonal_years`**.
   7. **Summarise** to one row per ADM2 (see Notes) and write **`[COUNTRY_CODE]_cases_seasonality.parquet`** and **`.csv`**.
6. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** in **`data/seasonality_cases/`** and upload it with **`[COUNTRY_CODE]_cases_seasonality.parquet`** and **`.csv`** to **`SNT_SEASONALITY_CASES`** via **`add_files_to_dataset`**. A file missing from the filesystem is skipped with a warning.
7. **Reporting:** Run **`snt_seasonality_cases_report.ipynb`** (or its custom or country version, chosen as in step 3).

With **`run_report_only`**, steps 4–6 are skipped: nothing is computed or published. Steps 1–3 and 7 still run.

## Inputs

* **`[COUNTRY_CODE]_routine.parquet`** on **`DHIS2_DATASET_FORMATTED`** (required; the run fails without it). Columns used: **`ADM2_ID`**, **`YEAR`**, **`MONTH`**, **`CONF`**.
* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** (required), for the ADM1/ADM2 ids and names of the output; the report also uses it for maps.
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`COUNTRY_CODE`** and the dataset identifiers **`DHIS2_DATASET_FORMATTED`** and **`SNT_SEASONALITY_CASES`**.
* **`pipelines/snt_seasonality_cases/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

* **`data/seasonality_cases/[COUNTRY_CODE]_cases_seasonality.parquet`** and **`.csv`**
* **`data/seasonality_cases/[COUNTRY_CODE]_cases_row_seasonality.parquet`** and **`.csv`**: ADM2 × month imputed cases, forward block sums, proportions and start flags for each block size. Read by the report; not published.
* **`data/seasonality_cases/[COUNTRY_CODE]_parameters.json`**, with **`MINIMUM_MONTH_BLOCK_SIZE`**, **`MAXIMUM_MONTH_BLOCK_SIZE`**, **`THRESHOLD_FOR_SEASONALITY`**, **`THRESHOLD_PROPORTION_SEASONAL_YEARS`**, **`USE_CALENDAR_YEAR_DENOMINATOR`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**. The **`run_report_only`** and **`use_custom_notebooks`** flags are not recorded.
* **`pipelines/snt_seasonality_cases/intermediate_results/[COUNTRY_CODE]_cases_imputed.csv`**, only when missing months were imputed; a full run first deletes the previous one. Not published.
* **Executed notebooks** under **`pipelines/snt_seasonality_cases/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_seasonality_cases/reporting/outputs/`**, named the same way, with PNG figures in its **`figures/`** subfolder
* **Synced scripts** under **`pipelines/snt_seasonality_cases/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `SNT_SEASONALITY_CASES`**

* **`[COUNTRY_CODE]_cases_seasonality.parquet`** and **`.csv`**
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** one row per **ADM2**, over the whole period of the routine data; there is no **`YEAR`** column. Columns: the ADM1/ADM2 ids and names from the shapes (**`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`**), then the four below. An ADM2 in the shapes but not in the routine data gets a row with empty values.
> - **`SEASONALITY_CASES`**: `1` if the ADM2 is seasonal for at least one block size, else `0`.
> - **`SEASONAL_BLOCK_DURATION_CASES`**: the smallest block size (months) for which the ADM2 is seasonal; empty when not seasonal.
> - **`SEASONAL_BLOCK_START_MONTH_CASES`**: the month (1–12) most often flagged as a season start for that block size, counted over all years; ties go to the earliest month. Empty when not seasonal.
> - **`CASES_PROPORTION`**: the mean over years of the largest block sum starting in that year (for the selected block size) divided by that calendar year's total cases. The denominator is the calendar year whatever **`use_calendar_year_denominator`** says, and a block starting late in the year runs into the next one. Empty when not seasonal.
> - **Missing vs zero:** an ADM2-month counts as missing only when the routine data has no row for it; a row whose **`CONF`** values are all empty sums to `0`. Zero months are excluded from the ARIMA fit but stay `0` in the output.
> - **End of the series:** a month whose forward window runs past the last month of data (the last 11 months with the sliding window, the last block-size − 1 months with the calendar year) is not flagged and does not count towards the share of seasonal years.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the generic one. Entries are resolved for both notebooks up front.
> - **Guarded execution:** a failed data check (step 5.3) stops the run with an error; nothing is published and the report does not run. The parameters file is saved only after the notebook succeeds.
> - **Report-only runs** read **`[COUNTRY_CODE]_cases_seasonality.parquet`** and **`[COUNTRY_CODE]_cases_row_seasonality.parquet`** from **`data/seasonality_cases/`** in the workspace, not from the dataset, so they need a previous full run in the same workspace.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_seasonality_cases/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
