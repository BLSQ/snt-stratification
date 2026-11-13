"""Build the release assets that sit beside release_manifest.json on a GitHub release.

From a manifest written by `tools/build_manifest.py` and the checkout it describes:

* `<repo name>-<tag>.tar.gz`, the **slim tarball**: exactly the manifest's `files`, under one top
  folder `<repo name>-<tag>/` at their repository paths. That is the layout of GitHub's source
  tarball, which the deployers read today (one top-level directory), so their switch to this
  asset in Phase 4 is a change of URL.
* `webapp-<name>-<tag>.zip`, one per entry of the manifest's `webapps` block: the bundle's files at
  their paths relative to `app/`, plus a stamped `version.json` (tag, commit, build time).

Every file is checked against its manifest hash before it is packed, so the assets cannot disagree
with the manifest they are published with. Contract: contracts/release_manifest.md.

Run by `.github/workflows/release.yaml` after `build_manifest.py`; by hand::

    python tools/build_manifest.py --version v0.1.0 --repo BLSQ/snt-stratification \
        --output dist/release_manifest.json
    python tools/build_release_assets.py --manifest dist/release_manifest.json \
        --commit "$(git rev-parse HEAD)"
"""

import argparse
import json
import os
import re
import sys
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from build_manifest import hash_file, validation_errors

# Stamped into each webapp zip; not part of the committed bundle, so not in the manifest.
VERSION_FILE = "version.json"

COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
BUILT_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# The version goes into asset file names, so it must be one plain path segment (a tag like
# "v0.1.0" or "v0.1.0-rc.1", or a test name on a manual run).
VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]*")


class AssetError(Exception):
    """The assets cannot be built, e.g. a file on disk differs from its manifest hash."""


def hash_errors(base: Path, files: dict[str, str], label: str) -> list[str]:
    """Compare files on disk with the hashes a manifest gives them.

    Returns
    -------
    list[str]
        One message per missing or changed file; empty when every file matches.
    """
    errors = []
    for path, expected in files.items():
        target = base / path
        if not target.is_file():
            errors.append(f"{label}{path}: listed in the manifest, missing on disk")
        elif hash_file(target) != expected:
            errors.append(f"{label}{path}: sha256 differs from the manifest")
    return errors


def archive_stem(manifest: dict) -> str:
    """Name the slim tarball and its top folder after the repository and the tag.

    Returns
    -------
    str
        `<repo name>-<tag>`, e.g. `snt-stratification-v0.1.0`.
    """
    return f"{manifest['repo'].split('/')[-1]}-{manifest['version']}"


def version_stamp(version: str, commit: str, built_at: str) -> dict[str, str]:
    """Build the content of a webapp's `version.json`.

    Returns
    -------
    dict[str, str]
        `{"version": tag, "commit": full git commit hash, "built_at": UTC time, ISO 8601}`.

    Raises
    ------
    AssetError
        When the commit is not a full 40-character hash or the time is not `YYYY-MM-DDTHH:MM:SSZ`.
    """
    if not COMMIT_PATTERN.fullmatch(commit):
        raise AssetError(f"commit {commit!r} is not a full 40-character lowercase git hash")
    try:
        datetime.strptime(built_at, BUILT_AT_FORMAT)
    except ValueError as error:
        raise AssetError(f"built_at {built_at!r} is not YYYY-MM-DDTHH:MM:SSZ") from error
    return {"version": version, "commit": commit, "built_at": built_at}


def _normalised(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Drop the build machine's user and group from a tar member.

    Returns
    -------
    tarfile.TarInfo
        The same member, owned by uid/gid 0 with no names.
    """
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def write_tarball(root: Path, manifest: dict, output_dir: Path) -> Path:
    """Pack the manifest's `files` under one top folder, in sorted order.

    Returns
    -------
    Path
        The written `<repo name>-<tag>.tar.gz`.
    """
    stem = archive_stem(manifest)
    path = output_dir / f"{stem}.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for file in sorted(manifest["files"]):
            tar.add(root / file, arcname=f"{stem}/{file}", recursive=False, filter=_normalised)
    return path


def write_webapp_zip(root: Path, name: str, spec: dict, stamp: dict, output_dir: Path) -> Path:
    """Pack one webapp bundle with its stamped `version.json` at the zip's root.

    Returns
    -------
    Path
        The written `webapp-<name>-<tag>.zip`.
    """
    app_dir = root / spec["path"]
    path = output_dir / f"webapp-{name}-{spec['version']}.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(spec["files"]):
            bundle.write(app_dir / file, arcname=file)
        bundle.writestr(VERSION_FILE, json.dumps(stamp, indent=2) + "\n")
    return path


def build_assets(root: Path, manifest: dict, output_dir: Path, commit: str, built_at: str) -> list[Path]:
    """Check the checkout against the manifest, then write the slim tarball and the webapp zips.

    Nothing is written unless every check passes.

    Returns
    -------
    list[Path]
        The written assets: the tarball first, then one zip per webapp in name order.

    Raises
    ------
    AssetError
        When the manifest is invalid, its version cannot name a file, a file differs from its
        hash, a bundle already holds a `version.json`, or the commit or time cannot be stamped.
    """
    errors = validation_errors(manifest)
    if errors:
        raise AssetError("the manifest is invalid: " + "; ".join(errors))
    if not VERSION_PATTERN.fullmatch(manifest["version"]):
        raise AssetError(
            f"version {manifest['version']!r} cannot name a file: use letters, digits, '.', '_', '-'"
        )
    webapps = manifest.get("webapps", {})
    errors = hash_errors(root, manifest["files"], "")
    for spec in webapps.values():
        errors += hash_errors(root / spec["path"], spec["files"], f"{spec['path']}/")
        if VERSION_FILE in spec["files"]:
            errors.append(
                f"{spec['path']}/{VERSION_FILE}: the release stamps this file, the bundle must not hold one"
            )
    if errors:
        raise AssetError("; ".join(errors))
    stamp = version_stamp(manifest["version"], commit, built_at)

    output_dir.mkdir(parents=True, exist_ok=True)
    written = [write_tarball(root, manifest, output_dir)]
    for name, spec in sorted(webapps.items()):
        written.append(write_webapp_zip(root, name, spec, stamp, output_dir))
    return written


def main(argv: list[str] | None = None) -> int:
    """Read the manifest, build and write the assets.

    Returns
    -------
    int
        The exit code: 0 when written, 1 when the manifest, the checkout or the stamp is invalid.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True, help="release_manifest.json to build from")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--output-dir", type=Path, help="where to write (default: the manifest's folder)")
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA"), help="full git commit hash")
    parser.add_argument(
        "--built-at",
        default=datetime.now(UTC).strftime(BUILT_AT_FORMAT),
        help="UTC build time for version.json (default: now)",
    )
    args = parser.parse_args(argv)
    if not args.commit:
        parser.error("--commit is required outside a GitHub workflow")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    output_dir = args.output_dir or args.manifest.parent
    try:
        written = build_assets(args.root.resolve(), manifest, output_dir, args.commit, args.built_at)
    except AssetError as error:
        print(f"[ERROR] Cannot build the release assets, nothing written: {error}", file=sys.stderr)
        return 1

    print(f"Wrote the release assets for {manifest['repo']} {manifest['version']} to {output_dir}:")
    print(f"  {written[0].name} ({len(manifest['files'])} files)")
    for path in written[1:]:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
