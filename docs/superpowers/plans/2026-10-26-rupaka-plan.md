# rupaka build plan

Spec: `docs/superpowers/specs/2026-10-26-rupaka-design.md`. Spike: `/tmp/demo-spike` (throwaway; copy ideas, not files).

Rules for every task:

- Write the failing test first, then the code. Run it and see it pass before the next task.
- Python lives in notebooks under `nbs/`. Run `uv run nbdev-prepare` (with a hyphen) after each notebook change. Never edit a generated `.py`.
- JS and CSS are hand-written files under `rupaka/static/`, `rupaka/blocks/` and `rupaka/fns/`.
- Browser tests run headless Chrome through playwright. No window may take focus.
- Prose (notebooks, docs, UI text, commit messages) is ASD-STE100, US grade 9. Commit messages are one plain line with no AI credit.
- fastcore and fastai style: `store_attr`, `patch`, `L`, `AttrDict`, one-line bodies, one-line docstrings.
- Phases 1 to 4 touch only this repo. Phase 5 touches abhyasa, phase 6 leela, phase 7 vedicreader. Each of those starts on a branch in its own repo.

## Phase 1: the package and the core runtime

1. **Scaffold.** `nbdev-new`-style `pyproject.toml` on hatchling (nbdev 3), `settings.ini` if nbdev needs it, `nbs/index.ipynb`,
   `CLAUDE.md` (copy the shape of abhyasa's), `.gitignore` (`tests/screens/`). Dev extras: `pytest`, `playwright`.
   Test: `uv run nbdev-prepare` passes on an empty package; `uv build` gives a wheel that contains `rupaka/static/`.
2. **Chrome fixture.** `tests/conftest.py`: a session `browser` fixture (playwright, `executable_path` from `RUPAKA_CHROME` or the Mac
   default, `headless=True`), and a `page_for(html)` helper that collects console errors, page errors and non-local requests.
   Test: a blank page has no errors; a page that fetches `https://example.com` reports one network error.
3. **Core runtime.** `rupaka/static/rupaka.js`: `el`, `sv`, path `get`, `fmt`, the store (state, derive, subscribe), `mount`, `build`,
   `after` and `lock` plumbing, `boot` on load and on `htmx:afterSwap`, the `rk-predict` event, `data-rk-ready` on host and root.
   Test (`tests/test_core.py`): a spec with one `readout` mounts, sets `data-rk-ready`, and boots only once after a second `boot()`.
4. **Theme CSS.** `rupaka/static/rupaka.css`: the `--rk-*` vars with the fallback chain abhyasa → vedicreader (`--mh-*`) → leela (`--lee-*`) → system.
   Test: in three pages that set only `--fg`, only `--mh-ink`, only `--lee-fg`, a readout's computed colour equals that var.
5. **Bundle.** `nbs/01_render.ipynb`: `assets()` (paths), `bundle()` (core + blocks + fns in a fixed order), and `page(spec, fonts='link'|'embed'|'none')`.
   Inline JSON escapes `</`. Copy Literata and Libre Baskerville subsets (OFL, with `LICENSES.txt`) into `rupaka/static/fonts/`.
   Test: `page()` output has no `http` URL; `fonts='none'` has no `@font-face`; a spec whose text holds `</script>` still mounts.

## Phase 2: the blocks

For each block: a folder with `<name>.js`, `<name>.css`, `block.json` (purpose in one line, props with types and defaults, keys, `since`)
and `example.json`. One generic test (`tests/test_blocks.py`) is parametrized over all block folders: the example passes `validate`, mounts with no
errors, has a non-empty box, and passes the contrast check in light and dark. Each block adds its own behaviour test.

6. **gate.** Options fixed or `{from}`; 1-9 pick; ⌘↩ lock; verdict with `context`; `again`; `why` line; `rk-predict` event; disabled options stay legible.
   Test: before lock, `after` blocks are hidden; a wrong pick shows the right answer; the event carries `{gate, picked, ans, ok, why}`.
7. **readout, caption, row, stack.** Caption escapes HTML, then allows only `**bold**`.
   Test: a caption with `<img src=x onerror=alert(1)>` in its text shows the text and makes no `img` element.
8. **slider, toggle, choice.** Test: keys move each value; the state changes; `aria-valuetext` follows.
9. **wheel.** Drag, click, ←/→ and A/D, Home/End; the hand starts outside the centre label. Test: two ← presses from `i` give `a`; a drag to 90° picks the item there.
10. **ranklist.** Drag; ↑/↓ focus; ⌥↑/⌥↓ and W/S move; `lock`. Test: a drag moves B from 4th to 1st; a move is refused while locked.
11. **bars.** Keyed rows that slide; stacked parts; key. Test: after a change, row order follows the values; hidden ids leave.
12. **axis, point, plot.** Shared scale from `axis`; `point` drags on it (and on a ring, for the nakṣatra wheel); `plot` draws a derived series.
    Test: a point dragged to x = 2 sets the state to 2 (with `step`); arrows move by `step`, ⇧ by ten steps.
13. **grid, tokens.** Heatmap with a sequential ramp mixed from `--rk-acc`; click or +/− changes a cell. Token strip with select and weight lines.
    Test: +/− changes the focused cell; selecting a token sets the state.
14. **stepper.** Steps with their own text and optional gate; ←/→ and A/D. Test: a step with a gate does not advance until the gate is locked in.

## Phase 3: the spec in Python

15. **fns.** `rupaka/fns/`: `rules` (with `alts`), `rrf`, `softmax`, `lookup`, `ids`, `pick`, `sort`, each with a manifest. Test in the browser
    against Python reference values: RRF at k = 60 and k = 1 for the spike lists; softmax at T = 0.5, 1, 2.
16. **expr.** A tiny safe grammar in JS (numbers, names, + − × ÷ ^, parentheses, `sin cos exp log sqrt abs min max`), and the same parser in
    Python for validation. Test: `2*x^2 - 1` at x = 3 is 17 in both; `constructor`, `__proto__`, `alert(1)` and `x;y` are refused.
17. **Builders.** `nbs/00_spec.ipynb`: `demo`, one builder per block (`slider(bind, label, ...)`), `from_`, `rules(...)`. Test: the builder form of the
    spike's sandhi demo equals the JSON form.
18. **validate.** Reads every `block.json` and fn manifest. Checks types, required props, binds, `after`/`lock` order, gate answers among options,
    the think rule (dependency walk from each gate answer through `derive`), sentence length. Errors carry paths.
    Test: one bad spec per rule fails with the right path; the two spike demos pass; a demo that shows `bars` of `fused` before the gate fails the think rule.
19. **upgrade.** `upgrade(spec)` for schema N−1 → N (an identity today, with the test frame in place).

## Phase 4: the surfaces, the check and the agent

20. **show and md.** `show(spec)` returns an object with `_repr_mimebundle_`: `application/vnd.rupaka+json` and `text/html` (the full document with
    `fonts='none'`). `md(spec, frame=False)` writes a ```` ```rupaka ```` fence; `md(spec, frame=True)` writes the `{=html}` iframe.
    Test: the `text/html` part contains `<script`; the mdhtml render of `md(spec, frame=True)` contains `<iframe` (needs `mdhtml` as a test extra).
21. **FT component.** `Demo(spec)` for FastHTML pages: the host div with inert JSON. `Assets()` gives the `Link` and `Script` tags for `/rupaka/`.
    Test: `to_xml(Demo(spec))` holds the JSON in a `script[type="application/json"]`.
22. **check.** `nbs/02_check.ipynb`: `check(spec, shots=None)` from the spike's `check.py`, made generic: ready, no errors, no network, boxes, hidden
    reveals, autoplay of each gate, keys on each control, contrast in light and dark, screenshots. Returns `AttrDict(ok, errors, shots)`.
    Test: the gallery passes; a spec with a broken fn name fails with the error text.
23. **Gallery.** `rupaka/demos/`: vowel sandhi, RRF, nakṣatra wheel, softmax and temperature, attention on a sentence, number line, function plotter,
    a three-step proof. Check the sandhi table and the nakṣatra data against vedicreader's sources (`vr/muhurtha/names.py`, ganapati), not memory.
    Test: `test_gallery.py` runs `validate` and `check` on each one.
24. **Agent.** `nbs/03_agent.ipynb`: `catalog()` (the prompt catalog from manifests), `DEMO_SP`, `demo_prompt(concept, first_error, examples)`,
    `author(ask, concept, ...)` with the parse → validate → check → repair loop (two repairs at most), and `repair_prompt(spec, errors)`.
    Test with a fake `ask` (as abhyasa's `Fake`): a good spec passes in one call; a spec with one error is fixed on the second call; three bad specs give up and return None.
25. **Live eval (by hand, not in CI).** Run `author` with the user's rishi model on ten concepts from the vault (read-only, through a temporary copy).
    Record the pass rate on the first try and after repair. Look at the screenshots. Write the numbers in the notebook.
26. **Release 0.1.0.** CHANGELOG, `nbdev-prepare`, push to a new GitHub repo (ask the user first), CI green, `nbdev-release-git`, `nbdev-pypi`.

## Phase 5: abhyasa

27. **Engine notebook.** abhyasa `nbs/0x_demo.ipynb`: `Learning.put_demo`, `Learning.demos(slug)`, `Learning.demo(slug)` on the `learning`
    shelf with `kind='demo'` and `source='learning://demo/<slug>'`; `make_demo(tutor, concept, first_error)` calls `rupaka.author`.
    Test with `temp_learning()` and `Fake`: a demo is stored, found by its concept, and found by search on its caption text.
28. **Tutor hook.** In `_close`, attach `demo` (a slug) to the result when the concept has one; queue `make_demo` in a thread when the rule in D4 says so.
    Test: a second miss with the same misconception queues one job; a concept with a demo gets its slug in the result.
29. **demo block.** `abhyasa/blocks/demo/`: routes `/demo/{slug}`, `/demo/{slug}.json`, `POST /demo/make`, `POST /demo/{slug}/predict`;
    serve `rupaka` assets at `/rupaka/`; hooks `concept_actions` and the session's lesson area; `demo.js` posts `rk-predict`. Add `demo` to `NAMES`.
    Test (`uv run pytest`): the page has the host div; the predict route writes an attempt with the gate result and the why line; `tests/test_blocks.py` still matches the folders.
30. **Notebook card.** `abhyasa.nb.learn` shows the demo with `rupaka.show` after a miss. Test: the card's output holds the rupaka mime.

## Phase 6: leela (only if the user picks route C in D2)

Before code, follow leela's AGENTS.md: write a short plan naming the entry points (markdown render pass, `outputEl`), every route that reaches them
(cell render, present mode `present.js:107`, agent replies, the markdown preview), the failure states (bad JSON, unknown schema), and the tests;
have an independent reviewer check it for missing cases.

31. **Vendor.** A script that copies `rupaka.js` and `rupaka.css` from the installed package into `leela/vendor/`, with the version in a comment.
32. **Fence pass.** In the post-render pass beside `enhanceCodeBlocks`, mount each `code.language-rupaka` in a shadow root; a bad spec shows the JSON and one muted line with the error.
    Test: a regression test that renders a markdown cell with the fence and finds `[data-rk-ready]` in the shadow root; a bad spec shows the error line.
33. **Mime.** In `outputEl`, draw `application/vnd.rupaka+json` before the `text/html` branch. Test: an output with both mimes draws in-page, not in a frame.
34. **Agent.** A skill for leela's assistant (a ramabana pyskill if ramabana finds skills in installed packages; else a skill file in leela) that tells it to call
    `rupaka.author` and write a fence. Test: the skill text lists only installed blocks (it is built from `catalog()`).

## Phase 7: vedicreader

35. **Sync tool.** `vr-rupaka` copies the assets into `static/js/vendor/` and `static/css/`. Link them with `js_src` and `css_src` on the pages that hold a demo.
36. **First use.** One primer chapter gets a demo (for example the nakṣatra pāda), with the spec as a `data-*` JSON block.
    Look check with a `tests/check_*.py` script and fastcdp, headless, as vedicreader does. No suite test reads CSS.

## Later

- `rupaka.ft.still(spec)`: a server-drawn first frame as FT SVG, so a page shows the figure with no script.
- Video: record a demo's autoplay as frames (abhyasa's "UI blocks for learning videos").
- A demo editor in abhyasa: change a spec by voice ("make k start at 10") and re-check.
