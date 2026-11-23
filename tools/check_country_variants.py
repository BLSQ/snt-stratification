"""Check the country notebooks in `pipelines/`: their `snt_variant` header, and drift (ADR 0046).

Two kinds of country notebook are recognised by their file name:

* **variant** `<generic>_<CC>.ipynb`, beside its generic notebook in `code/` or `reporting/`. It runs
  instead of the generic one in the workspace whose `COUNTRY_CODE` is `<CC>`.
* **hook** `<CC>_<name>.ipynb`, in `code/`. `pipeline.py` calls it by name for country `<CC>`.

`<CC>` is three uppercase letters. Each one carries, in its notebook metadata, the header::

    "snt_variant": {
      "kind": "variant",                       # or "hook"
      "country": "NER",                        # the <CC> of the file name
      "variant_of": "snt_dhis2_incidence.ipynb",   # null for a hook
      "base_sha256": "<64 hex>",   # sha256 of the generic's bytes when last aligned; null = unknown
      "base_ref": "v0.3.0",        # release or commit to diff the generic against; may be null
      "reason": "Why the country needs it",
      "tickets": ["SNT25-363"]
    }

**Errors** (exit code 1): a missing or malformed header; a header that contradicts the file name;
a variant with no generic notebook beside it; a variant outside `code/` or `reporting/`, or a hook
outside `code/`; a name that is both a variant and a hook; any `country_specific/` folder (it is on
no execution path). **Warnings** (exit code 0): a variant whose `base_sha256` is null, or differs
from the generic notebook's current sha256. The generic has changed since the variant was aligned
with it; review the difference, then record the new base with `--stamp`.

Files are git's tracked and untracked-but-not-ignored ones, so a new notebook is checked before
`git add`. Run by `.github/workflows/ci.yaml`, where warnings also become annotations; by hand::

    python tools/check_country_variants.py
    python tools/check_country_variants.py --stamp pipelines/<name>/code/<generic>_<CC>.ipynb --ref v0.3.0
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

HEADER_KEY = "snt_variant"
HEADER_FIELDS = ("kind", "country", "variant_of", "base_sha256", "base_ref", "reason", "tickets")
VARIANT_RE = re.compile(r"^(?P<generic>.+)_(?P<cc>[A-Z]{3})$")
HOOK_RE = re.compile(r"^(?P<cc>[A-Z]{3})_(?P<name>.+)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VARIANT_FOLDERS = ("code", "reporting")
HOOK_FOLDERS = ("code",)
INERT_FOLDER = "country_specific"


@dataclass(frozen=True)
class Finding:
    """One problem found, with the repository-relative path it is about."""

    path: str
    message: str


def sha256(path: Path) -> str:
    """Hash a file's raw bytes, as the checker and `NOTEBOOK_OVERRIDES` do (ADR 0028).

    Returns
    -------
    str
        The hex digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(name: str) -> tuple[str, str] | None:
    """Tell a country notebook from any other file by its name.

    Returns
    -------
    tuple[str, str] | None
        `("variant", CC)`, `("hook", CC)`, `("ambiguous", "")` for a name matching both patterns, or
        None for a file that is not a country notebook.
    """
    path = PurePosixPath(name)
    if path.suffix != ".ipynb":
        return None
    variant = VARIANT_RE.match(path.stem)
    hook = HOOK_RE.match(path.stem)
    if variant and hook:
        return ("ambiguous", "")
    if variant:
        return ("variant", variant["cc"])
    if hook:
        return ("hook", hook["cc"])
    return None


def read_header(path: Path) -> tuple[dict | None, str | None]:
    """Read the `snt_variant` header of a notebook.

    Returns
    -------
    tuple[dict | None, str | None]
        The header and None, or None and a description of why it cannot be read.
    """
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return None, f"not a readable notebook ({e.__class__.__name__})"
    header = notebook.get("metadata", {}).get(HEADER_KEY)
    if header is None:
        return None, f"no `{HEADER_KEY}` header in the notebook metadata"
    if not isinstance(header, dict):
        return None, f"`{HEADER_KEY}` is not an object"
    return header, None


def header_errors(header: dict, kind: str, cc: str, generic_name: str | None) -> list[str]:
    """Check a header's fields against the file name.

    Returns
    -------
    list[str]
        One message per problem; empty when the header is consistent.
    """
    errors = [f"header field `{f}` is missing" for f in HEADER_FIELDS if f not in header]
    if errors:
        return errors
    if header["kind"] != kind:
        errors.append(f"header says kind `{header['kind']}`, the file name says `{kind}`")
    if header["country"] != cc:
        errors.append(f"header says country `{header['country']}`, the file name says `{cc}`")
    if kind == "variant" and header["variant_of"] != generic_name:
        errors.append(f"header says variant_of `{header['variant_of']}`, the file name says `{generic_name}`")
    if kind == "hook":
        errors += [
            f"a hook's `{f}` must be null" for f in ("variant_of", "base_sha256") if header[f] is not None
        ]
    base = header["base_sha256"]
    if base is not None and not (isinstance(base, str) and SHA256_RE.match(base)):
        errors.append("`base_sha256` must be null or 64 lowercase hex characters")
    if header["base_ref"] is not None and not (isinstance(header["base_ref"], str) and header["base_ref"]):
        errors.append("`base_ref` must be null or a non-empty string")
    if not (isinstance(header["reason"], str) and header["reason"].strip()):
        errors.append("`reason` must say why the country needs this notebook")
    if not (isinstance(header["tickets"], list) and all(isinstance(t, str) for t in header["tickets"])):
        errors.append("`tickets` must be a list of strings (it may be empty)")
    return errors


def check(root: Path, files: list[str]) -> tuple[list[Finding], list[Finding], int]:
    """Check the country notebooks among the given repository-relative paths.

    Returns
    -------
    tuple[list[Finding], list[Finding], int]
        Errors, warnings, and the number of country notebooks seen.
    """
    errors: list[Finding] = []
    warnings: list[Finding] = []
    seen = 0
    inert_folders = set()
    for name in files:
        path = PurePosixPath(name)
        if path.parts[:1] != ("pipelines",) or not (root / name).is_file():
            continue
        if INERT_FOLDER in path.parts[:-1]:
            inert_folders.add(str(PurePosixPath(*path.parts[: path.parts.index(INERT_FOLDER) + 1])))
        found = classify(name)
        if found is None:
            continue
        seen += 1
        kind, cc = found
        if kind == "ambiguous":
            errors.append(Finding(name, "the name is both `<generic>_<CC>` and `<CC>_<name>`; rename it"))
            continue
        folders = VARIANT_FOLDERS if kind == "variant" else HOOK_FOLDERS
        if path.parent.name not in folders:
            where = " or ".join(f"`{f}/`" for f in folders)
            errors.append(Finding(name, f"a {kind} must sit in {where} of its pipeline, or it never runs"))
        generic_name = f"{VARIANT_RE.match(path.stem)['generic']}.ipynb" if kind == "variant" else None
        generic = root / path.parent / generic_name if generic_name else None
        if generic is not None and not generic.is_file():
            errors.append(Finding(name, f"no generic notebook `{generic_name}` beside it, so it never runs"))
        header, problem = read_header(root / name)
        if problem:
            errors.append(Finding(name, problem))
            continue
        problems = header_errors(header, kind, cc, generic_name)
        errors += [Finding(name, p) for p in problems]
        if problems or generic is None or not generic.is_file():
            continue
        if header["base_sha256"] is None:
            warnings.append(
                Finding(
                    name, f"its fork point from `{generic_name}` is unknown; compare the two, then --stamp"
                )
            )
        elif header["base_sha256"] != sha256(generic):
            since = f" since {header['base_ref']}" if header["base_ref"] else ""
            warnings.append(
                Finding(name, f"`{generic_name}` has changed{since}; review the variant, then --stamp")
            )
    errors += [
        Finding(f, "`country_specific/` is on no execution path; move the notebook") for f in inert_folders
    ]
    return errors, warnings, seen


def stamp(root: Path, variant: Path, ref: str) -> str:
    """Record the generic notebook's current sha256 and `ref` as a variant's base.

    The file's other bytes are kept: JSON written as Jupyter writes it (sorted keys, indent 1), with the
    original line endings and final newline.

    Returns
    -------
    str
        The new `base_sha256`.

    Raises
    ------
    ValueError
        If the file is not a variant with a header, or has no generic notebook beside it.
    """
    variant = variant if variant.is_absolute() else root / variant
    found = classify(variant.name)
    if found is None or found[0] != "variant":
        raise ValueError(f"{variant.name} is not named `<generic>_<CC>.ipynb`")
    generic = variant.with_name(f"{VARIANT_RE.match(variant.stem)['generic']}.ipynb")
    if not generic.is_file():
        raise ValueError(f"no generic notebook {generic.name} beside {variant.name}")
    raw = variant.read_bytes().decode("utf-8")
    notebook = json.loads(raw)
    if not isinstance(notebook.get("metadata", {}).get(HEADER_KEY), dict):
        raise ValueError(f"{variant.name} has no `{HEADER_KEY}` header to update; add it first")
    digest = sha256(generic)
    notebook["metadata"][HEADER_KEY].update(base_sha256=digest, base_ref=ref)
    text = json.dumps(notebook, sort_keys=True, indent=1, ensure_ascii=False)
    if raw.endswith("\n"):
        text += "\n"
    if "\r\n" in raw:
        text = text.replace("\n", "\r\n")
    variant.write_bytes(text.encode("utf-8"))
    return digest


def candidate_files(root: Path) -> list[str]:
    """List git's tracked files and its untracked, not-ignored ones.

    Returns
    -------
    list[str]
        Repository-relative paths, as git prints them.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted({p for p in out.split("\0") if p})


def main(argv: list[str] | None = None) -> int:
    """Check every country notebook, or stamp one, and print the result.

    Returns
    -------
    int
        0 if nothing failed (warnings do not fail), 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repo)")
    parser.add_argument(
        "--stamp", type=Path, metavar="VARIANT", help="record the generic's sha256 as its base"
    )
    parser.add_argument("--ref", help="with --stamp: the release or commit the variant is now aligned with")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.stamp:
        if not args.ref:
            parser.error("--stamp needs --ref (the release or commit the variant is now aligned with)")
        try:
            digest = stamp(root, args.stamp, args.ref)
        except ValueError as e:
            print(f"[ERROR] {e}")
            return 1
        print(f"Stamped {args.stamp}: base_sha256 {digest}, base_ref {args.ref}.")
        return 0

    errors, warnings, seen = check(root, candidate_files(root))
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    for f in errors:
        print(f"[ERROR] {f.path}: {f.message}")
    for f in warnings:
        print(f"[WARNING] {f.path}: {f.message}")
        if in_ci:
            print(f"::warning file={f.path}::{f.message}")
    print(f"{seen} country notebook(s) checked, {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
