"""tools/build_release_assets.py packs exactly what the manifest lists, on a synthetic tree and this repo."""

import json
import tarfile
import zipfile
from pathlib import Path

import build_manifest
import build_release_assets
import pytest
from test_build_manifest import ROOT, make_tree

REPO = "BLSQ/snt-stratification"
VERSION = "v9.9.9"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
BUILT_AT = "2026-11-13T10:00:00Z"


def tree_and_manifest(tmp_path: Path) -> tuple[Path, dict]:
    """Write the synthetic repository and build its manifest.

    Returns
    -------
    tuple[Path, dict]
        The repository root and its manifest v2.
    """
    root = make_tree(tmp_path / "repo")
    return root, build_manifest.build_manifest(root, VERSION, REPO)


def build(root: Path, manifest: dict, out: Path) -> list[Path]:
    """Build the assets with the test commit and time.

    Returns
    -------
    list[Path]
        The written assets.
    """
    return build_release_assets.build_assets(root, manifest, out, COMMIT, BUILT_AT)


def test_tarball_holds_exactly_the_manifest_files_under_one_top_folder(tmp_path: Path) -> None:
    """One top folder <repo name>-<tag>/, every manifest file at its repo path, byte for byte, no more."""
    root, manifest = tree_and_manifest(tmp_path)
    tarball = build(root, manifest, tmp_path / "dist")[0]
    assert tarball.name == "snt-stratification-v9.9.9.tar.gz"
    with tarfile.open(tarball) as tar:
        members = {m.name: m for m in tar.getmembers()}
        assert set(members) == {f"snt-stratification-v9.9.9/{p}" for p in manifest["files"]}
        for name, member in members.items():
            assert member.isfile()
            assert (member.uid, member.uname) == (0, "")
            path = name.removeprefix("snt-stratification-v9.9.9/")
            assert tar.extractfile(member).read() == (root / path).read_bytes()


def test_tarball_extracts_like_the_github_source_tarball(tmp_path: Path) -> None:
    """The deployers' rule today: the archive extracts to exactly one directory."""
    root, manifest = tree_and_manifest(tmp_path)
    tarball = build(root, manifest, tmp_path / "dist")[0]
    target = tmp_path / "extracted"
    with tarfile.open(tarball) as tar:
        tar.extractall(path=target, filter="data")
    assert [p.name for p in target.iterdir()] == ["snt-stratification-v9.9.9"]


def test_webapp_zip_holds_the_bundle_and_a_stamped_version_file(tmp_path: Path) -> None:
    """Bundle files relative to app/, no hidden files, plus version.json; no zip for a dotfile-only app/."""
    root, manifest = tree_and_manifest(tmp_path)
    written = build(root, manifest, tmp_path / "dist")
    assert [p.name for p in written[1:]] == ["webapp-orchestrator-v9.9.9.zip"]
    with zipfile.ZipFile(written[1]) as bundle:
        assert sorted(bundle.namelist()) == ["data/pipeline_map.json", "index.html", "version.json"]
        assert bundle.read("index.html") == (root / "webapps/orchestrator/app/index.html").read_bytes()
        assert json.loads(bundle.read("version.json")) == {
            "version": VERSION,
            "commit": COMMIT,
            "built_at": BUILT_AT,
        }


def test_a_changed_file_stops_the_build_and_writes_nothing(tmp_path: Path) -> None:
    """A checkout that drifted from its manifest gives no assets."""
    root, manifest = tree_and_manifest(tmp_path)
    (root / "shared/r/snt_utils.r").write_text("edited after the manifest", encoding="utf-8")
    (root / "webapps/orchestrator/app/index.html").unlink()
    out = tmp_path / "dist"
    with pytest.raises(build_release_assets.AssetError) as error:
        build(root, manifest, out)
    assert "shared/r/snt_utils.r: sha256 differs" in str(error.value)
    assert "webapps/orchestrator/app/index.html: listed in the manifest, missing" in str(error.value)
    assert not out.exists()


def test_a_bundle_holding_version_json_is_refused(tmp_path: Path) -> None:
    """The release stamps version.json; a committed one would be overwritten silently."""
    root = make_tree(tmp_path / "repo")
    (root / "webapps/orchestrator/app/version.json").write_text("{}", encoding="utf-8")
    manifest = build_manifest.build_manifest(root, VERSION, REPO)
    with pytest.raises(build_release_assets.AssetError, match="must not hold one"):
        build(root, manifest, tmp_path / "dist")


def test_an_invalid_manifest_is_refused(tmp_path: Path) -> None:
    """The assets are built only from a manifest the schema accepts."""
    root, manifest = tree_and_manifest(tmp_path)
    manifest["schema_version"] = 1
    with pytest.raises(build_release_assets.AssetError, match="manifest is invalid"):
        build(root, manifest, tmp_path / "dist")


@pytest.mark.parametrize("version", ["release/v1", "../v1", "v1 rc", "-v1"])
def test_a_version_that_cannot_name_a_file_is_refused(tmp_path: Path, version: str) -> None:
    """The version goes into the asset names, so it must be one plain path segment."""
    root = make_tree(tmp_path / "repo")
    manifest = build_manifest.build_manifest(root, version, REPO)
    with pytest.raises(build_release_assets.AssetError, match="cannot name a file"):
        build(root, manifest, tmp_path / "dist")


@pytest.mark.parametrize(
    ("commit", "built_at"),
    [("abc1234", BUILT_AT), (COMMIT.upper(), BUILT_AT), (COMMIT, "2026-11-13 10:00"), (COMMIT, "")],
)
def test_an_unstampable_commit_or_time_is_refused(commit: str, built_at: str) -> None:
    """version.json carries the full commit hash and a UTC time, never a short or local form."""
    with pytest.raises(build_release_assets.AssetError):
        build_release_assets.version_stamp(VERSION, commit, built_at)


def test_main_writes_next_to_the_manifest_with_the_commit_from_github_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In a workflow the commit comes from GITHUB_SHA, and the assets land beside the manifest."""
    root = make_tree(tmp_path / "repo")
    manifest_path = tmp_path / "dist" / "release_manifest.json"
    manifest_path.parent.mkdir()
    args = ["--root", str(root), "--version", VERSION, "--repo", REPO, "--output", str(manifest_path)]
    assert build_manifest.main(args) == 0
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    args = ["--manifest", str(manifest_path), "--root", str(root), "--built-at", BUILT_AT]
    assert build_release_assets.main(args) == 0
    assert sorted(p.name for p in manifest_path.parent.iterdir()) == [
        "release_manifest.json",
        "snt-stratification-v9.9.9.tar.gz",
        "webapp-orchestrator-v9.9.9.zip",
    ]


def test_main_fails_without_writing_on_drift(tmp_path: Path) -> None:
    """Exit code 1 and no asset when the checkout differs from the manifest."""
    root, manifest = tree_and_manifest(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "pipelines/snt_alpha/pipeline.py").write_text("changed", encoding="utf-8")
    out = tmp_path / "dist"
    args = ["--manifest", str(manifest_path), "--root", str(root), "--output-dir", str(out)]
    assert build_release_assets.main([*args, "--commit", COMMIT]) == 1
    assert not out.exists()


def test_this_repo_builds_its_assets(tmp_path: Path) -> None:
    """The checkout packs: every manifest file in the tarball, and an orchestrator zip."""
    manifest = build_manifest.build_manifest(ROOT, "v0.0.0-test", REPO)
    written = build(ROOT, manifest, tmp_path)
    assert [p.name for p in written] == [
        "snt-stratification-v0.0.0-test.tar.gz",
        "webapp-orchestrator-v0.0.0-test.zip",
    ]
    with tarfile.open(written[0]) as tar:
        assert len(tar.getnames()) == len(manifest["files"])
