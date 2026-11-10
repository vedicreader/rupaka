"Each block: its example passes the whole check, and its own behaviour works with keys and the pointer."
import json
import pytest
from rupaka.spec import examples, manifests, validate, run
from rupaka.check import check

EX = examples()

def test_each_block_folder_is_complete():
    assert set(EX) == set(manifests())

@pytest.mark.parametrize('name', sorted(EX))
def test_example_passes_check(br, name):
    assert validate(EX[name]) == []
    assert check(EX[name], b=br).errors == []

# gate

def test_gate_hides_then_reveals(draw):
    d = draw(EX['gate'])
    assert not d.pg.locator('.rk-readout').is_visible()
    assert d.pg.locator('button.go').is_disabled()
    d.pg.evaluate("window.__ev = []; document.addEventListener('rk-predict', e => __ev.push(e.detail))")
    d.pg.locator('.rk-gate textarea').fill('Two and three make five.')
    d.lock(1)                                            # 4 is wrong
    assert d.pg.locator('.verdict').inner_text().startswith('You said 4. It is 5.')
    assert d.pg.locator('.rk-readout').is_visible()
    ev = d.pg.evaluate('__ev[0]')
    assert {k: ev[k] for k in ('gate', 'picked', 'ans', 'ok', 'why')} == dict(gate='sum', picked=4, ans=5, ok=False, why='Two and three make five.')
    assert d.pg.locator('.opts button').first.is_disabled() and d.errors == []

def test_gate_again_names_its_inputs(draw):
    d = draw(EX['wheel'])
    d.lock(1)
    assert d.pg.locator('.verdict').inner_text().startswith('For Mon:')
    d.pg.locator('.rk-wheel svg').focus(); d.pg.keyboard.press('ArrowRight')
    assert 'The demo now shows other inputs.' in d.pg.locator('.verdict').inner_text()
    d.pg.get_by_role('button', name='Try another').click()
    assert not d.pg.locator('.rk-readout').is_visible() and not d.pg.locator('.verdict').is_visible()

# gate: a host that saves the prediction cancels rk-predict and calls detail.settle

HOLD = "window.__ev = []; document.addEventListener('rk-predict', e => { __ev.push(e.detail); if (window.__hold) e.preventDefault(); })"

def test_gate_no_listener_is_done_at_once(draw):
    d = draw(EX['gate'])
    d.pg.evaluate("window.__c = []; document.addEventListener('rk-predict', e => __c.push([e.cancelable, typeof e.detail.settle]))")
    d.lock(2)
    assert d.st('gate')['sum'] == 'done' and d.pg.locator('.verdict').is_visible() and d.pg.locator('.rk-readout').is_visible()
    assert d.pg.evaluate('__c') == [[True, 'function']] and not d.pg.locator('.rk-gate .note').is_visible() and d.errors == []

def test_gate_waits_then_settles_true(draw):
    d = draw(EX['gate'])
    d.pg.evaluate('window.__hold = true; ' + HOLD)
    d.lock(2)
    assert d.st('gate')['sum'] == 'pending' and d.pg.locator('button.go').is_disabled()
    assert not d.pg.locator('.verdict').is_visible() and not d.pg.locator('.rk-readout').is_visible()
    assert d.pg.locator('.rk-gate .note').inner_text() == 'Saving your prediction.'
    d.pg.evaluate('__ev[0].settle(true)')
    assert d.st('gate')['sum'] == 'done' and d.pg.locator('.verdict').inner_text().startswith('You said 5.')
    assert d.pg.locator('.rk-readout').is_visible() and not d.pg.locator('.rk-gate .note').is_visible() and d.errors == []

def test_gate_settle_false_lets_the_learner_lock_in_again(draw):
    d = draw(EX['gate'])
    d.pg.evaluate('window.__hold = true; ' + HOLD)
    d.pg.locator('.rk-gate textarea').fill('Two and three make five.')
    d.lock(2)
    d.pg.evaluate("__ev[0].settle(false, '<b>The store is locked.</b>')")
    note = d.pg.locator('.rk-gate .note')
    assert note.inner_text() == '<b>The store is locked.</b>' and note.locator('b').count() == 0
    assert d.st('gate')['sum'] == 'open' and d.pg.locator('button.go').is_enabled() and not d.pg.locator('.rk-readout').is_visible()
    assert d.pg.locator('.opts button').nth(1).get_attribute('aria-checked') == 'true'
    assert d.pg.locator('.rk-gate textarea').input_value() == 'Two and three make five.'
    d.pg.evaluate('window.__hold = false'); d.pg.locator('button.go').click()
    assert d.pg.evaluate('__ev.length') == 2 and d.pg.evaluate('__ev[1].why') == 'Two and three make five.'
    assert d.st('gate')['sum'] == 'done' and d.pg.locator('.rk-readout').is_visible() and d.errors == []

def test_gate_settle_twice_does_nothing(draw):
    d = draw(EX['gate'])
    d.pg.evaluate('window.__hold = true; ' + HOLD)
    d.lock(2)
    d.pg.evaluate("__ev[0].settle(true); __ev[0].settle(false, 'Too late.')")
    assert d.st('gate')['sum'] == 'done' and d.pg.locator('button.go').is_hidden() and not d.pg.locator('.rk-gate .note').is_visible()
    assert len(d.st('log')) == 1 and d.errors == []

# readout, caption

def test_caption_escapes_html(draw):
    spec = dict(id='c', state=dict(x='<img src=x onerror=alert(1)>'), blocks=[dict(type='caption', text='**Bold** {x} <b>raw</b>')])
    d = draw(spec)
    c = d.pg.locator('.rk-caption')
    assert c.locator('img').count() == 0 and c.locator('strong').count() == 1
    assert c.inner_text() == 'Bold <img src=x onerror=alert(1)> <b>raw</b>'

def test_bold_in_each_rich_text(draw):
    "The ask, a caption, a gate prompt and a gate context show **bold** as a strong element, with {path} and $maths$ kept."
    spec = dict(id='r', ask='You ask a shop for something **sweet**. Look at $x^2$.', state=dict(n=2),
                blocks=[dict(type='gate', id='g', prompt='Is **{n}** even?', options=['yes', 'no'], answer={'is': 'yes'},
                             context='For **n = {n}** and $a**b$:'),
                        dict(type='caption', after='g', text='So **{n}** is even, and $x^2$ stays. A lone ** stays too.')])
    d = draw(spec)
    strong = lambda css: d.pg.locator(f'{css} strong').all_inner_texts()
    assert strong('.rk-ask') == ['sweet'] and d.pg.locator('.rk-ask').inner_text() == 'You ask a shop for something sweet. Look at $x^2$.'
    assert strong('.rk-gate .q') == ['2'] and d.pg.locator('.rk-gate .q').inner_text() == 'Is 2 even?'
    d.lock(1)
    assert strong('.rk-gate .verdict') == ['n = 2'] and d.pg.locator('.rk-gate .verdict').inner_text().startswith('For n = 2 and $a**b$: You said')
    assert strong('.rk-caption') == ['2'] and d.pg.locator('.rk-caption').inner_text() == 'So 2 is even, and $x^2$ stays. A lone ** stays too.'
    assert '**' not in d.pg.locator('.rk-ask').inner_text() and d.errors == []

# slider, toggle, choice

def test_slider_keys(draw):
    d = draw(EX['slider'])
    s = d.pg.locator('.rk-slider input')
    assert s.is_disabled()                               # locked until the gate
    d.lock(2)
    s.focus(); d.pg.keyboard.press('ArrowRight'); d.pg.keyboard.press('d')
    assert d.st('n') == 5 and s.get_attribute('aria-valuetext') == 'n 5'
    d.pg.keyboard.press('Shift+a')
    assert d.st('n') == 0

def test_toggle_space(draw):
    d = draw(EX['toggle']); d.lock(2)
    b = d.pg.locator('.rk-toggle button')
    b.focus(); d.pg.keyboard.press('Space')
    assert d.st('neg') is True and b.get_attribute('aria-checked') == 'true' and d.st('y') == -4

def test_choice_keys(draw):
    d = draw(EX['choice'])
    d.pg.locator('.rk-choice button[aria-checked=true]').focus()
    d.pg.keyboard.press('ArrowRight'); assert d.st('shape') == 'hexagon'
    d.pg.keyboard.press('1'); assert d.st('shape') == 'triangle'
    d.pg.keyboard.press('a'); assert d.st('shape') == 'triangle'   # no move past the first

# wheel

def test_wheel_keys(draw):
    spec = json.loads(json.dumps(EX['wheel'])); spec['state']['day'] = 'Wed'
    d = draw(spec)
    d.pg.locator('.rk-wheel svg').focus()
    d.pg.keyboard.press('ArrowLeft'); d.pg.keyboard.press('a')
    assert d.st('day') == 'Mon'
    d.pg.keyboard.press('End'); assert d.st('day') == 'Sun'
    d.pg.keyboard.press('Home'); assert d.st('day') == 'Mon'

def test_wheel_drag_to_90_degrees(draw):
    spec = dict(id='w', state=dict(v='a'), blocks=[dict(type='wheel', bind='v', items=list('abcdefgh'))])
    d = draw(spec)
    bx = d.pg.locator('.rk-wheel svg').bounding_box()
    cx, cy = bx['x'] + bx['width'] / 2, bx['y'] + bx['height'] / 2
    d.pg.mouse.move(cx, cy - bx['height'] * .38); d.pg.mouse.down()
    d.pg.mouse.move(cx + bx['width'] * .38, cy, steps=6); d.pg.mouse.up()
    assert d.st('v') == 'c'                              # 90° of 8 items is the third item

def test_wheel_angle_mode_hides_the_sector_while_locked(draw):
    from rupaka.spec import gallery
    d = draw(gallery()['nakshatra-pada'])
    assert d.pg.locator('.rk-wheel text.tick.on').count() == 0
    assert 'Rohiṇī' not in d.pg.locator('.rk-wheel svg').get_attribute('aria-valuetext')
    d.lock(3)
    assert d.pg.locator('.rk-wheel text.tick.on').text_content() == 'Rohiṇī'
    d.pg.locator('.rk-wheel svg').focus(); d.pg.keyboard.press('Shift+ArrowLeft')
    assert d.st('lon') == 37 and d.st('where') == 'Kṛttikā, pāda 4'

# ranklist

def drag_row(d, list_i, id, rows):
    row = d.pg.locator('.rk-ranklist').nth(list_i).locator(f'g.row[data-id="{id}"]')
    row.scroll_into_view_if_needed(); d.pg.wait_for_timeout(50)   # the reveal can move the list; measure it where it is now
    bx = row.bounding_box()
    d.pg.mouse.move(bx['x'] + 20, bx['y'] + bx['height'] / 2); d.pg.mouse.down()
    d.pg.mouse.move(bx['x'] + 20, bx['y'] + bx['height'] / 2 + rows * bx['height'], steps=8); d.pg.mouse.up()

def test_ranklist_refuses_while_locked_then_drags(draw):
    d = draw(EX['ranklist'])
    drag_row(d, 0, 'B', -3)
    assert d.st('order') == list('ACEB')
    d.lock(1)
    d.pg.locator('.rk-ranklist.live').first.wait_for()   # the list opens after the lock in; a slow machine needs the wait
    d.pg.evaluate('''() => { window.rkLog = []; const svg = document.querySelector('.rk-ranklist svg');
      for (const t of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'lostpointercapture'])
        svg.addEventListener(t, e => rkLog.push([t, e.target.getAttribute('class') || e.target.tagName, Math.round(e.clientY), e.pointerType])); }''')
    drag_row(d, 0, 'B', -3)
    log = d.pg.evaluate('() => rkLog.slice(0, 6).concat(rkLog.slice(-3))')
    box = d.pg.evaluate("() => JSON.stringify(document.querySelector('.rk-ranklist svg').getBoundingClientRect())")
    assert d.st('order') == list('BACE'), f'events {log}; svg box {box}'
    assert not any(e[0] == 'pointercancel' for e in log), log   # the browser must not take the pointer away
    d.pg.locator('g.row[data-id="B"]').focus(); d.pg.keyboard.press('s')
    assert d.st('order') == list('ABCE')

# bars

def test_bars_follow_the_values(draw):
    from rupaka.spec import gallery
    d = draw(gallery()['reciprocal-rank-fusion']); d.lock(2)
    order = lambda: d.pg.locator('.rk-bars g.bar').evaluate_all(
        "gs => gs.filter(g => g.style.display !== 'none').sort((a, b) => new DOMMatrix(getComputedStyle(a).transform).f - new DOMMatrix(getComputedStyle(b).transform).f).map(g => g.querySelector('text.t').textContent).join('')")
    d.pg.wait_for_timeout(400)
    assert order()[0] == 'B'
    s = d.pg.locator('.rk-slider input'); s.fill('1'); s.dispatch_event('input')
    d.pg.wait_for_timeout(400)
    assert order()[:2] == 'AD'

def test_bars_drop_rows_that_leave(draw):
    spec = dict(id='b', state=dict(xs=[dict(id='p', value=1), dict(id='q', value=2)], n=2), derive=[], blocks=[dict(type='bars', bind='xs')])
    d = draw(spec)
    d.pg.evaluate("document.querySelector('[data-rupaka]').rupaka.set('xs', [{id: 'q', value: 3}])")
    assert d.pg.locator('.rk-bars g.bar:visible').count() == 1

# axis, point, plot

def test_point_drag_and_keys(draw):
    spec = dict(id='p', state=dict(x=0), blocks=[dict(type='axis', x=[-4, 4], blocks=[dict(type='point', bind='x', step=0.5)]),
                                               dict(type='gate', id='g', prompt='x?', options=[0, 1], answer='x')])
    d = draw(spec)
    svg = d.pg.locator('.rk-axis svg'); bx = svg.bounding_box()
    px = lambda v: bx['x'] + (40 + (v + 4) / 8 * (600 - 40 - 16)) / 600 * bx['width']
    dot = d.pg.locator('.rk-point .dot').bounding_box()
    d.pg.mouse.move(dot['x'] + dot['width'] / 2, dot['y'] + dot['height'] / 2); d.pg.mouse.down()
    d.pg.mouse.move(px(2.1), dot['y'] + dot['height'] / 2, steps=6); d.pg.mouse.up()
    assert d.st('x') == 2
    d.pg.locator('.rk-point').focus(); d.pg.keyboard.press('ArrowRight'); assert d.st('x') == 2.5
    d.pg.keyboard.press('Shift+ArrowLeft'); assert d.st('x') == -2.5
    d.pg.keyboard.press('w'); assert d.st('x') == -2   # on a number line, up moves it too

def test_plot_draws_the_series(draw):
    d = draw(EX['plot'])
    path = d.pg.locator('.rk-plot path.ln').get_attribute('d')
    assert path.startswith('M') and path.count('L') == 8

# grid

def test_grid_plus_minus(draw):
    d = draw(EX['grid']); d.lock(1)
    g = d.pg.locator('.rk-grid svg'); g.focus()
    d.pg.keyboard.press('+'); d.pg.keyboard.press('e')
    assert d.st('m') == [[3, 2], [3, 4]]
    d.pg.keyboard.press('ArrowDown'); d.pg.keyboard.press('d'); d.pg.keyboard.press('-')
    assert d.st('m') == [[3, 2], [3, 3]]
    assert g.get_attribute('aria-valuetext') == 'bottom, right: 3'

def test_grid_locked_refuses(draw):
    d = draw(EX['grid'])
    d.pg.locator('.rk-grid svg').focus(); d.pg.keyboard.press('+')
    assert d.st('m') == [[1, 2], [3, 4]]

# pixels

DIFFUSION = dict(id='diffusion', state=dict(t=500),
                 derive=[dict(fn='field', expr='sqrt(1 - t/1000) * (i + j)/30 + sqrt(t/1000) * noise(i, j)', n=16, seed=7, out='img')],
                 blocks=[dict(type='slider', bind='t', min=0, max=1000), dict(type='pixels', bind='img', label='Grid at t = {t}')])

PIXELS = "c => [...c.getContext('2d').getImageData(0, 0, c.width, c.height).data]"

def test_pixels_draws_each_cell(draw):
    d = draw(DIFFUSION)
    px = d.pg.locator('.rk-pixels canvas').evaluate(PIXELS)
    grey = [sum(px[k:k + 3]) for k in range(0, len(px), 4)]
    vs = sum(d.st('img'), [])
    assert len(grey) == len(vs) == 256 and all(a == 255 for a in px[3::4])
    assert len(set(grey)) > 50 and grey[vs.index(max(vs))] < grey[vs.index(min(vs))]   # light mode: the largest value is darkest
    assert d.errors == []

def test_pixels_label_follows_the_state(draw):
    d = draw(DIFFUSION)
    cv = d.pg.locator('.rk-pixels canvas')
    assert cv.get_attribute('role') == 'img' and cv.get_attribute('aria-label') == 'Grid at t = 500'
    before = cv.evaluate(PIXELS)
    d.pg.locator('.rk-slider input').focus(); d.pg.keyboard.press('ArrowRight')
    assert d.st('t') == 501 and cv.get_attribute('aria-label') == 'Grid at t = 501'
    assert cv.evaluate(PIXELS) != before and d.errors == []

# axis: dense ticks

from rupaka.render import page

DENSE = dict(id='dense', state=dict(d=170), blocks=[
    dict(type='axis', label='Moon minus Sun, one slice every 12°', x=[0, 360], xstep=12, blocks=[dict(type='point', bind='d', label='Moon − Sun')]),
    dict(type='axis', x=[0, 360], xstep=12, y=[-1, 1], ystep=0.04, height=200, blocks=[])])
APART = """() => [...document.querySelectorAll('.rk-axis svg')].map(s => {
  const rs = [...s.querySelectorAll('text.num')].map(t => t.getBoundingClientRect()), meet = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  return {n: rs.length, ticks: s.querySelectorAll('line.hair, line.zero').length, meets: rs.flatMap((a, i) => rs.slice(i + 1).filter(b => meet(a, b)).map(() => i)).length,
          texts: [...s.querySelectorAll('text.num')].map(t => t.textContent)}; })"""

@pytest.mark.parametrize('w', [420, 640, 1200])
def test_dense_axis_labels_never_meet(draw, w):
    "Each tick keeps its mark, but only every k-th tick has a label, so no two labels meet. The first and the last tick have one."
    d = draw(None, html=page(DENSE, fonts='none').replace('</style>', f'main.rk-page {{ max-width: none; width: {w}px; margin: 0; padding: 16px; }} .rk {{ max-width: none; }}</style>'))
    d.pg.set_viewport_size(dict(width=w + 32, height=900))
    line, xy = d.pg.evaluate(APART)
    assert line['meets'] == 0 and xy['meets'] == 0, w
    assert line['ticks'] == 31 and 3 < line['n'] < 31 and line['texts'][0] == '0' and line['texts'][-1] == '360'
    assert xy['texts'][-1] == '1' and d.errors == []
    ys = [float(t.replace('−', '-')) for t in d.pg.evaluate("[...document.querySelectorAll('.rk-axis')[1].querySelectorAll('text.num[text-anchor=end]')].map(t => t.textContent)")]
    step = min(abs(a - b) for a, b in zip(ys, ys[1:]))
    assert 0.0 in ys and all(abs(v / step - round(v / step)) < 1e-6 for v in ys), ys
    t, ls = d.pg.evaluate("""(() => { const a = document.querySelectorAll('.rk-axis')[1], r = e => e.getBoundingClientRect();
      return [r([...a.querySelectorAll('text.num[text-anchor=end]')].find(t => t.textContent === '0')), [...a.querySelectorAll('line.zero')].map(r)]; })()""")
    assert any(l['height'] < 2 and t['top'] <= l['top'] <= t['bottom'] for l in ls)     # the label 0 sits at the zero line

# plot ghost and tone, axis xlog

GH = dict(id='gh', state=dict(m=1), derive=[dict(fn='expr', expr='m * x', over=dict(x=[-4, 4, 9]), out='line')], blocks=[
    dict(type='axis', x=[-4, 4], y=[-8, 8], blocks=[dict(type='plot', series='line', ghost=True, tone='mute')]),
    dict(type='slider', bind='m', min=-3, max=3, step=1)])

def test_plot_ghost_keeps_the_line_from_before_the_change(draw):
    from rupaka.spec import validate
    assert [e for e in validate(GH) if 'gate' not in e] == []
    d = draw(GH)
    ln, gh = d.pg.locator('.rk-plot path.ln'), d.pg.locator('.rk-plot path.gh')
    first = ln.get_attribute('d')
    assert gh.get_attribute('d') is None                       # nothing has changed yet
    d.pg.locator('.rk-slider input').focus(); d.pg.keyboard.press('d')
    assert d.st('m') == 2 and gh.get_attribute('d') == first and ln.get_attribute('d') != first
    second = ln.get_attribute('d')
    d.pg.keyboard.press('d')                                   # a quick second step is the same drag: the ghost stays
    assert gh.get_attribute('d') == first
    d.pg.wait_for_timeout(600); d.pg.keyboard.press('a')       # after a pause, the line before this change is the ghost
    assert gh.get_attribute('d') != first and d.errors == []
    assert d.pg.locator('.rk-plot').first.evaluate("e => e.classList.contains('t-mute')")

def test_plot_draws_the_guess_dashed_only_after_lock_in_and_keeps_it_while_inputs_move(draw):
    from rupaka.spec import validate
    d = draw(EX['plot']); assert validate(EX['plot']) == []
    gs = d.pg.locator('.rk-plot path.gs')
    assert gs.get_attribute('d') is None                          # nothing before Lock in
    d.lock(2)                                                     # It gets flatter: m / 2
    drawn = gs.get_attribute('d')
    assert drawn and drawn != d.pg.locator('.rk-plot path.ln').get_attribute('d')
    assert gs.evaluate("e => getComputedStyle(e).strokeDasharray") != 'none'
    d.pg.locator('.rk-slider input').focus(); d.pg.keyboard.press('d')
    assert d.st('m') == 1.5 and gs.get_attribute('d') == drawn and d.errors == []

def test_a_point_that_rides_a_curve_drags_and_nudges_x_only(draw):
    spec = dict(id='al', state=dict(x=1), derive=[dict(fn='expr', expr='x * x', out='y'), dict(fn='expr', expr='x * x', over=dict(x=[0, 4, 9]), out='c')],
                blocks=[dict(type='axis', x=[0, 4], y=[0, 16], blocks=[dict(type='plot', series='c'), dict(type='point', x='x', y='y', along=True, step=0.5)])])
    from rupaka.spec import validate
    assert [e for e in validate(spec) if 'gate' not in e] == []
    d = draw(spec)
    pt = d.pg.locator('.rk-point'); assert pt.get_attribute('role') == 'slider'
    pt.focus(); d.pg.keyboard.press('d'); assert d.st('x') == 1.5 and d.st('y') == 2.25
    d.pg.keyboard.press('w'); assert d.st('x') == 1.5            # up does nothing: y is not an input
    svg = d.pg.locator('.rk-axis svg'); bx = svg.bounding_box()
    px = lambda v: bx['x'] + (40 + v / 4 * (600 - 40 - 16)) / 600 * bx['width']
    dot = d.pg.locator('.rk-point .dot').bounding_box()
    d.pg.mouse.move(dot['x'] + dot['width'] / 2, dot['y'] + dot['height'] / 2); d.pg.mouse.down()
    d.pg.mouse.move(px(3.1), dot['y'] + dot['height'] / 2, steps=6); d.pg.mouse.up()
    assert d.st('x') == 3 and d.st('y') == 9 and d.errors == []

def test_plot_without_ghost_draws_no_ghost(draw):
    d = draw(EX['plot'])
    assert d.pg.locator('.rk-plot path.gh').count() == 0

def test_axis_xlog_shows_decades(draw):
    spec = dict(id='xl', state={}, derive=[dict(fn='expr', expr='-x / 2', over=dict(x=[0, 4, 9]), out='c')],
                blocks=[dict(type='axis', x=[0, 4], xlog=True, y=[-3, 1], blocks=[dict(type='plot', series='c')])])
    from rupaka.spec import validate
    assert [e for e in validate(spec) if 'gate' not in e] == []
    d = draw(spec)
    labels = d.pg.evaluate("[...document.querySelectorAll('.rk-axis text.num[text-anchor=middle]')].map(t => t.textContent)")
    assert labels == ['1', '10', '100', '1k', '10k'] and d.errors == []

# a dot that rides a curve in the shipped demos, and the tags of the guess and the true curve

def _demo(name):
    from pathlib import Path
    import rupaka
    return json.loads((Path(rupaka.__file__).parent / 'demos' / f'{name}.json').read_text())

def _points(bs):
    for b in bs:
        if b['type'] == 'point': yield b
        yield from _points(b.get('blocks', []))

def test_every_demo_point_on_a_derived_value_rides_its_curve():
    from pathlib import Path
    import rupaka
    for f in sorted((Path(rupaka.__file__).parent / 'demos').glob('*.json')):
        sp = json.loads(f.read_text())
        for p in _points(sp['blocks']):
            if p.get('y') and p['y'] not in sp['state'] and p.get('x') in sp['state'] and p.get('drag') is not False and p.get('label') != 'cut-off':
                assert p.get('along'), f"{f.stem}: the dot '{p.get('label')}' cannot be dragged: its y is derived and it has no `along`"

def _drag_dot(d, dx=80):
    dot = d.pg.locator('.rk-point .dot').first.bounding_box()
    cx, cy = dot['x'] + dot['width'] / 2, dot['y'] + dot['height'] / 2
    d.pg.mouse.move(cx, cy); d.pg.mouse.down(); d.pg.mouse.move(cx + dx, cy, steps=6); d.pg.mouse.up()

def test_ohms_law_dot_drags_after_lock_in(draw):
    d = draw(_demo('ohms-law')); d.lock(1)
    assert d.pg.locator('.rk-point').first.get_attribute('role') == 'slider'
    v = d.st('V'); _drag_dot(d)
    assert d.st('V') > v and d.st('R') == 3 and d.errors == []

def test_rc_low_pass_input_dot_drags(draw):
    d = draw(_demo('rc-low-pass'))
    assert d.pg.locator('.rk-point').first.get_attribute('role') == 'slider'
    lf = d.st('lf'); _drag_dot(d)
    assert d.st('lf') > lf and d.errors == []

@pytest.mark.parametrize('mode,width', [('light', 720), ('dark', 720), ('dark', 340)])
def test_plot_names_the_guess_and_the_true_curve_after_lock_in(draw, mode, width):
    d = draw(_demo('rc-low-pass'), mode=mode); d.pg.set_viewport_size(dict(width=width, height=900))
    tags = d.pg.locator('.rk-plot text.tg')
    assert [t for t in tags.all() if t.is_visible()] == []              # no tags before Lock in
    d.lock(1)                                                           # "It doubles": a wrong guess, so the curves part
    shown = d.pg.evaluate("[...document.querySelectorAll('.rk-plot text.tg')].filter(t => t.getAttribute('display') !== 'none').map(t => t.textContent)")
    assert sorted(shown) == ['true', 'your guess'], shown
    box = d.pg.locator('.rk-axis svg').bounding_box()
    for t in tags.all():
        if t.is_visible():
            tb = t.bounding_box()
            assert tb['x'] >= box['x'] - 1 and tb['x'] + tb['width'] <= box['x'] + box['width'] + 1, (mode, width, tb, box)
    assert d.errors == []

def test_plot_gives_one_tag_when_the_guess_is_the_true_curve(draw):
    d = draw(_demo('rc-low-pass')); d.lock(3)                           # "It stays the same": the guess is the curve now
    shown = d.pg.evaluate("[...document.querySelectorAll('.rk-plot text.tg')].filter(t => t.getAttribute('display') !== 'none').map(t => t.textContent)")
    assert shown == ['your guess, true']

# the first drag after Lock in, and the one tag for a guess that lies on the true curve

def _grab(d, kind, dx=80):
    "Drag the first dot with the mouse or with a finger, from its centre."
    dot = d.pg.locator('.rk-point .dot').first; dot.scroll_into_view_if_needed(); bb = dot.bounding_box()
    cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
    if kind == 'mouse': d.pg.mouse.move(cx, cy); d.pg.mouse.down(); d.pg.mouse.move(cx + dx, cy, steps=8); d.pg.mouse.up(); return
    cdp = d.pg.context.new_cdp_session(d.pg); ev = lambda t, x=None: cdp.send('Input.dispatchTouchEvent', dict(type=t, touchPoints=[dict(x=x, y=cy)] if x is not None else []))
    ev('touchStart', cx)
    for i in range(1, 9): ev('touchMove', cx + dx * i / 8)
    ev('touchEnd')

@pytest.mark.parametrize('kind', ['mouse', 'touch'])
@pytest.mark.parametrize('name', ['ohms-law', 'rc-low-pass'])
def test_the_first_drag_after_lock_in_moves_the_dot_and_the_readout(draw, name, kind):
    d = draw(_demo(name)); d.lock(1)
    read = lambda: d.pg.locator('.rk-readout').first.text_content()
    first = read(); _grab(d, kind); d.pg.wait_for_timeout(100)
    assert read() != first and d.errors == [], (name, kind, first)

def test_in_every_demo_the_dot_that_drags_is_the_top_mark_at_the_start_state(draw):
    from pathlib import Path
    import rupaka
    for f in sorted((Path(rupaka.__file__).parent / 'demos').glob('*.json')):
        sp = json.loads(f.read_text())
        if not any(p.get('along') for p in _points(sp['blocks'])): continue
        d = draw(sp)
        if sp.get('blocks') and any(b['type'] == 'gate' for b in sp['blocks']): d.lock(1)
        for dot in d.pg.locator('.rk-point[role=slider] .dot').all():
            bb = dot.bounding_box(); cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
            top = d.pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y), g = e && e.closest('.rk-point'); return g ? g.getAttribute('role') : (e ? e.tagName : null) }", [cx, cy])
            assert top == 'slider', (f.stem, top)

@pytest.mark.parametrize('mode,width', [('light', 1200), ('dark', 1200), ('light', 390), ('dark', 390)])
def test_the_tag_for_a_guess_on_the_true_curve_touches_no_label_and_no_curve(draw, mode, width):
    d = draw(_demo('rc-low-pass'), mode=mode); d.pg.set_viewport_size(dict(width=width, height=900)); d.pg.wait_for_timeout(200)
    d.lock(3); d.pg.wait_for_timeout(200)                               # "It stays the same"
    hit = d.pg.evaluate("""() => {
      const R = e => e.getBoundingClientRect(), svg = document.querySelector('.rk-axis svg'), s = R(svg);
      const tags = [...svg.querySelectorAll('text.tg')].filter(t => t.getAttribute('display') !== 'none'); if (tags.length !== 1) return ['tags ' + tags.length];
      const r = R(tags[0]), out = [], meet = (a, b) => a.x < b.right && b.x < a.right && a.y < b.bottom && b.y < a.bottom;
      if (r.x < s.x || r.right > s.right || r.y < s.y || r.bottom > s.bottom) out.push('leaves the svg');
      svg.querySelectorAll('text:not(.tg)').forEach(t => { if (t.textContent.trim() && meet(r, R(t))) out.push('label ' + t.textContent.trim()); });
      svg.querySelectorAll('path.ln, path.gs').forEach(p => { const m = p.getScreenCTM(), L = p.getTotalLength(); let n = 0;
        for (let i = 0; i <= 400; i++) { const q = p.getPointAtLength(L * i / 400), x = q.x * m.a + m.e, y = q.y * m.d + m.f; if (x > r.x && x < r.right && y > r.y && y < r.bottom) n++; }
        if (n) out.push('curve ' + p.getAttribute('class')); });
      return out; }""")
    assert hit == [] and d.errors == [], (mode, width, hit)
