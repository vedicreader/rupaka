# Release notes

<!-- do not remove -->

## 0.0.3

- `Rupaka.version` in the bundle is the package version. In 0.0.2 it said `0.0.1`. `bundle()` now writes the version in, so a version bump cannot leave it behind.

## 0.0.2

- A host can confirm a gate's prediction. The `rk-predict` event is cancelable, and its detail has `settle(saved, message)`. A host that calls `preventDefault()` keeps the gate pending until it calls `settle`. `settle(true)` shows the result. `settle(false, message)` opens the gate again, keeps the pick and the reason, and shows the message. A host that does not cancel the event sees the same gate as before.
- The package has an icon, and the docs have one too.

## 0.0.1

- A ranklist drag keeps the pointer: the browser no longer cancels it when you grab a row by its text.

- First version. A demo is a JSON spec of blocks over a small state. Named fns compute the derived values. A spec holds no code.
- 15 blocks: gate, readout, caption, row, stack, slider, toggle, choice, wheel (items or degrees), ranklist, bars, axis, point, plot and grid.
- 9 fns: rules (with wrong options from the other rows), rrf, softmax, lookup, expr (a small safe formula grammar), ids, pick, sort and fmt. Each fn has a Python twin.
- `validate` checks a spec and enforces the think rule: a block that shows the answer must wait for the gate.
- `page`, `save`, `show`, `md`, `Demo` and `Assets` put a demo in a file, a notebook, Markdown or a FastHTML page. It works offline.
- `check` draws a demo in a headless browser (Playwright's Chromium, never your own Chrome) and plays it: no errors, no network, hidden reveals, keys on each control, and contrast in light and dark.
- `author` asks a model for a demo, then validates, checks and repairs it two times at most.
- A gallery of five demos: vowel sandhi, reciprocal rank fusion, softmax and temperature, nakṣatra and pāda, and a parabola.
