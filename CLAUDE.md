# Working in this repo

nbdev 3 on hatchling. Two kinds of code live here:

- The Python (`spec`, `render`, `check`, `agent`): the notebooks under `nbs/` are the source, and `rupaka/*.py` is generated.
  Edit the notebook (with `fastcore.nbio`: `read_nb`, `mk_cell`, `write_nb`). Run `uv run nbdev-prepare` (with a hyphen). Never edit a generated file.
- The runtime: plain JS and CSS written by hand under `rupaka/static/`, `rupaka/blocks/` and `rupaka/fns/`, tested with `uv run pytest`.

## Blocks

A block is a folder in `rupaka/blocks/<name>/`, as in lego: `<name>.js` (`Rupaka.block(name, (b, ctx) => node)`), `<name>.css`,
`block.json` (purpose in one line, props with types, keys, `since`) and `example.json` (a small demo with a gate).

- The validator and the agent prompt read `block.json`, so a new prop goes in the manifest first.
- Colours come only from the `--rk-*` vars. `rupaka.css` maps them to abhyasa, vedicreader (`--mh-*`) and leela (`--lee-*`) vars.
- Text goes in with `textContent`. No `innerHTML`, no `eval`, no network, no global keys, no `focus()` on mount.
- Every control works with keys and has a left-hand key (A/D, W/S, Q/E, 1-9). A control with `lock` refuses changes through `ctx.put`.
- A new fn is code: a `rupaka/fns/<name>.js` file, a `<name>.json` manifest, and a Python twin in `nbs/00_spec.ipynb` (`FNS`).
  The browser tests compare the two.

## Rules

- The think rule: a block that shows a value which a gate's answer depends on must wait for that gate (`after`). `validate` enforces it.
- Browser tests run headless through playwright, on playwright's own Chromium (`python -m playwright install chromium`) or `$FASTCDP_CHROME`.
  Never the everyday Chrome in /Applications: headless runs of it crash the Chrome the user works in. One browser at a time, closed in a `finally` block.
  No window may open or take focus.
- Prose (notebooks, docs, UI text, commit messages, release notes) is ASD-STE100 Simplified Technical English, US grade 9.
- Notebooks read as documents: an intro, short sections, a one-line lead before each code cell, small cells, tests in small steps.
- Commit messages are one plain line, with no AI credit.
- Release: write the CHANGELOG entry, `nbdev-prepare`, push, check that CI passes, then `nbdev-release-git` and `nbdev-pypi`. Never `nbdev-release-gh`.
