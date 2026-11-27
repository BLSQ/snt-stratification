import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from openhexa.sdk import current_run, parameter, pipeline, workspace
from openhexa.sdk.datasets.dataset import Dataset, DatasetVersion
from snt_lib.snt_pipeline_utils import validate_config

# ADR 0043: every SNT pipeline reads SNT_config.json from the latest version of this dataset, by slug.
CONFIG_DATASET_NAME = "SNT_CONFIGURATION"
CONFIG_DATASET_SLUG = "snt-configuration"
CONFIG_DATASET_DESCRIPTION = (
    "SNT_config.json, the country configuration read by the SNT pipelines. "
    "Published by the snt_config_publish pipeline."
)
CONFIG_FILENAME = "SNT_config.json"
LOG_FILENAME = "SNT_config.log.json"  # the config editor's log for this file (ADR 0047)


@pipeline("snt_config_publish")
@parameter(
    "config_json",
    name="SNT_config.json content",
    type=str,
    required=True,
    help=(
        "The whole SNT_config.json, as text. The config editor webapp fills this in when you click "
        "Publish. It is checked with validate_config() and published only if valid."
    ),
)
@parameter(
    "editor_log_json",
    name="Config editor log (optional)",
    type=str,
    required=False,
    default=None,
    help=(
        "SNT_config.log.json, written by the config editor for this exact file. Published beside "
        "the config when given. Leave empty when publishing a config by hand."
    ),
)
def snt_config_publish(config_json: str, editor_log_json: str | None = None) -> None:
    """Publish a valid SNT_config.json as a new version of the SNT_CONFIGURATION dataset.

    Fails the run, and publishes nothing, when the config is not JSON, does not pass validate_config(),
    or the SNT_CONFIGURATION dataset cannot be used safely (ADR 0047). A log that is not JSON or does
    not describe this exact file is left out with a warning; the config is still published.
    """
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        fail(f"{CONFIG_FILENAME} is not valid JSON ({e}). Nothing was published.", e)
    if not isinstance(config, dict):
        fail(f"{CONFIG_FILENAME} must be a JSON object. Nothing was published.")

    try:
        validate_config(config)
    except (KeyError, ValueError) as e:
        fail(f"{CONFIG_FILENAME} does not pass validate_config(): {e}. Nothing was published.", e)
    country_code = str(config["SNT_CONFIG"]["COUNTRY_CODE"]).strip()
    current_run.log_info(f"{CONFIG_FILENAME} for {country_code} passes validate_config().")

    log_text = usable_editor_log(editor_log_json, config_json)

    try:
        dataset = get_or_create_config_dataset()
    except ConfigDatasetError as e:
        fail(f"{e} Nothing was published.", e)
    except Exception as e:
        fail(f"Could not find or create the {CONFIG_DATASET_NAME} dataset: {e}. Nothing was published.", e)

    publish(dataset, country_code, config_json, log_text)


class PipelineFailedError(Exception):
    """Ends the run as failed; its message has already been logged at error level."""


class ConfigDatasetError(Exception):
    """The SNT_CONFIGURATION dataset exists in a state the pipelines would not read."""


def fail(message: str, cause: Exception | None = None) -> NoReturn:
    """Log an error and fail the run.

    Parameters
    ----------
    message : str
        What went wrong and what was (not) published.
    cause : Exception | None
        The underlying exception, chained for the traceback.

    Raises
    ------
    PipelineFailedError
        Always.
    """
    current_run.log_error(f"[ERROR] {message}")
    raise PipelineFailedError(message) from cause


def usable_editor_log(editor_log_json: str | None, config_json: str) -> str | None:
    """Return the editor's log if it can be published beside this config, else None.

    The log is kept only if it is a JSON object whose `file_sha256`, when present, is the SHA-256 of the
    exact config text received, so a log never describes a different file than the one beside it.

    Parameters
    ----------
    editor_log_json : str | None
        The log text, or None/empty when there is none.
    config_json : str
        The config text, exactly as it will be published.

    Returns
    -------
    str | None
        The log text to publish, or None to publish the config alone.
    """
    if not editor_log_json or not editor_log_json.strip():
        return None
    try:
        log = json.loads(editor_log_json)
    except json.JSONDecodeError as e:
        current_run.log_warning(
            f"[WARNING] The editor log is not valid JSON ({e}); {LOG_FILENAME} is left out."
        )
        return None
    if not isinstance(log, dict):
        current_run.log_warning(f"[WARNING] The editor log is not a JSON object; {LOG_FILENAME} is left out.")
        return None
    claimed = log.get("file_sha256")
    actual = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    if claimed and claimed != actual:
        current_run.log_warning(
            f"[WARNING] The editor log describes another file (file_sha256 {str(claimed)[:12]}, "
            f"received {actual[:12]}); {LOG_FILENAME} is left out."
        )
        return None
    return editor_log_json


def get_or_create_config_dataset() -> Dataset:
    """Return the SNT_CONFIGURATION dataset the pipelines read, creating it if there is none.

    The pipelines look the dataset up by its slug, so the target is the dataset with slug
    `snt-configuration`, and it must also be named exactly `SNT_CONFIGURATION`. If no dataset has that
    slug or that name, it is created and its slug checked.

    Returns
    -------
    Dataset
        The dataset to publish to.

    Raises
    ------
    ConfigDatasetError
        If the slug belongs to a dataset with another name, a dataset with the name has another slug,
        or the dataset just created did not get the slug.
    """
    try:
        dataset = workspace.get_dataset(CONFIG_DATASET_SLUG)
    except ValueError:  # the SDK raises when no dataset has this slug
        dataset = None

    if dataset is not None:
        if dataset.name != CONFIG_DATASET_NAME:
            raise ConfigDatasetError(
                f"The slug '{CONFIG_DATASET_SLUG}' belongs to a dataset named '{dataset.name}', not "
                f"{CONFIG_DATASET_NAME}. The pipelines read the dataset with that slug. Rename or remove "
                "that dataset in OpenHEXA, then run again."
            )
        return dataset

    same_name = [d.slug for d in workspace.list_datasets() if d.name == CONFIG_DATASET_NAME]
    if same_name:
        raise ConfigDatasetError(
            f"A dataset named {CONFIG_DATASET_NAME} exists with slug {', '.join(same_name)}, not "
            f"'{CONFIG_DATASET_SLUG}', so the pipelines would not find it. Fix it in OpenHEXA, then run "
            "again."
        )

    dataset = workspace.create_dataset(CONFIG_DATASET_NAME, CONFIG_DATASET_DESCRIPTION)
    if dataset.slug != CONFIG_DATASET_SLUG:
        raise ConfigDatasetError(
            f"The dataset {CONFIG_DATASET_NAME} was created, but OpenHEXA gave it the slug "
            f"'{dataset.slug}', not '{CONFIG_DATASET_SLUG}', so the pipelines would not find it. Fix it in "
            "OpenHEXA, then run again."
        )
    current_run.log_info(f"Created the dataset {CONFIG_DATASET_NAME} (slug '{dataset.slug}').")
    return dataset


def publish(dataset: Dataset, country_code: str, config_json: str, log_text: str | None) -> DatasetVersion:
    """Publish the config, and its log if given, as a new version of the dataset.

    The config is published as the exact text received, so its SHA-256 matches the editor log's
    `file_sha256`.

    Parameters
    ----------
    dataset : Dataset
        The SNT_CONFIGURATION dataset.
    country_code : str
        Used in the version name, as the other SNT datasets do (SNT_<CC>_<YYYYMMDD_HHMM>, UTC).
    config_json : str
        The config text.
    log_text : str | None
        The editor log text, or None.

    Returns
    -------
    DatasetVersion
        The new version.
    """
    now = datetime.now(UTC)
    try:
        version = dataset.create_version(f"SNT_{country_code}_{now:%Y%m%d_%H%M}")
    except ValueError:  # a version with this name already exists: two runs in the same minute
        version = dataset.create_version(f"SNT_{country_code}_{now:%Y%m%d_%H%M%S}")

    files = {CONFIG_FILENAME: config_json}
    if log_text is not None:
        files[LOG_FILENAME] = log_text

    with tempfile.TemporaryDirectory() as tmp:
        for filename, text in files.items():
            path = Path(tmp) / filename
            path.write_bytes(text.encode("utf-8"))
            try:
                version.add_file(path, filename=filename)
            except Exception as e:
                fail(
                    f"Version '{version.name}' of {CONFIG_DATASET_NAME} was created, but adding {filename} "
                    f"failed: {e}. Until a new version is published, pipelines read this incomplete one: "
                    "run this pipeline again.",
                    e,
                )

    current_run.log_info(
        f"Published {', '.join(files)} to {CONFIG_DATASET_NAME} as version '{version.name}' "
        f"(id {version.id}). The next pipeline runs read it."
    )
    return version


if __name__ == "__main__":
    snt_config_publish()
