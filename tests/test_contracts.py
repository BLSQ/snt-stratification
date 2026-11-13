"""Fixtures validate against the contracts in contracts/; the orchestrator bundle's two files agree.

The status report is a real sandbox artefact. The v2 manifest example is synthetic until the first
release of this repo produces a real one.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from build_manifest import invariant_errors as manifest_v2_invariant_errors
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


V2_MANIFESTS = sorted(
    p.name for p in FIXTURES.glob("release_manifest_*.json") if load(p).get("schema_version") == 2
)


def test_every_manifest_fixture_is_v2() -> None:
    """No manifest fixture of another shape lingers unchecked (v1 was deleted in Phase 4)."""
    assert sorted(p.name for p in FIXTURES.glob("release_manifest_*.json")) == V2_MANIFESTS


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


def test_orchestrator_map_ids_match_description_keys() -> None:
    """Every orchestrator map node has a description and every description has a node.

    The join key between the two hand-authored files in the orchestrator bundle
    (contracts/orchestrator/pipeline_descriptions.schema.json, rule 2). Their schemas there are prose
    references, not JSON Schema, so this pairing is the part checked mechanically (BACKLOG TOOL-6).
    """
    app = ROOT / "webapps" / "orchestrator" / "app"
    node_ids = [node["id"] for node in load(app / "pipeline_map.json")["nodes"]]
    description_keys = set(load(app / "pipeline_descriptions.json")["descriptions"])
    assert len(node_ids) == len(set(node_ids)), "duplicate node id in pipeline_map.json"
    assert set(node_ids) == description_keys
