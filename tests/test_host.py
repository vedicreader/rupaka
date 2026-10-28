"The host API: Rupaka.state, Rupaka.set, Rupaka.settle and the save option of Rupaka.mount. A host mirrors one demo into a second copy with them."
import re
from rupaka.render import page

SPEC = dict(id='mir', state=dict(a=2, b=3), derive=[dict(fn='expr', expr='a + b', out='sum')],
            blocks=[dict(type='slider', bind='a', min=0, max=10),
                    dict(type='axis', x=[0, 10], blocks=[dict(type='point', bind='a')]),
                    dict(type='gate', id='s', prompt='What is {a} + {b}?', options=[4, 5, 6], answer='sum'),
                    dict(type='readout', text='{a} + {b} = {sum}', after='s')])

# rk-predict events, with the index of the copy that sent each one
EVENTS = """window.__ev = []; const hs = [...document.querySelectorAll('[data-rupaka]')];
  document.addEventListener('rk-predict', e => __ev.push({copy: hs.indexOf(e.target.closest('[data-rupaka]')), gate: e.detail.gate}))"""

def copies(draw, n=2):
    "A page with `n` copies of SPEC, and an rk-predict recorder."
    d = draw(None, html=page([SPEC] * n, fonts='none'))
    d.pg.wait_for_function(f"document.querySelectorAll('[data-rupaka][data-rk-ready=\"1\"]').length === {n}")
    d.pg.evaluate(EVENTS)
    return d

def st(d, i, k=None):
    s = d.pg.evaluate(f"JSON.parse(JSON.stringify(document.querySelectorAll('[data-rupaka]')[{i}].rupaka.st))")
    return s if k is None else s.get(k)

def js(d, code): return d.pg.evaluate(f"() => {{ const h = [...document.querySelectorAll('[data-rupaka]')]; return {code}; }}")

def host(d, i): return d.pg.locator('[data-rupaka]').nth(i)

def drawn(d, i):
    "The text and the SVG of copy `i`. The clip id is unique on the page, so its number is not compared."
    h = host(d, i)
    return h.locator('.rk').inner_text(), [re.sub(r'rk-clip-\d+', 'rk-clip-N', s) for s in h.locator('svg').evaluate_all('ss => ss.map(s => s.outerHTML)')]

# The mirror: copy 2 follows copy 1

def test_mirror_two_copies(draw):
    d = copies(draw, 3)
    s = host(d, 0).locator('.rk-slider input'); s.fill('3'); s.dispatch_event('input')
    assert st(d, 0, 'a') == 3 and st(d, 1, 'a') == 2
    js(d, 'Rupaka.set(h[1], Rupaka.state(h[0]))')
    assert st(d, 1, 'a') == 3 and st(d, 1, 'sum') == 6
    assert drawn(d, 0) == drawn(d, 1) and 'What is 3 + 3?' in drawn(d, 1)[0]
    g = host(d, 0).locator('.rk-gate'); g.locator('.opts button').first.focus()
    d.pg.keyboard.press('3'); d.pg.keyboard.press('Meta+Enter')     # copy 1: the learner locks in 6
    js(d, "Rupaka.settle(h[1], 's', 6)")
    assert host(d, 1).locator('.verdict').inner_text().startswith('You said 6. That is right.')
    assert host(d, 1).locator('.rk-readout').is_visible() and host(d, 1).locator('.rk-readout').inner_text() == '3 + 3 = 6'
    assert drawn(d, 0) == drawn(d, 1)
    js(d, "Rupaka.settle(h[2], 's', null)")                      # a fresh copy, with no verdict
    assert st(d, 2, 'gate')['s'] == 'done' and not host(d, 2).locator('.verdict').is_visible()
    assert host(d, 2).locator('.rk-readout').is_visible()
    assert d.pg.evaluate('__ev') == [dict(copy=0, gate='s')]
    assert st(d, 1, 'log') in (None, []) and st(d, 2, 'log') in (None, []) and len(st(d, 0, 'log')) == 1
    assert d.errors == []

# Rupaka.state

def test_state_gives_a_copy_of_the_input_keys(draw):
    d = copies(draw, 1)
    assert js(d, 'Rupaka.state(h[0])') == dict(a=2, b=3)                 # no sum, no gate, no log
    js(d, 'Rupaka.state(h[0]).a = 9')
    assert st(d, 0, 'a') == 2 and d.errors == []

# Rupaka.set

def test_set_ignores_other_keys_and_draws_once(draw):
    d = copies(draw, 1)
    js(d, 'window.__n = 0, h[0].rupaka.on(() => __n++)')
    js(d, "Rupaka.set(h[0], {a: 1, b: 4, sum: 99, zz: 1, gate: {s: 'done'}})")
    s = st(d, 0)
    assert (s['a'], s['b'], s['sum'], 'zz' in s, s['gate']) == (1, 4, 5, False, dict(s='open'))
    assert d.pg.evaluate('__n') == 1
    assert 'What is 1 + 4?' in host(d, 0).locator('.rk-gate .q').inner_text()
    assert d.pg.evaluate('__ev') == [] and s.get('log') is None and d.errors == []

# Rupaka.settle

def test_settle_draws_a_wrong_pick(draw):
    d = copies(draw, 1)
    js(d, "Rupaka.settle(h[0], 's', 4)")
    assert host(d, 0).locator('.verdict').inner_text().startswith('You said 4. It is 5.')
    assert host(d, 0).locator('.rk-readout').is_visible() and host(d, 0).locator('button.go').is_hidden()
    assert d.pg.evaluate('__ev') == [] and st(d, 0, 'log') is None and d.errors == []

def test_settle_unknown_gate_does_nothing(draw):
    d = copies(draw, 1)
    before = drawn(d, 0)
    js(d, "window.__n = 0, h[0].rupaka.on(() => __n++), Rupaka.settle(h[0], 'nope', 5)")
    assert st(d, 0, 'gate') == dict(s='open') and drawn(d, 0) == before and d.pg.evaluate('__n') == 0
    assert not host(d, 0).locator('.rk-readout').is_visible() and d.errors == []

def test_settle_null_after_try_another_shows_no_old_verdict(draw):
    spec = {**SPEC, 'blocks': [{**b, 'again': True} if b['type'] == 'gate' else b for b in SPEC['blocks']]}
    d = draw(spec); d.pg.evaluate(EVENTS)
    d.lock(2)
    d.pg.get_by_role('button', name='Try another').click()
    js(d, "Rupaka.settle(h[0], 's', null)")
    assert d.st('gate')['s'] == 'done' and not d.pg.locator('.verdict').is_visible() and d.pg.locator('.rk-readout').is_visible()

# Rupaka.mount(el, spec, {save})

MOUNT = """() => { window.__saves = []; const n = document.createElement('div'); n.id = 'own'; document.body.append(n);
  Rupaka.mount(n, %s, {save: s => __saves.push(s)}); }"""

def test_save_on_each_input_change(draw):
    import json
    d = draw(SPEC)
    d.pg.evaluate(MOUNT % json.dumps(SPEC))
    assert d.pg.evaluate('__saves') == []                                # not on mount
    s = d.pg.locator('#own .rk-slider input'); s.fill('7'); s.dispatch_event('input')   # two input events, one change
    assert d.pg.evaluate('__saves') == [dict(a=7, b=3)]
    s.focus(); d.pg.keyboard.press('d')
    assert d.pg.evaluate('__saves') == [dict(a=7, b=3), dict(a=8, b=3)]
    assert d.pg.evaluate("__saves.at(-1)") == d.pg.evaluate("Rupaka.state(document.getElementById('own'))")
    d.pg.evaluate("Rupaka.settle(document.getElementById('own'), 's', 5); Rupaka.set(document.getElementById('own'), {a: 1})")
    assert len(d.pg.evaluate('__saves')) == 2 and d.errors == []      # a host call is not a change by the learner
