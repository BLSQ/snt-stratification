"""The config conformance fixtures, run through snt_lib's real validate_config().

Each fixture in contracts/snt_config/fixtures/ holds a config and the verdict the pipelines' gate,
snt_lib.validate_config(), must return: valid, or invalid on exactly the config paths listed. The
config editor's JS validator will run the same folder (editor spec section 12.2, option 2).

The fixture checks run offline. The validate_config() checks need snt_lib, which pulls in
geopandas, polars and papermill, so they skip when it is not installed, unless SNT_LIB_REQUIRED=1
(set by CI, which installs the pinned ref in tests/requirements-conformance.txt): a CI run never
passes by skipping.
"""

import importlib
import json
import os
import re
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNT_CONFIG = ROOT / "contracts" / "snt_config"
FIXTURES = sorted((SNT_CONFIG / "fixtures").glob("*.json"))


def load(path: Path) -> dict:
    """Read a JSON file.

    Returns
    -------
    dict
        The parsed document.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def key_tree(value: object) -> object:
    """Reduce a config to its nested dict keys, ignoring values and list contents.

    Returns
    -------
    object
        `{key: subtree}` for a dict, None for anything else.
    """
    if isinstance(value, dict):
        return {k: key_tree(v) for k, v in value.items()}
    return None


def real_validator() -> Callable[[dict], None]:
    """Import snt_lib's validator, skipping the test when absent unless SNT_LIB_REQUIRED=1.

    Returns
    -------
    Callable[[dict], None]
        snt_lib.snt_pipeline_utils.validate_config.
    """
    try:
        module = importlib.import_module("snt_lib.snt_pipeline_utils")
    except ImportError as error:
        if os.environ.get("SNT_LIB_REQUIRED") == "1":
            raise
        pytest.skip(f"snt_lib not installed ({error}); pip install -r tests/requirements-conformance.txt")
    return module.validate_config


def reported_paths(error: Exception) -> set[str]:
    """Extract the config paths a validate_config() failure names.

    A missing top-level section raises KeyError("Missing top-level key(s) in config: A, B"); every
    other failure raises one ValueError with a "  - <PATH> <reason>" line per problem.

    Returns
    -------
    set[str]
        The dotted config paths reported.
    """
    message = error.args[0] if error.args else ""
    if isinstance(error, KeyError):
        return set(message.split(": ", 1)[1].split(", "))
    return set(re.findall(r"^  - (\S+)", message, flags=re.MULTILINE))


def test_fixture_folder_is_not_empty() -> None:
    """The parametrised tests below cannot pass by collecting nothing."""
    assert FIXTURES


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_is_well_formed(path: Path) -> None:
    """A fixture has a description, a verdict that matches its file name, and a config."""
    fixture = load(path)
    assert set(fixture) == {"description", "expected", "config"}
    assert set(fixture["expected"]) == {"valid", "fails"}
    valid, fails = fixture["expected"]["valid"], fixture["expected"]["fails"]
    assert path.stem.startswith("valid_" if valid else "invalid_")
    assert (fails == []) if valid else bool(fails)


@pytest.mark.parametrize("path", [p for p in FIXTURES if p.stem.startswith("valid_")], ids=lambda p: p.stem)
def test_valid_fixture_keeps_the_skeleton_shape(path: Path) -> None:
    """A valid fixture has exactly the skeleton's keys, so a skeleton change forces a fixture update."""
    skeleton = load(SNT_CONFIG / "SNT_config.skeleton.json")
    assert key_tree(load(path)["config"]) == key_tree(skeleton)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_validate_config_returns_the_expected_verdict(path: Path) -> None:
    """snt_lib accepts each valid fixture and rejects each invalid one on exactly its listed paths."""
    real = real_validator()
    fixture = load(path)
    if fixture["expected"]["valid"]:
        real(fixture["config"])
        return
    with pytest.raises((KeyError, ValueError)) as caught:
        real(fixture["config"])
    assert reported_paths(caught.value) == set(fixture["expected"]["fails"])
