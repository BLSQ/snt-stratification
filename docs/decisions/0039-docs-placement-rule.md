# 0039. Where docs live, and how agent instructions are split

Date: 2026-11-02 (agent-file choices from 2026-10-16)
Status: Accepted

## Context

The monorepo holds pipelines, webapps, bootstrap pipelines and contracts, each with docs that came
from its own repo. Agents load the root `CLAUDE.md` in every session, so whatever it carries costs
tokens every time. `snt_development` had already slimmed its CLAUDE.md in October 2026, from about
55 KB to under 20 KB, and recorded how.

## Decision

**A unit's own docs live with the unit; docs that span several units live in `docs/`.**

- **Webapp:** `webapps/<name>/docs/` and `webapps/<name>/design/`, beside the deployable
  `webapps/<name>/app/`. Only `app/` is deployed, so docs never leak into the bundle.
- **Pipeline:** its own doc is `readme.md`, the operator contract deployed with the zip. No
  `docs/` subfolder in a pipeline: the zip ships every `.md`. Longer notes that cover several
  pipelines go in `docs/<area>/` (as `docs/bootstrap/` does).
- **Contract:** the prose sits next to its schema in `contracts/<name>/`.
- **Several units or the whole system:** `docs/`. No top-level `design/`.

**Agent instructions:**

- `CLAUDE.md` is the agent file. No `AGENTS.md`.
- The root `CLAUDE.md` is a router of at most 15 KB: guardrails, the Register, Traps, and where to
  find things. Rules needed in one area live in that area's nested `CLAUDE.md` (`pipelines/`,
  `webapps/`, `webapps/<name>/`), which loads only when an agent works there.
- No `@import` in `CLAUDE.md`: imports load at startup and save no tokens. Plain links are read only
  when needed.
- No `CLAUDE.md` inside a pipeline folder: it would ship in the pipeline zip.
- Each fact lives in one file; other places link to it.

## Consequences

- An agent editing a webapp never loads the notebook rules, and the other way round.
- A new doc's home follows from what it covers, not from where its author works.
- The system map that ties the units together is `docs/ARCHITECTURE.md`.

Source: migration plan D-10, §4.1; `snt_development` docs restructure, 2026-10-16.
