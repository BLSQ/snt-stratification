"""Check the relative links and #anchors in the repository's Markdown files.

Every inline link `[text](target)` that is not an external URL must point at a file or folder that
exists, and a `#fragment` into a Markdown file must match an anchor there: a heading (GitHub slug
rules, with -1, -2 for duplicates) or an explicit `<a id=...>` / `<a name=...>`. Links inside code
fences and code spans are not links and are skipped.

The files checked are the ones git knows about (tracked, plus untracked files not ignored), so
`ignore/` and tool caches are skipped by `.gitignore`, not by a list kept here. Run by
`.github/workflows/ci.yaml`; by hand, from anywhere::

    python tools/check_links.py

Exit code 1 if a link is broken, else 0. Ported from the old repo's git-ignored
`ignore/docs-restructure/check_links.py` (BACKLOG TOOL-5).
"""

import argparse
import re
import subprocess
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LINK_RE = re.compile(r"(?<!!)\[(?:[^\]\[]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
EXPLICIT_ANCHOR_RE = re.compile(r"<a\s+(?:name|id)=\"([^\"]+)\"")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
URL_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)  # http:, mailto:, ...


def github_slug(text: str) -> str:
    """Return the anchor GitHub generates for a heading text.

    Returns
    -------
    str
        Lowercased slug: markup stripped, punctuation (except - and _) removed, spaces to hyphens.
    """
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> their text
    text = re.sub(r"<[^>]+>", "", text)  # inline html
    text = text.replace("`", "").strip().lower()
    kept = [ch for ch in text if ch in "-_ " or unicodedata.category(ch).startswith(("L", "N", "M"))]
    return "".join(kept).replace(" ", "-")


def outside_fences(md: Path) -> Iterator[tuple[int, str]]:
    """Yield the lines of a Markdown file that are not inside a code fence.

    Yields
    ------
    tuple[int, str]
        (1-based line number, line text).
    """
    in_fence = False
    for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield lineno, line


def anchors_of(md: Path, cache: dict[Path, set[str]]) -> set[str]:
    """Return every anchor a Markdown file defines.

    Returns
    -------
    set[str]
        Heading slugs (with GitHub's -1, -2 suffixes for duplicates) plus explicit <a name/id>.
    """
    if md not in cache:
        seen: dict[str, int] = {}
        anchors: set[str] = set()
        for _, line in outside_fences(md):
            anchors.update(EXPLICIT_ANCHOR_RE.findall(line))
            m = HEADING_RE.match(line)
            if not m:
                continue
            slug = github_slug(m.group(2))
            n = seen.get(slug, 0)
            anchors.add(slug if n == 0 else f"{slug}-{n}")
            seen[slug] = n + 1
        cache[md] = anchors
    return cache[md]


def links_of(md: Path) -> Iterator[tuple[int, str]]:
    """Yield each inline link target outside code fences and code spans.

    Yields
    ------
    tuple[int, str]
        (1-based line number, link target).
    """
    for lineno, line in outside_fences(md):
        # Blank out code spans, keeping offsets, so the target is read from the original line.
        masked = CODE_SPAN_RE.sub(lambda m: "x" * len(m.group(0)), line)
        for m in LINK_RE.finditer(masked):
            yield lineno, line[m.start(1) : m.end(1)]


def broken_links(root: Path, files: list[Path]) -> tuple[int, list[str]]:
    """Check every relative link in the given Markdown files.

    Returns
    -------
    tuple[int, list[str]]
        The number of relative links checked, and one `path:line: problem target` per broken link.
    """
    cache: dict[Path, set[str]] = {}
    broken = []
    n_links = 0
    for md in files:
        for lineno, target in links_of(md):
            if URL_SCHEME_RE.match(target):
                continue
            n_links += 1
            path_part, _, frag = target.partition("#")
            dest = md if not path_part else (md.parent / path_part).resolve()
            where = f"{md.relative_to(root)}:{lineno}"
            if not dest.exists():
                broken.append(f"{where}: missing file   {target}")
            elif frag and dest.is_file() and dest.suffix.lower() == ".md":
                if frag.lower() not in anchors_of(dest, cache):
                    broken.append(f"{where}: missing anchor {target}")
    return n_links, broken


def markdown_files(root: Path) -> list[Path]:
    """List the Markdown files git knows about: tracked, plus untracked and not ignored.

    Returns
    -------
    list[Path]
        Sorted absolute paths of the .md files that exist on disk.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    paths = {root / p for p in out.split("\0") if p}
    return sorted(p for p in paths if p.is_file())  # a tracked file deleted on disk is skipped


def main(argv: list[str] | None = None) -> int:
    """Check all links and print the broken ones.

    Returns
    -------
    int
        0 if all links resolve, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repo)")
    root = parser.parse_args(argv).root.resolve()
    files = markdown_files(root)
    n_links, broken = broken_links(root, files)
    for line in broken:
        print(f"[ERROR] {line}")
    print(f"{len(files)} Markdown files, {n_links} relative links checked, {len(broken)} broken.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
