"""Fail if a tracked file breaks rule R1 (country data) or R2 (notebook outputs).

* **R1:** no tracked `.csv`, `.xlsx`, `.parquet`, `.rds` or `.geojson`, whatever its content.
  `.gitignore` blocks them, but `git add -f` gets past it.
* **R2:** no tracked notebook with a cell that has `outputs`. Read from the `.ipynb` JSON itself,
  not with `nbstripout --verify` (see the handover skill): the `nbstripout` filter lives in each
  developer's `.git/config`, so a clone without it commits outputs silently.

Only files in git's index are checked: what a pull request would add. Run by
`.github/workflows/ci.yaml`; by hand, from anywhere::

    python tools/check_tracked_files.py

Exit code 1 if anything failed, else 0.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Rule R1's list. Matched case-insensitively, so `data.CSV` fails too.
DATA_SUFFIXES = {".csv", ".xlsx", ".parquet", ".rds", ".geojson"}


def notebook_problem(path: Path) -> str | None:
    """Say what is wrong with one notebook, if anything.

    Returns
    -------
    str | None
        A short description of the problem, or None if the notebook has no outputs.
    """
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return f"not a readable notebook ({e.__class__.__name__})"
    cells = [i for i, cell in enumerate(notebook.get("cells", [])) if cell.get("outputs")]
    if not cells:
        return None
    shown = ", ".join(str(i) for i in cells[:5]) + (", ..." if len(cells) > 5 else "")
    return f"outputs in {len(cells)} cell(s) (index {shown}): run nbstripout on it"


def problems(root: Path, files: list[str]) -> list[str]:
    """Check the given repository-relative paths against R1 and R2.

    Returns
    -------
    list[str]
        One `path: problem` line per failing file, in the order given.
    """
    found = []
    for name in files:
        suffix = Path(name).suffix.lower()
        if suffix in DATA_SUFFIXES:
            found.append(f"{name}: data file in git (R1); remove it with `git rm --cached`")
        elif suffix == ".ipynb" and (root / name).is_file():
            problem = notebook_problem(root / name)
            if problem:
                found.append(f"{name}: {problem} (R2)")
    return found


def tracked_files(root: Path) -> list[str]:
    """List the paths in git's index.

    Returns
    -------
    list[str]
        Repository-relative paths, as git prints them.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    """Check every tracked file and print the failures.

    Returns
    -------
    int
        0 if nothing failed, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repo)")
    root = parser.parse_args(argv).root.resolve()
    files = tracked_files(root)
    found = problems(root, files)
    for line in found:
        print(f"[ERROR] {line}")
    n_notebooks = sum(1 for f in files if f.lower().endswith(".ipynb"))
    print(f"{len(files)} tracked files ({n_notebooks} notebooks) checked, {len(found)} problem(s).")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
