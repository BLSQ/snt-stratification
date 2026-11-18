import time
from pathlib import Path

from openhexa.sdk import current_run, pipeline, workspace, parameter
from snt_lib.snt_pipeline_utils import (
    add_files_to_dataset,
    load_configuration_snt_from_dataset,
    validate_config,
    run_report_notebook,
    run_notebook,
    get_notebook_overrides,
    sync_pipeline_scripts,
    save_pipeline_parameters,
    check_outputs_generated,
)


@pipeline("snt_dhis2_quality_of_care")
@parameter(
    "data_action",
    name="Data action",
    help="Choose whether to use imputed data (outliers replaced) or removed data (outliers removed).",
    type=str,
    choices=["imputed", "removed"],
    default="imputed",
    required=True,
)
@parameter(
    "run_report_only",
    name="Run reporting only",
    help="Skip computations and execute only the reporting notebook.",
    type=bool,
    default=False,
    required=False,
)
@parameter(
    "use_custom_notebooks",
    name="Use custom notebooks",
    help=(
        "Run the edited notebooks in pipelines/snt_dhis2_quality_of_care/custom/ "
        "instead of this pipeline's own"
    ),
    type=bool,
    default=False,
    required=False,
)
def snt_dhis2_quality_of_care(
    data_action: str,
    run_report_only: bool,
    use_custom_notebooks: bool,
):
    """Compute quality-of-care indicators from outliers routine data.

    The pipeline reads the latest outliers output matching `data_action`
    (`imputed` or `removed`), computes district-year quality-of-care indicators,
    saves outputs, and runs the reporting notebook.
    """
    current_run.log_info("Starting SNT Quality of Care pipeline...")
    root_path = Path(workspace.files_path)
    pipeline_path = root_path / "pipelines" / "snt_dhis2_quality_of_care"
    data_path = root_path / "data" / "dhis2" / "quality_of_care"
    pipeline_path.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)

    # Copy this pipeline version's notebooks and utils to the workspace (ADR 0044); stops the run on failure.
    sync_pipeline_scripts(pipeline_name="snt_dhis2_quality_of_care", bundle_path=Path(__file__).parent)

    try:
        snt_config, snt_config_version = load_configuration_snt_from_dataset()
        validate_config(snt_config)
        country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    except Exception as e:
        current_run.log_error(f"Loading configuration failed: {e}")
        raise

    # Every notebook this pipeline may run; resolved before any runs, so a missing custom notebook
    # stops the run up front.
    notebook_overrides = get_notebook_overrides(
        nb_paths=[
            pipeline_path / "code" / "snt_dhis2_quality_of_care.ipynb",
            pipeline_path / "reporting" / "snt_dhis2_quality_of_care_report.ipynb",
        ],
        country_code=country_code,
        use_custom_notebooks=use_custom_notebooks,
    )

    nb_parameters = {
        "DATA_ACTION": data_action,
    }

    if not run_report_only:
        parameters_file = save_pipeline_parameters(
            pipeline_name="snt_dhis2_quality_of_care",
            parameters=nb_parameters,
            output_path=data_path,
            country_code=country_code,
            extra_metadata={
                "SNT_CONFIG_VERSION": snt_config_version.name,
                "SNT_CONFIG_VERSION_ID": snt_config_version.id,
                "NOTEBOOK_OVERRIDES": notebook_overrides,
            },
        )

        expected_outputs = [
            data_path / f"{country_code}_quality_of_care_district_year_{data_action}.parquet",
            data_path / f"{country_code}_quality_of_care_district_year_{data_action}.csv",
        ]

        run_start_ts = time.time()
        try:
            run_notebook(
                nb_path=pipeline_path / "code" / "snt_dhis2_quality_of_care.ipynb",
                out_nb_path=pipeline_path / "papermill_outputs",
                kernel_name="ir",
                parameters=nb_parameters,
                error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
                country_code=country_code,
                use_custom_notebooks=use_custom_notebooks,
            )
        except Exception as e:
            current_run.log_error(f"Running notebook failed: {e}")
            raise

        check_outputs_generated(file_paths=expected_outputs, run_start_ts=run_start_ts)

        files_to_dataset = [*expected_outputs, parameters_file]
        try:
            add_files_to_dataset(
                dataset_id=snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_QUALITY_OF_CARE"],
                country_code=country_code,
                file_paths=files_to_dataset,
            )
        except Exception as e:
            current_run.log_error(f"Adding files to dataset failed: {e}")
            raise
    else:
        current_run.log_info("Skipping computations, running only reporting notebook.")

    try:
        run_report_notebook(
            nb_file=pipeline_path / "reporting" / "snt_dhis2_quality_of_care_report.ipynb",
            nb_output_path=pipeline_path / "reporting" / "outputs",
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Reporting notebook failed: {e}")
        raise

    current_run.log_info("Quality of Care pipeline finished successfully.")


if __name__ == "__main__":
    snt_dhis2_quality_of_care()
