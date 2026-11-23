# SNT DHS Indicators Pipeline

The **SNT DHS Indicators** pipeline computes five families of indicators from DHS survey recodes — **bed nets**, **care seeking**, **under-5 mortality**, **malaria prevalence (RDT)** and **vaccination (DTP)**. Each family is estimated at **ADM1** (the DHS sampling level) and written as **ADM2**-level parquet and CSV tables, each ADM2 repeating its ADM1 value. All tables are published together to **`DHS_INDICATORS`**, and each family's reporting notebook is run.

## Parameters

None. `pipeline.py` defines no domain parameters. The standard flags are omitted per project conventions: **`use_custom_notebooks`** (what it changes is described in steps 1 and 3 below, [ADR 0044](../../docs/decisions/0044-self-sync-replaces-pull-scripts.md)) and the report-only flag, which in this pipeline is named **`run_reports_only`** (UI name "Run reportings only"), not `run_report_only`. Its behaviour is described below the steps.

## Functionality Overview

1. **Sync the R half (every run, report-only included):** Copy each **`code/*.ipynb`**, **`reporting/*.ipynb`** and **`utils/*.r`** of this pipeline version to **`pipelines/snt_dhs_indicators/`** in the workspace, when the workspace copy is missing or its sha256 differs. A replaced copy is first moved to **`archive/self_sync/<UTC stamp>/pipelines/snt_dhs_indicators/<path>`**, with a `[WARNING]` naming it. Nothing is deleted; **`custom/`**, and any **`*_[COUNTRY_CODE].ipynb`** variant that is not in this pipeline version, are never touched. If the sync fails, the run stops with an `[ERROR]`.
2. **Configuration:** Load and validate **`SNT_config.json`** and resolve **`COUNTRY_CODE`**.
3. **Choose each notebook (before any runs):** For each of the ten notebooks below (five computation, five report), run **`custom/<notebook>`** if **`use_custom_notebooks`** is on and the file exists, else **`<notebook stem>_[COUNTRY_CODE].ipynb`** beside the generic notebook if it exists, else the generic notebook. Each notebook that is not the generic one logs a `[WARNING]`. With **`use_custom_notebooks`** on and no file in **`pipelines/snt_dhs_indicators/custom/`** matching any of the ten names, the run stops with an `[ERROR]` before any notebook runs.
4. **Bed nets:** Run **`snt_dhs_bednets_computation.ipynb`** (**`HR`** + **`PR`** recodes), check that its four **`bednets/`** files were written during this run, then run **`snt_dhs_bednets_report.ipynb`**.
5. **Care seeking:** Run **`snt_dhs_careseeking_computation.ipynb`** (**`HR`** + **`KR`**), check its eight **`careseeking/`** files, then run **`snt_dhs_careseeking_report.ipynb`**.
6. **Mortality:** Run **`snt_dhs_mortality_computation.ipynb`** (**`HR`** + **`BR`**), check its two **`mortality/`** files, then run **`snt_dhs_mortality_report.ipynb`**.
7. **Prevalence:** Run **`snt_dhs_prevalence_computation.ipynb`** (**`HR`** + **`PR`**), check its two **`prevalence/`** files, then run **`snt_dhs_prevalence_report.ipynb`**.
8. **Vaccination:** Run **`snt_dhs_vaccination_computation.ipynb`** (**`HR`** + **`KR`**), check its eight **`vaccination/`** files, then run **`snt_dhs_vaccination_report.ipynb`**.
9. **Publish:** Save **`[COUNTRY_CODE]_parameters.json`** and upload the 24 indicator files plus the parameters file to **`DHS_INDICATORS`** via **`add_files_to_dataset`**, as one new dataset version.

Inside each computation notebook: load the ADM1/ADM2 pyramid from **`[COUNTRY_CODE]_shapes.geojson`**, unzip the latest **`SV`** zip of each recode it needs from **`data/dhs/raw/`**, stop if the two recodes are not the same survey version or if the DHS ADM1 names do not all match the DHIS2 **`ADM1_NAME`** values, then estimate the indicator per ADM1 with the survey design (cluster **`HV021`**/**`V021`**, strata **`HV023`**/**`V023`**, weight **`HV005`**/**`V005`** ÷ 1 000 000; mortality uses `DHS.rates::chmort()` per ADM1 instead, with jackknife confidence intervals over the 120 months before the interview) and join the estimate onto every ADM2 of the ADM1.

The families run in order, and a failure stops the run: a computation notebook error, or an expected file not written during this run, stops it before that family's report and before anything is published.

With **`run_reports_only`**, steps 4–8 run only their report notebooks (no computation, no output check), on the CSVs already in **`data/dhs/indicators/`**, and step 9 is skipped: no parameters file is written and no dataset version is created. Steps 1–3 still run.

## Inputs

* **DHS recode zips** in **`data/dhs/raw/`** on the workspace filesystem (required, placed there by hand): the latest-numbered **`*HR*SV.zip`** for every family, plus **`*PR*SV.zip`** (bed nets, prevalence), **`*KR*SV.zip`** (care seeking, vaccination) or **`*BR*SV.zip`** (mortality).
* **`[COUNTRY_CODE]_shapes.geojson`** on **`DHIS2_DATASET_FORMATTED`** (required; written by **`snt_dhis2_formatting`**): the ADM1/ADM2 pyramid, read by every computation and report notebook.
* **`data/dhs/indicators/<family>/[COUNTRY_CODE]_DHS_ADM2_*.csv`** on the workspace filesystem, read back by the report notebooks (written by the computation step of the same run, or of an earlier run with **`run_reports_only`**).
* **`SNT_config.json`** from the latest version of **`SNT_CONFIGURATION`** (required) for **`SNT_CONFIG.COUNTRY_CODE`** and **`SNT_DATASET_IDENTIFIERS`** (**`DHIS2_DATASET_FORMATTED`**, **`DHS_INDICATORS`**).
* **`pipelines/snt_dhs_indicators/custom/*.ipynb`** in the workspace (optional), used only when **`use_custom_notebooks`** is on.
* **`*_[COUNTRY_CODE].ipynb`** beside a generic notebook in the workspace (optional), used whenever present.

## Outputs

**Workspace filesystem**

All tables are under **`data/dhs/indicators/<family>/`**, named **`[COUNTRY_CODE]_DHS_ADM2_<INDICATOR>`**, each as **`.parquet`** and **`.csv`**:

* **`bednets/`**: **`PCT_ITN_ACCESS`**, **`PCT_ITN_USE`**
* **`careseeking/`**: **`PCT_PUBLIC_CARE`**, **`PCT_PRIVATE_CARE`**, **`PCT_NO_CARE`**, **`PCT_CARESEEKING_SAMPLE_AVERAGE`** (summary of the three)
* **`mortality/`**: **`U5MR_PERMIL`**
* **`prevalence/`**: **`PCT_U5_PREV_RDT`**
* **`vaccination/`**: **`PCT_DTP1`**, **`PCT_DTP2`**, **`PCT_DTP3`**, **`PCT_DROPOUT_DTP`**
* **`data/dhs/indicators/[COUNTRY_CODE]_parameters.json`**, full runs only, with **`RUN_REPORTS_ONLY`**, **`USE_CUSTOM_NOTEBOOKS`**, **`SNT_CONFIG_VERSION`** and **`SNT_CONFIG_VERSION_ID`** (the name and id of the **`SNT_CONFIGURATION`** version read), and **`NOTEBOOK_OVERRIDES`**
* **Unzipped recode files** in **`data/dhs/raw/`** (see the note on clean-up below)
* **Executed notebooks** under **`pipelines/snt_dhs_indicators/papermill_outputs/`**, named **`<stem>_OUTPUT_<timestamp>.ipynb`**, or **`<stem>_CUSTOM_OUTPUT_<timestamp>.ipynb`** for a custom notebook
* **Report outputs** under **`pipelines/snt_dhs_indicators/reporting/outputs/`**, named the same way, with their HTML, and the map and confidence-interval PNGs in its **`figures/`** subfolder. The reports plot at ADM1.
* **Synced scripts** under **`pipelines/snt_dhs_indicators/`** (`code/`, `reporting/`, `utils/`) and replaced copies under **`archive/self_sync/`** (step 1)

**Published to `DHS_INDICATORS`**

* The 12 tables above, each **`.parquet`** and **`.csv`** (24 files)
* **`[COUNTRY_CODE]_parameters.json`**

> **Notes for the Data Analyst:**
>
> - **Grain:** one row per **ADM2**, with **`ADM1_ID`**, **`ADM1_NAME`**, **`ADM2_ID`**, **`ADM2_NAME`** and **`YEAR`**. The values are **ADM1** estimates (DHS sampling level), repeated for every ADM2 of the ADM1. The **`ADM2`** in the file names is the level of the table, not of the estimate.
> - **`YEAR`**: the survey year, the latest **`HV007`** in the **`HR`** recode.
> - **`<INDICATOR>_SAMPLE_AVERAGE`**, **`<INDICATOR>_CI_LOWER_BOUND`**, **`<INDICATOR>_CI_UPPER_BOUND`**: survey-weighted mean and 95% confidence interval, as a percentage (0–100; bounds clipped to 0–100), in the bed nets, care seeking (per indicator), prevalence and DTP dose tables.
> - **`U5MR_PERMIL_*`**: under-5 mortality rate per 1 000 (the `U5MR` row of `chmort()`), same three columns; the lower bound is capped at 0.
> - **`PCT_CARESEEKING_SAMPLE_AVERAGE`** table: one column per care-seeking indicator (**`PCT_PUBLIC_CARE`**, **`PCT_PRIVATE_CARE`**, **`PCT_NO_CARE`**), sample averages only, no confidence intervals.
> - **`PCT_DROPOUT_DTP`** table: **`PCT_DROPOUT_DTP_1_2`**, **`PCT_DROPOUT_DTP_1_3`**, **`PCT_DROPOUT_DTP_2_3`**, the percentage drop between two doses, `(1 − later dose ÷ earlier dose) × 100`, from the sample averages.
> - **Indicator definitions:** numerators, denominators and survey-design choices are documented in the markdown cells of each computation notebook; treat those as the source of truth.
> - **Name matching:** each computation notebook stops if a DHS ADM1 name does not match a DHIS2 **`ADM1_NAME`** after formatting. For **COD**, the ADM1 names of the shapes are cleaned first, and the DHS name `MAI NDOMBE` is rewritten to `MAINDOMBE`.
> - **Recode clean-up:** before unzipping, each computation notebook deletes every file and folder in **`data/dhs/raw/`** that is not a **`.zip`**. Do not keep anything else there.
> - **`NOTEBOOK_OVERRIDES`**: one entry per notebook that is not the generic one (a country variant shipped with this version included), with **`NOTEBOOK`** (generic file name), **`SOURCE`** (`custom` or `country_variant`), **`PATH`** and **`SHA256`**. An empty list means every notebook was the generic one. Entries are resolved for all ten notebooks up front. A run with **`run_reports_only`** writes no parameters file, so its overrides appear only in the run log.
> - **Output check:** after each computation notebook, every expected file must have been written during this run; otherwise the run stops with an error naming the missing files, and nothing is published. Files of the families that already ran stay on the filesystem.
> - **Edited notebooks**: the sync overwrites any hand edit to a notebook in `code/` or `reporting/` (the edited copy is kept in **`archive/self_sync/`**). To run an edited notebook, put it in **`pipelines/snt_dhs_indicators/custom/`** under the same file name and switch on **`use_custom_notebooks`**. `utils/*.r` always comes from the pipeline version.
