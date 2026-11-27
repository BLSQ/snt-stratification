"""Offline tests of the two deployers: shared helpers, the bootstrap guard, and drift between them (D28)."""

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
# without_older_bootstrap skips bootstrap pipelines; the variant refuses one instead
# (refuse_older_bootstrap), since it deploys nothing else. The variant installs no webapp (ADR 0048).
NOT_IN_VARIANT = {
    "snt_workspace_deployer",
    "deploy_release",
    "deploy_all",
    "write_release_marker",
    "without_older_bootstrap",
    "deploy_webapps",
    "deploy_webapp",
    "download_webapp_bundle",
    "get_webapp_by_slug",
    "served_webapp_files",
    "webapp_file_inputs",
    "create_webapp",
    "update_webapp",
}


class Log:
    """Stand-in for `current_run` that records each log call as (method name, message)."""

    def __init__(self) -> None:
        self.lines = []

    def __getattr__(self, name: str) -> Callable[[str], None]:
        return lambda msg: self.lines.append((name, msg))


def load(path: Path, module_name: str) -> ModuleType:
    """Import a pipeline.py under its own name, since every pipeline file is `pipeline`.

    Returns
    -------
    ModuleType
        The imported module, its `current_run` replaced by a `Log`.
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.current_run = Log()
    return module


dep = load(VARIANT, "snt_pipeline_deployer_pipeline")
deployer = load(DEPLOYER, "snt_workspace_deployer_pipeline")


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
    """A changed or missing shared file is named in one warning; pipeline folders are not checked."""
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
    assert message.startswith("Shared R library (shared/r/")
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
    """A v1 manifest (no schema_version) or an unknown version stops the run with an error."""
    manifest = {k: v for k, v in V2_MANIFEST.items() if k != "schema_version"}
    if version is not None:
        manifest["schema_version"] = version
    dep.current_run = log = Log()
    with pytest.raises(dep.DeploymentAbortedError) as raised:
        dep.check_manifest_version(manifest, "v0.1.0")
    assert str(raised.value).startswith("Cannot deploy:")
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


# Bootstrap guard (ADR 0042): bootstrap pipelines only from the latest full release or newer.

LATEST = {"tag_name": "v1.1.0", "published_at": "2026-12-10T09:00:00Z"}


def release(tag: str, published_at: str | None) -> dict:
    """Build a GitHub release object for the guard.

    Returns
    -------
    dict
        The release's tag and publication time.
    """
    return {"tag_name": tag, "published_at": published_at}


@pytest.mark.parametrize(
    ("target", "latest"),
    [
        (release("v0.1.0", "2026-11-20T10:00:00Z"), None),  # no full release yet: every release is newest
        (release("v1.1.0", "2026-12-10T09:00:00Z"), LATEST),  # the latest full release itself
        (release("v1.2.0-rc.1", "2026-12-15T09:00:00Z"), LATEST),  # a release candidate after it
        (release("v1.1.0", None), LATEST),  # same tag: allowed without reading any date
    ],
)
def test_bootstrap_guard_allows_latest_or_newer(target: dict, latest: dict | None) -> None:
    """The latest full release, a release published after it, or any release when none is full."""
    assert dep.bootstrap_guard(target, latest) is None


def test_bootstrap_guard_blocks_an_older_release() -> None:
    """A release published before the latest full one is blocked, and the reason names both."""
    reason = dep.bootstrap_guard(release("v1.0.0", "2026-12-01T09:00:00Z"), LATEST)
    assert reason == (
        "release v1.0.0 (published 2026-12-01T09:00:00Z) is older than the latest full release v1.1.0 "
        "(published 2026-12-10T09:00:00Z)"
    )


def test_bootstrap_guard_blocks_when_a_date_is_missing() -> None:
    """Without both publication dates the release cannot be shown to be newer, so it is blocked."""
    reason = dep.bootstrap_guard(release("v1.2.0", None), LATEST)
    assert reason is not None
    assert "publication date" in reason


MIXED = {
    "snt_map_extracts": {"kind": "snt"},
    "snt_workspace_checker": {"kind": "bootstrap"},
    "snt_workspace_deployer": {"kind": "bootstrap"},
}


def test_older_release_skips_bootstrap_pipelines_with_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """An older release still deploys its snt pipelines; its bootstrap ones are skipped, logged as info."""
    monkeypatch.setattr(deployer, "latest_full_release", lambda repo: LATEST)
    deployer.current_run = log = Log()
    kept = deployer.without_older_bootstrap("BLSQ/x", release("v1.0.0", "2026-12-01T09:00:00Z"), MIXED)
    assert kept == {"snt_map_extracts": {"kind": "snt"}}
    [(level, message)] = log.lines
    assert level == "log_info"
    assert message.startswith("Bootstrap pipelines skipped (snt_workspace_checker, snt_workspace_deployer)")


def test_latest_release_keeps_bootstrap_pipelines(monkeypatch: pytest.MonkeyPatch) -> None:
    """The latest full release deploys every pipeline, bootstrap included, and logs nothing."""
    monkeypatch.setattr(deployer, "latest_full_release", lambda repo: LATEST)
    deployer.current_run = log = Log()
    assert deployer.without_older_bootstrap("BLSQ/x", release("v1.1.0", None), MIXED) == MIXED
    assert log.lines == []


def test_no_bootstrap_pipeline_asks_github_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A release without bootstrap pipelines needs no latest-release lookup."""

    def fail(repo: str) -> None:
        raise AssertionError("latest_full_release called")

    monkeypatch.setattr(deployer, "latest_full_release", fail)
    snt_only = {"snt_map_extracts": {"kind": "snt"}}
    assert deployer.without_older_bootstrap("BLSQ/x", release("v1.0.0", None), snt_only) == snt_only


def test_single_deployer_refuses_an_older_bootstrap_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Asked for a bootstrap pipeline from an older release, the variant stops with an error."""
    monkeypatch.setattr(dep, "latest_full_release", lambda repo: LATEST)
    dep.current_run = Log()
    with pytest.raises(dep.DeploymentAbortedError) as raised:
        dep.refuse_older_bootstrap(
            "BLSQ/x", release("v1.0.0", "2026-12-01T09:00:00Z"), "snt_workspace_deployer"
        )
    assert str(raised.value).startswith("Cannot deploy: snt_workspace_deployer is a bootstrap pipeline")
    assert "older than the latest full release v1.1.0" in str(raised.value)


def test_single_deployer_accepts_a_newer_bootstrap_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A release candidate published after the latest full release may deploy a bootstrap pipeline."""
    monkeypatch.setattr(dep, "latest_full_release", lambda repo: LATEST)
    dep.current_run = log = Log()
    dep.refuse_older_bootstrap(
        "BLSQ/x", release("v1.2.0-rc.1", "2026-12-15T09:00:00Z"), "snt_workspace_deployer"
    )
    assert log.lines == []


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


def test_release_marker_records_tag_and_repository() -> None:
    """.snt_release holds the tag under its original key, and the repository beside it."""
    deployer.current_run = Log()
    with tempfile.TemporaryDirectory() as tmp:
        deployer.write_release_marker(Path(tmp), "v0.1.0", "BLSQ/snt-stratification")
        marker = json.loads((Path(tmp) / ".snt_release").read_text())
    assert marker == {"snt_release": "v0.1.0", "repo": "BLSQ/snt-stratification"}


# Webapps (ADR 0048): installed by the workspace deployer, after the pipelines, found by slug.

COMMITTED = {"index.html": b"<html>cockpit</html>\n", "app.js": b"console.log('v1');\n"}
STAMP = b'{"version": "v1.0.0", "commit": "abc", "built_at": "2026-12-01T09:00:00Z"}\n'
SCOPES = ["FILES_READ", "PIPELINES_READ", "PIPELINES_RUN", "USER_READ"]
WEBAPP_SPEC = {
    "path": "webapps/orchestrator/app",
    "version": "v1.0.0",
    "name": "SNT Pipelines Orchestrator - Cockpit",
    "slug": "snt-pipelines-orchestrator-cockpit",
    "scopes": SCOPES,
    "files": {path: hashlib.sha256(content).hexdigest() for path, content in COMMITTED.items()},
}
WEBAPP_RELEASE = {
    "tag_name": "v1.0.0",
    "html_url": "https://github.com/BLSQ/snt-stratification/releases/tag/v1.0.0",
    "assets": [asset("release_manifest.json"), asset("webapp-orchestrator-v1.0.0.zip")],
}
# The bundle as the release zip holds it: the committed files and the stamped version.json.
BUNDLE = {**COMMITTED, "version.json": STAMP}


def zip_bytes(files: dict[str, bytes]) -> bytes:
    """Zip files in memory, as the release workflow zips a webapp bundle.

    Returns
    -------
    bytes
        The zip archive.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


class FakeOpenHexa:
    """Stand-in for `call_graphql`: one webapp at most, its served files, and every call recorded."""

    def __init__(
        self, app: dict | None = None, served: dict[str, bytes] | None = None, created_slug: str | None = None
    ) -> None:
        self.app = app
        self.served = served or {}
        self.created_slug = created_slug or WEBAPP_SPEC["slug"]
        self.calls = []

    def __call__(self, token: str, operation: str, variables: dict) -> dict:
        """Answer one GraphQL call from the fake state, and record it.

        Returns
        -------
        dict
            The `data` object call_graphql would return.
        """
        self.calls.append((operation, variables))
        if "createWebapp" in operation:
            webapp = {"id": "new-id", "slug": self.created_slug}
            return {"createWebapp": {"success": True, "errors": [], "webapp": webapp}}
        if "updateWebapp" in operation:
            return {"updateWebapp": {"success": True, "errors": []}}
        if "files {" in operation:
            nodes = [{"path": "assets", "type": "directory", "encoding": None, "content": None}]
            nodes += [
                {
                    "path": path,
                    "type": "file",
                    "encoding": "BASE64",
                    "content": base64.b64encode(raw).decode(),
                }
                for path, raw in self.served.items()
            ]
            return {"webapp": {"files": nodes}}
        return {"webapp": self.app}

    def mutations(self) -> list[dict]:
        """List the input of every mutation sent, in order.

        Returns
        -------
        list[dict]
            Each mutation's `input` variable.
        """
        return [variables["input"] for operation, variables in self.calls if operation.startswith("mutation")]


def existing_app(is_public: bool = False, scopes: list[str] = SCOPES, kind: str = "STATIC") -> dict:
    """Build the webapp lookup result for an app already at the orchestrator's slug.

    Returns
    -------
    dict
        The fields get_webapp_by_slug asks for.
    """
    return {
        "id": "app-id",
        "name": "SNT Pipelines Orchestrator - Cockpit",
        "slug": WEBAPP_SPEC["slug"],
        "type": kind,
        "isPublic": is_public,
        "allowedOperations": scopes,
    }


@pytest.fixture
def openhexa(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeOpenHexa]:
    """Point the deployer at a fake API, a fake workspace and a release zip holding BUNDLE.

    Returns
    -------
    Callable[..., FakeOpenHexa]
        Builds the fake API with the given webapp state and installs it.
    """
    monkeypatch.setattr(deployer, "workspace", SimpleNamespace(slug="ws"))
    monkeypatch.setattr(
        deployer,
        "github_get",
        lambda url: SimpleNamespace(ok=True, status_code=200, content=zip_bytes(BUNDLE)),
    )
    deployer.current_run = Log()

    def install(**state: object) -> FakeOpenHexa:
        fake = FakeOpenHexa(**state)
        monkeypatch.setattr(deployer, "call_graphql", fake)
        return fake

    return install


def test_missing_webapp_is_created_private_with_its_scopes(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """No app at the slug: one createWebapp, private, the manifest's scopes, every bundle file."""
    fake = openhexa()
    deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)
    [created] = fake.mutations()
    assert created["name"] == "SNT Pipelines Orchestrator - Cockpit"
    assert (created["isPublic"], created["allowedOperations"]) == (False, SCOPES)
    assert {f["path"]: f["content"].encode() for f in created["source"]["static"]} == BUNDLE
    assert {f["encoding"] for f in created["source"]["static"]} == {"TEXT"}
    assert deployer.current_run.lines[-1][1].startswith("Webapp snt-pipelines-orchestrator-cockpit: created")


def test_create_under_another_slug_fails(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """A taken slug gives a suffixed duplicate: the step fails and names the app to delete."""
    openhexa(created_slug="snt-pipelines-orchestrator-cockpit-fcb549")
    with pytest.raises(ValueError, match="Delete the webapp 'snt-pipelines-orchestrator-cockpit-fcb549'"):
        deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)


def test_webapp_serving_the_bundle_is_skipped(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """Same files, private, same scopes in any order: no mutation at all."""
    fake = openhexa(app=existing_app(scopes=list(reversed(SCOPES))), served=BUNDLE)
    deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)
    assert fake.mutations() == []
    assert deployer.current_run.lines[-1][1].endswith("skipped.")


def test_hand_uploaded_webapp_is_adopted(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """A public app with an old file and a stray one: changed files written, stray deleted, made private."""
    served = {"index.html": b"<html>old</html>\n", "app.js": COMMITTED["app.js"], "notes.txt": b"hand\n"}
    fake = openhexa(app=existing_app(is_public=True, scopes=["PIPELINES_READ"]), served=served)
    deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)
    [update] = fake.mutations()
    assert sorted(f["path"] for f in update["files"]) == ["index.html", "version.json"]
    assert update["filesToDelete"] == ["notes.txt"]
    assert (update["id"], update["commitMessage"]) == ("app-id", "v1.0.0")
    assert (update["isPublic"], update["allowedOperations"]) == (False, SCOPES)
    [warning] = [message for level, message in deployer.current_run.lines if level == "log_warning"]
    assert "was public=True with scopes ['PIPELINES_READ']" in warning


def test_settings_only_update_makes_no_commit(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """Right files but a scope removed by hand: scopes set back, no file keys, so no empty commit."""
    fake = openhexa(app=existing_app(scopes=SCOPES[:2]), served=BUNDLE)
    deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)
    [update] = fake.mutations()
    assert update == {"id": "app-id", "isPublic": False, "allowedOperations": SCOPES}


@pytest.mark.parametrize(
    ("app", "expected"), [(None, "DRY RUN would create"), (True, "DRY RUN would update")]
)
def test_dry_run_changes_no_webapp(openhexa: Callable[..., FakeOpenHexa], app: object, expected: str) -> None:
    """A dry run reads the workspace and the release, logs what it would do, and sends no mutation."""
    fake = openhexa(app=existing_app() if app else None, served={"index.html": b"old"})
    deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=True)
    assert fake.mutations() == []
    assert deployer.current_run.lines[-1][1].startswith(expected)


def test_non_static_webapp_at_the_slug_fails(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """An iframe app holding the slug cannot take files: the step fails before reading or writing any."""
    fake = openhexa(app=existing_app(kind="IFRAME"))
    with pytest.raises(ValueError, match="is a IFRAME webapp, not a static one"):
        deployer.deploy_webapp(WEBAPP_RELEASE, "orchestrator", WEBAPP_SPEC, "token", dry_run=False)
    assert len(fake.calls) == 1


def test_bundle_must_match_the_manifest(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """A release zip whose committed files differ from the manifest's hashes is refused, naming the path."""
    openhexa()
    spec = {**WEBAPP_SPEC, "files": {**WEBAPP_SPEC["files"], "app.js": "0" * 64}}
    with pytest.raises(ValueError, match=r"paths that differ: \['app.js'\]"):
        deployer.download_webapp_bundle(WEBAPP_RELEASE, "orchestrator", spec)


def test_binary_file_travels_as_base64() -> None:
    """A file that is not UTF-8 is sent BASE64, the rest as TEXT."""
    inputs = deployer.webapp_file_inputs({"logo.png": b"\x89PNG\x00\xff", "index.html": b"<p>ok</p>"})
    assert [(i["path"], i["encoding"]) for i in inputs] == [("index.html", "TEXT"), ("logo.png", "BASE64")]
    assert base64.b64decode(inputs[1]["content"]) == b"\x89PNG\x00\xff"


def test_deploy_webapps_skips_old_entries_and_collects_failures(
    openhexa: Callable[..., FakeOpenHexa],
) -> None:
    """An entry from before ADR 0048 is skipped with a warning; a missing zip fails only its webapp."""
    fake = openhexa()
    manifest = {
        "webapps": {
            "config_editor": {**WEBAPP_SPEC, "path": "webapps/config_editor/app"},  # no zip asset
            "old_app": {"path": "webapps/old_app/app", "version": "v1.0.0", "files": {}},
            "orchestrator": WEBAPP_SPEC,
        }
    }
    failures = deployer.deploy_webapps(WEBAPP_RELEASE, manifest, "token", dry_run=False)
    assert failures == ["config_editor"]
    assert len(fake.mutations()) == 1
    levels = [level for level, _ in deployer.current_run.lines]
    assert levels.count("log_warning") == 1
    assert levels.count("log_error") == 1
    assert deployer.current_run.lines[-1][1] == "Webapps: 1/2 installed or up to date."


def test_release_without_webapps_installs_none(openhexa: Callable[..., FakeOpenHexa]) -> None:
    """A manifest with no webapps block asks OpenHEXA nothing."""
    fake = openhexa()
    assert deployer.deploy_webapps(WEBAPP_RELEASE, {"files": {}}, "token", dry_run=False) == []
    assert fake.calls == []
