"""Offline tests of snt_pipeline_deployer: its own helpers, and drift from snt_workspace_deployer (D28)."""

import ast
import base64
import hashlib
import importlib.util
import io
import json
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOYER = ROOT / "pipelines" / "snt_workspace_deployer" / "pipeline.py"
VARIANT = ROOT / "pipelines" / "snt_pipeline_deployer" / "pipeline.py"

# Shared functions the variant changes on purpose: the version description names the tool, and
# get_release's messages differ (no .snt_release to point at; the latest tag is quoted).
ALLOWED_DIFFERENCES = {"build_version_input", "get_release"}
# Deployer functions the variant replaces or drops. deploy_all's per-pipeline loop and its
# "Pipelines: n/m deployed" line make no sense for one pipeline; deploy_one is called directly.
NOT_IN_VARIANT = {"snt_workspace_deployer", "deploy_release", "deploy_all", "write_release_marker"}


class Log:
    """Stand-in for `current_run` that records each log call as (method name, message)."""

    def __init__(self) -> None:
        self.lines = []

    def __getattr__(self, name: str) -> Callable[[str], None]:
        return lambda msg: self.lines.append((name, msg))


def load_variant() -> ModuleType:
    """Import the variant's pipeline.py under its own name, since every pipeline file is `pipeline`.

    Returns
    -------
    ModuleType
        The imported module, its `current_run` replaced by a `Log`.
    """
    spec = importlib.util.spec_from_file_location("snt_pipeline_deployer_pipeline", VARIANT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.current_run = Log()
    return module


dep = load_variant()


def functions(path: Path) -> dict:
    """Dump each top-level function of a Python file to its AST, which ignores comments and layout.

    Returns
    -------
    dict
        {function name: ast.dump of its definition}.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: ast.dump(node) for node in tree.body if isinstance(node, ast.FunctionDef)}


def sha(text: str) -> str:
    """Hash a string the way the manifest hashes a file.

    Returns
    -------
    str
        The sha256 hex digest of the UTF-8 bytes.
    """
    return hashlib.sha256(text.encode()).hexdigest()


def test_shared_functions_have_not_drifted() -> None:
    """Every function copied from the deployer is still identical, bar the deliberate differences."""
    deployer, variant = functions(DEPLOYER), functions(VARIANT)
    missing = set(deployer) - set(variant) - NOT_IN_VARIANT
    assert not missing, f"deployer functions missing from the variant: {missing}"
    drifted = [
        name for name in set(deployer) & set(variant) - ALLOWED_DIFFERENCES if deployer[name] != variant[name]
    ]
    assert not drifted, f"copy these from snt_workspace_deployer into snt_pipeline_deployer: {drifted}"


DIRS = ["snt_dhis2_extract", "snt_map_extracts", "snt_metadata_json_trim"]


@pytest.mark.parametrize("typed", ["snt_dhis2_extract", "snt-dhis2-extract", "  SNT-DHIS2-Extract "])
def test_resolve_pipeline_dir_accepts_dir_name_and_code(typed: str) -> None:
    """The directory name and the OpenHEXA code both resolve, whatever the case and padding."""
    assert dep.resolve_pipeline_dir(typed, DIRS, "v1") == "snt_dhis2_extract"


def test_resolve_pipeline_dir_lists_pipelines_on_unknown_name() -> None:
    """A typo stops the run, and the message lists every pipeline of the release."""
    with pytest.raises(dep.DeploymentAbortedError) as raised:
        dep.resolve_pipeline_dir("snt_dhis2_extrat", DIRS, "v1")
    assert "'snt_dhis2_extrat'" in str(raised.value)
    assert ", ".join(DIRS) in str(raised.value)


ANALYTICS = {
    "shared/r/snt_utils.r": "a",
    "pipelines/snt_dhis2_extract/code/extract.ipynb": "b",
    "pipelines/snt_dhis2_extract/utils/extract.r": "c",
    "pipelines/snt_dhis2_extract_other/code/x.ipynb": "d",
    "pipelines/snt_map_extracts/code/map.ipynb": "e",
}

PIPELINES = {"snt_dhis2_extract": {"path": "pipelines/snt_dhis2_extract"}}


def test_pipeline_analytics_selects_only_its_own_folder() -> None:
    """Only the pipeline's folder is selected: no shared/r/, no folder that merely shares a prefix."""
    assert dep.pipeline_analytics(ANALYTICS, "pipelines/snt_dhis2_extract") == {
        "pipelines/snt_dhis2_extract/code/extract.ipynb": "b",
        "pipelines/snt_dhis2_extract/utils/extract.r": "c",
    }
    assert dep.pipeline_analytics(ANALYTICS, "pipelines/snt_metadata_json_trim") == {}


def test_shared_library_drift_names_differing_and_missing_files() -> None:
    """A changed or missing shared file is named in one [WARNING]; pipeline folders are not checked."""
    files = {"shared/r/same.r": sha("same"), "shared/r/changed.r": sha("new"), "shared/r/gone.r": sha("x")}
    files["pipelines/snt_dhis2_extract/utils/extract.r"] = sha("not shared")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "shared/r").mkdir(parents=True)
        (root / "shared/r/same.r").write_text("same")
        (root / "shared/r/changed.r").write_text("old")
        dep.current_run = log = Log()
        dep.report_shared_library_drift(files, PIPELINES, root, "v1")

    [(level, message)] = log.lines
    assert level == "log_warning"
    assert message.startswith("[WARNING]")
    assert "2/3 file(s)" in message
    assert "shared/r/changed.r" in message
    assert "shared/r/gone.r (missing)" in message
    assert "same.r" not in message
    assert "extract.r" not in message


def test_shared_library_in_line_is_info() -> None:
    """A workspace whose shared library matches the release gets an info line, not a warning."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "shared/r").mkdir(parents=True)
        (root / "shared/r/same.r").write_text("same")
        dep.current_run = log = Log()
        dep.report_shared_library_drift({"shared/r/same.r": sha("same")}, PIPELINES, root, "v1")

    assert log.lines == [
        (
            "log_info",
            "Shared R library (shared/r/, used by all pipelines, not updated by this run): all 1 file(s) "
            "match release v1.",
        )
    ]


# The shared functions below are identical in both deployers (test_shared_functions_have_not_drifted),
# so testing them through the variant tests snt_workspace_deployer too.

V2_MANIFEST = json.loads(
    (ROOT / "tests/fixtures/release_manifest_v2_example.json").read_text(encoding="utf-8")
)


def test_v2_manifest_is_readable() -> None:
    """The v2 example manifest passes the version check, with nothing logged."""
    dep.current_run = log = Log()
    dep.check_manifest_version(V2_MANIFEST, "v0.1.0")
    assert log.lines == []


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, "it is a v1 manifest, from the old snt_development repository"),
        (3, "has schema_version 3, and this deployer reads only schema_version 2"),
        ("2", "has schema_version '2', and this deployer reads only schema_version 2"),
    ],
)
def test_unreadable_manifest_version_stops_the_run(version: object, expected: str) -> None:
    """A v1 manifest (no schema_version) or an unknown version stops the run with an [ERROR]."""
    manifest = {k: v for k, v in V2_MANIFEST.items() if k != "schema_version"}
    if version is not None:
        manifest["schema_version"] = version
    dep.current_run = log = Log()
    with pytest.raises(dep.DeploymentAbortedError) as raised:
        dep.check_manifest_version(manifest, "v0.1.0")
    assert str(raised.value).startswith("[ERROR] Cannot deploy:")
    assert expected in str(raised.value)
    assert log.lines == [("log_error", str(raised.value))]


def test_split_manifest_copies_exactly_the_filesystem_files() -> None:
    """The filesystem route is filesystem_files, never derived from a path: no pipeline.py, no readme."""
    analytics, pipelines = dep.split_manifest(V2_MANIFEST)
    assert sorted(analytics) == sorted(V2_MANIFEST["filesystem_files"])
    assert all(analytics[path] == V2_MANIFEST["files"][path] for path in analytics)
    assert "pipelines/snt_map_extracts/pipeline.py" not in analytics
    assert "shared/r/snt_utils.r" in analytics
    assert pipelines == V2_MANIFEST["pipelines"]


def asset(name: str) -> dict:
    """Build a GitHub release asset object.

    Returns
    -------
    dict
        The asset's name and download URL.
    """
    return {"name": name, "browser_download_url": f"https://example.org/{name}"}


RELEASE = {
    "tag_name": "v0.1.0",
    "html_url": "https://github.com/BLSQ/snt-stratification/releases/tag/v0.1.0",
    "assets": [asset("release_manifest.json"), asset("snt-stratification-v0.1.0.tar.gz")],
}


def test_slim_tarball_asset_is_named_after_repo_and_version() -> None:
    """The asset is <repo name>-<version>.tar.gz, as tools/build_release_assets.py names it."""
    assert dep.slim_tarball_asset(RELEASE, V2_MANIFEST)["name"] == "snt-stratification-v0.1.0.tar.gz"


def test_missing_slim_tarball_stops_the_run() -> None:
    """A release without its slim tarball stops the run, naming the asset and the workflow."""
    release = {**RELEASE, "assets": [asset("release_manifest.json")]}
    dep.current_run = Log()
    with pytest.raises(dep.DeploymentAbortedError) as raised:
        dep.slim_tarball_asset(release, V2_MANIFEST)
    assert "no snt-stratification-v0.1.0.tar.gz asset" in str(raised.value)
    assert "'release' workflow" in str(raised.value)


def test_pipeline_zip_holds_exactly_its_manifest_zip_files() -> None:
    """Zipping pipelines.<name>.path of an extracted release gives exactly that pipeline's zip_files."""
    spec = V2_MANIFEST["pipelines"]["snt_map_extracts"]
    parsed = SimpleNamespace(parameters=[], timeout=None, functional_type=None)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for path in V2_MANIFEST["files"]:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(path)
        version_input = dep.build_version_input(root / spec["path"], parsed, RELEASE)

    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(version_input["zipfile"])))
    assert sorted(archive.namelist()) == sorted(spec["zip_files"])
    assert version_input["name"] == "v0.1.0"


@pytest.mark.parametrize(
    ("replaced", "backup", "dry_run", "expected"),
    [
        (0, True, False, ""),
        (3, True, False, "; the 3 previous copies moved to archive/v1/pipelines/snt_x/"),
        (3, True, True, "; the 3 previous copies would be moved to archive/v1/pipelines/snt_x/"),
        (2, False, False, "; 2 existing file(s) overwritten, no backup (Backup existing files is off)"),
    ],
)
def test_describe_replaced_says_where_old_copies_went(
    replaced: int, backup: bool, dry_run: bool, expected: str
) -> None:
    """The sync line names the archive folder when backing up, and says files were overwritten when not."""
    assert dep.describe_replaced(replaced, "snt_x", "v1", backup, dry_run) == expected
