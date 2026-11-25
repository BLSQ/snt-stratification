import time
from pathlib import Path

from openhexa.sdk import current_run, parameter, pipeline, workspace
from snt_lib.snt_pipeline_utils import (
    add_files_to_dataset,
    get_notebook_overrides,
    load_configuration_snt_from_dataset,
    push_data_to_db_table,
    run_notebook,
    run_report_notebook,
    save_pipeline_parameters,
    sync_pipeline_scripts,
    validate_config,
)


@pipeline("snt_dhis2_outliers_imputation_path")
@parameter(
    "deviation_mean",
    name="Number of SD around the mean",
    help="Number of standard deviations around the mean (PATH default: 10)",
    type=int,
    default=10,
    required=False,
)
@parameter(
    "push_db",
    name="Push outliers table to DB",
    help="Push outliers table to DB",
    type=bool,
    default=True,
    required=False,
)
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
    help=(
        "Run the edited notebooks in pipelines/snt_dhis2_outliers_imputation_path/custom/ "
        "instead of this pipeline's own"
    ),
    type=bool,
    default=False,
    required=False,
)
def snt_dhis2_outliers_imputation_path(
    deviation_mean: int,
    push_db: bool,
    run_report_only: bool,
    use_custom_notebooks: bool,
):
    """Outliers imputation pipeline for SNT DHIS2 data."""
    # Copy this pipeline version's notebooks and utils to the workspace (ADR 0044); stops the run on failure.
    sync_pipeline_scripts(
        pipeline_name="snt_dhis2_outliers_imputation_path", bundle_path=Path(__file__).parent
    )

    current_run.log_info("Starting SNT DHIS2 outliers imputation PATH method pipeline...")

    # Define paths
    root_path = Path(workspace.files_path)
    pipeline_path = root_path / "pipelines" / "snt_dhis2_outliers_imputation_path"
    data_path = root_path / "data" / "dhis2" / "outliers_imputation"

    pipeline_path.mkdir(parents=True, exist_ok=True)  # Ensure pipeline path exists
    data_path.mkdir(parents=True, exist_ok=True)  # Ensure data path exists
    current_run.log_info(f"Pipeline path: {pipeline_path}")
    current_run.log_info(f"Data path: {data_path}")

    # Load configuration
    try:
        snt_config, snt_config_version = load_configuration_snt_from_dataset()
        validate_config(snt_config)
        country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    except Exception as e:
        current_run.log_error(f"Failed to load and validate configuration: {e}")
        raise

    # Every notebook this pipeline may run; resolved before any runs, so a missing custom notebook
    # stops the run up front.
    notebook_overrides = get_notebook_overrides(
        nb_paths=[
            pipeline_path / "code" / "snt_dhis2_outliers_imputation_path.ipynb",
            pipeline_path / "reporting" / "snt_dhis2_outliers_imputation_path_report.ipynb",
        ],
        country_code=country_code,
        use_custom_notebooks=use_custom_notebooks,
    )

    if not run_report_only:
        input_params = {
            "ROOT_PATH": root_path.as_posix(),
            "DEVIATION_MEAN": deviation_mean,
        }
        expected_outputs = [
            data_path / f"{country_code}_routine_outliers_detected.parquet",
            data_path / f"{country_code}_routine_outliers_imputed.parquet",
            data_path / f"{country_code}_routine_outliers_removed.parquet",
        ]

        run_start_ts = time.time()
        try:
            run_notebook(
                nb_path=pipeline_path / "code" / "snt_dhis2_outliers_imputation_path.ipynb",
                out_nb_path=pipeline_path / "papermill_outputs",
                kernel_name="ir",
                parameters=input_params,
                error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
                country_code=country_code,
                use_custom_notebooks=use_custom_notebooks,
            )
        except Exception as e:
            current_run.log_error(f"Failed to run outliers imputation notebook: {e}")
            raise

        check_outputs_generated(file_paths=expected_outputs, run_start_ts=run_start_ts)

        try:
            parameters_file = save_pipeline_parameters(
                pipeline_name="snt_dhis2_outliers_imputation_path",
                parameters=input_params,
                output_path=data_path,
                country_code=country_code,
                extra_metadata={
                    "SNT_CONFIG_VERSION": snt_config_version.name,
                    "SNT_CONFIG_VERSION_ID": snt_config_version.id,
                    "NOTEBOOK_OVERRIDES": notebook_overrides,
                },
            )
        except Exception as e:
            current_run.log_error(f"Failed to save pipeline parameters: {e}")
            raise

        try:
            add_files_to_dataset(
                dataset_id=snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_OUTLIERS_IMPUTATION"],
                country_code=country_code,
                file_paths=[*expected_outputs, parameters_file],
            )
        except Exception as e:
            current_run.log_error(f"Failed to add files to dataset: {e}")
            raise

        # Create consolidated outliers DB table
        if push_db:
            try:
                push_data_to_db_table(
                    table_name="outliers_detected",
                    file_path=data_path / f"{country_code}_routine_outliers_detected.parquet",
                )
            except Exception as e:
                current_run.log_error(f"Failed to push data to DB table: {e}")
                raise

    else:
        current_run.log_info("Skipping outliers calculations, running only the reporting notebook.")

    try:
        run_report_notebook(
            nb_file=pipeline_path / "reporting" / "snt_dhis2_outliers_imputation_path_report.ipynb",
            nb_output_path=pipeline_path / "reporting" / "outputs",
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Failed to run reporting notebook: {e}")

    current_run.log_info("Pipeline finished successfully.")


def check_outputs_generated(file_paths: list[Path], run_start_ts: float) -> None:
    """Raise if any expected output was not written during the current run.

    Guards against publishing stale files: all outliers imputation pipelines write the same
    filenames, so a leftover file may come from a previous run of another method.

    Parameters
    ----------
    file_paths : list[Path]
        Output files the notebook is expected to produce.
    run_start_ts : float
        Timestamp taken just before the notebook ran; files modified earlier are stale.

    Raises
    ------
    RuntimeError
        If a file is missing or was last modified before ``run_start_ts``.
    """
    missing = [p.name for p in file_paths if not p.exists() or p.stat().st_mtime < run_start_ts]
    if missing:
        msg = f"Expected output files were not generated during this run: {', '.join(missing)}"
        current_run.log_error(msg)
        raise RuntimeError(msg)


if __name__ == "__main__":
    snt_dhis2_outliers_imputation_path()
