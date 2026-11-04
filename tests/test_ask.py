"Ask about this: the rk-ask event, its payload, and the switches in the spec and in the host page."
from rupaka.render import page

SPEC = dict(id='ask', state=dict(a=2, name='x' * 300, xs=list(range(80)), deep=dict(p=dict(q=dict(r=1)))),
            derive=[dict(fn='expr', expr='a + 1', out='next')],
            blocks=[dict(type='slider', bind='a', min=0, max=10),
                    dict(type='gate', id='g', prompt='What comes after {a}?', options=[2, 3, 4], answer='next'),
                    dict(type='readout', text='{next}', after='g')])

TAKE = "window.__ask = []; document.addEventListener('rk-ask', e => { __ask.push(e.detail); e.preventDefault(); })"

def drawn(draw, spec=SPEC, **kw):
    d = draw(None, html=page(spec, fonts='none', **kw))
    d.pg.wait_for_function("document.querySelector('[data-rupaka]').dataset.rkReady === '1'")
    return d

def ask(d, text):
    d.pg.locator('.rk-askopen').click()
    d.pg.locator('.rk-asker input').fill(text)
    d.pg.locator('.rk-asker button[type=submit]').click()

def test_payload_has_declared_controls_clipped(draw):
    d = drawn(draw); d.pg.evaluate(TAKE)
    s = d.pg.locator('.rk-slider input'); s.fill('4'); s.dispatch_event('input')
    ask(d, '  explain this at a = 4  ')
    ev = d.pg.evaluate('__ask')
    assert ev == [dict(demo='ask', text='explain this at a = 4', step='g',
                       state=dict(a=4, name='x' * 200, xs=list(range(50)), deep=dict(p=dict(q=None))))]
    assert d.pg.locator('.rk-asker .rk-note').inner_text() == 'Sent to the tutor.'
    assert not d.pg.locator('.rk-asker form').is_visible() and d.errors == []

def test_host_call_clips_text_and_step_moves(draw):
    d = drawn(draw); d.pg.evaluate(TAKE)
    d.lock(2)
    took = d.pg.evaluate("!Rupaka.ask(document.querySelector('[data-rupaka]'), 'y'.repeat(600))")
    ev = d.pg.evaluate('__ask')[0]
    assert took and len(ev['text']) == 500 and ev['step'] is None and set(ev['state']) == {'a', 'name', 'xs', 'deep'}

def test_explainer_step_and_no_listener(draw):
    d = drawn(draw, dict(id='ex', mode='learn', state=dict(step=2), blocks=[dict(type='readout', text='Step {step}')]))
    d.pg.evaluate("window.__ask = []; document.addEventListener('rk-ask', e => __ask.push(e.detail))")
    ask(d, '')
    assert d.pg.evaluate('__ask') == [dict(demo='ex', text='', state=dict(step=2), step=2)]
    assert d.pg.locator('.rk-asker .rk-note').inner_text() == 'No tutor is on this page.'

def test_cmd_enter_in_field_asks_not_locks(draw):
    d = drawn(draw); d.pg.evaluate(TAKE)
    d.pg.locator('.rk-gate .opts button').first.click()
    d.pg.locator('.rk-askopen').click()
    d.pg.locator('.rk-asker input').fill('why')
    d.pg.keyboard.press('Meta+Enter')
    assert [e['text'] for e in d.pg.evaluate('__ask')] == ['why'] and d.st('gate')['g'] == 'open'

def test_spec_turns_control_off(draw):
    assert drawn(draw).pg.locator('.rk-asker').count() == 1
    assert drawn(draw, {**SPEC, 'askable': False}).pg.locator('.rk-asker').count() == 0

def test_host_switch_comes_first(draw):
    assert drawn(draw, askable=False).pg.locator('.rk-asker').count() == 0
    assert drawn(draw, {**SPEC, 'askable': False}, askable=True).pg.locator('.rk-asker').count() == 1
    d = drawn(draw, askable=False)
    d.pg.evaluate(TAKE + "; Rupaka.ask(document.querySelector('[data-rupaka]'), 'hi')")
    assert d.pg.evaluate('__ask')[0]['text'] == 'hi'
    n = d.pg.evaluate("""() => { const h = document.createElement('div'); document.body.append(h);
      Rupaka.mount(h, {id: 'm', state: {a: 1}, blocks: [{type: 'readout', text: '{a}'}]}, {askable: false});
      return h.querySelectorAll('.rk-asker').length; }""")
    assert n == 0 and d.errors == []

def test_append_goes_before_the_control(draw):
    d = drawn(draw)
    d.pg.evaluate("Rupaka.append(document.querySelector('[data-rupaka]'), {type: 'readout', text: 'new'})")
    assert d.pg.evaluate("document.querySelector('.rk').lastElementChild.className") == 'rk-asker'
