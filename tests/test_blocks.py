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

# readout, caption

def test_caption_escapes_html(draw):
    spec = dict(id='c', state=dict(x='<img src=x onerror=alert(1)>'), blocks=[dict(type='caption', text='**Bold** {x} <b>raw</b>')])
    d = draw(spec)
    c = d.pg.locator('.rk-caption')
    assert c.locator('img').count() == 0 and c.locator('b').count() == 1
    assert c.inner_text() == 'Bold <img src=x onerror=alert(1)> <b>raw</b>'

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
    row = d.pg.locator('.rk-ranklist').nth(list_i).locator(f'g.row[data-id="{id}"]'); bx = row.bounding_box()
    d.pg.mouse.move(bx['x'] + 20, bx['y'] + bx['height'] / 2); d.pg.mouse.down()
    d.pg.mouse.move(bx['x'] + 20, bx['y'] + bx['height'] / 2 + rows * bx['height'], steps=8); d.pg.mouse.up()

def test_ranklist_refuses_while_locked_then_drags(draw):
    d = draw(EX['ranklist'])
    drag_row(d, 0, 'B', -3)
    assert d.st('order') == list('ACEB')
    d.lock(1)
    drag_row(d, 0, 'B', -3)
    assert d.st('order') == list('BACE')
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
    path = d.pg.locator('.rk-plot path').get_attribute('d')
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
