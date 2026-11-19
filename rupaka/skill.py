"""Make interactive teaching demos with rupaka. A demo is a JSON spec of small blocks: sliders, plots, 3D scenes, flows, and a gate that asks the learner to predict before the result shows. `validate` checks a spec, and `md`, `show`, `page` and `save` put it on a page. Use this skill when you write, check or fix a demo, a `rupaka` fence in a notebook or a Markdown page, or a screen-guide board.

## Make a demo

Build a spec with the Python builders, or write the same JSON by hand.

```python
from rupaka.spec import *
from rupaka.render import md
d = demo('sum', 'Add two numbers', ask='Predict the sum before you see it.', state=dict(a=2, b=3), derive=[expr('a + b', 'sum')],
         blocks=[gate('s', 'What is {a} + {b}?', [4, 5, 6], 'sum', why='Say why, in one line.', context='For a = {a} and b = {b}:'),
                 readout('{a} + {b} = {sum}', after='s'),
                 row(slider('a', 'a', 0, 9, 1, lock='s'), slider('b', 'b', 0, 9, 1, lock='s'))])
assert validate(d) == []
fence = md(d)
```

`validate(spec)` gives a list of errors. Each error is `path: sentence`, and the sentence names the fix. An empty list means that the spec is good. Fix each error and run `validate` again. `plain_errors(spec)` gives each text that is not plain English (ASD-STE100 at US grade 9).

`from rupaka.agent import catalog` and `print(catalog())` give every block and fn with its purpose and props. The catalog is the full list. This sheet is a summary.

## The spec

| key | what it holds |
|---|---|
| `id` | the demo id |
| `title` | the title above the demo |
| `ask` | one lead line under the title |
| `state` | the input keys and their opening values |
| `derive` | a list of fns; each fn computes one derived key, in order |
| `blocks` | the blocks, from top to bottom |
| `tables` | named lists of rows, for `lookup` and `rules` |
| `concept` | the slug of the concept that the demo teaches |
| `mode` | `predict` (the default) or `learn` |
| `askable` | `false` removes the Ask about this control |

A text takes `{key}` for a state value, `{key:2}` for a value rounded to two decimal places, and `{row.name}` for a field of a row. A gate `prompt` and a `caption` also take `**bold**`.

## The think rule

A demo in `predict` mode asks before it shows. `validate` refuses a spec that breaks one of these rules:

- A `predict` demo has at least one `gate`.
- A block that shows a value which a gate's answer depends on waits for that gate. Give the block `after='<gate id>'`, or name the derived keys in the gate's `hides`.
- A gate whose answer a control changes has a `context` that names the inputs, for example `'For {a}:'`.
- A `learn` demo (an explainer) has no gate, and no block in it has `after` or `lock`.

The learner predicts, locks in with Cmd+Return, sees the result, then moves the controls. Give each control that feeds the answer `lock='<gate id>'`. A locked control does not move before the lock in. End the `caption` with a new question that the learner answers with the controls.

## Derived values

`expr(formula, out)` computes one number. A formula has `+ - * / ^`, parentheses, number state keys, `sin cos tan exp log sqrt abs min max floor ceil round`, `pi` and `e`. `sin`, `cos` and `tan` take radians. A formula has no `%`, no comparison and no condition. `validate` refuses each of them.

- Wrap an angle to one circle with `x - 360*floor(x/360)`.
- Pick a case with `rules` (the first row of a table that matches) or `lookup` (a row of a table by key or position).
- `expr('x^2 + b*x', 'curve', over=dict(x=[-5, 5, 101]))` gives a series of points for `plot`.

| fn | gives |
|---|---|
| `lookup` | the row of a table for a key |
| `rules` | the row of a rule table that matches, its `out`, and `alts` as wrong options for a gate |
| `rrf`, `softmax` | reciprocal rank fusion scores; shares from scores at a temperature |
| `fmt` | a string from a template, to compare with a gate option |
| `field`, `sample`, `dft` | a grid of values for `pixels`; the points of a formula in time; a spectrum |
| `ease`, `keyframes` | a number along a curve; the value at a time |
| `ids`, `pick`, `sort` | the ids of rows; one field of each row; a sorted copy |
| `bubble` | one step of a bubble sort: the list, `bars` with the compared pair marked, `comps`, `swaps`, the code `line` and a `mark` per line |

## Blocks

| block | what it does |
|---|---|
| `gate` | asks one question and hides the result until the learner locks in a prediction |
| `readout`, `caption` | one large line from a template; the explanation after the reveal |
| `slider`, `toggle`, `choice` | change a number; turn a thing on or off; pick one case |
| `wheel`, `ranklist` | pick an item on a ring, or point at an angle over equal sectors; drag rows to change an order |
| `axis`, `plot`, `point` | axes with a curve or dots, and a dot that the learner can drag |
| `bars`, `grid`, `pixels` | bars of a list; a heatmap; a grey image of rows of numbers |
| `row`, `stack` | blocks side by side; blocks in one group, one above the other |
| `pair`, `flow` | one row of a worked example; two to five boxes with arrows |
| `layers`, `layer`, `timeline` | a flat picture of layers with parallax; one layer; a bar for the time `t` |
| `scene`, `body`, `force`, `label3d`, `shot` | a 3D view, its parts, its arrows, its labels and its cameras |

A block with `step: n` shows from step `n` of an explainer that has the state key `step`.

A `choice` with `resets`, for example `{"tick": 0}`, sets those state keys back when the pick changes. Use it when a control such as a step bar belongs to the picked case.

## Sound

A `sound` block plays a sample-free `strike` only on a click of Play, or W on that button.
It never plays on mount, state change, gate restore or reveal. Use `after` to wait for a gate.
Opening that gate again stops audio and disables Play. The visible text labels synthesis as an approximation.
Optional `ref: {url, title}` links to a real lesson or recording; it never plays the link.
Use `voice: {kind: "strike", frequency: 138.59, decay: 1.2, gain: 0.6, partials: [{ratio: 1, gain: 1}], noise: 0.08}`.
Frequency is 20–8000 Hz, decay is 0.01–5 seconds, and gains and noise are 0–1.
Use one to eight partials with ratio 0.0025–400 and gain 0–1. Each partial stays at 20–8000 Hz.
Optional `bend` is -1200–1200 cents; the bent frequency must also stay in range.
Voice fields cannot contain URLs, samples or code. `tone` is reserved for later, not supported.
See `examples()['sound']` for the sourced Nam and Tha comparison.

A spec can embed profiles: `profiles: {alias: {id, revision, school, data}}`, with `revision` equal to `profile_hash(data)`.
Check `data` with `profile_errors`. A clean result means good structure and attribution, not true facts.
A sound has `voice` or `play: {profile, technique}`, never both. A `play` technique with no voice shows its facts and sources, and Play stays disabled.
A sound with `play` shows the parts, facts and source links of its technique when the block shows.
A fact with no `school` shows for all schools. A per-school fact shows only for the embed `school`. With no fact for that school, the value shows as unknown.
A gate names a technique that gives its answer away in `hides`: `profiles.<alias>.techniques.<id>`. Then each sound that plays it must wait for that gate.
This is a declared guard, not a detector: a sound that no gate names can play before any gate. The raw spec is in the page, so a hidden block is not a secret.
See `gallery()['mridangam-profile']`.

A profile can hold `media: {id: {kind, src, credit, start, end, alt, sources}}`. `kind` is `audio`, `image` or `video`. `credit` is `{who, license, url}`; the page shows the link and never loads it.
`src` is `asset:<sha256>.<ext>`, a file that the host serves, or `youtube:<11-character id>` for a video with `start` and `end`, at most 120 seconds apart. No other URL is allowed. An image needs `alt`.
A technique lists `media: [{media, school}]`, with the same school rule as facts. A technique voice can be `{kind: "sample", media: <audio id>}`.
The media of a technique shows only while its sound block shows, so a gate that hides the technique also hides its media. A YouTube clip loads only when the learner clicks Load video.
The page loads an asset from `data-rk-media` and the asset name (default `media/`). `save(spec, path, media=folder)` copies the assets to `media/` beside the page.
`rupaka.media` makes assets: `import_asset`, `clip` and `still` (with ffmpeg), and `find_span` for a phrase in a transcript. See `gallery()['mridangam-real']`.

## 3D scenes

```python
s = demo('lift', 'Twice the weight', state=dict(step=1, cam='wide', w=4), derive=[expr('w * 2', 'up')],
         blocks=[gate('g', 'What is twice {w}?', [6, 8], 'up'),
                 scene(body('base', 'box', [2, 1, 2]), force([0, 1, 0], 'up', on='base', at=[0, 1.5, 0], label='lift, {up}', after='g'),
                       shot(bind='cam'), shot('close:base', step=2), bind='step', steps=['A box.', 'Look closer.'])])
assert validate(s) == []
```

- A `scene` holds only `body`, `force`, `label3d` and `shot` blocks. With `bind='step'` and `steps`, it builds one step at a time. A part with `step: n` shows from step `n`.
- The frame has `y` up. `at` is a place in the frame of the parent body. `rot` is a turn in degrees about `x`, `y` and `z`, and each item can be a state key. A positive turn about `y` moves `+x` toward `-z`: counterclockwise, seen from above. `pivot` is the point that `rot` turns about.
- The JSON key `in` (the `inside=` argument of the `body` builder) puts a body in another body. The inner body moves and turns with it. A `group` body has no shape and only holds other bodies.
- `body` kinds and their `size`: `box` `[x, y, z]`, `cylinder` `[radius, height]` or `[top radius, bottom radius, height]`, `cone` and `capsule` `[radius, height]`, `sphere` `[radius]`, `torus` `[radius, tube]`. `color` is one of `body light dark glass acc ok no`.
- `force(dir, mag)` is an arrow. `dir` is a direction in the world, and each item can be a state key. `mag` is a number or a key, and a negative `mag` turns the arrow round. `on` and `at` fix its start. `tone` is one of `up down side acc ok no ink`.
- `label3d` is a chip of at most 60 characters on a body (`on`) or a point (`at`). The scene places the chips so that they do not overlap.
- `shot` names a camera: `wide`, `side`, `front`, `top` or `close:<body id>`. A `choice` and a `shot` with the same `bind` key give the learner a camera picker.
- Compute a direction with trigonometry in `derive`, then put the derived keys in `dir`. Say in the scene `label` when sizes and distances are not to scale.

## Put a demo on a page

| where | how |
|---|---|
| a notebook (Leela, Jupyter) | `show(spec)` gives an output with the HTML page and the `application/vnd.rupaka+json` mime |
| a Markdown cell or page | `md(spec)` gives a `rupaka` fence of readable JSON; `md(spec, frame=True)` gives a frame |
| a FastHTML page | `Demo(spec)` in the page, `Assets('/rupaka')` in the headers, and `bundle('js')`, `bundle('css')` and `bundle('three')` served as `rupaka.js`, `rupaka.css` and `three.js` at that prefix |
| a file | `save(spec, 'demo.html')` writes one page that works from `file://` with no network |

These names are in `rupaka.render`. In Leela, a Markdown cell whose source is the `md(spec)` fence draws the demo. `page(spec)` gives the HTML as a string. `theme='paper'` gives the paper look.

## Check in a browser

`from rupaka.check import check, can_check`. `check(spec)` draws the demo in headless Chromium and plays it. It gives `AttrDict(ok, errors, info, shots)`. It finds errors that `validate` cannot see: a script error, a network request, a gate that shows its answer, a control that keys do not move, and text with low contrast.

`check` needs the `check` extra (`rupaka[check]`) and playwright's Chromium (`python -m playwright install chromium`), or a browser in `$FASTCDP_CHROME`. `can_check()` is True when both are there. `check` never starts the everyday Chrome.

## Ask a model for a demo

`author(concept, ask)` in `rupaka.agent` asks a model for a demo, then validates it, plays it in a headless browser and repairs it. `ask(prompt, sp)` is any function that sends a prompt and a system prompt to a model and gives back text. `author` gives the best spec that passed `validate` and `check`, or None. Its texts can still fail `plain_errors`, so run `plain_errors` on the result.

When you are the model, read `catalog()`, write the spec, and run `validate` and `plain_errors` until both give `[]`. `near(dict(name=..., statement=..., subject=...))` gives the two gallery demos that share the most words with a concept. In `rupaka.spec`, `gallery()` gives every gallery demo by id, and `examples()` gives the example spec of each block.

## Boards and room questions

A board is the screen guide's answer: one spoken line for each step, marks on the page, and a side panel. A model writes it as JSON lines in a closed language (`rupaka.board.OPS`). `clean_context(raw)` keeps the known keys of the page context. `parse_board(text, ctx)` checks each line against that context and drops a bad line. `stream_board(chunks, ctx, on_step)` reads a reply as it comes and gives the whole checked board at the end. When the header's `sure` is `SURE` (0.7) or more, `on_step(step, k)` gets each step when its first mark is in, and again each time its strokes change.

`rupaka.poll.of_gate(spec, gate)` makes a question for a room from a gate, with the index of the answer. `public(question)` removes the answer and the source.

## This sheet in a harness

The `pyskills` entry point `rupaka` names this module. Leela and ramabana list it with the other skills, and `read_skill('rupaka')` reads it. When `pyskills` is installed, this module allows the names in `ALLOW` in a sandbox. `save` and `check` are not in `ALLOW`, because they write a file and start a browser. Call them yourself.

`mv_skill_md(dry_run=False)` writes this sheet as `.agents/skills/rupaka/SKILL.md` and `.claude/skills/rupaka/SKILL.md` in the current git repository, for Claude Code, Codex and other harnesses that read Agent Skills.

Docs: https://vedicreader.github.io/rupaka/skill.html.md"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/07_skill.ipynb.

# %% auto #0
__all__ = ['ALLOW', 'skill_md', 'mv_skill_md']

# %% ../nbs/07_skill.ipynb #77ea22cd
from importlib import import_module
import json
from fastcore.xtras import Path, find_file_parents
from . import agent, board, poll, render, spec
try: from pyskills import allow
except ImportError: allow = None

ALLOW = {spec: ('demo gate readout caption row stack flow pair slider toggle choice wheel ranklist bars axis point plot grid pixels '
                'scene body force label3d shot rules rrf softmax lookup expr sample dft field fmt from_ is_ '
                'validate plain_why plain_errors run shots append upgrade examples gallery manifests fn_manifests').split(),
         render: 'md host page spec_json needs'.split(), agent: 'catalog near demo_sp'.split(),
         board: 'parse_board clean_context'.split(), poll: 'of_gate public'.split()}
if allow: allow(ALLOW)

# %% ../nbs/07_skill.ipynb #5bd3cbbd
def skill_md() -> str:
    "This sheet as an Agent Skills `SKILL.md`: a front matter with `name` and `description`, then the body."
    desc, _, body = import_module('rupaka.skill').__doc__.partition('\n\n')
    return f"---\nname: rupaka\ndescription: {json.dumps(' '.join(desc.split()), ensure_ascii=False)}\n---\n\n{body}\n"

def mv_skill_md(dry_run=True, dir=None):
    "Write `skill_md()` to the `.agents` and `.claude` skill folders of `dir` or of the current git repository; with `dry_run`, print the paths only."
    root = Path(dir or find_file_parents('.git') or '.')
    ts = [root/f'{d}/skills/rupaka/SKILL.md' for d in ('.agents', '.claude')]
    if dry_run: return print(f'Would write: {list(map(str, ts))}')
    for p in ts: p.mk_write(skill_md())
    print(f'Wrote: {list(map(str, ts))}')
