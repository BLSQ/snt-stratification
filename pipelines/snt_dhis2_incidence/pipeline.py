import time
from pathlib import Path
from openhexa.sdk import current_run, parameter, pipeline, workspace, File
from snt_lib.snt_pipeline_utils import (
    get_notebook_overrides,
    sync_pipeline_scripts,
    run_notebook,
    add_files_to_dataset,
    load_configuration_snt_from_dataset,
    run_report_notebook,
    validate_config,
    save_pipeline_parameters,
    check_outputs_generated,
    dataset_file_exists,
)


@pipeline("snt_dhis2_incidence")
@parameter(
    "n1_method",
    name="Method for N1 calculations",
    help="Calculate N1 using `PRES` or `SUSP-TEST`",
    choices=["PRES", "SUSP-TEST"],
    type=str,
    default="PRES",
    required=True,
)
@parameter(
    "routine_data_choice",
    name="Routine data to use",
    help="Which routine data to use for the analysis. Options: 'raw' data is simply formatted and aligned;"
    "'raw_without_outliers' is the raw data after outliers removed;"
    " 'imputed' contains imputed values after outliers removal",
    choices=["raw", "raw_without_outliers", "imputed"],
    type=str,
    default="imputed",
    required=True,
)
@parameter(
    "population_selection",
    name="Population data selection",
    help="Select the source of population data for the analysis. ",
    choices=["DHIS2", "User-provided", "Population-transformed"],
    type=str,
    default="DHIS2",
    required=True,
)
@parameter(
    "disaggregation_selection",
    name="Analyze by Population Group (only if available)",
    help="Select the population group. "
    "Important: both the indicators and the population data must be available for the selected group! "
    "Else, the pipeline will fail.",
    multiple=False,
    choices=["Children Under 5 Years Old", "Pregnant Women"],
    type=str,
    default=None,
    required=False,
)
@parameter(
    "careseeking_file_path",
    name="Care seeking behaviour (CSB) data file (.csv)",
    help="Path to the care seeking behaviour data file to be used for the analysis. If none provided,"
    " the pipeline will attempt to load DHS data. If this is also not available, the analysis will proceed "
    "without CSB data, hence skipping the last step of calculating 'INCIDENCE_ADJ_CARESEEKING'.",
    type=File,
    required=False,
    default=None,
)
@parameter(
    "run_report_only",
    name="Run Report only",
    help="This will only execute the reporting notebook",
    type=bool,
    default=False,
    required=False,
)
@parameter(
    "use_custom_notebooks",
    name="Use custom notebooks",
    help="Run the edited notebooks in pipelines/snt_dhis2_incidence/custom/ instead of this pipeline's own",
    type=bool,
    default=False,
    required=False,
)
def snt_dhis2_incidence(
    n1_method: str,
    routine_data_choice: str,
    population_selection: str,
    disaggregation_selection: str,
    careseeking_file_path: File,
    run_report_only: bool,
    use_custom_notebooks: bool,
):
    """Pipeline entry point for running the SNT DHIS2 incidence notebook with specified parameters."""
    # Copy this pipeline version's notebooks and utils to the workspace (ADR 0044); stops the run on failure.
    sync_pipeline_scripts(pipeline_name="snt_dhis2_incidence", bundle_path=Path(__file__).parent)

    current_run.log_info("Starting SNT DHIS2 Incidence pipeline...")
    root_path = Path(workspace.files_path)
    pipeline_path = root_path / "pipelines" / "snt_dhis2_incidence"
    data_path = root_path / "data" / "dhis2" / "incidence"
    pipeline_path.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)

    try:
        # Load configuration
        snt_config, snt_config_version = load_configuration_snt_from_dataset()
        validate_config(snt_config)
        country_code = snt_config["SNT_CONFIG"]["COUNTRY_CODE"]
    except Exception as e:
        current_run.log_error(f"An error occurred: {e}")
        raise

    # Every notebook this pipeline may run; resolved before any runs, so a missing custom notebook
    # stops the run up front.
    notebook_overrides = get_notebook_overrides(
        nb_paths=[
            pipeline_path / "code" / "snt_dhis2_incidence.ipynb",
            pipeline_path / "reporting" / "snt_dhis2_incidence_report.ipynb",
        ],
        country_code=country_code,
        use_custom_notebooks=use_custom_notebooks,
    )

    if not run_report_only:
        # check if it exists otherwise fail
        try:
            dataset_id = resolve_population_dataset(snt_config, population_selection)
            check_population_file_exists(country_code, dataset_id)
        except Exception as e:
            msg = f"Population not available in {population_selection}: {e}."
            current_run.log_error(msg)
            raise FileNotFoundError(msg) from e

        # Helper to format the parameters for injection
        mapping_dictionary = {
            "Children Under 5 Years Old": "UNDER_5",
            "Pregnant Women": "PREGNANT_WOMAN",
        }

        notebook_params = {
            "N1_METHOD": n1_method,
            "ROUTINE_DATA_CHOICE": routine_data_choice,
            "POPULATION_DATASET_ID": dataset_id,
            "DISAGGREGATION_SELECTION": (
                mapping_dictionary.get(disaggregation_selection) if disaggregation_selection else None
            ),
            "CARESEEKING_FILE_PATH": careseeking_file_path.path if careseeking_file_path else None,
            "ROOT_PATH": root_path.as_posix(),
        }

        try:
            params_file = save_pipeline_parameters(
                pipeline_name="snt_dhis2_incidence",
                parameters=notebook_params,
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

        current_run.log_info(f"Saved pipeline parameters to {params_file}")

        expected_outputs = [
            data_path / f"{country_code}_incidence.parquet",
            data_path / f"{country_code}_incidence.csv",
        ]

        run_start_ts = time.time()
        try:
            run_notebook(
                nb_path=pipeline_path / "code" / "snt_dhis2_incidence.ipynb",
                out_nb_path=pipeline_path / "papermill_outputs",
                parameters=notebook_params,
                error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
                country_code=country_code,
                use_custom_notebooks=use_custom_notebooks,
            )
        except Exception as e:
            current_run.log_error(f"Notebook execution failed: {e}")
            raise

        check_outputs_generated(file_paths=expected_outputs, run_start_ts=run_start_ts)

        add_files_to_dataset(
            dataset_id=snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_INCIDENCE"],
            country_code=country_code,
            file_paths=[
                *expected_outputs,
                params_file,
            ],
        )

    else:
        current_run.log_info("Skipping incidence calculations, running only the reporting.")

    try:
        run_report_notebook(
            nb_file=pipeline_path / "reporting" / "snt_dhis2_incidence_report.ipynb",
            nb_output_path=pipeline_path / "reporting" / "outputs",
            error_label_severity_map={"[ERROR]": "error", "[WARNING]": "warning"},
            country_code=country_code,
            use_custom_notebooks=use_custom_notebooks,
        )
    except Exception as e:
        current_run.log_error(f"Report notebook execution failed: {e}")

    current_run.log_info("Pipeline finished!")


def check_population_file_exists(country_code: str, population_dataset_id: str) -> None:
    """Check that {country_code}_population.parquet exists in the latest version of the given dataset.

    Args:
        country_code (str): The country code used as the filename prefix.
        population_dataset_id (str): The dataset ID resolved by `resolve_population_dataset()`.

    Raises:
        FileNotFoundError: If the population file does not exist.
    """
    if not dataset_file_exists(population_dataset_id, f"{country_code}_population.parquet"):
        msg = (
            f"Population file {country_code}_population.parquet not found in dataset {population_dataset_id}."
        )
        current_run.log_error(msg)
        raise FileNotFoundError(msg)


def resolve_population_dataset(snt_config: dict, population_selection: str) -> str:
    """Resolve the population dataset ID based on the population selection.

    Args:
        snt_config (dict): The SNT configuration dictionary.
        population_selection (str): The population selection option. One of "DHIS2", "Population-transformed"
         or "User-provided".

    Returns:
        str: The dataset ID corresponding to the population selection.

    Raises:
        ValueError: If the population selection is unknown.
        KeyError: If the matching dataset identifier is missing from SNT_DATASET_IDENTIFIERS.
    """
    if population_selection == "DHIS2":
        return snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_DATASET_FORMATTED"]
    if population_selection == "Population-transformed":
        return snt_config["SNT_DATASET_IDENTIFIERS"]["DHIS2_POPULATION_TRANSFORMATION"]
    if population_selection == "User-provided":
        return snt_config["SNT_DATASET_IDENTIFIERS"]["SNT_POPULATION_USER_PROVIDED"]
    raise ValueError(f"Unknown population selection: {population_selection}")


if __name__ == "__main__":
    snt_dhis2_incidence()
