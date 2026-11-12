"""tools/build_manifest.py builds a valid manifest v2, on a synthetic tree and on this repo."""

import hashlib
import json
from pathlib import Path

import build_manifest
import pytest

ROOT = Path(__file__).resolve().parents[1]

# Every file of the synthetic tree; its content is its own path, so each hash is predictable.
TREE = [
    # An snt pipeline: Python half, R half, a helper package, and files the SDK leaves out of the zip.
    "pipelines/snt_alpha/pipeline.py",
    "pipelines/snt_alpha/requirements.txt",
    "pipelines/snt_alpha/readme.md",
    "pipelines/snt_alpha/Helper.PY",  # the SDK's suffix test is case-insensitive
    "pipelines/snt_alpha/client/__init__.py",
    "pipelines/snt_alpha/code/snt_alpha.ipynb",
    "pipelines/snt_alpha/reporting/snt_alpha_report.ipynb",
    "pipelines/snt_alpha/utils/snt_alpha.r",
    "pipelines/snt_alpha/country_specific/snt_alpha_XYZ.ipynb",  # zipped, but no filesystem pattern
    "pipelines/snt_alpha/settings.json",  # .json is not a zipped suffix
    "pipelines/snt_alpha/.gitignore",  # no suffix
    "pipelines/snt_alpha/workspace/scratch.py",  # the SDK excludes <pipeline>/workspace
    "pipelines/snt_alpha/utils/nested/workspace/kept.py",  # only the top-level workspace/ is excluded
    # A bootstrap pipeline: Python only.
    "pipelines/snt_workspace_checker/pipeline.py",
    "pipelines/snt_workspace_checker/requirements.txt",
    # Registry and folder docs: not pipelines, never in the manifest.
    "pipelines/CLAUDE.md",
    # The shared R library, at any depth.
    "shared/r/snt_utils.r",
    "shared/r/extra/snt_more.r",
    "shared/r/README.md",
    # Fetched at run time.
    "catalogs/SNT_metadata_master.json",
    "catalogs/README.md",
    # Webapps: one bundle, one bundle holding only a dotfile (skipped), and design files (never shipped).
    "webapps/orchestrator/app/index.html",
    "webapps/orchestrator/app/data/pipeline_map.json",
    "webapps/orchestrator/app/.DS_Store",
    "webapps/orchestrator/design/wireframe.png",
    "webapps/config_editor/app/.gitkeep",
    # Elsewhere in the repo: never in the manifest.
    "docs/ARCHITECTURE.md",
    "tools/build_manifest.py",
]

REGISTRY = {"pipelines": {"snt_alpha": {"kind": "snt"}, "snt_workspace_checker": {"kind": "bootstrap"}}}


def sha(path: str) -> str:
    """Hash a synthetic file, whose content is its own path.

    Returns
    -------
    str
        The hex sha256.
    """
    return hashlib.sha256(path.encode()).hexdigest()


def make_tree(root: Path, registry: dict = REGISTRY) -> Path:
    """Write the synthetic repository under `root`.

    Returns
    -------
    Path
        `root`, for chaining.
    """
    for path in TREE:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.encode())
    (root / "pipelines" / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    return root


ALPHA_ZIP = [
    "Helper.PY",
    "client/__init__.py",
    "code/snt_alpha.ipynb",
    "country_specific/snt_alpha_XYZ.ipynb",
    "pipeline.py",
    "readme.md",
    "reporting/snt_alpha_report.ipynb",
    "requirements.txt",
    "utils/nested/workspace/kept.py",
    "utils/snt_alpha.r",
]
CHECKER_ZIP = ["pipeline.py", "requirements.txt"]
FILESYSTEM = [
    "pipelines/snt_alpha/code/snt_alpha.ipynb",
    "pipelines/snt_alpha/reporting/snt_alpha_report.ipynb",
    "pipelines/snt_alpha/utils/snt_alpha.r",
    "shared/r/extra/snt_more.r",
    "shared/r/snt_utils.r",
]
EXPECTED = {
    "schema_version": 2,
    "version": "v9.9.9",
    "repo": "BLSQ/snt-stratification",
    "files": {
        p: sha(p)
        for p in sorted(
            [f"pipelines/snt_alpha/{m}" for m in ALPHA_ZIP]
            + [f"pipelines/snt_workspace_checker/{m}" for m in CHECKER_ZIP]
            + ["shared/r/extra/snt_more.r", "shared/r/snt_utils.r"]
        )
    },
    "filesystem_files": FILESYSTEM,
    "pipelines": {
        "snt_alpha": {
            "path": "pipelines/snt_alpha",
            "kind": "snt",
            "code": "snt-alpha",
            "zip_files": ALPHA_ZIP,
        },
        "snt_workspace_checker": {
            "path": "pipelines/snt_workspace_checker",
            "kind": "bootstrap",
            "code": "snt-workspace-checker",
            "zip_files": CHECKER_ZIP,
        },
    },
    "repository_files": {"catalogs/SNT_metadata_master.json": sha("catalogs/SNT_metadata_master.json")},
    "webapps": {
        "orchestrator": {
            "path": "webapps/orchestrator/app",
            "version": "v9.9.9",
            "files": {
                "data/pipeline_map.json": sha("webapps/orchestrator/app/data/pipeline_map.json"),
                "index.html": sha("webapps/orchestrator/app/index.html"),
            },
        },
    },
}


def test_synthetic_tree_gives_the_expected_manifest(tmp_path: Path) -> None:
    """Every routing rule at once: zip mirror, filesystem patterns, catalogs, webapps, exclusions."""
    manifest = build_manifest.build_manifest(make_tree(tmp_path), "v9.9.9", "BLSQ/snt-stratification")
    assert manifest == EXPECTED


def test_synthetic_manifest_is_valid(tmp_path: Path) -> None:
    """The builder's output passes the schema and the invariants it checks itself."""
    manifest = build_manifest.build_manifest(make_tree(tmp_path), "v9.9.9", "BLSQ/snt-stratification")
    assert build_manifest.validation_errors(manifest) == []


def test_unregistered_folder_is_refused(tmp_path: Path) -> None:
    """A pipeline folder missing from registry.json has no kind, so the build stops."""
    registry = {"pipelines": {"snt_alpha": {"kind": "snt"}}}
    with pytest.raises(build_manifest.ManifestError, match="snt_workspace_checker"):
        build_manifest.build_manifest(make_tree(tmp_path, registry), "v9.9.9", "BLSQ/snt-stratification")


def test_registered_folder_missing_is_refused(tmp_path: Path) -> None:
    """A registry entry whose folder has no pipeline.py stops the build."""
    registry = {"pipelines": {**REGISTRY["pipelines"], "snt_gone": {"kind": "snt"}}}
    with pytest.raises(build_manifest.ManifestError, match="snt_gone"):
        build_manifest.build_manifest(make_tree(tmp_path, registry), "v9.9.9", "BLSQ/snt-stratification")


def test_main_writes_a_deterministic_file(tmp_path: Path) -> None:
    """Two runs on the same tree write byte-identical files, read back as the built manifest."""
    root = make_tree(tmp_path / "repo")
    outputs = [tmp_path / "a.json", tmp_path / "b.json"]
    for out in outputs:
        args = ["--root", str(root), "--version", "v9.9.9", "--repo", "BLSQ/snt-stratification"]
        assert build_manifest.main([*args, "--output", str(out)]) == 0
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    assert json.loads(outputs[0].read_text(encoding="utf-8")) == EXPECTED


def test_main_takes_version_and_repo_from_github_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In a workflow, the tag and the repository come from GITHUB_REF_NAME and GITHUB_REPOSITORY."""
    monkeypatch.setenv("GITHUB_REF_NAME", "v9.9.9")
    monkeypatch.setenv("GITHUB_REPOSITORY", "BLSQ/snt-stratification")
    out = tmp_path / "m.json"
    assert build_manifest.main(["--root", str(make_tree(tmp_path / "repo")), "--output", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == EXPECTED


def test_main_refuses_an_invalid_manifest(tmp_path: Path) -> None:
    """A repo value the schema refuses fails the run and writes nothing."""
    out = tmp_path / "m.json"
    args = ["--root", str(make_tree(tmp_path / "repo")), "--version", "v9.9.9", "--repo", "no-owner"]
    assert build_manifest.main([*args, "--output", str(out)]) == 1
    assert not out.exists()


def test_this_repo_builds_a_valid_manifest() -> None:
    """The repo checkout gives a valid manifest that lists every registered pipeline with its kind."""
    manifest = build_manifest.build_manifest(ROOT, "v0.0.0-test", "BLSQ/snt-stratification")
    assert build_manifest.validation_errors(manifest) == []
    registry = json.loads((ROOT / "pipelines" / "registry.json").read_text(encoding="utf-8"))["pipelines"]
    assert {name: spec["kind"] for name, spec in manifest["pipelines"].items()} == {
        name: entry["kind"] for name, entry in registry.items()
    }
    assert any(p.startswith("shared/r/") for p in manifest["filesystem_files"])
    assert "config_editor" not in manifest["webapps"]  # its app/ holds only .gitkeep
