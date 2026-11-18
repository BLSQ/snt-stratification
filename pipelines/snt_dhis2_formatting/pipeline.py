from pathlib import Path

from openhexa.sdk import current_run, parameter, pipeline, workspace
from snt_lib.snt_pipeline_utils import (
    add_files_to_dataset,
    dataset_file_exists,
    get_notebook_overrides,
    load_configuration_snt_from_dataset,
    run_notebook,
    run_report_notebook,
    save_pipeline_parameters,
    sync_pipeline_scripts,
    validate_config,
)

# ticket:
# https://bluesquare.atlassian.net/browse/SNT25-659


@pipeline("snt_dhis2_formatting")
@parameter(
    "run_report_only",
    name="Run reporting only",
    help="This will only execute the reporting notebook",
    type=bool,
    default=False,
    required=False,
)
@parameter(
    "use_custom_notebooks",
    name="Use custom notebooks",
    help="Run the edited notebooks in pipelines/snt_dhis2_formatting/custom/ instead of this pipeline's own",
    type=bool,
    default=False,
    required=False,
)
def snt_dhis2_formatting(run_report_only: bool, use_custom_notebooks: bool):
    """Write your pipeline orchestration here.

    Pipeline functions should only call tasks and should never perform IO operations or
    expensive computations.
    """
    # set paths
    snt_root_path = Path(workspace.files_path)
    snt_pipeline_path = snt_root_path / "pipelines" / "snt_dhis2_formatting"
    snt_dhis2_formatted_path = snt_root_path / "data" / "dhis2" / "extracts_formatted"
    snt_dhis2_formatted_path.mkdir(parents=True, exist_ok=True)

    # Copy this pipeline version's notebooks and utils to the workspace (ADR 0044); stops the run on failure.
    sync_pipeline_scripts(pipeline_name="snt_dhis2_formatting", bundle_path=Path(__file__).parent)

    try:
        # Load configuration (needed for report and for main run)
        snt_config_dict, snt_config_version = load_configuration_snt_from_dataset()
        validate_config(snt_config_dict)
        country_code = snt_config_dict["SNT_CONFIG"].get("COUNTRY_CODE", None)
    except Exception as e:
        current_run.log_error(f"Error in loading configuration: {e}")
        raise

    # Every notebook this pipeline may run; resolved before any runs, so a missing custom notebook
    # stops the run up front.
    notebook_overrides = get_notebook_overrides(
        nb_paths=[
            snt_pipeline_path / "code" / "snt_dhis2_formatting_population.ipynb",
            snt_pipeline_path / "code" / "snt_dhis2_formatting_pyramid.ipynb",
            snt_pipeline_path / "code" / "snt_dhis2_formatting_reporting_rates.ipynb",
            snt_pipeline_path / "code" / "snt_dhis2_formatting_routine.ipynb",
            snt_pipeline_path / "code" / "snt_dhis2_formatting_shapes.ipynb",
            snt_pipeline_path / "reporting" / "snt_dhis2_formatting_report.ipynb",
        ],
        country_code=country_code,
        use_custom_notebooks=use_custom_notebooks,
    )

    if not run_report_only:
        # Shapes must be generated first because pyramid coordinate validation
        # uses the country geojson boundaries.
        dhis2_shapes_formatting(
            snt_root_path=snt_root_path,
            pipeline_root_path=snt_pipeline_path,
            snt_config=snt_config_dict,
            use_custom_notebooks=use_custom_notebooks,
        )

        dhis2_pyramid_formatting(
            snt_root_path=snt_root_path,
            pipeline_root_path=snt_pipeline_path,
            snt_config=snt_config_dict,
            use_custom_notebooks=use_custom_notebooks,
        )

        dhis2_analytics_formatting(
            snt_root_path=snt_root_path,
            pipeline_root_path=snt_pipeline_path,
            snt_config=snt_config_dict,
            use_custom_notebooks=use_custom_notebooks,
        )

        dhis2_population_formatting(
            snt_root_path=snt_root_path,
            pipeline_root_path=snt_pipeline_path,
            snt_config=snt_config_dict,
            use_custom_notebooks=use_custom_notebooks,
        )

        dhis2_reporting_rates_formatting(
            snt_root_path=snt_root_path,
            pipeline_root_path=snt_pipeline_path,
            snt_config=snt_config_dict,
            use_custom_notebooks=use_custom_notebooks,
        )

        try:
            parameters_file = save_pipeline_parameters(
                pipeline_name="snt_dhis2_formatting",
                parameters={"run_report_only": run_report_only, "use_custom_notebooks": use_custom_notebooks},
                output_path=snt_dhis2_formatted_path,
                country_code=country_code,
                extra_metadata={
                    "SNT_CONFIG_VERSION": snt_config_version.name,
                    "SNT_CONFIG_VERSION_ID": snt_config_version.id,
                    "NOTEBOOK_OVERRIDES": notebook_overrides,
                },
            )
        except Exception as e:
            current_run.log_error(f"Error in saving pipeline parameters: {e}")
            raise

        add_files_to_dataset(
            dataset_id=snt_config_dict["SNT_DATASET_IDENTIFIERS"].get("DHIS2_DATASET_FORMATTED", None),
            country_code=country_code,
            file_paths=[
                snt_dhis2_formatted_path / f"{country_code}_routine.parquet",
                snt_dhis2_formatted_path / f"{country_code}_routine.csv",
                snt_dhis2_formatted_path / f"{country_code}_population.parquet",
                snt_dhis2_formatted_path / f"{country_code}_population.csv",
                snt_dhis2_formatted_path / f"{country_code}_shapes.geojson",
                snt_dhis2_formatted_path / f"{country_code}_pyramid.parquet",
                snt_dhis2_formatted_path / f"{country_code}_pyramid.csv",
                snt_dhis2_formatted_path / f"{country_code}_reporting.parquet",
                snt_dhis2_formatted_path / f"{country_code}_reporting.csv",
                parameters_file,
            ],
        )

    try:
        run_report_notebook(
            nb_file=snt_pipeline_path / "reporting" / "snt_dhis2_formatting_report.ipynb",
            nb_output_path=snt_pipeline_path / "reporting" / "outputs",
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in running report notebook: {e}")
        raise


def dhis2_analytics_formatting(
    snt_root_path: Path,
    pipeline_root_path: Path,
    snt_config: dict,
    use_custom_notebooks: bool = False,
) -> None:
    """Format DHIS2 analytics data for SNT."""
    current_run.log_info("Formatting DHIS2 analytics data.")

    # set parameters for notebook
    nb_parameter = {
        "SNT_ROOT_PATH": str(snt_root_path),
    }

    # Check if the reporting rates data file exists
    country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    ds_id = snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_EXTRACTS"]
    if not dataset_file_exists(ds_id=ds_id, filename=f"{country_code}_dhis2_raw_analytics.parquet"):
        current_run.log_info("File analytics data not found, skipping formatting.")
        return

    try:
        run_notebook(
            nb_path=pipeline_root_path / "code" / "snt_dhis2_formatting_routine.ipynb",
            out_nb_path=pipeline_root_path / "papermill_outputs",
            parameters=nb_parameter,
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in formatting analytics data: {e}")
        raise


def dhis2_population_formatting(
    snt_root_path: Path,
    pipeline_root_path: Path,
    snt_config: dict,
    use_custom_notebooks: bool = False,
) -> None:
    """Format DHIS2 population data for SNT."""
    current_run.log_info("Formatting DHIS2 population data.")

    # set parameters for notebook
    nb_parameter = {
        "SNT_ROOT_PATH": snt_root_path.as_posix(),
    }

    # Check if the reporting rates data file exists
    country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    ds_id = snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_EXTRACTS"]
    if not dataset_file_exists(ds_id=ds_id, filename=f"{country_code}_dhis2_raw_population.parquet"):
        current_run.log_info("File population data not found, skipping formatting.")
        return

    try:
        run_notebook(
            nb_path=pipeline_root_path / "code" / "snt_dhis2_formatting_population.ipynb",
            out_nb_path=pipeline_root_path / "papermill_outputs",
            parameters=nb_parameter,
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in formatting population data: {e}")
        raise


def dhis2_shapes_formatting(
    snt_root_path: Path,
    pipeline_root_path: Path,
    snt_config: dict,
    use_custom_notebooks: bool = False,
) -> None:
    """Format DHIS2 shapes data for SNT."""
    current_run.log_info("Formatting DHIS2 shapes data.")

    # set parameters for notebook
    nb_parameter = {
        "SNT_ROOT_PATH": str(snt_root_path),
    }

    # Check if the reporting rates data file exists
    country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    ds_id = snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_EXTRACTS"]
    if not dataset_file_exists(ds_id=ds_id, filename=f"{country_code}_dhis2_raw_shapes.parquet"):
        current_run.log_info("File shapes data not found, skipping formatting.")
        return

    try:
        run_notebook(
            nb_path=pipeline_root_path / "code" / "snt_dhis2_formatting_shapes.ipynb",
            out_nb_path=pipeline_root_path / "papermill_outputs",
            parameters=nb_parameter,
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in formatting shapes data: {e}")
        raise


def dhis2_pyramid_formatting(
    snt_root_path: Path,
    pipeline_root_path: Path,
    snt_config: dict,
    use_custom_notebooks: bool = False,
) -> None:
    """Format DHIS2 pyramid data for SNT."""
    current_run.log_info("Formatting DHIS2 pyramid data.")

    # set parameters for notebook
    nb_parameter = {
        "SNT_ROOT_PATH": str(snt_root_path),
    }

    # Check if the reporting rates data file exists
    country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    ds_id = snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_EXTRACTS"]
    if not dataset_file_exists(ds_id=ds_id, filename=f"{country_code}_dhis2_raw_pyramid.parquet"):
        current_run.log_info("File pyramid data not found, skipping formatting.")
        return

    try:
        run_notebook(
            nb_path=pipeline_root_path / "code" / "snt_dhis2_formatting_pyramid.ipynb",
            out_nb_path=pipeline_root_path / "papermill_outputs",
            parameters=nb_parameter,
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in formatting pyramid data: {e}")
        raise


def dhis2_reporting_rates_formatting(
    snt_root_path: Path,
    pipeline_root_path: Path,
    snt_config: dict,
    use_custom_notebooks: bool = False,
) -> None:
    """Format DHIS2 reporting data for SNT."""
    current_run.log_info("Formatting DHIS2 reporting rates data.")

    # set parameters for notebook
    nb_parameter = {
        "SNT_ROOT_PATH": str(snt_root_path),
    }

    # Check if the reporting rates data file exists
    country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    ds_id = snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_EXTRACTS"]
    if not dataset_file_exists(ds_id=ds_id, filename=f"{country_code}_dhis2_raw_reporting.parquet"):
        current_run.log_info("File reporting rates data not found, skipping formatting.")
        return

    try:
        run_notebook(
            nb_path=pipeline_root_path / "code" / "snt_dhis2_formatting_reporting_rates.ipynb",
            out_nb_path=pipeline_root_path / "papermill_outputs",
            parameters=nb_parameter,
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Error in formatting reporting rates data: {e}")
        raise


if __name__ == "__main__":
    snt_dhis2_formatting()
