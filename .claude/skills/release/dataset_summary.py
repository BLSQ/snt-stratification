"""Summarise every SNT dataset of this workspace, for comparing two workspaces' outputs.

Paste this whole file into ONE cell of a new Jupyter notebook in the workspace, and run it.
It writes /home/hexa/workspace/snt_compare/<workspace slug>_summary.json: for every file in the
latest version of each dataset named in configuration/SNT_config.json, its size, sha256 and, for
tables (.parquet/.csv), the row count, columns, dtypes and an order-independent content hash.
No data values leave the workspace: only names, counts and hashes. Compare two summaries with
compare_summaries.py, next to this file. Used by the `release` skill (SKILL.md, step 3.10).
"""

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from openhexa.sdk import workspace

ROOT = Path("/home/hexa/workspace")
config = json.loads((ROOT / "configuration" / "SNT_config.json").read_text())


def table_summary(df: pd.DataFrame) -> dict:
    """Describe a table by its shape and an order-independent hash of its content.

    Parameters
    ----------
    df : pd.DataFrame
        The table read from a dataset file.

    Returns
    -------
    dict
        ``rows``, ``columns``, ``dtypes`` and ``content_hash`` (sha256 of the sorted row hashes, so
        row order does not matter; values are compared as text).
    """
    as_text = df.astype(str)
    row_hashes = pd.util.hash_pandas_object(as_text, index=False).sort_values().to_numpy()
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "content_hash": hashlib.sha256(row_hashes.tobytes()).hexdigest(),
    }


summary = {
    "workspace": workspace.slug,
    # timezone.utc, not datetime.UTC: runs on the workspace kernel, whose Python may predate 3.11.
    "generated_at": datetime.now(timezone.utc).isoformat(  # ruff: ignore[datetime-timezone-utc]
        timespec="seconds"
    ),
    "datasets": {},
}
for key, slug in config["SNT_DATASET_IDENTIFIERS"].items():
    try:
        dataset = workspace.get_dataset(slug)
    except Exception as e:
        dataset = None
        print(f"{key}: {slug} not readable ({e})")
    if dataset is None or dataset.latest_version is None:
        summary["datasets"][key] = {"slug": slug, "present": False}
        continue
    version = dataset.latest_version
    files = {}
    for f in version.files:
        content = requests.get(f.download_url, timeout=600).content
        entry = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        suffix = Path(f.filename).suffix.lower()
        try:
            if suffix == ".parquet":
                entry |= table_summary(pd.read_parquet(io.BytesIO(content)))
            elif suffix == ".csv":
                entry |= table_summary(pd.read_csv(io.BytesIO(content), low_memory=False))
        except Exception as e:
            entry["read_error"] = str(e)
        files[f.filename] = entry
    summary["datasets"][key] = {"slug": slug, "present": True, "version": version.name, "files": files}
    print(f"{key}: {slug}, version {version.name}, {len(files)} file(s)")

out = ROOT / "snt_compare" / f"{workspace.slug}_summary.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, indent=2))
print(f"Written: {out}")
