"""Build release_manifest.json (manifest v2) for a checkout of this repository.

Every file a release delivers to a workspace, with its sha256, and the route each one takes
(contract: contracts/release_manifest.schema.json, prose: contracts/release_manifest.md):

* the **zip** route: everything the OpenHEXA SDK puts in a pipeline's version zip, which is the whole
  `pipelines/<name>/` folder filtered by suffix, R half included;
* the **filesystem** route: the R half of each pipeline and the shared R library, copied into the
  workspace filesystem by the deployer, each at its own path (repo path = workspace path, ADR 0038).

A notebook takes both routes. `files` is the union, `filesystem_files` and each pipeline's
`zip_files` say which route, so a consumer never derives it from a path.

Ported from the old repo's `generate_manifest.yaml` heredoc. Run by `.github/workflows/release.yaml`;
by hand::

    python tools/build_manifest.py --version v0.1.0 --repo BLSQ/snt-stratification

The manifest is checked against the schema and the invariants before it is written, so a release
never carries an invalid one.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts" / "release_manifest.schema.json"

# Suffixes the OpenHEXA SDK puts in a pipeline version zip. Source: openhexa/cli/api.py,
# generate_zip_file() (checked against openhexa.sdk 2.23.1). The test there is case-insensitive.
ZIP_SUFFIXES = {".py", ".ipynb", ".txt", ".md", ".r", ".sql"}

# The SDK leaves <pipeline>/workspace out of the zip (it would break the bucket mount). Its other
# exclusions, a virtualenv and a custom WORKSPACE_FILES_PATH, cannot occur in a clean checkout.
ZIP_EXCLUDED_DIR = "workspace"

# The filesystem route: each pipeline's R half and the shared R library.
FILESYSTEM_PATTERNS = (
    "pipelines/*/code/*.ipynb",
    "pipelines/*/reporting/*.ipynb",
    "pipelines/*/utils/*.r",
    "shared/r/**/*.r",
)

# Files a pipeline fetches from the repository at run time, at the release tag (snt_metadata_json_trim
# reads the SNT Explorer master list). Provenance only: never synced, in no zip, so not in `files`.
REPOSITORY_PATTERNS = ("catalogs/*.json",)


class ManifestError(Exception):
    """The checkout cannot give a manifest, e.g. pipelines/ and registry.json disagree."""


def hash_file(path: Path) -> str:
    """Compute the sha256 of a file's bytes, read in chunks.

    Returns
    -------
    str
        The lowercase hex digest.
    """
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def registered_pipelines(root: Path) -> dict[str, str]:
    """Read the pipeline kinds and check them against the folders that hold a pipeline.py.

    A folder counts as a pipeline when it holds `pipelines/<name>/pipeline.py`, the folder that
    `openhexa pipelines push` is pointed at.

    Returns
    -------
    dict[str, str]
        `{pipeline name: kind}`, sorted by name.

    Raises
    ------
    ManifestError
        When a pipeline folder is not registered, or a registered folder has no pipeline.py.
    """
    registry = json.loads((root / "pipelines" / "registry.json").read_text(encoding="utf-8"))
    kinds = {name: entry["kind"] for name, entry in registry["pipelines"].items()}
    folders = {p.parent.name for p in (root / "pipelines").glob("*/pipeline.py")}
    problems = [
        f"pipelines/{name}/ is not in pipelines/registry.json" for name in sorted(folders - set(kinds))
    ]
    problems += [
        f"pipelines/registry.json lists {name}, but pipelines/{name}/pipeline.py does not exist"
        for name in sorted(set(kinds) - folders)
    ]
    if problems:
        raise ManifestError("; ".join(problems))
    return dict(sorted(kinds.items()))


def zip_members(pipeline_dir: Path) -> list[str]:
    """List the files the SDK would put in this pipeline's version zip, as paths inside the zip.

    Mirrors generate_zip_file(): a recursive walk of the pipeline folder, keeping the zipped suffixes,
    minus the top-level workspace/ folder.

    Returns
    -------
    list[str]
        POSIX paths relative to `pipeline_dir`, sorted.
    """
    members = []
    for path in pipeline_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ZIP_SUFFIXES:
            continue
        relative = path.relative_to(pipeline_dir)
        if relative.parts[0] == ZIP_EXCLUDED_DIR:
            continue
        members.append(relative.as_posix())
    return sorted(members)


def matching_files(root: Path, patterns: tuple[str, ...]) -> list[str]:
    """List the files under `root` that match any of the glob patterns.

    Returns
    -------
    list[str]
        Repository-relative POSIX paths, sorted.
    """
    return sorted(
        {p.relative_to(root).as_posix() for pattern in patterns for p in root.glob(pattern) if p.is_file()}
    )


def webapp_bundles(root: Path, version: str) -> dict[str, dict]:
    """Describe every webapps/<name>/app/ bundle that holds at least one file.

    Hidden files (`.gitkeep`, `.DS_Store`) are not part of a bundle, so an app/ folder holding only
    those is skipped.

    Returns
    -------
    dict[str, dict]
        `{webapp name: {path, version, files}}`, sorted by name.
    """
    bundles = {}
    for app_dir in sorted((root / "webapps").glob("*/app")):
        files = {
            p.relative_to(app_dir).as_posix(): hash_file(p)
            for p in sorted(app_dir.rglob("*"))
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(app_dir).parts)
        }
        if files:
            name = app_dir.parent.name
            bundles[name] = {"path": f"webapps/{name}/app", "version": version, "files": files}
    return bundles


def build_manifest(root: Path, version: str, repo: str) -> dict:
    """Hash every file a release delivers and say which route each takes.

    Returns
    -------
    dict
        The manifest v2, with every map and list sorted.
    """
    pipelines = {}
    routed = set(matching_files(root, FILESYSTEM_PATTERNS))
    filesystem = sorted(routed)
    for name, kind in registered_pipelines(root).items():
        members = zip_members(root / "pipelines" / name)
        routed.update(f"pipelines/{name}/{m}" for m in members)
        pipelines[name] = {
            "path": f"pipelines/{name}",
            "kind": kind,
            "code": name.replace("_", "-"),
            "zip_files": members,
        }
    return {
        "schema_version": 2,
        "version": version,
        "repo": repo,
        "files": {p: hash_file(root / p) for p in sorted(routed)},
        "filesystem_files": filesystem,
        "pipelines": pipelines,
        "repository_files": {p: hash_file(root / p) for p in matching_files(root, REPOSITORY_PATTERNS)},
        "webapps": webapp_bundles(root, version),
    }


def invariant_errors(manifest: dict) -> list[str]:
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


def validation_errors(manifest: dict, schema_path: Path = SCHEMA_PATH) -> list[str]:
    """Check a manifest against the v2 schema, then against the invariants.

    The invariants assume the schema's shape, so they run only when the schema passes.

    Returns
    -------
    list[str]
        Every problem found; empty when the manifest is valid.
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(manifest)
    ]
    return errors or invariant_errors(manifest)


def main(argv: list[str] | None = None) -> int:
    """Build, validate and write the manifest.

    Returns
    -------
    int
        The exit code: 0 when written, 1 when the checkout or the manifest is invalid.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--version", default=os.environ.get("GITHUB_REF_NAME"), help="release tag")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/name")
    parser.add_argument("--output", type=Path, default=Path("release_manifest.json"))
    args = parser.parse_args(argv)
    if not args.version or not args.repo:
        parser.error("--version and --repo are required outside a GitHub workflow")

    try:
        manifest = build_manifest(args.root.resolve(), args.version, args.repo)
    except ManifestError as error:
        print(f"[ERROR] Cannot build the manifest: {error}", file=sys.stderr)
        return 1
    errors = validation_errors(manifest)
    if errors:
        print("[ERROR] The manifest is invalid, nothing written:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {args.repo} {args.version}")
    print(f"  files: {len(manifest['files'])} ({len(manifest['filesystem_files'])} to the filesystem)")
    for name, spec in manifest["pipelines"].items():
        print(f"  {spec['kind']:<9} {name} -> {spec['code']} ({len(spec['zip_files'])} files in zip)")
    print(f"  repository_files: {len(manifest['repository_files'])}")
    print(f"  webapps: {', '.join(manifest['webapps']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
