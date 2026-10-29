"The host API: Rupaka.state, Rupaka.set, Rupaka.options, Rupaka.settle, Rupaka.open and the save option of Rupaka.mount. A host mirrors one demo into a second copy with them."
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

# Rupaka.options

OPTS = dict(id='opt', state=dict(raw=[3, 1, 2]), derive=[dict(fn='sort', **{'from': 'raw'}, out='ranked')],
            blocks=[dict(type='gate', id='lit', prompt='?', options=[-1.5, 2, 'x', True], answer={'is': 2}),
                    dict(type='gate', id='st', prompt='?', options={'from': 'raw'}, answer={'is': 1}),
                    dict(type='gate', id='dv', prompt='?', options={'from': 'ranked'}, answer='ranked.0')])

def test_options_gives_raw_values_in_the_order_shown(draw):
    d = draw(OPTS)
    assert js(d, "Rupaka.options(h[0], 'lit')") == [-1.5, 2, 'x', True]           # raw values, not the text −1.5 or true
    assert js(d, "Rupaka.options(h[0], 'st')") == [3, 1, 2]                       # from the state
    assert js(d, "Rupaka.options(h[0], 'dv')") == [1, 2, 3]                       # from a derived value
    shown = lambda g: d.pg.locator('.rk-gate').nth(g).locator('.opts button').evaluate_all('bs => bs.map(b => b.firstChild.textContent)')
    assert shown(1) == ['3', '1', '2'] and shown(2) == ['1', '2', '3']
    js(d, 'Rupaka.set(h[0], {raw: [9, 7]})')                                        # after derive
    assert js(d, "Rupaka.options(h[0], 'st')") == [9, 7] and js(d, "Rupaka.options(h[0], 'dv')") == [7, 9]
    js(d, "Rupaka.options(h[0], 'st').push(1)")                                     # a copy
    assert js(d, "Rupaka.options(h[0], 'st')") == [9, 7] and d.errors == []

def test_options_unknown_gate_is_null(draw):
    d = draw(OPTS)
    assert js(d, "Rupaka.options(h[0], 'nope')") is None and d.errors == []

def test_options_with_no_demo_throws_as_state_does(draw):
    d = draw(OPTS)
    f = "(f => { try { f(document.createElement('div')); return null; } catch (e) { return e.message; } })"
    want = d.pg.evaluate(f + '(n => Rupaka.state(n))')
    assert want and d.pg.evaluate(f + "(n => Rupaka.options(n, 'lit'))") == want

# Rupaka.settle(el, gate, pick, {answer}): an audience copy with no answers in its spec

def stripped(spec):
    "`spec` with no gate answers, as a host mounts it for a room."
    return {**spec, 'id': spec['id'] + '-room', 'blocks': [{k: v for k, v in b.items() if k != 'answer'} for b in spec['blocks']]}

def room(draw):
    "Copy 0 is the presenter's (with answers). Copies 1 to 3 are the room's (with no answers)."
    d = draw(None, html=page([SPEC] + [stripped(SPEC)] * 3, fonts='none'))
    d.pg.wait_for_function("document.querySelectorAll('[data-rupaka][data-rk-ready=\"1\"]').length === 4")
    d.pg.evaluate(EVENTS)
    return d

def test_settle_with_answer_on_a_stripped_copy(draw):
    d = room(draw)
    assert 'answer' not in js(d, 'h[1].rupaka.spec.blocks[2]')
    js(d, "Rupaka.settle(h[0], 's', 4)")
    js(d, "Rupaka.settle(h[1], 's', 4, {answer: 'sum'})")                         # a state path
    js(d, "Rupaka.settle(h[2], 's', 4, {answer: {is: 5}})")                       # a literal
    want = host(d, 0).locator('.verdict').inner_text()
    assert want.startswith('You said 4. It is 5.')
    assert host(d, 1).locator('.verdict').inner_text() == want == host(d, 2).locator('.verdict').inner_text()
    assert drawn(d, 1) == drawn(d, 0) and drawn(d, 2) == drawn(d, 0)
    js(d, "Rupaka.settle(h[3], 's', 5, {answer: {is: 5}})")
    assert host(d, 3).locator('.verdict').inner_text().startswith('You said 5. That is right.')
    for i in (1, 2, 3):                                                            # the answer is only drawn
        assert 'answer' not in js(d, f'h[{i}].rupaka.spec.blocks[2]')
        assert set(st(d, i)) == {'a', 'b', 'sum', 'gate'} and st(d, i, 'gate') == dict(s='done')
    assert d.pg.evaluate('__ev') == [] and d.errors == []

def test_settle_on_a_stripped_copy_with_no_answer_shows_no_verdict(draw):
    d = room(draw)
    assert js(d, "Rupaka.settle(h[1], 's', 4)") is True
    assert st(d, 1, 'gate') == dict(s='done') and not host(d, 1).locator('.verdict').is_visible()
    assert host(d, 1).locator('.verdict').inner_text() == '' and host(d, 1).locator('.rk-readout').is_visible()
    assert d.pg.evaluate('__ev') == [] and st(d, 1, 'log') is None and d.errors == []

def test_settle_answer_does_not_override_the_spec(draw):
    d = copies(draw, 1)
    js(d, "Rupaka.settle(h[0], 's', 4, {answer: {is: 4}})")
    assert host(d, 0).locator('.verdict').inner_text().startswith('You said 4. It is 5.')
    assert js(d, 'h[0].rupaka.spec.blocks[2].answer') == 'sum' and d.errors == []

def test_settle_unknown_gate_with_answer_is_false(draw):
    d = room(draw)
    assert js(d, "Rupaka.settle(h[1], 'nope', 4, {answer: {is: 5}})") is False
    assert st(d, 1, 'gate') == dict(s='open') and d.errors == []

# Rupaka.open(el, gate): open a closed gate again, as Try another does

AGAIN = {**SPEC, 'id': 'again', 'blocks': [{**b, 'again': True, 'why': 'Why?'} if b['type'] == 'gate' else b for b in SPEC['blocks']]}

def pair(draw, spec=AGAIN, n=1):
    "A page with `n` copies of `spec`, an rk-predict recorder and a draw counter `__n[i]` for each copy."
    d = draw(None, html=page([spec] * n, fonts='none'))
    d.pg.wait_for_function(f"document.querySelectorAll('[data-rupaka][data-rk-ready=\"1\"]').length === {n}")
    d.pg.evaluate(EVENTS)
    js(d, 'window.__n = h.map(() => 0), h.forEach((x, i) => x.rupaka.on(() => __n[i]++))')
    return d

ACTIVE = "document.activeElement === document.querySelector('.rk-slider input')"

def test_open_opens_a_settled_gate(draw):
    d = pair(draw)
    h = host(d, 0)
    h.locator('.rk-gate textarea').fill('a guess')
    js(d, "Rupaka.settle(h[0], 's', 4)")
    assert st(d, 0, 'gate') == dict(s='done') and h.locator('.verdict').is_visible() and h.locator('.rk-readout').is_visible()
    h.locator('.rk-slider input').focus()
    js(d, '__n[0] = 0')
    assert js(d, "Rupaka.open(h[0], 's')") is True
    assert st(d, 0, 'gate') == dict(s='open') and d.pg.evaluate('__n[0]') == 1            # one draw
    assert not h.locator('.verdict').is_visible() and h.locator('.verdict').inner_text() == ''
    assert not h.locator('.rk-readout').is_visible() and h.locator('.rk-gate textarea').input_value() == ''
    bs = h.locator('.rk-gate .opts button')
    assert bs.evaluate_all('bs => bs.map(b => [b.disabled, b.getAttribute("aria-checked")])') == [[False, 'false']] * 3
    assert h.locator('button.go').is_visible() and h.locator('button.go').is_disabled()
    assert d.pg.evaluate(ACTIVE)                                                         # focus did not move
    bs.nth(1).click()                                                                    # the options can be picked again
    assert bs.nth(1).get_attribute('aria-checked') == 'true' and h.locator('button.go').is_enabled()
    assert d.pg.evaluate('__ev') == [] and st(d, 0, 'log') is None and d.errors == []

def test_open_on_an_open_gate_changes_nothing(draw):
    d = pair(draw)
    h = host(d, 0)
    h.locator('.rk-gate .opts button').nth(2).click()
    h.locator('.rk-slider input').focus()
    before, n = drawn(d, 0), d.pg.evaluate('__n[0]')
    assert js(d, "Rupaka.open(h[0], 's')") is True
    assert st(d, 0, 'gate') == dict(s='open') and drawn(d, 0) == before and d.pg.evaluate('__n[0]') == n
    assert h.locator('.rk-gate .opts button').nth(2).get_attribute('aria-checked') == 'true' and d.pg.evaluate(ACTIVE)
    assert d.pg.evaluate('__ev') == [] and d.errors == []

def test_open_unknown_gate_is_false(draw):
    d = pair(draw)
    js(d, "Rupaka.settle(h[0], 's', 5)")
    before, n = drawn(d, 0), d.pg.evaluate('__n[0]')
    assert js(d, "Rupaka.open(h[0], 'nope')") is False
    assert st(d, 0, 'gate') == dict(s='done') and drawn(d, 0) == before and d.pg.evaluate('__n[0]') == n and d.errors == []

def test_open_on_a_gate_that_waits_for_the_host_is_false(draw):
    d = pair(draw)
    h = host(d, 0)
    d.pg.evaluate("document.addEventListener('rk-predict', e => e.preventDefault())")   # the host saves first, so the gate waits
    h.locator('.rk-gate .opts button').nth(1).click(); h.locator('button.go').click()
    assert st(d, 0, 'gate') == dict(s='pending')
    assert js(d, "Rupaka.open(h[0], 's')") is False                                    # it did not open, so the host must not think it did
    assert st(d, 0, 'gate') == dict(s='pending') and d.errors == []

def test_open_with_no_demo_throws_as_state_does(draw):
    d = pair(draw)
    f = "(f => { try { f(document.createElement('div')); return null; } catch (e) { return e.message; } })"
    want = d.pg.evaluate(f + '(n => Rupaka.state(n))')
    assert want and d.pg.evaluate(f + "(n => Rupaka.open(n, 's'))") == want

def test_open_round_trip_on_two_copies(draw):
    d = pair(draw, n=2)
    p, a = host(d, 0), host(d, 1)
    d.lock(3)                                                                            # the presenter commits 6
    i = js(d, "Rupaka.options(h[0], 's').indexOf(h[0].rupaka.st.log[0].picked)")     # the host sends the index of the pick
    js(d, f"Rupaka.settle(h[1], 's', Rupaka.options(h[1], 's')[{i}])")
    assert drawn(d, 0) == drawn(d, 1) and a.locator('.verdict').is_visible()
    p.get_by_role('button', name='Try another').click()
    assert d.pg.evaluate("document.activeElement === document.querySelector('.rk-gate .opts button')")   # the button moves focus
    js(d, "Rupaka.open(h[1], 's')")
    assert st(d, 0, 'gate') == st(d, 1, 'gate') == dict(s='open')
    assert js(d, 'Rupaka.state(h[0])') == js(d, 'Rupaka.state(h[1])') and drawn(d, 0) == drawn(d, 1)
    for h in (p, a):
        assert not h.locator('.verdict').is_visible() and not h.locator('.rk-readout').is_visible() and h.locator('button.go').is_visible()
        assert h.locator('.rk-gate .opts button').evaluate_all('bs => bs.map(b => [b.disabled, b.getAttribute("aria-checked")])') == [[False, 'false']] * 3
    assert d.pg.evaluate('__ev') == [dict(copy=0, gate='s')] and st(d, 1, 'log') is None and len(st(d, 0, 'log')) == 1
    assert d.errors == []

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
    d.pg.evaluate("Rupaka.settle(document.getElementById('own'), 's', 5); Rupaka.open(document.getElementById('own'), 's'); Rupaka.set(document.getElementById('own'), {a: 1})")
    assert len(d.pg.evaluate('__saves')) == 2 and d.errors == []      # a host call is not a change by the learner
