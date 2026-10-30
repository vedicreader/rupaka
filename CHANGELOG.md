# Release notes

<!-- do not remove -->

## 0.0.8

- A new block family draws 3D scenes. The `scene` block holds `body`, `force`, `label3d` and `shot` blocks. Each one has a manifest and an example.
- A `body` is a `box`, `cylinder`, `cone`, `sphere`, `capsule`, `torus` or `group`. `in` puts it in another body, so it moves and turns with that body. An item of `rot` can be a state key, and a change of it eases over `turn` ms.
- A `force` is an arrow on a body. Its length is `mag` times the scene `scale`, so the arrows of one scene compare. It grows when it shows and when `mag` changes.
- A `label3d` is a chip with a leader line to a point. The chips of a scene never overlap. A chip goes to a free place around its point and keeps it while it stays free. A chip with no free place does not show.
- A `shot` is a named camera: `wide`, `side`, `front`, `top` or `close:<body id>`. The scene finds the framing from the bounds of what shows. The camera moves to the newest shot with easing. With `prefers-reduced-motion`, it cuts.
- With `bind`, a scene builds one step at a time. A part with `step: n` shows from step n. `steps` gives one line for each step. A/D or the arrows go back and on, 1-9 go to a step, Q/E turn the view and W/S tilt it.
- The look is toon style: flat colours in three soft bands, ink outlines from an edge pass on depth and normals, a soft floor and a blurred contact shadow. The colours come from the `--rk-*` vars, in light and dark.
- `Rupaka.cam(el, shot)` sets the key that a bound `shot` block reads, for the `cam` operation of a board. It gives `false` for a bad name. `shots(spec)` gives the shot names that a spec knows.
- `validate` refuses an unknown body kind, a size with the wrong count of numbers, a body id that is used twice, a body `in` a body below it, a force or a label `on` a missing body, a bad shot name, and a step outside the `steps` lines. A manifest prop can have `of`, a list of the values that it allows.
- rupaka keeps three.js 0.185.0 (MIT) in `rupaka/static/vendor/three/`. It loads only for a spec with a scene. `page` puts it in the page, and a server serves `bundle('three')` as `three.js` beside `rupaka.js`. The tests check the hash of each vendored file.
- `Rupaka.rgb(node, colour)` gives the RGB of a colour or a `--rk-*` var. `pixels` uses it now.
- The headless check starts Chromium with `--enable-unsafe-swiftshader`, so WebGL draws on a machine with no GPU.
- A spec with `"mode": "learn"` is an explainer. It has no gate, so it shows a thing at once, with no prediction step. The runtime shows a small "Explainer" label above the title. `validate` refuses a gate in an explainer, a block that waits for a gate, and a `mode` that is not `predict` or `learn`. A spec with no `mode` still needs a gate. `demo` takes `mode`.

## 0.0.7

- The fn `field` computes an `expr` formula for each cell of an n x n grid. It gives a list of n rows. Row `i` and column `j` go from 0 to n - 1. The formula can read `i`, `j` and number state keys. `n` is from 1 to 64, and the default is 16.
- A `field` formula can call `noise(i, j)`. It gives a value with mean 0 and variance 1. The same `seed`, `i` and `j` always give the same value. The default `seed` is 0. The runtime and `rupaka.spec.noise` give the same bits. A plain `expr` formula cannot call `noise`. It fails with `expr: no function "noise"`.
- The block `pixels` draws a list of rows of numbers as a grey image, one square per cell. The smallest value has the page colour and the largest value has the text colour. `lo` and `hi` set the ends of the scale. The image changes when the state changes. It is read-only.
- The `label` of `pixels` can hold `{path}`. The label shows above the image. It is also the `aria-label` of the image, which has the role `img`.
- `validate` refuses a `field` with an `n` that is not an int from 1 to 64, or a `seed` that is not an int. A bad formula gives its `expr:` error. In the browser, a bad formula stops the demo with the same error, as a bad `expr` does.
- A manifest prop can have `min` and `max`. `validate` refuses a value outside them with `must be from <min> to <max>`.
- `parse_expr(src, fns)` and `Rupaka.expr(src, fns)` take more functions by name in `fns`.
- The gallery has a new demo, `diffusion-noise`. It shows the forward noise of a diffusion model with a linear schedule.

## 0.0.6

- `Rupaka.open(el, gate)` opens a closed gate again, as the Try another button of the gate does. It removes the pick, the reason and the verdict, sets `gate.<id>` to `'open'` and hides the blocks that wait for the gate. It draws one time. It does not move the focus. It sends no `rk-predict`, adds nothing to `st.log` and does not call `save`. A gate that is open does not change, and the call gives `true`. A gate that waits for the host to save a prediction does not open, and the call gives `false`. An unknown gate gives `false`. It throws the same error as `Rupaka.state` when no demo is mounted in `el`.
- The Try another button and `Rupaka.open` use the same code. The button also removes the old verdict text now. Before, the button only hid it.

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
