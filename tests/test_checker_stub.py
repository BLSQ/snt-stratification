"""Stubbed test of snt_workspace_checker phase-2 classification, mirroring the sandbox fixtures."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipelines" / "snt_workspace_checker"))
import pipeline as chk


class Log:
    def __getattr__(self, name):
        return lambda msg: print(f"  [{name}] {msg}")


chk.current_run = Log()

H = {
    k: chk.sha256_bytes(k.encode())
    for k in ["A", "B", "C", "S", "R", "F", "P", "X", "Y", "E", "E2", "Ar", "Br", "N"]
}


def manifest(fs, pipes):
    """Build a v2 manifest: fs = {path: hash key} copied to the filesystem; pipes = {name: {member: key}}.

    A member's repository path is pipelines/<name>/<member>; a path in both (a notebook helper)
    takes both routes, as in a real release.

    Returns
    -------
    dict
        The manifest, schema_version 2.
    """
    files = {p: H[v] for p, v in fs.items()}
    pipelines = {}
    for name, members in pipes.items():
        path = f"pipelines/{name}"
        files.update({f"{path}/{m}": H[v] for m, v in members.items()})
        pipelines[name] = {
            "path": path,
            "kind": "snt",
            "code": name.replace("_", "-"),
            "zip_files": sorted(members),
        }
    return {
        "schema_version": 2,
        "version": "stub",
        "repo": "o/r",
        "files": files,
        "filesystem_files": sorted(fs),
        "pipelines": pipelines,
    }


ADDED_R = "pipelines/snt_dhis2_incidence/utils/fixture_added.r"  # filesystem AND incidence zip
base = {"shared/r/edited.r": "E", "shared/r/fixture_stable.r": "S"}

v010 = manifest(
    {**base, "shared/r/fixture_changing.r": "A", "shared/r/fixture_removed.r": "R"},
    {
        "snt_dhis2_incidence": {"pipeline.py": "P", "fixture_reverted.py": "Ar"},
        "snt_fixture_pipeline_removed": {"pipeline.py": "X"},
    },
)
v021 = manifest(
    {**base, "shared/r/fixture_changing.r": "B", ADDED_R: "F"},
    {
        "snt_dhis2_incidence": {
            "pipeline.py": "P",
            "fixture_reverted.py": "Br",
            "utils/fixture_added.r": "F",
        },
        "snt_fixture_pipeline_added": {"pipeline.py": "Y"},
    },
)
v030 = manifest(
    {**base, "shared/r/fixture_changing.r": "C", ADDED_R: "F", "shared/r/fixture_future.r": "N"},
    {
        "snt_dhis2_incidence": {
            "pipeline.py": "P",
            "fixture_reverted.py": "Ar",
            "utils/fixture_added.r": "F",
        },
        "snt_fixture_pipeline_added": {"pipeline.py": "Y"},
    },
)
releases = [
    {"tag_name": "v0.1.0-test", "published_at": "2026-09-21T15:20:00Z"},
    {"tag_name": "v0.2.0-test", "published_at": "2026-09-21T15:40:00Z"},
    {"tag_name": "v0.2.1-test", "published_at": "2026-09-21T16:00:00Z"},
    {"tag_name": "v0.3.0-test", "published_at": "2026-09-21T16:04:00Z"},
]
manifests = {"v0.1.0-test": v010, "v0.2.0-test": v010, "v0.2.1-test": v021, "v0.3.0-test": v030}
index = chk.build_index(manifests, releases, "v0.2.1-test")

# ---- filesystem: workspace deployed at v0.1.0-test, plus hand-made cases
root = Path(tempfile.mkdtemp())
files = {
    "shared/r/edited.r": "E2",  # hand edit -> unknown_content
    "shared/r/fixture_stable.r": "S",
    "shared/r/fixture_changing.r": "A",
    "shared/r/fixture_removed.r": "R",
    "shared/r/fixture_future.r": "N",  # only in v0.3.0 -> added_after_target
    "code/fixture_stable.r": "S",  # the old snt_development layout: no release here ships code/
    "scratch_notes.ipynb": "junk",
    "pipelines/x/code/.ipynb_checkpoints/n-checkpoint.ipynb": "junk",
    "pipelines/x/reporting/outputs/r.html": "junk",
    "pipelines/x/papermill_outputs/o.ipynb": "junk",
    "data/x.csv": "junk",
    "snt_status/status_latest.json": "{}",
    ".snt_release": "{}",
    "pipelines/snt_dhis2_incidence/pipeline.py": "P",  # zip-only path on the filesystem: inert copy
}
for rel, content in files.items():
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content.encode())

fs_entries, inert = chk.check_filesystem(root, index)
got = {e["path"]: (e["status"], e["matching_releases"], e["position"]) for e in fs_entries}
expected = {
    "shared/r/edited.r": ("unknown_content", None, None),
    "shared/r/fixture_stable.r": ("match", None, None),
    "shared/r/fixture_changing.r": (
        "mismatch_known",
        [{"from": "v0.1.0-test", "to": "v0.2.0-test", "count": 2}],
        "older",
    ),
    "shared/r/fixture_removed.r": (
        "removed_in_target",
        [{"from": "v0.1.0-test", "to": "v0.2.0-test", "count": 2}],
        "older",
    ),
    "shared/r/fixture_future.r": (
        "added_after_target",
        [{"from": "v0.3.0-test", "to": "v0.3.0-test", "count": 1}],
        "newer",
    ),
    "code/fixture_stable.r": ("untracked", None, None),
    "scratch_notes.ipynb": ("untracked", None, None),
    ADDED_R: ("missing", None, None),  # the filesystem copy; the zip copy is checked on the zip side
}
assert got == expected, got
assert inert == ["pipelines/snt_dhis2_incidence/pipeline.py"], inert
assert all(e["source"] == "filesystem" for e in fs_entries)
print("filesystem OK")

# ---- zip side: members are keyed under pipelines.<name>.path
e = chk.classify_zip_member("snt_dhis2_incidence", "fixture_reverted.py", H["Ar"], index)
assert e["path"] == "pipelines/snt_dhis2_incidence/fixture_reverted.py", e
assert (e["status"], e["position"]) == ("mismatch_known", "both"), e
assert e["matching_releases"] == [
    {"from": "v0.1.0-test", "to": "v0.2.0-test", "count": 2},
    {"from": "v0.3.0-test", "to": "v0.3.0-test", "count": 1},
], e
e = chk.classify_zip_member("snt_dhis2_incidence", "extra_helper.py", H["N"], index)
assert e["status"] == "untracked" and "deployed code" in e["remediation"], e
e = chk.classify_zip_member("snt_dhis2_incidence", "notes.json", H["N"], index)
assert e["status"] == "not_covered", e
e = chk.classify_zip_member("snt_dhis2_incidence", "workspace/x.py", H["N"], index)
assert e["status"] == "not_covered", e
e = chk.classify_zip_member("snt_fixture_pipeline_removed", "pipeline.py", H["X"], index)
assert e["status"] == "removed_in_target" and "Redeploy" in e["remediation"], e
e = chk.classify_zip_member("snt_fixture_pipeline_added", "pipeline.py", None, index)
assert e["status"] == "missing", e
e = chk.classify_zip_member("snt_dhis2_incidence", "utils/fixture_added.r", H["F"], index)
assert (e["path"], e["status"], e["source"]) == (ADDED_R, "match", "pipeline_version"), e
print("zip OK")

# ---- version name vs content
members_010 = {"pipeline.py": H["P"], "fixture_reverted.py": H["Ar"]}
assert chk.name_matches_content("snt_dhis2_incidence", "v0.1.0-test [v1]", members_010, index) is True
assert chk.name_matches_content("snt_dhis2_incidence", "v0.2.1-test [v2]", members_010, index) is False
assert chk.name_matches_content("snt_dhis2_incidence", "v3", members_010, index) is None
extra = {**members_010, "stray.py": H["N"]}
assert chk.name_matches_content("snt_dhis2_incidence", "v0.1.0-test [v1]", extra, index) is False
assert (
    chk.name_matches_content("snt_fixture_pipeline_removed", "v0.2.1-test", {"pipeline.py": H["X"]}, index)
    is False
)
print("names OK")

# ---- unordered: a release with no timestamp
releases_u = [*releases, {"tag_name": "v9-nodate", "published_at": None}]
manifests_u = {**manifests, "v9-nodate": manifest({**base, "shared/r/fixture_changing.r": "C"}, {})}
index_u = chk.build_index(manifests_u, sorted(releases_u, key=chk.release_sort_key), "v0.2.1-test")
assert index_u.ordered_tags[-1] == "v9-nodate"
r = chk.classify("shared/r/fixture_changing.r", H["C"], index_u)
assert (r["status"], r["position"]) == ("mismatch_known", "unordered"), r
r = chk.classify("shared/r/fixture_changing.r", H["A"], index_u)
assert r["position"] == "older", r
print("unordered OK")
# a manifest-less release breaks a span (D14)
rel_hole = [
    releases[0],
    {"tag_name": "v0.1.5-nomanifest", "published_at": "2026-09-21T15:30:00Z"},
    *releases[1:],
]
idx_h = chk.build_index(manifests, rel_hole, "v0.2.1-test")
r = chk.classify("shared/r/fixture_changing.r", H["A"], idx_h)
assert [s["count"] for s in r["matching_releases"]] == [1, 1], r
print("spans OK")
# pre-releases are left out unless one is the target (D27); with them out, the span is unbroken
rel_pre = [
    releases[0],
    {"tag_name": "pr1_staging", "published_at": "2026-09-21T15:30:00Z", "prerelease": True},
    *releases[1:],
    {"tag_name": "pr2_staging", "published_at": "2026-09-21T16:10:00Z", "prerelease": True},
]
kept, skipped = chk.drop_prereleases(rel_pre, "v0.2.1-test")
assert kept == releases and skipped == ["pr1_staging", "pr2_staging"], (kept, skipped)
kept, skipped = chk.drop_prereleases(rel_pre, "pr2_staging")
assert [r["tag_name"] for r in kept] == [*(r["tag_name"] for r in releases), "pr2_staging"], kept
assert skipped == ["pr1_staging"], skipped
kept, skipped = chk.drop_prereleases(rel_pre, None)
assert kept == releases and len(skipped) == 2, (kept, skipped)
r = chk.classify("shared/r/fixture_changing.r", H["A"], chk.build_index(manifests, kept, "v0.2.1-test"))
assert [s["count"] for s in r["matching_releases"]] == [2], r
print("pre-releases OK")

# ---- which manifests the checker reads (Phase 4): v2 only, anything else is skipped with a reason
assert chk.manifest_problem(v010) is None
assert "v1 manifest" in chk.manifest_problem({"files": {}, "pipelines": {}})
assert "schema_version 3" in chk.manifest_problem({**v010, "schema_version": 3})
assert "not a JSON object" in chk.manifest_problem(["v0.1.0"])
print("manifest versions OK")


# ============================================================================================
# Phase 3
# ============================================================================================


def considered(rels, mans):
    return [
        {"tag": r["tag_name"], "published_at": r["published_at"], "manifest_available": r["tag_name"] in mans}
        for r in rels
    ]


# ---- target resolution (D17)
assert chk.resolve_target("none", "v0.1.0-test") == (None, "parameter")
assert chk.resolve_target(" NONE ", None) == (None, "parameter")
assert chk.resolve_target(None, None) == (None, "nothing_given")
assert chk.resolve_target("", "v0.1.0-test") == ("v0.1.0-test", "marker")
assert chk.resolve_target("v0.2.1-test", "v0.1.0-test") == ("v0.2.1-test", "parameter")
print("resolve OK")


# ---- the .snt_release marker: both shapes, and the repository it names (Phase 4)
def read_marker(text):
    with tempfile.TemporaryDirectory() as tmp:
        if text is not None:
            (Path(tmp) / ".snt_release").write_text(text)
        return chk.read_release_marker(Path(tmp))


assert read_marker(None) == (None, None)
assert read_marker('{"snt_release": "v0.3.0-test"}') == ("v0.3.0-test", None)
assert read_marker('{"snt_release": "v0.1.0", "repo": "BLSQ/snt-stratification"}') == (
    "v0.1.0",
    "BLSQ/snt-stratification",
)
assert read_marker("not json") == (None, None)
assert read_marker('["v0.1.0"]') == (None, None)

assert chk.marker_target(None, None, "BLSQ/snt-stratification") is None
assert chk.marker_target("v0.3.0-test", None, "BLSQ/snt-stratification") == "v0.3.0-test"  # old marker
assert chk.marker_target("v0.1.0", "BLSQ/snt-stratification", "BLSQ/snt-stratification") == "v0.1.0"
assert chk.marker_target("v0.1.0", "blsq/SNT-Stratification", "BLSQ/snt-stratification") == "v0.1.0"
assert chk.marker_target("v0.1.0", "BLSQ/snt_development_sandbox", "BLSQ/snt-stratification") is None
print("marker OK")


# ---- verification mode also carries the per-release scores (section 4.2), from the phase-2 fs run.
# 5 files scored: edited(E2), stable, changing(A), removed(R), future(N); untracked scratch_notes
# and code/fixture_stable.r, and missing fixture_added, are left out. Columns: shipped, present,
# agreeing, extra, agreement, completeness. shipped counts copies: v0.2.1 and v0.3.0 ship
# fixture_added.r twice (filesystem + incidence zip), so 4 fs + 3 + 1 zip = 8, and 5 + 3 + 1 = 9.
def scores(summary):
    return [
        (r["tag"], r["shipped"], r["present"], r["agreeing"], r["extra"], r["agreement"], r["completeness"])
        for r in summary["by_release"]
    ]


s = chk.attribution_summary(fs_entries, index, considered(releases, manifests))
assert s["files_scored"] == 5, s
assert scores(s) == [
    ("v0.1.0-test", 7, 4, 3, 1, 0.75, 0.5714),  # future.r is extra; edited.r disagrees
    ("v0.2.0-test", 7, 4, 3, 1, 0.75, 0.5714),
    ("v0.2.1-test", 8, 3, 1, 2, 0.3333, 0.375),  # removed.r and future.r are extra
    ("v0.3.0-test", 9, 4, 2, 1, 0.5, 0.4444),
], scores(s)
# v0.1.0 and v0.2.0 tie on agreement AND completeness -> the newest
assert s["best_fit"] == {"tag": "v0.2.0-test", "agreement": 0.75, "completeness": 0.5714}, s
assert s["matches_no_release"] == {"count": 1, "share": 0.2}, s
print("verification summary OK")

# ---- attribution mode. Mirrors the sandbox after snt_workspace_deployer ran at v0.3.0-test with
# pipeline deployment off: analytics at v0.3.0 (plus the leftover fixture_removed.r), pipeline
# zips still at v0.1.0, one hand edit. v0.4.0-test is the newest release and has no manifest.
releases_a = [*releases, {"tag_name": "v0.4.0-test", "published_at": "2026-09-21T16:10:00Z"}]
index_a = chk.build_index(manifests, releases_a, None)
assert index_a.target_files == {} and index_a.target_pipelines == {}

root_a = Path(tempfile.mkdtemp())
files_a = {
    "shared/r/edited.r": "E2",
    "shared/r/fixture_stable.r": "S",
    "shared/r/fixture_changing.r": "C",
    "shared/r/fixture_removed.r": "R",
    ADDED_R: "F",
    "scratch_notes.ipynb": "junk",
    "pipelines/snt_dhis2_incidence/pipeline.py": "P",  # inert copy
}
for rel, content in files_a.items():
    p = root_a / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content.encode())

fs_a, inert_a = chk.check_filesystem(root_a, index_a)
got = {e["path"]: (e["status"], e["matching_releases"], e["position"], e["target_sha256"]) for e in fs_a}


def span(a, b, n):
    return {"from": a, "to": b, "count": n}


expected = {
    "shared/r/edited.r": ("unknown_content", None, None, None),
    # one span of 4: v0.4.0 has no manifest, but it is last, so it ends the span without breaking it
    "shared/r/fixture_stable.r": ("attributed", [span("v0.1.0-test", "v0.3.0-test", 4)], None, None),
    "shared/r/fixture_changing.r": ("attributed", [span("v0.3.0-test", "v0.3.0-test", 1)], None, None),
    "shared/r/fixture_removed.r": ("attributed", [span("v0.1.0-test", "v0.2.0-test", 2)], None, None),
    ADDED_R: ("attributed", [span("v0.2.1-test", "v0.3.0-test", 2)], None, None),
    "scratch_notes.ipynb": ("untracked", None, None, None),
}
assert got == expected, got  # and no `missing` pass: nothing else appears
assert inert_a == ["pipelines/snt_dhis2_incidence/pipeline.py"], inert_a
assert all(e["remediation"] is None for e in fs_a if e["status"] == "attributed")
print("attribution filesystem OK")

# ---- attribution, pipeline side: stub the API with zips as deployed at v0.1.0-test
import base64, io, zipfile  # ruff: ignore[multiple-imports-on-one-line, module-import-not-at-top-of-file]


def zipped(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    return base64.b64encode(buf.getvalue()).decode()


deployed = {
    "snt-dhis2-incidence": {
        "versionName": "v0.1.0-test [v1]",
        "zipfile": zipped({"pipeline.py": "P", "fixture_reverted.py": "Ar"}),
    },
    "snt-fixture-pipeline-removed": {
        "versionName": "v0.1.0-test [v1]",
        "zipfile": zipped({"pipeline.py": "X"}),
    },
}
chk.fetch_current_version = lambda token, code: deployed.get(code)
unknown_calls = []
chk.list_unknown_pipelines = lambda token, codes, has_target: (
    unknown_calls.append(has_target)
    or [
        chk.pipeline_report(
            None, "snt-workspace-checker", False if has_target else None, "v1", None, "not_in_any_release"
        )
    ],
    None,
)
zip_a, pipes_a, errs_a = chk.check_pipeline_versions(index_a, "token")
assert errs_a == [] and unknown_calls == [False], (errs_a, unknown_calls)
got = {e["path"]: (e["status"], e["matching_releases"]) for e in zip_a}
assert got == {
    "pipelines/snt_dhis2_incidence/pipeline.py": ("attributed", [span("v0.1.0-test", "v0.3.0-test", 4)]),
    "pipelines/snt_dhis2_incidence/fixture_reverted.py": (
        "attributed",
        [span("v0.1.0-test", "v0.2.0-test", 2), span("v0.3.0-test", "v0.3.0-test", 1)],
    ),
    "pipelines/snt_fixture_pipeline_removed/pipeline.py": (
        "attributed",
        [span("v0.1.0-test", "v0.2.0-test", 2)],
    ),
}, got
blocks = {b["code"]: b for b in pipes_a}
assert set(blocks) == {"snt-dhis2-incidence", "snt-fixture-pipeline-removed", "snt-workspace-checker"}, blocks
assert blocks["snt-dhis2-incidence"]["in_target"] is None
assert blocks["snt-dhis2-incidence"]["version_name_matches_content"] is True
assert blocks["snt-fixture-pipeline-removed"]["in_target"] is None
assert blocks["snt-fixture-pipeline-removed"]["remediation"] is None  # not "not in target"
print("attribution pipelines OK")


# ---- the exit criterion: a mixed workspace gives the right per-release breakdown (D15, revised).
# 8 files scored: edited(E2), stable, changing(C), removed(R), added(F), incidence pipeline.py,
# reverted(A), removed-pipeline(X). The leftovers removed.r and X are what the first D15 counted
# against v0.3.0, producing a three-way tie; judged on shipped paths only, they are extra for it,
# and v0.3.0 wins outright - the sandbox finding of 2026-09-29, in miniature. The zips are still at
# v0.1.0, so the zip copy of added.r that v0.2.1 and v0.3.0 ship is absent: it lowers their
# completeness, never their agreement.
s = chk.attribution_summary(fs_a + zip_a, index_a, considered(releases_a, manifests))
assert s["files_scored"] == 8, s
assert scores(s) == [
    ("v0.1.0-test", 7, 7, 5, 1, 0.7143, 1.0),  # added.r extra; edited, changing(C) disagree
    ("v0.2.0-test", 7, 7, 5, 1, 0.7143, 1.0),
    ("v0.2.1-test", 8, 6, 3, 2, 0.5, 0.75),  # removed.r, X extra; added pipeline, zip added.r absent
    ("v0.3.0-test", 9, 6, 5, 2, 0.8333, 0.6667),  # only edited.r disagrees
    ("v0.4.0-test", None, None, None, None, None, None),
], scores(s)
assert s["best_fit"] == {"tag": "v0.3.0-test", "agreement": 0.8333, "completeness": 0.6667}, s
assert s["matches_no_release"] == {"count": 1, "share": 0.125}, s
assert s["unreadable"] == {"count": 0, "share": 0.0}, s
# an empty workspace: nothing to score, no best fit, no division by zero
e = chk.attribution_summary([], index_a, considered(releases_a, manifests))
assert e["files_scored"] == 0 and e["best_fit"] is None, e
assert scores(e)[0] == ("v0.1.0-test", 7, 0, 0, 0, None, 0.0), scores(e)
assert e["matches_no_release"]["share"] is None, e
# agreement ties are broken by completeness before recency: a release that agrees just as well
# but is less present here loses to an older, complete one
row_old = {"tag": "old", "published_at": None, "manifest_available": True}
row_new = {"tag": "new", "published_at": None, "manifest_available": True}
idx_t = chk.ReleaseIndex(
    None,
    {},
    ["old", "new"],
    ["old", "new"],
    {"a": {"old": H["A"], "new": H["A"]}, "b": {"old": H["B"]}},
    {},
    {
        "old": {"files": {"a": H["A"], "b": H["B"]}, "filesystem_files": ["a", "b"], "pipelines": {}},
        "new": {"files": {"a": H["A"], "c": H["C"]}, "filesystem_files": ["a", "c"], "pipelines": {}},
    },
    {},
    {"a", "b", "c"},
)
ents = [
    {"path": "a", "source": "filesystem", "status": "attributed", "observed_sha256": H["A"]},
    {"path": "b", "source": "filesystem", "status": "attributed", "observed_sha256": H["B"]},
]
t = chk.attribution_summary(ents, idx_t, [row_old, row_new])
assert t["best_fit"] == {"tag": "old", "agreement": 1.0, "completeness": 1.0}, t  # new: 1.0 / 0.5
print("attribution summary OK")
print("ALL PASS")


# ============================================================================================
# Phase 4: reports built by build_report() conform to the frozen schema
# ============================================================================================
import json  # ruff: ignore[module-import-not-at-top-of-file]
from types import SimpleNamespace  # ruff: ignore[module-import-not-at-top-of-file]

from jsonschema import Draft202012Validator, FormatChecker  # ruff: ignore[module-import-not-at-top-of-file]

schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/status_report.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
chk.workspace = SimpleNamespace(slug="stub-workspace")


def assert_conforms(report, label):
    errs = list(validator.iter_errors(report))
    assert not errs, (label, [(list(e.path), e.message[:100]) for e in errs[:5]])
    # every key written must be declared, and every declared key written (no drift either way)
    assert set(report) == set(schema["properties"]), (label, set(report) ^ set(schema["properties"]))


# attribution mode, from the objects built above
rep_a = chk.build_report(
    fs_a + zip_a,
    index_a,
    pipes_a,
    inert_a,
    errs_a,
    "o/r",
    None,
    considered(releases_a, manifests),
    "parameter",
    "v0.3.0-test",
    "o/r",
)
assert rep_a["mode"] == "attribution" and rep_a["snt_workspace_check_version"] is None
assert rep_a["declared_release"] == {"tag": "v0.3.0-test", "repo": "o/r", "source": ".snt_release"}
assert_conforms(rep_a, "attribution")

# verification mode: target v0.2.1-test, one pipeline unreadable, so `unreadable` and `errors` appear
index_v = chk.build_index(manifests, releases, "v0.2.1-test")


def flaky(token, code):
    if code == "snt-fixture-pipeline-added":
        raise RuntimeError("stub API failure")
    return deployed.get(code)


chk.fetch_current_version = flaky
zip_v, pipes_v, errs_v = chk.check_pipeline_versions(index_v, "token")
assert any(e["status"] == "unreadable" for e in zip_v) and errs_v, (zip_v, errs_v)
rep_v = chk.build_report(
    fs_entries + zip_v,
    index_v,
    pipes_v,
    inert,
    errs_v,
    "o/r",
    {"tag_name": "v0.2.1-test", "published_at": "2026-09-21T16:00:00Z"},
    considered(releases, manifests),
    "marker",
    None,
    None,
)
assert rep_v["mode"] == "verification" and rep_v["incomplete"] is True
assert {e["position"] for e in rep_v["entries"]} >= {"older", "newer"}
assert_conforms(rep_v, "verification")

# a JSON round trip (what is written to disk) must conform too
assert_conforms(json.loads(json.dumps(rep_v)), "verification, round-tripped")
print("schema conformance OK")
print("ALL PASS (phase 4)")


# ============================================================================================
# Migration Phase 4: bootstrap pipelines are attributed through the manifest like any other
# ============================================================================================
import importlib.util  # ruff: ignore[module-import-not-at-top-of-file]

# A fresh copy: the stubs above replaced fetch_current_version and list_unknown_pipelines.
_spec = importlib.util.spec_from_file_location("checker_fresh", chk.__file__)
fresh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fresh)
fresh.current_run = Log()
fresh.workspace = SimpleNamespace(slug="stub-workspace")

example = json.loads(
    (Path(__file__).resolve().parent / "fixtures/release_manifest_v2_example.json").read_text()
)
index_b = fresh.build_index({"v0.1.0": example}, [{"tag_name": "v0.1.0", "published_at": None}], None)
assert index_b.pipeline_codes["snt_workspace_checker"] == "snt-workspace-checker"
fresh.fetch_current_version = lambda token, code: (
    {"versionName": "v1", "zipfile": zipped({"pipeline.py": "x"})}
    if code == "snt-workspace-checker"
    else None
)
listing = {
    "pipelines": {"totalPages": 1, "items": [{"code": "snt-workspace-checker", "currentVersion": None}]}
}
fresh.call_graphql = lambda token, operation, variables: listing
_, pipes_b, errs_b = fresh.check_pipeline_versions(index_b, "token")
assert errs_b == [], errs_b
[block] = pipes_b  # the checker, once: not repeated as a pipeline no release describes
assert (block["code"], block["pipeline"], block["in_any_release"]) == (
    "snt-workspace-checker",
    "snt_workspace_checker",
    True,
), block
print("bootstrap attribution OK")


def test_stub_assertions_hold() -> None:
    """Give pytest a test to collect: every assertion above runs at import, so reaching here means all held."""
