"""tools/check_tracked_files.py: the R1 (data files) and R2 (notebook outputs) checks.

The git index listing (tracked_files) is not exercised here; CI runs the script on the real repo.
"""

import json
from pathlib import Path

import pytest
from check_tracked_files import problems


def notebook(root: Path, name: str, cells: list[dict]) -> str:
    """Write a minimal notebook with the given cells.

    Returns
    -------
    str
        Its path relative to root, as git would list it.
    """
    (root / name).write_text(json.dumps({"cells": cells, "nbformat": 4}), encoding="utf-8")
    return name


@pytest.mark.parametrize("name", ["x.csv", "a/b.XLSX", "c.parquet", "d.rds", "e.geojson"])
def test_data_file_fails(tmp_path: Path, name: str) -> None:
    """Every R1 suffix fails, in any case, without reading the file."""
    assert problems(tmp_path, [name]) == [f"{name}: data file in git (R1); remove it with `git rm --cached`"]


def test_other_files_pass(tmp_path: Path) -> None:
    """JSON, Markdown, code and images are not R1 data files."""
    assert problems(tmp_path, ["registry.json", "readme.md", "pipeline.py", "map.png", "csv.r"]) == []


def test_stripped_notebook_passes(tmp_path: Path) -> None:
    """Empty outputs pass; a leftover execution_count alone is not a failure (handover skill)."""
    cells = [
        {"cell_type": "code", "outputs": [], "execution_count": 3, "source": ["1"]},
        {"cell_type": "markdown", "source": ["# t"]},
    ]
    assert problems(tmp_path, [notebook(tmp_path, "n.ipynb", cells)]) == []


def test_notebook_with_outputs_fails(tmp_path: Path) -> None:
    """Any cell with outputs fails the notebook, and the cells are named."""
    output = {"output_type": "stream", "name": "stdout", "text": ["DISTRICT,CASES\n"]}
    cells = [
        {"cell_type": "code", "outputs": [], "source": []},
        {"cell_type": "code", "outputs": [output], "source": []},
    ]
    found = problems(tmp_path, [notebook(tmp_path, "n.ipynb", cells)])
    assert found == ["n.ipynb: outputs in 1 cell(s) (index 1): run nbstripout on it (R2)"]


def test_unreadable_notebook_fails(tmp_path: Path) -> None:
    """A notebook that is not JSON cannot be shown to be stripped, so it fails."""
    (tmp_path / "bad.ipynb").write_text("{not json", encoding="utf-8")
    assert problems(tmp_path, ["bad.ipynb"]) == ["bad.ipynb: not a readable notebook (JSONDecodeError) (R2)"]


def test_deleted_notebook_is_skipped(tmp_path: Path) -> None:
    """A path in the index but not on disk (deleted, not yet staged) is not read."""
    assert problems(tmp_path, ["gone.ipynb"]) == []
