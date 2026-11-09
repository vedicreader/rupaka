# Release notes

<!-- do not remove -->

## Unreleased

- A picture can have layers. The `layers` block holds `layer` blocks (sky, hill, water, sun, cloud, boat). Each layer has a place, a size, a turn, a fade and a depth, and a far layer moves less than a near one. A layer with `drag` has a handle that writes a state key. The new `timeline` block moves a time `t` with a bar, Play, markers and the keys A/D, Q/E and W. While a handle or the bar changes, a layer can show a faint ghost of its earlier place.
- The new fns `ease` (linear, in, out, inout, step) and `keyframes` (a value at a time from `[t, value]` keys) have Python twins. The demo `scene-dawn-to-dusk` shows a boat on a river from dawn to dusk.
- Six new demos on circuits and signals: `ohms-law`, `rc-charging`, `rc-low-pass`, `add-sine-waves`, `sampling-aliasing` and `the-spectrum`.
- New fns `sample` and `dft` for signals. A plot takes `ghost` and `tone`, and an axis takes `xlog`.
- A plot draws the learner's guess dashed after Lock in.
- A point can ride a curve: with `along`, its y follows its x, and a drag or the keys A/D change x only.

## 0.0.15

- A 3D scene that a host takes off the page and puts back (a tab switch) draws again. The view keeps its renderer while it is away. When the browser takes its WebGL context away, the view makes a new one when it comes back. Only a demo that the host replaces frees its context.

## 0.0.14

- A demo has an "Ask about this" control. It sends the `rk-ask` event with the learner's words, the demo, the current step and the values of its declared state, clipped. It sends no DOM and no HTML. A host that takes the event calls `preventDefault`. With no listener, the demo says "No tutor is on this page." `Rupaka.ask(el, text)` sends the same event from code.
- A spec turns the control off with `askable: false`. A host page turns it off or on with `askable=` on `host`, `page` and `Demo`, or `Rupaka.mount(el, {askable})`, and the host wins over the spec. Turn it off for a room's screen.
- A row of step boxes in a flow fits each box to its words and wraps the row. In a column under 480 px it becomes a list from the top down. Arrows no longer cover a box.
- An axis labels only every k-th tick, so labels never meet. The labels start at 0 on a round step, so the zero line says 0.

## 0.0.13

- The ask, a gate prompt and a gate context showed **bold** with its stars. Now these texts and the caption show bold in a `strong` element through one helper, `Rupaka.rich`, and `validate` refuses **bold** in the other texts.
- The README is short, with examples that run as tests, screenshots and animations, and its images show on PyPI. `docs/decisions.md` keeps the decisions that a maintainer needs.

## 0.0.12

- The panel of the board has six shapes, and each panel has one shape. A table has column names over rows of cells and an answer. A list has the same rows with no names. A flow of boxes (`node`, `edge`) shows a pipeline, a loop or a branch, one box at a time. A faded example hides parts of a row as `{"blank": value}`, and a blank shows at the next step or on a click. A card of a wrong idea (`myth`) shows "You might think" next to "In fact", with one line of why. Three stages (`"stages": true`) go from a case to a picture to the symbols.
- The board repairs a panel line that is too long: it keeps the line and cuts only its bad part. A panel line that has nothing in it drops, and a panel shows with its first row, so the page never shows an empty card. Bad panel lines do not end the board.
- A follow-up builds on the board before it. `play(..., {keep: true})` keeps the old marks at 30 % and the old panel at the top, with the new part under it. A thread turn can say what its panel showed (`shown`).
- Labels on the page never cover each other: a label with no free place drops. Marks on a formula part sit on their line, and they move again when the web fonts load.
- `plain_why(text)` finds the parts of a text that are not plain English: sentences of more than 20 words, a reading grade over 9, semicolons, vague words and nicknames. `plain_errors(spec)` checks the texts of a demo. `plain(ask, x)` writes a failing text again one time, and keeps the new text only when it is better and keeps the numbers, the maths and the code. `author` repairs a demo that is not plain with its repair prompt. Each spoken line of a board keeps its problems in `hard`, with no model call.
- The demo agent writes for a human learner of any level. It starts from a concrete case and says why. `demo_prompt` and `author` take an optional `level` line. Three gallery demos start from a concrete case.
- Less code: one walk of the blocks, one closure for the keys of the think rule, one pattern for the `{path}` slots, and fastcore `Path.read_json`, `Path.mk_write` and `last` in place of hand-written code.

## 0.0.11

- The panel of the board follows the steps. A panel row moves to the step whose line names it. A row that names nothing on the page drops. `key_terms`, `named` and `page_terms` find the words and maths tokens that a line and a row share.
- A cell of the panel can hold maths. A `$` sign does not count toward the length of a cell.
- The curve from a row to its line goes around the text, and a label stays off the lines that it marks.
- A mark on a part of a formula finds the block of that part. A label tries more places above the block before it gives up.

## 0.0.10

- A new module, `rupaka.board`, has the board of the screen guide, from abhyasa 0.0.16: the board language (`OPS`, `FIELDS`, `LIMITS`), `check_line`, `parse_board`, `clean_context`, `norm_tex`, the video cues (`cue_at`, `cue_quote`, `video_id`, `video_cues`) and `stream_board`. It needs only fastcore. `parse_board` and `stream_board` take `verbatim`, the check of a quote, so an app can give its own rules for sources.
- rupaka ships the board files: `static/board.js`, `static/board.css` and `static/texparts.js`, with Rough.js 4.6.6 and perfect-freehand 1.2.2 (MIT) in `static/vendor/board/`. `rupaka.board.assets()` gives their paths, and `rupaka.board.bundle('js')` and `bundle('css')` give one script and one style sheet.
- The script sets `window.rupakaBoard` and `window.rupakaTex`. The old names `window.abhyasaBoard` and `window.abhyasaTex` are the same objects, so abhyasa and Leela can move one step at a time.
- `paper.css` holds the tokens of the paper look (`--rk-paper`, `--rk-paper-ink`, `--rk-hand` and others). The paper theme of a demo and the side panel of the board both use them, so they look the same. `bundle('css')` starts with it.

## 0.0.9

- In an explainer, any block can have `step`. It shows when the state key `step` is at that value or more, and draws in from the left. The host moves on with `Rupaka.set(el, {step: n})`. A block that has its own `step` (a slider, a scene part) keeps it; put it in a `stack` to show it by step. `validate` refuses a step in a demo that predicts, and a step with no int state key `step`.
- `Rupaka.append(el, block, {into})` adds one block to a mounted demo with no rebuild, at the end or in a `stack` or `row`. It gives the path of the new block. `append(spec, block, into)` in Python adds the block only when the grown spec passes `validate`, and gives the errors.
- A new block, `pair`, shows one row of a worked example: input cells, an arrow and the answer. It can have two `heads` and a number `n`. The cells, the arrow and the answer draw in 80 ms apart.
- A new block, `flow`, shows two to five nodes and at most eight arrows, in a `row` (left to right) or a `cycle` (a loop). With no edges, each node points to the next. A skip arrow goes over the row and an arrow back goes under it. `validate` checks the node ids, the node text (at most 32 characters) and the arrow words (at most 3 words).
- `Rupaka.anchor(el, path)` gives the element of a block or of a part. Each block has a stable `data-rk-id`: its path in the spec, for example `blocks.2`, `blocks.2.cells.0` or `blocks.3.nodes.1`.
- A paper theme: `data-rk-theme="paper"` on the demo element or a parent gives a warm paper ground, light boxes, sketch lines and a hand font. `host`, `page` and `Demo` take `theme='paper'`. The light and dark page themes do not change.
- rupaka keeps the hand font Patrick Hand (SIL Open Font License 1.1) in `rupaka/static/fonts/`, with its licence in `LICENSES.txt`. `font_css` loads it.
- A manifest prop can have `least` and `most`, the count of items that a list allows.

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
- `rupaka.css` has shared tokens for space, radius, type size and motion: `--rk-s1` to `--rk-s6`, `--rk-r`, `--rk-r-s`, `--rk-t-lbl`, `--rk-t-meta`, `--rk-t-small`, `--rk-t-big`, `--rk-dur-1` to `--rk-dur-3` and `--rk-ease`. Each token takes the abhyasa var first, if the page has it. The block CSS uses these tokens.
- A disabled button shows as an outline with readable text. A selected option has a light tint of the accent colour. The reason box has no resize grip.
- A block that shows after the reveal moves up 6 px into its place. Its colour does not fade.
- With `prefers-reduced-motion`, rupaka stops all transitions and animations.
- The `ranklist` SVG is at most 360 px wide, so its text is near the size of the body text.
- The `grid` example says "strongest colour" in place of "darkest colour". The strongest colour is correct in light and dark.
- The selected day of a `wheel` fits inside its dot.
- The floor of a scene fades into the page. The view has no ground band and no cut edge.
- The parts of a scene have softer colours. On a dark page, a light part does not glare. Round parts show three soft bands, so they look round.
- A scene chip goes first to a free place that covers no part. Among those places, a place where its leader line crosses no other leader line wins. If each free place covers a part, the chip goes to the place that covers the least. A chip searches farther from its point than before.
- The step line of a scene shows above the Back and Next buttons. The step count uses the small meta type.
- The `wide` shot looks from a lower and closer angle: 30 degrees around, 18 degrees up.

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
