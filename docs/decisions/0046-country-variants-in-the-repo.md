# 0046. Country variants are committed beside their generic notebook

Date: 2026-11-23
Status: Accepted (amends [0003](0003-country-variants-outside-pull-scripts.md) and [0044](0044-self-sync-replaces-pull-scripts.md); supersedes the country-notebook part of migration plan D-13)

## Context

A country variant `<generic>_<CC>.ipynb` runs instead of its generic notebook in the workspace whose
`COUNTRY_CODE` is `<CC>` ([0003](0003-country-variants-outside-pull-scripts.md)). Until now a
variant lived only in its country's workspace. Nothing versioned it, reviewed it or delivered it.
Nothing told anyone when the generic notebook it was copied from changed, and the workspace checker
could only report it as `untracked`. The import left the known variants out of this public repo
(migration plan D-13), because they hold country details such as Jira links, a Google Sheets link and
DHIS2 identifiers. How to version them was the open decision OD-10.

A workspace is not a reliable long-term home for code. When access to a country's workspace ends,
as it has for Niger, its variants are out of reach.

Self-sync ([0044](0044-self-sync-replaces-pull-scripts.md)) copies every `code/*.ipynb` and
`reporting/*.ipynb` in the pipeline version to the workspace. A variant committed beside its
generic notebook is in the pipeline version, so it reaches a workspace by every route (self-sync,
the deployer, templates) with no new mechanism.

The country details in the variants are not secrets. A Jira link needs a Bluesquare login; a private
Google Sheet does not open from its link.

## Decision

1. **A country variant is committed beside its generic notebook**, in `code/` or `reporting/`, and
   ships in the pipeline version like any other notebook. Which notebook runs is unchanged:
   `custom/` (when switched on), then `<generic>_<CC>.ipynb`, then the generic one. A variant is
   inert in every other country's workspace. A country notebook that `pipeline.py` calls directly
   (a **hook**, such as Niger's pyramid fix) is committed in `code/` as `<CC>_<name>.ipynb`.
   `country_specific/` folders, which are on no execution path, are not used.
2. **What may be public.** Anything except credentials, country data files and notebook outputs
   (R1, R2) and personal data. Jira links, Google Sheets links and DHIS2 identifiers may be committed;
   removing them is an optional clean-up. Until the project manager has ruled on these categories,
   the repo owner approves each such item in a country notebook before it is committed. The
   redactions made at import stay as they are.
3. **Each variant and hook records what it was forked from**, in the notebook metadata key
   `snt_variant`: `kind` (`variant` or `hook`), `country`, `variant_of`, `base_sha256` (the
   fingerprint of the generic notebook's bytes when the variant was last aligned with it, `null`
   when unknown), `base_ref` (the release or commit to compare against), `reason` and `tickets`.
   A check in CI fails when the header is missing or contradicts the file name, or when a variant
   has no generic notebook beside it. It warns, without failing, when the generic notebook has
   changed since `base_sha256`. A fix to a generic notebook is never blocked by a variant.
4. **A change to a variant reaches its country with the next release.** It goes through a pull
   request like any notebook. For an urgent fix, the analyst puts the edited notebook in
   `pipelines/<name>/custom/` and switches on `use_custom_notebooks` (a custom notebook wins over
   a variant), then opens the pull request. Self-sync overwrites a hand edit to a shipped variant
   and archives the edited copy, as it does for every notebook in the pipeline version. `custom/`
   stays a temporary, unversioned escape hatch: an edit worth keeping becomes a change to the
   generic notebook or a variant, through a pull request.
5. **Each release is verified once per supported country**, in a test workspace with that
   country's `COUNTRY_CODE`, DHIS2 connection and configuration, so that its variants actually run.
   Countries outside the supported list may see failures if their data differ a lot from those of
   the supported countries.

## Consequences

- The repo is the record of which variants exist. Before changing a generic notebook, list its
  `_<CC>` siblings in the same folder. The checker reports a shipped variant as `tracked`.
- Every workspace receives every country's variants, unused outside their country.
- A variant that falls behind its generic notebook shows up in CI on the pull request that changes
  the generic one. Re-aligning it, or accepting the gap, is a decision someone has to make.
- A country fix waits for a release, unless it goes through `custom/` for the meantime.
- Verifying a release costs one test workspace pair (candidate and baseline) per supported country.
  Until the Niger incidence variant is re-based, a Niger test workspace runs it stale and is
  expected to fail at that notebook.
- Forking is now cheap. Preferring a configuration switch inside the generic notebook matters more,
  not less.
- When a country moves to this repo, the first run of each pipeline replaces any hand-made variant
  in its workspace with the repo copy and archives the old one. Collect the workspace copies first.
- `snt_lib`'s `sync_pipeline_scripts` docstring says variants are never touched. That remains true
  only for variants not shipped in the pipeline version.
- Live countries run the old `snt_development` repo, where variants are unchanged.

Source: discussion 2026-11-23, closing migration plan OD-10.
