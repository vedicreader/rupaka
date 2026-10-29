# Release notes

<!-- do not remove -->

## 0.0.5

- `Rupaka.options(el, gate)` gives the option values of a gate, in the order that the gate shows them. Each value is the value itself, not the text that the gate shows. Options that come from the state are read after `derive`. An unknown gate gives `null`. It throws the same error as `Rupaka.state` when no demo is mounted in `el`.
- `Rupaka.settle(el, gate, pick, {answer})` draws the verdict with `answer` when the spec of the copy has no answer for the gate. `answer` is `{is: value}` or a path in the state, as in a gate. When the spec has an answer, the gate uses the answer in the spec. Rupaka does not write `answer` into the spec or the state. The rest of the 0.0.4 contract does not change.
- `Rupaka.settle` on a gate with no answer in the spec, and with no `answer`, now closes the gate with no verdict. In 0.0.4 it showed a broken verdict ("It is .").

## 0.0.4

- `Rupaka.state(el)` gives a copy of the input keys (the keys of `spec.state`) of the demo in `el`, with their values.
- `Rupaka.set(el, state)` sets the input keys that `state` has, runs `derive` one time and draws one time. It ignores other keys. It sends no `rk-predict` and adds nothing to `st.log`.
- `Rupaka.settle(el, gate, pick)` closes a gate as if the learner picked `pick`, and draws the verdict and the blocks that wait for the gate. A null `pick` closes the gate with no verdict. An unknown gate does nothing. It sends no `rk-predict` and adds nothing to `st.log`. The `settle(saved, message)` of the `rk-predict` detail does not change.
- `Rupaka.mount(el, spec, {save})` calls `save(state)` after each change of an input key, with the value that `Rupaka.state(el)` gives. A mount with no options does the same as in 0.0.3.
- `rupaka.poll` has `of_gate(spec, gate)` and `public(p)`: a choice question for a room from a demo gate, and the part of it that the room sees. They have the contract of `abhyasa.talk.ask_from_gate` and `public_ask`.
- `of_gate` writes the values in the prompt and the options as the demo shows them in the browser, so 2.0 shows as 2 and the options are text.
- The Python copies of the runtime, `js_str` and `show_value`, give the same text as the browser. Before, they differed for tiny and large floats, for ties such as 1.03125, and for a null in a list. `validate`, the `rules` seed and the `lookup` and `softmax` ids use them, so their result can change for those values only.

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
