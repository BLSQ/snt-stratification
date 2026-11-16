"""Compare two dataset summaries written by dataset_summary.py.

Usage (from the repo root; A = the baseline workspace, B = the candidate):
    python3 .claude/skills/release/compare_summaries.py A_summary.json B_summary.json

Pass = every dataset present in both, the same file names, and for every table the same columns
(names and order) and row count. "content" (identical values, row order ignored) is reported too
but is not a pass criterion: {CC}_parameters.json and report files are expected to differ. For a
release that changes code, a FAIL or "differs" line is expected where the change explains it; the
`release` skill (SKILL.md, step 3.10) says how to read the output.
"""

import json
import sys
from pathlib import Path

a_path, b_path = sys.argv[1], sys.argv[2]
a = json.loads(Path(a_path).read_text(encoding="utf-8"))
b = json.loads(Path(b_path).read_text(encoding="utf-8"))
print(f"A = {a['workspace']} ({a['generated_at']})\nB = {b['workspace']} ({b['generated_at']})\n")

failures = 0
for key in sorted(set(a["datasets"]) | set(b["datasets"])):
    da, db = a["datasets"].get(key, {}), b["datasets"].get(key, {})
    if not da.get("present") and not db.get("present"):
        continue
    print(f"== {key} ({da.get('slug') or db.get('slug')})")
    if not (da.get("present") and db.get("present")):
        print(f"   FAIL present in A: {bool(da.get('present'))}, in B: {bool(db.get('present'))}")
        failures += 1
        continue
    fa, fb = da["files"], db["files"]
    for name in sorted(set(fa) | set(fb)):
        if name not in fa or name not in fb:
            print(f"   FAIL {name}: only in {'A' if name in fa else 'B'}")
            failures += 1
            continue
        x, y = fa[name], fb[name]
        if "rows" in x or "rows" in y:
            same_cols = x.get("columns") == y.get("columns")
            same_rows = x.get("rows") == y.get("rows")
            same_types = x.get("dtypes") == y.get("dtypes")
            same_content = x.get("content_hash") == y.get("content_hash")
            status = "ok  " if same_cols and same_rows else "FAIL"
            failures += status == "FAIL"
            print(
                f"   {status} {name}: rows {x.get('rows')} / {y.get('rows')}, "
                f"columns {'same' if same_cols else 'DIFFER'}, dtypes {'same' if same_types else 'differ'}, "
                f"content {'identical' if same_content else 'differs'}"
            )
            if not same_cols:
                print(f"        only in A: {sorted(set(x.get('columns', [])) - set(y.get('columns', [])))}")
                print(f"        only in B: {sorted(set(y.get('columns', [])) - set(x.get('columns', [])))}")
        else:
            same = x["sha256"] == y["sha256"]
            print(f"   info {name}: bytes {x['bytes']} / {y['bytes']}, {'identical' if same else 'differs'}")

print(f"\n{'PASS' if failures == 0 else f'FAIL: {failures} problem(s)'}")
