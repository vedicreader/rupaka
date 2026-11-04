"A panel that grows in time with a voice: parts show by step, Rupaka.append adds blocks, and Rupaka.anchor finds a part."
from rupaka.spec import validate

H = "document.querySelector('[data-rupaka]')"

def shown(d, sel='.rk > .rk-b'):
    "The text of each part that shows, in page order."
    return d.pg.locator(sel).evaluate_all("ns => ns.filter(n => n.checkVisibility()).map(n => n.textContent)")

def set_step(d, n): d.pg.evaluate(f"Rupaka.set({H}, {{step: {n}}})")

# step

STEPS = dict(rupaka=1, id='steps', mode='learn', state=dict(step=1),
             blocks=[dict(type='readout', text='one', step=1), dict(type='readout', text='two', step=2),
                     dict(type='stack', step=3, blocks=[dict(type='caption', text='three')]), dict(type='caption', text='always')])

def test_step_reveals_in_order(draw):
    assert validate(STEPS) == []
    d = draw(STEPS)
    assert shown(d) == ['one', 'always']
    set_step(d, 2); assert shown(d) == ['one', 'two', 'always']
    set_step(d, 3); assert shown(d) == ['one', 'two', 'three', 'always']
    set_step(d, 1); assert shown(d) == ['one', 'always']
    assert d.errors == []

def test_step_draws_in(draw):
    d = draw(STEPS); set_step(d, 2)
    assert d.pg.locator('[data-rk-step="2"]').evaluate("n => n.getAnimations().map(a => a.animationName)") == ['rk-draw']

def test_no_step_key_shows_each_part(draw):
    d = draw({**STEPS, 'state': {}})
    assert shown(d) == ['one', 'two', 'three', 'always'] and d.errors == []

def test_step_is_ignored_when_a_demo_predicts(draw):
    "A 0.0.8 spec, or a control with its own step, draws as before."
    d = draw(dict(id='p', state=dict(a=2, step=1), blocks=[dict(type='slider', bind='a', step=2, min=0, max=10), dict(type='readout', text='{a}', step=3)]))
    assert d.pg.locator('.rk-readout').is_visible() and d.pg.locator('.rk-slider input').get_attribute('step') == '2'
    assert d.pg.locator('[data-rk-step]').count() == 0 and d.errors == []

# append

PANEL = dict(rupaka=1, id='panel', mode='learn', state=dict(step=1, a=3), blocks=[dict(type='stack', blocks=[dict(type='readout', text='first')])])

def append(d, block, into=None):
    return d.pg.evaluate("([b, o]) => Rupaka.append(document.querySelector('[data-rupaka]'), b, o)", [block, dict(into=into) if into else None])

def test_append_keeps_earlier_parts(draw):
    d = draw(PANEL)
    first = d.pg.evaluate_handle("document.querySelector('.rk-readout')")
    assert append(d, dict(type='readout', text='a is {a}')) == 'blocks.1'
    assert append(d, dict(type='caption', text='inside'), into='blocks.0') == 'blocks.0.blocks.1'
    assert shown(d, '.rk-readout, .rk-caption') == ['first', 'inside', 'a is 3']
    assert d.pg.evaluate("n => n === document.querySelector('.rk-readout') && n.isConnected", first)   # the same node: no rebuild
    assert [b['type'] for b in d.pg.evaluate(f"{H}.rupaka.spec.blocks")] == ['stack', 'readout'] and d.errors == []

def test_append_follows_step_and_state(draw):
    d = draw(PANEL)
    append(d, dict(type='readout', text='later', step=2))
    assert 'later' not in shown(d)
    set_step(d, 2); d.pg.evaluate(f"Rupaka.set({H}, {{a: 5}})")
    assert shown(d, '.rk > .rk-b') == ['first', 'later']

def test_append_refuses_a_bad_block(draw):
    d = draw(PANEL)
    for b, into, msg in [(dict(type='dial'), None, 'unknown block "dial"'), (dict(type='caption', text='x'), 'blocks.0.blocks.0', 'is not a stack or a row')]:
        err = d.pg.evaluate("([b, o]) => { try { Rupaka.append(document.querySelector('[data-rupaka]'), b, o); } catch (e) { return e.message; } }", [b, dict(into=into)])
        assert msg in err
    assert d.pg.locator('.rk > .rk-b').count() == 1 and len(d.pg.evaluate(f"{H}.rupaka.spec.blocks")) == 1

# pair

from rupaka.spec import examples
PAIR = examples()['pair']

def test_pair_rows_build_by_step(draw):
    d = draw({**PAIR, 'state': dict(step=1)})
    row = lambda i: d.pg.locator('.rk-pair').nth(i)
    assert row(0).locator('.cell').all_inner_texts() == ['[18]'] and row(0).locator('.to').inner_text() == '47'
    assert row(0).locator('.heads').inner_text().split('\n') == ['Input tensor', 'Target: known answer']
    assert not row(1).is_visible()
    set_step(d, 2)
    assert row(1).is_visible() and row(1).locator('.cell').all_inner_texts() == ['[18, 47]'] and row(1).locator('.to').inner_text() == '56'
    assert d.errors == []

def test_pair_parts_come_one_by_one(draw):
    "Each cell, then the arrow, then the answer, starts 80 ms after the one before it."
    d = draw({**PAIR, 'state': dict(step=2)}); set_step(d, 3)
    delays = d.pg.locator('.rk-pair').nth(2).locator('.cell, .arrow, .to').evaluate_all("ns => ns.map(n => getComputedStyle(n).animationDelay)")
    assert delays == ['0s', '0.08s', '0.16s', '0.24s', '0.32s']
    assert d.pg.locator('.rk-pair').nth(2).locator('.n').inner_text() == '3'

def test_pair_reads_the_state(draw):
    d = draw(dict(id='pr', mode='learn', state=dict(x=18), derive=[dict(fn='expr', expr='x + 29', out='y')],
                  blocks=[dict(type='pair', cells=['[{x}]'], to='{y}')]))
    assert d.pg.locator('.rk-pair .to').inner_text() == '47'
    d.pg.evaluate(f"Rupaka.set({H}, {{x: 1}})")
    assert d.pg.locator('.rk-pair .cell').inner_text() == '[1]' and d.pg.locator('.rk-pair .to').inner_text() == '30'

# flow

FLOW = examples()['flow']
BOX = "g => { const r = (g.querySelector('rect') || g).getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height}; }"

def still(d): d.pg.evaluate("Promise.all(document.getAnimations().map(a => a.finished))")

def boxes(d, i):
    "The centre and size of each node box of flow i, after the draw-in."
    still(d)
    return d.pg.locator('.rk-flow').nth(i).locator('.node').evaluate_all(f"gs => gs.map({BOX})")

def test_flow_row_goes_left_to_right(draw):
    d = draw(FLOW)
    bs = boxes(d, 0)
    assert d.pg.locator('.rk-flow').nth(0).locator('.node').all_text_contents() == ['Guess', 'Compare', 'Adjust']
    assert bs[0]['x'] < bs[1]['x'] < bs[2]['x'] and len({round(b['y']) for b in bs}) == 1
    assert d.pg.locator('.rk-flow').nth(0).locator('.edge').count() == 2           # no edges: each node points to the next
    assert d.errors == []

def test_flow_cycle_makes_a_loop(draw):
    "The nodes go round the middle, and the words of an arrow sit outside the loop."
    d = draw(FLOW)
    bs, f = boxes(d, 1), d.pg.locator('.rk-flow').nth(1)
    cx, cy = sum(b['x'] for b in bs) / 4, sum(b['y'] for b in bs) / 4
    assert bs[0]['y'] < cy < bs[2]['y'] and bs[3]['x'] < cx < bs[1]['x']             # top, right, bottom, left
    assert f.locator('.edge').count() == 4 and f.locator('.et').all_text_contents() == ['compare', 'next batch']
    t = f.locator('.et').first.evaluate(f"t => {{ const r = t.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }}")
    assert t[0] > cx and t[1] < cy                                                    # 'compare' is on the top right, outside the arc
    assert 'Guess the next token to Measure the loss' in f.locator('svg').get_attribute('aria-label')

def test_flow_nodes_never_overlap(draw):
    d = draw(FLOW)
    for i in (0, 1):
        bs = boxes(d, i)
        assert not [(a, b) for j, a in enumerate(bs) for b in bs[j + 1:] if abs(a['x'] - b['x']) < (a['w'] + b['w']) / 2 and abs(a['y'] - b['y']) < (a['h'] + b['h']) / 2]

def test_flow_skip_and_back_arrows_curve(draw):
    nodes = [dict(id=c, text=c.upper()) for c in 'abcd']
    d = draw(dict(id='f', mode='learn', blocks=[dict(type='flow', nodes=nodes, edges=[{'from': 'a', 'to': 'b'}, {'from': 'a', 'to': 'c', 'text': 'skip'}, {'from': 'd', 'to': 'a', 'text': 'again'}])]))
    ys = d.pg.locator('.rk-flow .et').evaluate_all("ts => ts.map(t => t.getBoundingClientRect().y)")
    row = boxes(d, 0)[0]['y']
    assert ys[0] < row < ys[1] and d.errors == []                                     # a skip goes over the row, a step back under it

# anchor

def anchor(d, path): return d.pg.evaluate(f"p => {{ const e = Rupaka.anchor({H}, p); return e && [e.dataset.rkId, e.textContent]; }}", path)

def test_anchor_returns_the_right_element(draw):
    d = draw(PAIR)
    assert anchor(d, 'blocks.1') == ['blocks.1', '[18, 47]56']
    assert anchor(d, 'blocks.1.cells.0') == ['blocks.1.cells.0', '[18, 47]']
    assert anchor(d, 'blocks.2.cells.2') == ['blocks.2.cells.2', 'is'] and anchor(d, 'blocks.0.to') == ['blocks.0.to', '47']
    assert anchor(d, 'blocks.9') is None and anchor(d, 'blocks.0"]') is None

def test_anchor_finds_flow_nodes_and_appended_parts(draw):
    d = draw(PANEL)
    p = append(d, FLOW['blocks'][1])
    assert anchor(d, f'{p}.nodes.2') == [f'{p}.nodes.2', 'Find thegradient']   # two lines of text
    assert anchor(d, f'{p}.edges.3') == [f'{p}.edges.3', 'next batch']
    assert anchor(d, 'blocks.0.blocks.0') == ['blocks.0.blocks.0', 'first']

def test_anchor_ids_are_stable(draw):
    "A step change or a new state keeps the same element at each id, so a curve stays on its part."
    d = draw({**PAIR, 'state': dict(step=1)})
    d.pg.evaluate(f"window.__a = Rupaka.anchor({H}, 'blocks.0.cells.0')")
    set_step(d, 3); append(d, dict(type='pair', cells=['x'], to='y'))
    assert d.pg.evaluate(f"Rupaka.anchor({H}, 'blocks.0.cells.0') === __a") and anchor(d, 'blocks.3.to') == ['blocks.3.to', 'y']
    assert d.pg.evaluate(f"(() => {{ try {{ Rupaka.anchor(document.body, 'blocks.0'); }} catch (e) {{ return e.message; }} }})()") == 'no rupaka demo is mounted in this element'

# the paper theme

from rupaka.render import page
from rupaka.check import contrast
from rupaka.spec import gallery

def paper(draw, spec, **kw): return draw(spec, html=page(spec, fonts='embed', theme='paper'), **kw)

def test_paper_theme_has_the_hand_font_and_sketch_lines(draw):
    d = paper(draw, FLOW)
    d.pg.evaluate("document.fonts.ready")
    assert d.pg.evaluate("getComputedStyle(document.querySelector('.rk-title')).fontFamily").startswith('"Patrick Hand"')
    assert d.pg.evaluate("document.fonts.check('16px \"Patrick Hand\"')")
    assert d.pg.locator('.rk-flow .edge .sk').first.evaluate("n => getComputedStyle(n).display") != 'none'
    assert d.errors == []

def test_page_themes_keep_their_look(draw):
    "With no theme, light and dark stay as they were: the page font, and no sketch lines."
    for mode in ('light', 'dark'):
        d = draw(FLOW, mode=mode)
        assert 'Patrick Hand' not in d.pg.evaluate("getComputedStyle(document.querySelector('.rk-title')).fontFamily")
        assert d.pg.locator('.rk-flow .edge .sk').first.evaluate("n => getComputedStyle(n).display") == 'none'

def test_paper_theme_passes_contrast(draw):
    for spec in (PAIR, FLOW, *gallery().values()):
        for mode in ('light', 'dark'):           # paper is always light, also on a dark page
            d = paper(draw, spec, mode=mode); still(d)
            assert contrast(d.pg) == [], (spec['id'], mode)

ORDER = dict(id='order', mode='learn', blocks=[dict(type='flow', label='The right order', nodes=[dict(id=f'n{i}', text=t) for i, t in enumerate(
    ['1. Find the sunrise', '2. Note limbs at sunrise', '3. Name the day', '4. Pick the limb at your time', '5. Check the answer'], 1)])])
FITS = """() => { const f = document.querySelector('.rk-flow').getBoundingClientRect(), r = e => e.getBoundingClientRect();
  const ns = [...document.querySelectorAll('.rk-flow .node')], es = [...document.querySelectorAll('.rk-flow .edge')], bad = [];
  const meet = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  const inside = (a, b) => a.left >= b.left - .5 && a.right <= b.right + .5 && a.top >= b.top - .5 && a.bottom <= b.bottom + .5;
  ns.forEach((n, i) => { const t = document.createRange(); t.selectNodeContents(n);
    if (!inside(t.getBoundingClientRect(), r(n)) || n.scrollWidth > n.clientWidth) bad.push(`node ${i} text is outside its box`); });
  es.forEach((e, j) => ns.forEach((n, i) => { if (meet(r(e), r(n))) bad.push(`edge ${j} is on node ${i}`); }));
  [...ns, ...es].forEach((e, i) => { if (!inside(r(e), f) || r(e).right > innerWidth) bad.push(`part ${i} is outside the flow`); });
  return bad; }"""

def order_at(draw, w, spec=ORDER):
    "ORDER in a column `w` px wide, after the draw-in."
    html = page(spec, fonts='none').replace('</style>', f'main.rk-page {{ max-width: none; width: {w}px; margin: 0; padding: 16px; }}</style>')
    d = draw(None, html=html); d.pg.set_viewport_size(dict(width=w + 32, height=900)); still(d)
    return d

def test_flow_order_row_fits_each_width(draw):
    "The boxes hold their words, the arrows sit between the boxes, and no part goes out: a slide column, a walk step, a full slide."
    for w in (420, 540, 700, 1280):
        d = order_at(draw, w)
        assert d.pg.evaluate(FITS) == [], w
        assert d.pg.locator('.rk-flow .node').count() == 5 and d.pg.locator('.rk-flow .edge').count() == 4 and d.errors == []
