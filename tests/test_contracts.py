"""Fixtures validate against the contracts in contracts/.

The status reports and v1 manifests are real sandbox artefacts. The v2 manifest example is
synthetic until the first release of this repo produces a real one.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(path: Path) -> dict:
    """Read a JSON file.

    Returns
    -------
    dict
        The parsed document.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def validator(schema_name: str) -> Draft202012Validator:
    """Build a validator for one of the contract schemas, after checking the schema itself.

    Returns
    -------
    Draft202012Validator
        A validator that also checks `format` keywords.
    """
    schema = load(CONTRACTS / schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.parametrize("name", sorted(p.name for p in FIXTURES.glob("status_report_*.json")))
def test_status_report_fixture_conforms(name: str) -> None:
    """A report the checker wrote in the sandbox has exactly the frozen schema's keys and validates."""
    report = load(FIXTURES / name)
    schema = validator("status_report.schema.json")
    assert set(report) == set(schema.schema["properties"])
    errors = [e.message for e in schema.iter_errors(report)]
    assert not errors


V1_MANIFESTS = sorted(
    p.name for p in FIXTURES.glob("release_manifest_*.json") if "schema_version" not in load(p)
)
V2_MANIFESTS = sorted(
    p.name for p in FIXTURES.glob("release_manifest_*.json") if load(p).get("schema_version") == 2
)


@pytest.mark.parametrize("name", V1_MANIFESTS)
def test_release_manifest_v1_fixture_conforms(name: str) -> None:
    """A v1 manifest the old generator attached to a sandbox release validates, invariants included."""
    manifest = load(FIXTURES / name)
    errors = [e.message for e in validator("release_manifest.v1.schema.json").iter_errors(manifest)]
    assert not errors
    # The two invariants the schema states but JSON Schema cannot express.
    for directory, spec in manifest["pipelines"].items():
        assert "pipeline.py" in spec["zip_files"], directory
        unknown = [m for m in spec["zip_files"] if f"{directory}/{m}" not in manifest["files"]]
        assert not unknown, (directory, unknown)


def manifest_v2_invariant_errors(manifest: dict) -> list[str]:
    """Check the manifest v2 invariants that its schema states but JSON Schema cannot express.

    Returns
    -------
    list[str]
        One message per broken invariant; empty when the manifest is consistent.
    """
    errors = []
    files = manifest["files"]
    in_a_zip = set()
    for name, spec in manifest["pipelines"].items():
        if spec["path"] != f"pipelines/{name}":
            errors.append(f"pipeline {name}: path {spec['path']!r} is not 'pipelines/{name}'")
        if "pipeline.py" not in spec["zip_files"]:
            errors.append(f"pipeline {name}: zip_files lacks pipeline.py")
        for member in spec["zip_files"]:
            path = f"{spec['path']}/{member}"
            in_a_zip.add(path)
            if path not in files:
                errors.append(f"pipeline {name}: zip member {member!r} has no entry {path!r} in files")
    filesystem = set(manifest["filesystem_files"])
    errors += [f"filesystem_files entry {p!r} is not a key of files" for p in sorted(filesystem - set(files))]
    errors += [
        f"files entry {p!r} is in neither filesystem_files nor any zip_files"
        for p in sorted(set(files) - filesystem - in_a_zip)
    ]
    for name, spec in manifest.get("webapps", {}).items():
        if spec["path"] != f"webapps/{name}/app":
            errors.append(f"webapp {name}: path {spec['path']!r} is not 'webapps/{name}/app'")
    return errors


@pytest.mark.parametrize("name", V2_MANIFESTS)
def test_release_manifest_v2_fixture_conforms(name: str) -> None:
    """A v2 manifest validates against the current schema, invariants included."""
    manifest = load(FIXTURES / name)
    errors = [e.message for e in validator("release_manifest.schema.json").iter_errors(manifest)]
    assert not errors
    assert not manifest_v2_invariant_errors(manifest)


def test_v2_fixture_exists() -> None:
    """At least one v2 manifest is checked, so the v2 tests cannot pass by collecting nothing."""
    assert V2_MANIFESTS


def _v2_example() -> dict:
    """Load a fresh copy of the v2 example manifest.

    Returns
    -------
    dict
        The parsed fixture, safe to mutate.
    """
    return load(FIXTURES / "release_manifest_v2_example.json")


def _drop(key: str) -> Callable[[dict], object]:
    """Build a mutation that deletes one top-level key.

    Returns
    -------
    Callable[[dict], object]
        The mutation.
    """
    return lambda m: m.pop(key)


SCHEMA_BREAKS = {
    "no schema_version": _drop("schema_version"),
    "schema_version 1": lambda m: m.update(schema_version=1),
    "no repo": _drop("repo"),
    "repo not owner/name": lambda m: m.update(repo="snt-stratification"),
    "no filesystem_files": _drop("filesystem_files"),
    "unknown kind": lambda m: m["pipelines"]["snt_map_extracts"].update(kind="analytics"),
    "no kind": lambda m: m["pipelines"]["snt_map_extracts"].pop("kind"),
    "pipeline path outside pipelines/": lambda m: m["pipelines"]["snt_map_extracts"].update(
        path="snt_map_extracts"
    ),
    "webapp without files": lambda m: m["webapps"]["orchestrator"].pop("files"),
    "unknown top-level key": lambda m: m.update(extra=True),
}


@pytest.mark.parametrize("case", sorted(SCHEMA_BREAKS))
def test_v2_schema_rejects(case: str) -> None:
    """Each shape break of a valid v2 manifest is caught by the schema itself."""
    manifest = _v2_example()
    SCHEMA_BREAKS[case](manifest)
    assert list(validator("release_manifest.schema.json").iter_errors(manifest))


INVARIANT_BREAKS = {
    "path does not match its key": lambda m: m["pipelines"]["snt_map_extracts"].update(
        path="pipelines/snt_other"
    ),
    "zip member missing from files": lambda m: m["files"].pop("pipelines/snt_map_extracts/utils.py"),
    "zip_files without pipeline.py": lambda m: m["pipelines"]["snt_workspace_checker"]["zip_files"].remove(
        "pipeline.py"
    ),
    "filesystem entry missing from files": lambda m: m["filesystem_files"].append("shared/r/gone.r"),
    "file on no route": lambda m: m["filesystem_files"].remove("shared/r/snt_utils.r"),
    "webapp path does not match its key": lambda m: m["webapps"]["orchestrator"].update(
        path="webapps/config_editor/app"
    ),
}


@pytest.mark.parametrize("case", sorted(INVARIANT_BREAKS))
def test_v2_invariants_reject(case: str) -> None:
    """Each break the schema cannot express is caught by the invariant check."""
    manifest = _v2_example()
    INVARIANT_BREAKS[case](manifest)
    assert manifest_v2_invariant_errors(manifest)
