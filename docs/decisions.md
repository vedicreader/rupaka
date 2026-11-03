# Decisions

This page lists the decisions that a maintainer must know. Each entry gives the decision, the reason, the date or version, and the place in the code.
The rules of daily work (blocks, the think rule, browser tests, prose, commits, release) are in [CLAUDE.md](../CLAUDE.md). This page does not repeat them.
The first design and plan (26 October 2026) are in the git history under `docs/superpowers/`.

## What a demo is

- **A demo is data, not code.** A spec is JSON: blocks, a small state, `derive` steps and tables. A model writes data only, never JavaScript. A new fn is code that a person writes and reviews.
  Why: a demo is then safe to store, safe to show in Leela, and easy to check. (26 Oct 2026) `validate` and `FNS` in `nbs/00_spec.ipynb`, `rupaka/fns/`.
- **The learner predicts first.** A demo has a gate, and the result stays hidden until the learner locks in a pick.
  Why: the tool must not think for the learner. This is the first rule of abhyasa. (26 Oct 2026) `rupaka/blocks/gate/`, `validate`.
- **An explainer is the one exception.** A spec with `"mode": "learn"` has no gate. It shows its parts by `step`. `validate` refuses a gate, `after` or `lock` in it. (0.0.8, 0.0.9) `nbs/00_spec.ipynb`.
- **`expr` covers formulas.** One small safe grammar, parsed the same in JS and in Python. Most plots need no new fn. It refuses names that start with `_`, `constructor` and `prototype`. (26 Oct 2026) `rupaka/fns/expr.js`, `parse_expr`.
- **Schema versions.** The `rupaka` field of a spec is the schema major. The runtime draws schema N and N - 1. `upgrade(spec)` moves an old spec up. (26 Oct 2026) `SCHEMA` and `UPGRADES` in `nbs/00_spec.ipynb`.

## Package and runtime

- **One Python package ships plain JS and CSS.** No npm, no bundler, no ES modules. `bundle()` joins the core, the blocks and the fns in a fixed order.
  Why: all the hosts are Python apps. A plain script runs the same in a `srcdoc` frame, a shadow root and a `file://` page. (26 Oct 2026) `nbs/01_render.ipynb`.
- **No network. Vendor what a demo needs.** Third-party code is in the package with its licence: three.js 0.185.0 (it loads only for a spec with a scene), Rough.js 4.6.6, perfect-freehand 1.2.2 and the Patrick Hand font. Tests check the hash of each vendored file.
  Why: a demo works offline and from `file://`. (0.0.8 to 0.0.10) `rupaka/static/vendor/`, `rupaka/static/fonts/LICENSES.txt`, `tests/test_board.py`.
- **The bundle gets its version from the package.** `bundle()` writes `Rupaka.version`, so a version bump cannot leave it behind. (0.0.3) `nbs/01_render.ipynb`.

## Hosts

- **Leela shows a demo from a `rupaka` fence or a mime type.** A markdown cell holds a fence of readable JSON. Leela mounts it in a shadow root, so the demo gets Leela's theme and its own height. `show(spec)` gives `application/vnd.rupaka+json`, with `text/html` as the fallback for Jupyter and VS Code. `md(spec, frame=True)` gives an iframe for a host with no rupaka code.
  Why: Leela's sandbox frame is 450 px tall and cannot see Leela's theme. (26 Oct 2026, "route C") `MIME`, `show` and `md` in `nbs/01_render.ipynb`.
- **The host API is a contract.** abhyasa and Leela call `Rupaka.mount`, `state`, `set`, `settle`, `open`, `options`, `append`, `anchor` and `cam`. These calls send no `rk-predict` event, add nothing to `st.log` and do not move the focus. A host can cancel `rk-predict` and then call `settle(saved, message)`. Write each change of this API in the CHANGELOG. (0.0.2 to 0.0.9) `rupaka/static/rupaka.js`, `rupaka/blocks/scene/scene.js`.
- **`rupaka.poll` keeps the abhyasa contract.** `of_gate` and `public` match `abhyasa.talk.ask_from_gate` and `public_ask`. (0.0.4) `nbs/05_poll.ipynb`.
- **The board moved here from abhyasa 0.0.16.** `rupaka.board` needs only fastcore. An app gives its own check of a quote as `verbatim`. The script sets `window.rupakaBoard` and `window.rupakaTex`. The old names `window.abhyasaBoard` and `window.abhyasaTex` point to the same objects, so abhyasa and Leela can move one step at a time. Remove the old names when no host uses them. (0.0.10) `nbs/06_board.ipynb`, `rupaka/static/board.js`, `rupaka/static/texparts.js`.

## The agent and the checks

- **The prompt comes from the manifests.** `catalog()` reads each `block.json` and fn manifest, so the prompt and the code agree. (26 Oct 2026) `nbs/03_agent.ipynb`.
- **`author` repairs two times at most.** It runs parse, `validate`, `check` and repair. After two failed repairs it gives `None` and stores nothing. The host then shows its text lesson. (26 Oct 2026) `author` in `nbs/03_agent.ipynb`.
- **Plain English is checked with no model.** `plain_why` finds long sentences, a grade over 9, semicolons, vague words and nicknames. `plain` writes a text again one time. It keeps the new text only when it is better and keeps the numbers, the maths and the code. (0.0.12) `nbs/00_spec.ipynb`, `nbs/03_agent.ipynb`.
- **`check` plays each demo in a headless browser.** It fails on a console error, a page error, a network request or a contrast under 4.5:1 in light or dark. It starts Chromium with `--enable-unsafe-swiftshader`, so WebGL draws on a machine with no GPU. (26 Oct 2026, 0.0.8) `nbs/02_check.ipynb`.

## Release and docs

- **Mark the release as Latest.** `nbdev-release-git` makes the GitHub release, but it does not mark it as Latest. After it, run `gh api -X PATCH repos/<owner>/rupaka/releases/<id> -f make_latest=true`. (3 Nov 2026)
- **Give the imports of a test cell their own cell.** The docs build runs only the cells with an import, `#| export` or `show_doc`. A test cell that starts with an import runs there without its setup, and the build fails. Before a release push, run `uv run nbdev-proc-nbs --force`. (3 Nov 2026)
