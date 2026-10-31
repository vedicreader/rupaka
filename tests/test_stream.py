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
