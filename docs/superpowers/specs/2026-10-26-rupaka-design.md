# rupaka: interactive SVG demos that make the learner think

Date: 26 October 2026. Status: design, before any code. A spike in `/tmp/demo-spike` proves the hard parts (see "Spike").
The text "(my call)" marks a decision that I made. Check these decisions first. The last section lists the decisions for the user.

## Why

The user asked: "we need the tool to create svg based interactive demos to teach concepts. have an agent (design + functionality plan)
that can also be leveraged by leela to create them as markdown cells which show them. we can create lego block like ui blocks for reuse
and have a repo of such ui blocks."

abhyasa teaches with text only. After a miss, `teach_prompt` (abhyasa `nbs/03_tutor.ipynb`, `tutor.py:93`) writes a lesson of 120 words.
Some ideas are easier to see than to read: a sandhi rule, a fusion score, a softmax with a temperature, a wheel of 27 stars.
A demo lets the learner change the inputs and see the result. But a demo that only shows the answer breaks the first rule of abhyasa:
the tool never thinks for the learner. So each demo here asks the learner to predict first.

## Name (my call)

`rupaka` (रूपक). The word has three senses, and each one fits:

1. A form, a figure, a model. A demo is a small model of one idea.
2. In the Nāṭyaśāstra, a rūpaka is a play that the audience sees acted. Here the learner acts in the play.
3. In alaṅkāra, rūpaka is the figure that shows one thing through another (metaphor). A demo shows an abstract rule through a picture.

It is short, it is easy to type, and it fits the other names (abhyasa, leela, vedicreader, vishalakshi). The folder
`orgs/rupaka` was free. The PyPI name is not checked yet (decision D1).

## What a demo is

A demo is one interactive SVG figure that teaches one concept. It has three parts:

1. A spec: a JSON object. It lists blocks, a small state, derived values and data tables.
2. Blocks: reusable UI parts (a slider, a wheel, a gate). Each block is a folder, like a lego block.
3. Named functions (fns): pure functions that compute derived values from the state, for example `rrf` or `rules`.

A demo never holds code. An LLM writes data (a spec and its tables), never JavaScript (my call). This makes a demo safe to store,
safe to show in leela, and easy to check.

Each demo follows one loop. This is the "make the learner think" rule:

1. Predict. The demo shows the inputs and asks one question. The learner picks an answer and, if they want, writes one line on why.
   The result is hidden.
2. Reveal. The learner locks in (⌘↩). The demo shows the result, says if the prediction was right, and shows the rule.
3. Manipulate. Now the controls are live. The learner changes the inputs and sees the result change.
4. Explain. The caption ends with a new question ("Move k down to 1. Which document wins now? Why?"). In abhyasa the tutor grades
   that answer as the next check question.

The validator enforces step 1 (see "Validation"): every block that shows a value which the gate's answer depends on must wait for the gate.

### Examples

| demo | blocks | gate question |
|---|---|---|
| vowel sandhi | two `wheel`s (vowels), `gate`, `readout`, `caption` | "What do a + i become?" |
| reciprocal rank fusion | two `ranklist`s, `gate`, `slider` (k), `bars` | "With k = 60, which document comes first?" |
| nakṣatra wheel | `wheel` (27 stars), `point` on the ring (a longitude), `readout` | "At 47°, which star and which pāda?" |
| softmax and temperature | `grid` (logits), `slider` (T), `bars` | "If T doubles, does the top share rise or fall?" |
| attention | `tokens` (a sentence), `grid` (weights), click a token | "Which word does 'it' attend to most?" |
| number line | `axis`, `point` | "Where is −7/3?" |
| function plotter | `axis`, `plot`, `slider`s for parameters | "What does b do to the curve?" |
| proof step-through | `stepper`, `caption`, a `gate` per step | "What is the next step?" |

## Blocks

A block is a folder in `rupaka/blocks/<name>/`, as in lego, abhyasa and vedicreader:

```
rupaka/blocks/wheel/
  wheel.js      # R.block('wheel', (b, ctx) => node): builds the DOM and SVG, binds to state
  wheel.css     # the block's own style; colours only from --rk-* vars
  block.json    # the manifest: purpose (one line, for the LLM), props with types and defaults, keys, an example
  example.json  # a small demo that uses only this block (and a gate); the browser test renders it
```

### The vocabulary

| block | binds | what it does | keys |
|---|---|---|---|
| `slider` | number | a range input with its value | ←/→ (native) |
| `toggle` | bool | on or off | Space |
| `choice` | string | a row of options, one picked | ←/→, 1-9 |
| `wheel` | string | a ring of items; drag the hand or click an item | ←/→ or A/D, Home/End |
| `point` | number or [x, y] | a draggable point on an `axis`, a plane or a ring | arrows or WASD; ⇧ for big steps |
| `axis` | none | a number line or x/y axes with ticks; other blocks draw on it | none |
| `plot` | derived series | a line or points from a derived list | none |
| `grid` | 2-D list | a heatmap; a cell can be clicked to change its value | arrows move, +/− change |
| `tokens` | list of strings | a token strip; select one token; optional weight lines | ←/→, Space |
| `ranklist` | list of ids | an ordered list; drag a row to move it | ↑/↓ focus, ⌥↑/⌥↓ or W/S move |
| `bars` | derived list | horizontal bars with stacked parts; rows slide to their new place | none |
| `stepper` | index | a timeline of steps; each step can hold its own gate | ←/→ or A/D |
| `readout` | template | one large line, for example "a + i → e" | none |
| `caption` | template | the explain panel: short text with `{path}` values and **bold** | none |
| `gate` | none | predict, then reveal; blocks with `after` wait for it | 1-9 pick, ⌘↩ lock in |
| `row`, `stack` | none | layout: children side by side, or one above the other | none |

### The contract

Every block must obey these rules. The browser test checks each one.

- Input is data. A block reads its props from the spec and its values from the state. It never reads the network or the page outside its root.
- Theme by CSS vars. Blocks use only `--rk-bg`, `--rk-fg`, `--rk-ink2`, `--rk-mute`, `--rk-line`, `--rk-acc`, `--rk-ok`, `--rk-no`,
  `--rk-serif`, `--rk-mono`. `rupaka.css` maps each one to the host's vars, in this order: abhyasa (`--fg`, `--acc`, …),
  vedicreader (`--mh-ink`, `--mh-accent`, `--mh-paper`, …), leela (`--lee-fg`, `--lee-accent`, …), then system colours. So the same demo takes
  the look of the page it is in. A standalone file carries abhyasa's palette, with light and dark from `prefers-color-scheme`.
- Look. Muted, no boxes in boxes, hairlines in `--rk-line`, one accent. Text contrast is at least 4.5:1 in light and dark. Labels are small
  spaced capitals, as in abhyasa's `base.css`.
- Keyboard. Every control takes focus in reading order and works with keys. Keys act only while the demo has focus; a demo never takes a
  global shortcut, so it cannot fight leela's keymap. Each control has a left-hand alternative (A/D, W/S, 1-4). Key hints use Mac symbols (⌘ ⌥ ⇧ ↩).
- Access. SVG controls have `role`, `aria-label` and `aria-valuetext`. A reveal is `aria-live="polite"`.
- No network, no `eval`, no dependencies. No d3 in the core (my call): the spike draws two demos with 15 KB of plain JS. A block that
  needs d3 (for example a force layout) may declare it in its manifest, and the static export then inlines d3.
- No focus stealing. A demo never calls `focus()` on mount.
- Text in a spec goes in with `textContent`. The caption allows only `**bold**` and `{path}`; it escapes everything else first.
- Size. A demo fits in 640 × 720 CSS pixels. Leela's sandboxed output frame is 450 pixels tall today (see "Leela").

### Named functions

| fn | inputs | output |
|---|---|---|
| `rules` | state keys, a table of rows `{when: {key: [values]}, out: "template {key}", name, sutra, why}` | the first row that matches, its `out`, and `alts` (what other rows would give: distractors for a gate) |
| `rrf` | ranked lists, `k` | fused scores with one part for each list |
| `softmax` | a list or grid, temperature | probabilities |
| `lookup` | a key, a table | the row for the key |
| `expr` | a formula in a tiny safe grammar (numbers, + − × ÷ ^, a few math functions, state names) | a number or a series over a range |
| `ids`, `pick`, `sort` | a list | a list (small helpers) |

A new fn is code, so a person writes and reviews it in this repo. The LLM can only use the fns that exist. `expr` covers most plots
without new code. The `rules` fn with its `alts` lets the LLM write a whole rule system (vowel sandhi needs 18 rows) as data, and get
plausible wrong options for free.

## The spec

```json
{
  "rupaka": 1,
  "id": "reciprocal-rank-fusion",
  "concept": "reciprocal-rank-fusion",
  "title": "Reciprocal rank fusion",
  "ask": "Two searches rank the same documents. ... Predict the winner.",
  "state": {"bm25": ["A","C","E","B"], "vec": ["D","F","G","B"], "k": 60},
  "derive": [{"fn": "rrf", "in": ["bm25", "vec"], "k": "k", "out": "fused"}],
  "blocks": [
    {"type": "row", "blocks": [
      {"type": "ranklist", "bind": "bm25", "label": "Keyword search (BM25)", "lock": "win"},
      {"type": "ranklist", "bind": "vec", "label": "Vector search", "lock": "win"}]},
    {"type": "gate", "id": "win", "prompt": "With k = 60, which document comes first after fusion?",
     "options": ["A","B","C","D"], "answer": "fused.0.id", "why": "Say why, in one line, before you lock in."},
    {"type": "slider", "after": "win", "bind": "k", "label": "k", "min": 1, "max": 100},
    {"type": "bars", "after": "win", "bind": "fused", "label": "Fused score"},
    {"type": "caption", "after": "win", "text": "First now: **{fused.0.id}**. Move k down to 1. Which document wins now? Why?"}
  ],
  "tables": {}
}
```

- `rupaka` is the schema version. The runtime draws schema N and N−1. `rupaka.upgrade(spec)` moves an old spec up.
- `state` holds the inputs. `derive` runs in order after each change, and writes its `out` into the state.
- A path such as `fused.0.id` reads into lists and objects.
- `after: gate-id` hides a block until the gate is locked in. `lock: gate-id` shows a control but keeps it still until then.
- A gate reads its `answer` from the state, so the answer stays correct when the inputs change. `options` is a list, or `{"from": "join.alts"}`.
- `again: true` lets the learner arm the gate again for a new pair (sandhi). `context` says which inputs the verdict was for.

Python helpers build the same dict in fastai style, so a notebook author does not type JSON:

```python
from rupaka import demo, wheel, gate, readout, caption, rules
d = demo('vowel-sandhi', 'Vowel sandhi', state=dict(a='a', b='i'), derive=[rules('sandhi', ['a','b'], 'join')],
         blocks=[row(wheel('a', VOWELS, 'End of word 1'), wheel('b', VOWELS, 'Start of word 2')),
                 gate('join', 'What do the two vowels become?', options=from_('join.alts'), answer='join.out'),
                 readout('{a} + {b} → {join.out}', after='join'), caption('**{join.name}** ({join.sutra}). {join.why}', after='join')],
         tables=dict(sandhi=SANDHI))
```

## Where a demo shows

One runtime (`rupaka.js` + `rupaka.css`) draws a spec everywhere. A host element carries the spec as inert JSON:

```html
<div data-rupaka><script type="application/json">{...spec...}</script></div>
```

The runtime boots on load and after each htmx swap, as vedicreader's scripts do. Nothing is templated into the script.

### abhyasa: a `demo` block

A new folder `abhyasa/blocks/demo/` (cfg.py, ui.py, app.py with `CAPS = ('learning', 'ask')`, demo.css, demo.js).

- Routes: `/demo/{slug}` (a page), `/demo/{slug}.json`, `POST /demo/make` (author one for a concept), `POST /demo/{slug}/predict` (log a prediction).
- It serves `rupaka`'s assets at `/rupaka/` from the installed package, so the app stays offline.
- Hooks: `concept_actions` adds "See the demo" or "Make a demo". The session page shows the demo under the lesson after a miss.
- `demo.js` listens for the `rk-predict` event (the gate sends `{gate, picked, ans, ok, why}`) and posts it. The prediction is code-graded.
  The "why" line and the answer to the caption's last question go to the tutor's grade loop as think-aloud.

### leela

These findings come from leela's source, and from mdhtml 0.1.38 run in isolation with the same calls as leela.

| finding | where |
|---|---|
| A markdown cell renders on the server through mdhtml. Plain raw HTML in Markdown is escaped, so `<svg>` and `<script>` show as text. | `leela/app.py:980-994` (`/markdown/render`) |
| Markdown cells ask for `allow_raw=true`, so a ```` ```{=html} ```` fence passes its HTML through. mdhtml does not sanitize it: `<script>`, `<style>`, `<iframe>` and `on*` attributes all come out. There is no DOMPurify. | `leela/blocks/nb/cells.js:382`, `leela/app.py:985-987`; spike `leela_md.py` |
| The client puts the HTML in the page with `el.innerHTML = d.html`. So a `<script>` from the fence does not run. | `leela/static/js/core.js:671` |
| An unknown fence, for example ```` ```rupaka ````, renders as `<pre><code class="language-rupaka">`. Code blocks get a post-render pass. | `core.js:676-679` (`enhanceCodeBlocks`) |
| A code-cell output with `text/html` that contains `<script` goes into an iframe with `sandbox="allow-scripts"` and `srcdoc`, 450 px tall, resizable. Its scripts run, in an opaque origin. | `leela/blocks/nb/cells.js:534-539` (`sandboxFrame`), `cells.js:572` |
| `text/html` without a script, and `image/svg+xml`, go into a shadow root by `innerHTML`. Scripts do not run there. | `cells.js:571-585` |
| ipywidgets work through a vendored widget manager over a comm socket. anywidget is not in the bundle. | `leela/blocks/nb/widgets.js:1-60`, `leela/vendor/lee-widgets.js` (0 matches for anywidget) |
| Leela's theme vars are `--lee-bg`, `--lee-fg`, `--lee-accent`, … on `:root[data-theme="leela"][data-mode=…]`, not `prefers-color-scheme`. | `leela/static/lee-ide.css:31-42` |

So there are three routes:

- **A. A code-cell output, no leela change.** `rupaka.show(spec)` returns an object whose `_repr_html_` is one HTML document with the runtime
  inlined (27 KB). Leela sends it to the sandboxed frame. This works today; the spike proves it. Limits: the frame is 450 px tall (the
  sandhi demo needs about 700 px, so the gate is below the fold until the learner drags the frame taller); the frame cannot see leela's
  vars or its dark mode (it follows the OS scheme); fonts fall back to the system serif, because a sandboxed `srcdoc` frame cannot load
  local font files.
- **B. A markdown cell, no leela change.** `rupaka.md(spec)` writes a ```` ```{=html} ```` fence that holds `<iframe sandbox="allow-scripts" srcdoc="…">`.
  It works today; the spike proves it. Limits: as in route A, and the cell source is 28 KB of escaped HTML, which no person can edit.
- **C. A `rupaka` fence, a small leela change (recommended, my call).** The markdown cell holds readable JSON:

  ````
  ```rupaka
  {"rupaka": 1, "id": "rrf", ...}
  ```
  ````

  Leela vendors `rupaka.js` and `rupaka.css` (as it vendors the widget bundle). In the post-render pass (`core.js:676`, beside
  `enhanceCodeBlocks`), it finds `code.language-rupaka`, parses the JSON, and mounts the demo in a shadow root. The demo then takes
  leela's vars and dark mode, and its height is natural. The same pass handles a new output mime `application/vnd.rupaka+json` in
  `outputEl` (`cells.js`, before line 571), so `show(spec)` publishes the mime and keeps route A as the fallback for Jupyter and VS Code.
  Other renderers (GitHub, nbdev docs) show the fence as JSON code, which is a fair degradation. The change is about 30 lines and a test.

The abhyasa design said "no change to leela". Route C breaks that rule, so the user must choose (decision D2). Routes A and B ship first in
any case, because they need nothing from leela.

Side finding, not part of this work: the ```` ```{=html} ```` fence lets `on*` attributes and `<style>` from a notebook into leela's own DOM
(`core.js:671`). An `<img onerror=…>` in a markdown cell runs in leela's origin. A notebook from someone else could use this.

### vedicreader

vedicreader draws figures on the server with `fasthtml.svg` (`vr/jyotisha/nakshatra/wheel.py`, `vr/jyotisha/kit/plot.py`) and adds
behaviour with one IIFE per script that boots from `data-*` attributes (`static/js/jy-nakwheel.js`). rupaka keeps both habits: the spec
travels in the page as data, and the runtime is a plain IIFE. vedicreader links `rupaka.js` and `rupaka.css` through its hashed `js_src`
and `css_src`. A small `vr-rupaka` sync tool copies the files from the installed package into `static/js/vendor/` and `static/css/`,
because a hashed static file is how vedicreader serves every script. The `--mh-*` vars map into `--rk-*` in `rupaka.css`.

A later step: a server-side first frame. `rupaka.ft.still(spec)` draws the opening state as FT SVG, so a page shows the figure with no
script and the runtime takes it over. Not in the first build.

### Static HTML

`rupaka.page(spec)` writes one self-contained file: runtime, CSS, spec, and the abhyasa palette. `fonts='link'` links Literata from
`./fonts`; `fonts='embed'` inlines it as data URIs (about 95 KB more); `fonts='none'` uses the system serif (for `srcdoc`). A file works
from `file://` with no network. The spike's `index.html` is such a file.

## The demo agent

### Who asks

1. abhyasa's tutor, after a miss. `_close` (tutor.py:215) teaches the smallest step. If the concept has a demo, the session shows it under
   the lesson, and the demo's gate replaces the lesson's "Check:" line. If the concept has no demo, and the same misconception came twice,
   or the concept is marked `visual`, the tutor queues an authoring job in the background. The demo is ready next time. The learner never waits.
2. The learner, from the concept page ("Make a demo").
3. Leela's assistant, when the user asks for a demo in a notebook. The assistant calls the same `rupaka.author` and writes a ```` ```rupaka ````
   fence (route C) or a code cell `show(spec)` (route A).

### The prompt

The system prompt is built from the block manifests, so it never drifts from the code:

```
You design one interactive demo that makes the learner think. You write a JSON spec. You never write code.
Rules:
- One concept. One gate at least. The learner predicts before the demo shows any result.
- Every block that shows a value the gate's answer depends on has "after": the gate id.
- After the reveal, the controls are live. The last caption asks one new question that the learner can answer only by using the controls.
- Wrong options in a gate each match one named misconception. Use "rules" with "alts" when the concept is a rule system.
- Use only these blocks and fns: <catalog: name, one-line purpose, props with types, one example, from block.json>.
- Fit in 640 x 720. At most 8 blocks. Text in ASD-STE100 Simplified Technical English, US grade 9: short sentences, active voice.
Return JSON only.
```

The user prompt is abhyasa's `_concept_block` (name, statement, misconceptions, learner floor), plus the first error from the grade, plus
two or three gallery demos that are near the concept (from a search over the demo shelf), as few-shot examples.

### Validation

`rupaka.author(ask, concept, ...)` runs this loop, with at most two repairs:

1. Parse. `ask_json` returns a dict, or the loop asks again.
2. Schema check (`rupaka.validate`). Each error has a path and a sentence, for example `blocks[3].bind: "fused" is not in state or derive`.
   - Each block type and fn exists; each prop has the right type; required props are present.
   - Each `bind` names a state key or a derive `out`. Each `after` and `lock` names a gate that comes earlier.
   - Each gate's `answer` path resolves on the opening state, and the answer is one of its options.
   - The think rule: the validator follows the answer's root key (for `fused.0.id`, it is `fused`) back through `derive`. Any block that reads
     that key, or a key it depends on, must be `after` the gate. A demo that shows the answer first fails here.
   - Text: each sentence has at most 20 words (a cheap STE check).
3. Headless render check (`rupaka.check`). It writes the static page, and opens it in Chrome with playwright, headless only:
   - It waits for `[data-rk-ready]`. It fails on any console error, any page error, and any request that is not `file:`, `data:` or `about:`.
   - Each block has a non-empty box. Each `after` block is hidden before the gate.
   - It plays the demo: picks an option, locks in, and checks the verdict and the reveals. It sends keys to each control and checks that the state moves.
   - It measures the contrast of each text node against the page in light and dark, and fails under 4.5:1.
   - It takes screenshots (light and dark, 2×) for the record.
4. Repair. On failure, the errors go back to the model with the spec: "Fix only these errors. Return the whole spec."
5. Give up. After two failed repairs, the loop logs the errors and stores nothing. The text lesson still shows.

The check is the same one that learnharness uses for its HTML demos: a page that draws with no errors in a real browser.

### Storage

A demo is one vault document on the `learning` shelf, as concepts, attempts and sessions are (abhyasa `store.py`):

| field | value |
|---|---|
| `kind` | `demo` |
| `source` | `learning://demo/<slug>` |
| `title` | the demo title |
| text | the ask, the gate prompts and the captions, so that hybrid search finds the demo |
| `meta.concept` | the concept slug (the link) |
| `meta.spec` | the spec |
| `meta.schema`, `meta.rupaka` | schema version, and the package version that checked it |
| `meta.by` | `model:<name>` or `hand` |
| `meta.checked` | the time of the last passing check |
| `meta.stats` | how often it was shown, and how often the first prediction was right |

A demo whose first predictions are always right is too easy. A demo that nobody gets right may be wrong. The stats show both.
`Learning.demos(slug)` lists the demos of a concept. Hand-made demos also live in this repo under `rupaka/demos/` as a gallery, and
abhyasa can import them into the shelf.

## The repo

### Layout (my call: an nbdev Python package that ships the JS and CSS)

```
rupaka/
  nbs/                      # the Python source (nbdev 3, hatchling)
    00_spec.ipynb           # builders (demo, slider, wheel, gate, ...), schema from manifests, validate, upgrade
    01_render.ipynb         # bundle, page, show (_repr_html_ and the mime), md (fence or iframe), FT Demo for FastHTML
    02_check.ipynb          # headless check with playwright
    03_agent.ipynb          # prompts, author loop, repair
    index.ipynb
  rupaka/
    spec.py render.py check.py agent.py    # generated
    static/rupaka.js        # the core runtime: store, mount, gate plumbing, boot (hand-written)
    static/rupaka.css       # the --rk-* vars and the host mapping (hand-written)
    blocks/<name>/          # <name>.js, <name>.css, block.json, example.json (hand-written)
    fns/<name>.js           # named fns, with a manifest each
    demos/*.json            # the gallery
  tests/test_blocks.py      # each block's example renders and passes check (pytest + playwright, headless)
  tests/test_gallery.py     # each gallery demo passes validate and check
```

Why one Python package and not a JS package on npm: all three consumers are Python apps, the user's stack has no npm build, and the
validator, the check and the agent are Python anyway. `bundle()` concatenates the core and the blocks in a fixed order. No bundler. Like
abhyasa, the notebooks are the source for Python, and the JS and CSS are plain hand-written files tested with pytest.

The JS is plain scripts, not ES modules, so it runs in a `srcdoc` frame, in a shadow root and in a `file://` page the same way.

### Versioning

- The package uses semver. A new block or fn is a minor version. A change to a block's props is a schema change.
- The spec's `rupaka` field is the schema major. The runtime draws N and N−1. `upgrade` moves stored demos up.
- Each `block.json` has `since`. The prompt catalog lists only blocks that the installed runtime has.
- The release flow is the user's nbdev flow: CHANGELOG, `nbdev-prepare`, push, CI green, `nbdev-release-git`, `nbdev-pypi`. Never `nbdev-release-gh`.

### Consumers

| consumer | how |
|---|---|
| abhyasa | depends on `rupaka`; the `demo` block serves `rupaka/static` at `/rupaka/`; a new engine notebook calls `author` and stores demos |
| leela | route A and B need nothing. Route C vendors `rupaka.js`/`rupaka.css` into `leela/vendor` with a sync script, and adds the fence and mime pass |
| vedicreader | a `vr-rupaka` tool copies the assets into `static/`; pages link them hashed; specs go in as `data-*` JSON |
| notebooks | `from rupaka import show; show(spec)` |

### Tests

- pytest with playwright, on playwright's own Chromium, or `$FASTCDP_CHROME`. Never the everyday Chrome app (changed during the build:
  headless runs of it crashed the user's Chrome). Headless only, so no window takes focus. One browser at a time.
- The suite does not test looks by class names. It tests behaviour (state moves, reveals hide and show, keys work, no errors, no network)
  and contrast numbers. Screenshots go to `tests/screens/` (gitignored) for a person to look at.

## Spike

`/tmp/demo-spike/` is throwaway. It has a 15 KB runtime (`src/rupaka.js`), 6 KB of CSS, eight blocks (`slider`, `wheel`, `ranklist`, `bars`,
`gate`, `readout`, `caption`, `row`), three fns (`rules`, `rrf`, `ids`), two specs, a build script, a leela harness and a headless check.

What it proved:

1. Two demos (vowel sandhi with 18 rule rows; RRF with drag and k) draw from JSON specs alone. No d3, no network, no console errors.
2. The gate works: results are hidden before the prediction, the verdict is right, and the reveals show after ⌘↩.
3. Drag works (a ranklist row moved from 4th to 1st), keys work (the wheel moved with ←), the slider moves the bars, and rows slide.
4. The `rules` fn gives plausible wrong options with no extra work (for a + i: ā, ū, e, ī).
5. The vedicreader look holds in light and dark with abhyasa's palette.
6. Leela route A works: the same document, sent as `text/html` with a script, draws in a copy of leela's `sandboxFrame`.
7. Leela route B works: mdhtml passes the `{=html}` fence, and the `srcdoc` frame draws inside the markdown cell. A plain `<script>`
   in Markdown, and a `<script>` in a `{=html}` fence, do not run.

What it showed as limits (the reasons for route C):

1. The sandboxed frame is 450 px tall, which cuts the sandhi demo above its gate.
2. The frame shows abhyasa's light paper inside leela's dark IDE: it cannot see leela's mode.
3. A `srcdoc` frame cannot load local fonts. The first run failed the check with "Not allowed to load local resource"; the export now
   leaves out `@font-face` for frames.

Bugs the spike found, which the plan covers: a block's CSS class must match its type (`rk-ranklist`); a JSON string inlined in a
`<script>` must escape `</`; a verdict must name the inputs it was for, because the inputs can change after the reveal.

## Decisions for the user

- D1. The name `rupaka`, and a check that the PyPI name is free.
- D2. Leela route C (a ```` ```rupaka ```` fence and a mime, about 30 lines in leela). The abhyasa design said "no change to leela".
- D3. No LLM-written code in a demo: data and named fns only, with `expr` for formulas. The cost: a new kind of demo sometimes needs a person to add a fn.
- D4. When the tutor makes a demo: only after a repeated misconception or for a `visual` concept, in the background (my call), or after every miss.
- D5. Whether a wrong prediction counts in the learner model (as a depth-1 miss), or is only logged.
- D6. vedicreader: copy the assets with a sync tool (my call), or add `rupaka` as a runtime dependency of the server image.
- D7. The leela side finding: sanitize `on*` attributes and `<style>` in `{=html}` fences, or leave it.
