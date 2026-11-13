"""tools/check_links.py: which links count as broken, on small Markdown trees built per test.

The git file listing (markdown_files) is not exercised here; CI runs the script on the real repo.
"""

from pathlib import Path

import pytest
from check_links import broken_links, github_slug


def write(root: Path, name: str, text: str) -> Path:
    """Write a UTF-8 file under root, creating its folders.

    Returns
    -------
    Path
        The file written.
    """
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def check(root: Path, text: str) -> list[str]:
    """Check the links of one file, a.md, written with the given text.

    Returns
    -------
    list[str]
        The broken-link lines.
    """
    _, broken = broken_links(root, [write(root, "a.md", text)])
    return broken


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Phase 3 — Tooling and CI", "phase-3--tooling-and-ci"),
        ("`ci.yaml`: the checks", "ciyaml-the-checks"),
        ("[R1](x.md) No data", "r1-no-data"),
        ("7.3 CI coverage", "73-ci-coverage"),
        ("Données de routine", "données-de-routine"),
    ],
)
def test_github_slug(heading: str, slug: str) -> None:
    """Headings slug the way GitHub renders them: punctuation dropped, spaces to hyphens."""
    assert github_slug(heading) == slug


def test_resolving_links_pass(tmp_path: Path) -> None:
    """A file, a folder, a heading anchor, a duplicate heading and an explicit anchor all resolve."""
    write(tmp_path, "docs/b.md", '# Title\n\n## Part\n\n## Part\n\n<a id="r1"></a>\n')
    (tmp_path / "folder").mkdir()
    text = (
        "[b](docs/b.md) [dir](folder/) [t](docs/b.md#title) [p1](docs/b.md#part-1) "
        "[r1](docs/b.md#R1) [self](#top)\n\n# Top\n"
    )
    assert check(tmp_path, text) == []


def test_missing_file_and_anchor_fail(tmp_path: Path) -> None:
    """A missing file and a missing anchor are each reported with their line."""
    write(tmp_path, "b.md", "# Title\n")
    broken = check(tmp_path, "intro\n[x](nope.md)\n[y](b.md#nope)\n")
    assert broken == ["a.md:2: missing file   nope.md", "a.md:3: missing anchor b.md#nope"]


def test_external_images_and_code_are_skipped(tmp_path: Path) -> None:
    """URLs, images, code spans and fenced blocks are not checked."""
    text = (
        "[w](https://example.org/x.md) [m](mailto:a@b.c) ![img](missing.png) `[c](missing.md)`\n"
        "```\n[f](missing.md)\n```\n"
    )
    n_links, broken = broken_links(tmp_path, [write(tmp_path, "a.md", text)])
    assert (n_links, broken) == (0, [])


def test_anchor_into_non_markdown_is_not_checked(tmp_path: Path) -> None:
    """A fragment into a non-Markdown file (e.g. a line anchor into code) only needs the file."""
    write(tmp_path, "tool.py", "x = 1\n")
    assert check(tmp_path, "[l](tool.py#L1)\n") == []
