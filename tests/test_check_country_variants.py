"""tools/check_country_variants.py: the snt_variant header, the placement rules, drift and --stamp.

The git listing (candidate_files) is not exercised here; CI runs the script on the real repo.
"""

import hashlib
import json
from pathlib import Path

import pytest
from check_country_variants import check, classify, main, stamp

GENERIC = "pipelines/p/code/snt_p.ipynb"
VARIANT = "pipelines/p/code/snt_p_NER.ipynb"
HOOK = "pipelines/p/code/NER_fix.ipynb"


def write_notebook(root: Path, name: str, header: dict | None = None, text: str = "x") -> str:
    """Write a minimal notebook, with an snt_variant header if given.

    Returns
    -------
    str
        Its path relative to root, as git would list it.
    """
    metadata = {"kernelspec": {"name": "ir"}}
    if header is not None:
        metadata["snt_variant"] = header
    notebook = {"cells": [{"cell_type": "code", "source": [text]}], "metadata": metadata, "nbformat": 4}
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notebook, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    return name


def variant_header(**changes: object) -> dict:
    """Build a valid variant header for VARIANT, with fields overridden.

    Returns
    -------
    dict
        The header.
    """
    header = {
        "kind": "variant",
        "country": "NER",
        "variant_of": "snt_p.ipynb",
        "base_sha256": None,
        "base_ref": "snt_development, before the import",
        "reason": "Niger needs it",
        "tickets": ["SNT25-1"],
    }
    return header | changes


def hook_header(**changes: object) -> dict:
    """Build a valid hook header for HOOK, with fields overridden.

    Returns
    -------
    dict
        The header.
    """
    return variant_header(kind="hook", variant_of=None, base_ref=None) | changes


def digest(root: Path, name: str) -> str:
    """Hash a file under root.

    Returns
    -------
    str
        Its sha256 hex digest.
    """
    return hashlib.sha256((root / name).read_bytes()).hexdigest()


def messages(findings: list) -> list[str]:
    """Flatten findings for comparison.

    Returns
    -------
    list[str]
        `path: message` per finding.
    """
    return [f"{f.path}: {f.message}" for f in findings]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("snt_p_NER.ipynb", ("variant", "NER")),
        ("NER_pyramid_format.ipynb", ("hook", "NER")),
        ("snt_p.ipynb", None),
        ("snt_p_ner.ipynb", None),
        ("snt_p_NIGER.ipynb", None),
        ("snt_p_NER.r", None),
        ("NER_x_BDI.ipynb", ("ambiguous", "")),
    ],
)
def test_classify(name: str, expected: tuple | None) -> None:
    """Only three uppercase letters after the last or before the first underscore count."""
    assert classify(name) == expected


def test_no_country_notebook_passes(tmp_path: Path) -> None:
    """A repo without variants has nothing to report."""
    files = [write_notebook(tmp_path, GENERIC), "README.md"]
    assert check(tmp_path, files) == ([], [], 0)


def test_aligned_variant_and_hook_pass(tmp_path: Path) -> None:
    """A variant stamped with its generic's current sha256, and a valid hook, are clean."""
    generic = write_notebook(tmp_path, GENERIC)
    variant = write_notebook(tmp_path, VARIANT, variant_header(base_sha256=digest(tmp_path, generic)))
    hook = write_notebook(tmp_path, HOOK, hook_header())
    assert check(tmp_path, [generic, variant, hook]) == ([], [], 2)


def test_unknown_base_warns(tmp_path: Path) -> None:
    """base_sha256 null is a warning, not an error: the fork point is unknown."""
    files = [write_notebook(tmp_path, GENERIC), write_notebook(tmp_path, VARIANT, variant_header())]
    errors, warnings, _ = check(tmp_path, files)
    assert errors == []
    assert messages(warnings) == [
        f"{VARIANT}: its fork point from `snt_p.ipynb` is unknown; compare the two, then --stamp"
    ]


def test_changed_generic_warns(tmp_path: Path) -> None:
    """A generic edited after the stamp makes the variant stale, naming the base_ref."""
    generic = write_notebook(tmp_path, GENERIC)
    variant = write_notebook(
        tmp_path, VARIANT, variant_header(base_sha256=digest(tmp_path, generic), base_ref="v0.3.0")
    )
    write_notebook(tmp_path, GENERIC, text="changed")
    errors, warnings, _ = check(tmp_path, [generic, variant])
    assert errors == []
    assert messages(warnings) == [
        f"{VARIANT}: `snt_p.ipynb` has changed since v0.3.0; review the variant, then --stamp"
    ]


def test_missing_header_fails(tmp_path: Path) -> None:
    """A country notebook without a header fails."""
    files = [write_notebook(tmp_path, GENERIC), write_notebook(tmp_path, VARIANT)]
    errors, warnings, _ = check(tmp_path, files)
    assert messages(errors) == [f"{VARIANT}: no `snt_variant` header in the notebook metadata"]
    assert warnings == []


def test_missing_field_fails(tmp_path: Path) -> None:
    """Every header field is required, even when its value may be null."""
    header = variant_header()
    del header["tickets"]
    files = [write_notebook(tmp_path, GENERIC), write_notebook(tmp_path, VARIANT, header)]
    assert messages(check(tmp_path, files)[0]) == [f"{VARIANT}: header field `tickets` is missing"]


def test_header_contradicting_the_name_fails(tmp_path: Path) -> None:
    """kind, country and variant_of must match the file name."""
    header = variant_header(kind="hook", country="BDI", variant_of="other.ipynb")
    files = [write_notebook(tmp_path, GENERIC), write_notebook(tmp_path, VARIANT, header)]
    assert messages(check(tmp_path, files)[0]) == [
        f"{VARIANT}: header says kind `hook`, the file name says `variant`",
        f"{VARIANT}: header says country `BDI`, the file name says `NER`",
        f"{VARIANT}: header says variant_of `other.ipynb`, the file name says `snt_p.ipynb`",
    ]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"base_sha256": "abc"}, "`base_sha256` must be null or 64 lowercase hex characters"),
        ({"base_ref": ""}, "`base_ref` must be null or a non-empty string"),
        ({"reason": " "}, "`reason` must say why the country needs this notebook"),
        ({"tickets": "SNT25-1"}, "`tickets` must be a list of strings (it may be empty)"),
    ],
)
def test_bad_field_values_fail(tmp_path: Path, changes: dict, message: str) -> None:
    """Field values are checked for shape."""
    files = [write_notebook(tmp_path, GENERIC), write_notebook(tmp_path, VARIANT, variant_header(**changes))]
    assert messages(check(tmp_path, files)[0]) == [f"{VARIANT}: {message}"]


def test_hook_with_a_base_fails(tmp_path: Path) -> None:
    """A hook replaces no generic notebook, so it has no variant_of or base_sha256."""
    header = hook_header(variant_of="snt_p.ipynb", base_sha256="0" * 64)
    files = [write_notebook(tmp_path, HOOK, header)]
    assert messages(check(tmp_path, files)[0]) == [
        f"{HOOK}: a hook's `variant_of` must be null",
        f"{HOOK}: a hook's `base_sha256` must be null",
    ]


def test_variant_without_generic_fails(tmp_path: Path) -> None:
    """A variant with nothing to replace never runs; its drift is not checked."""
    files = [write_notebook(tmp_path, VARIANT, variant_header())]
    errors, warnings, _ = check(tmp_path, files)
    assert messages(errors) == [f"{VARIANT}: no generic notebook `snt_p.ipynb` beside it, so it never runs"]
    assert warnings == []


def test_misplaced_notebooks_fail(tmp_path: Path) -> None:
    """Variants belong in code/ or reporting/, hooks in code/; country_specific/ is reported once."""
    generic = write_notebook(tmp_path, "pipelines/p/country_specific/snt_p.ipynb")
    variant = write_notebook(tmp_path, "pipelines/p/country_specific/snt_p_NER.ipynb", variant_header())
    hook = write_notebook(tmp_path, "pipelines/p/reporting/NER_fix.ipynb", hook_header())
    errors, _, seen = check(tmp_path, [generic, variant, hook])
    assert seen == 2
    assert messages(errors) == [
        f"{variant}: a variant must sit in `code/` or `reporting/` of its pipeline, or it never runs",
        f"{hook}: a hook must sit in `code/` of its pipeline, or it never runs",
        "pipelines/p/country_specific: `country_specific/` is on no execution path; move the notebook",
    ]


def test_reporting_variant_passes(tmp_path: Path) -> None:
    """A variant of a report notebook sits in reporting/."""
    generic = write_notebook(tmp_path, "pipelines/p/reporting/snt_p_report.ipynb")
    variant = write_notebook(
        tmp_path,
        "pipelines/p/reporting/snt_p_report_BDI.ipynb",
        variant_header(country="BDI", variant_of="snt_p_report.ipynb", base_sha256=digest(tmp_path, generic)),
    )
    assert check(tmp_path, [generic, variant]) == ([], [], 1)


def test_files_outside_pipelines_are_ignored(tmp_path: Path) -> None:
    """Only pipelines/ is checked; deleted files in the listing are skipped."""
    files = [write_notebook(tmp_path, "docs/x_NER.ipynb"), "pipelines/p/code/gone_NER.ipynb"]
    assert check(tmp_path, files) == ([], [], 0)


def test_stamp_records_the_generic_and_keeps_the_rest(tmp_path: Path) -> None:
    """--stamp writes the generic's sha256 and the ref, changes nothing else, and clears the warning."""
    generic = write_notebook(tmp_path, GENERIC)
    variant = write_notebook(tmp_path, VARIANT, variant_header())
    before = json.loads((tmp_path / variant).read_text(encoding="utf-8"))

    assert stamp(tmp_path, Path(variant), "v0.3.0") == digest(tmp_path, generic)

    after = json.loads((tmp_path / variant).read_text(encoding="utf-8"))
    before["metadata"]["snt_variant"].update(base_sha256=digest(tmp_path, generic), base_ref="v0.3.0")
    assert after == before
    assert (tmp_path / variant).read_text(encoding="utf-8").endswith("}\n")
    assert check(tmp_path, [generic, variant]) == ([], [], 1)


def test_stamp_keeps_crlf_and_missing_final_newline(tmp_path: Path) -> None:
    """A file saved with CRLF and no final newline keeps both."""
    write_notebook(tmp_path, GENERIC)
    variant = write_notebook(tmp_path, VARIANT, variant_header())
    path = tmp_path / variant
    path.write_bytes(path.read_text(encoding="utf-8").rstrip("\n").replace("\n", "\r\n").encode("utf-8"))
    stamp(tmp_path, Path(variant), "v0.3.0")
    raw = path.read_bytes()
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert not raw.endswith(b"\n")


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("hook", "NER_fix.ipynb is not named `<generic>_<CC>.ipynb`"),
        ("no_generic", "no generic notebook snt_p.ipynb beside snt_p_NER.ipynb"),
        ("no_header", "snt_p_NER.ipynb has no `snt_variant` header to update; add it first"),
    ],
)
def test_stamp_refuses(tmp_path: Path, setup: str, message: str) -> None:
    """--stamp only updates the header of a variant that has a generic beside it."""
    if setup == "hook":
        target = write_notebook(tmp_path, HOOK, hook_header())
    else:
        if setup == "no_header":
            write_notebook(tmp_path, GENERIC)
        target = write_notebook(tmp_path, VARIANT, None if setup == "no_header" else variant_header())
    with pytest.raises(ValueError, match="^" + message.replace("(", r"\(").replace(")", r"\)") + "$"):
        stamp(tmp_path, Path(target), "v0.3.0")


def test_main_stamp_needs_ref(tmp_path: Path) -> None:
    """--stamp without --ref is a usage error."""
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(tmp_path), "--stamp", VARIANT])
    assert exc.value.code == 2
