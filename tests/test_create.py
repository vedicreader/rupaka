"Layers, timeline, ease and keyframes: the fns match their Python twins, and the scene moves with the bar, the handles and the keys."
import math, tempfile
from pathlib import Path
import pytest
from rupaka.spec import gallery, run, validate
from rupaka.render import page, save

DEMO = gallery()['scene-dawn-to-dusk']
KS = [[0, 10], [10, 20, 'out'], [20, 0, 'in'], [30, 5]]

def js_run(draw, spec):
    return draw({**spec, 'id': 'f', 'mode': 'learn', 'blocks': [dict(type='readout', text='x')]}).st()

@pytest.mark.parametrize('kind', ['linear', 'in', 'out', 'inout', 'step'])
def test_ease_matches_python(draw, kind):
    spec = dict(state=dict(t=0), derive=[dict(fn='ease', kind=kind, over=[0, 10], out=f'u{j}', **{'in': x}) for j, x in enumerate((-3, 0, 2.5, 5, 7.5, 10, 14))])
    js, py = js_run(draw, spec), run(spec)
    assert all(math.isclose(js[f'u{i}'], py[f'u{i}'], abs_tol=1e-12) for i in range(7))

@pytest.mark.parametrize('ease', [None, 'inout', 'step'])
def test_keyframes_match_python(draw, ease):
    xs = [-5, 0, 3, 10, 12.5, 20, 27, 30, 45]
    spec = dict(state=dict(t=0), derive=[dict(fn='keyframes', keys=KS, out=f'v{i}', **{'in': x}, **({'ease': ease} if ease else {})) for i, x in enumerate(xs)])
    js, py = js_run(draw, spec), run(spec)
    assert all(math.isclose(js[f'v{i}'], py[f'v{i}'], abs_tol=1e-12) for i in range(len(xs)))

def test_keyframes_read_a_state_key_and_hold_the_ends(draw):
    spec = dict(state=dict(t=5), derive=[dict(fn='keyframes', keys=KS, out='v', **{'in': 't'})])
    assert js_run(draw, spec)['v'] == run(spec)['v'] == 15
    assert run(spec, dict(t=-9))['v'] == 10 and run(spec, dict(t=99))['v'] == 5

def test_keyframes_bad_curve_shows_an_error(draw):
    bad = {**DEMO, 'derive': [dict(fn='keyframes', keys=[[0, 1, 'wobble'], [1, 2]], out='v', **{'in': 't'})]}
    assert validate(bad)[0].startswith('derive[0].keys[0]: must be [t, value]')

def test_demo_is_valid_and_draws_without_errors(draw):
    assert validate(DEMO) == []
    for mode in ('light', 'dark'):
        d = draw(DEMO, mode=mode)
        assert d.pg.locator('.rk-layers .rk-layer').count() == 8
        assert d.errors == []

def transform(d, n): return d.pg.locator('.rk-layer .pose').nth(n).get_attribute('transform')
def tx(d, n): return float(transform(d, n).split('(')[1].split(' ')[0])

def test_scrub_moves_layers_with_parallax(draw):
    d = draw(DEMO)
    far, near, boat = 4, 5, 7     # far hill, near hill, boat
    f0, n0, b0 = tx(d, far), tx(d, near), tx(d, boat)
    d.pg.locator('.rk-timeline input').focus(); d.pg.keyboard.press('Shift+d'); d.pg.keyboard.press('Shift+d')
    assert d.st('t') == 40
    df, dn = tx(d, far) - f0, tx(d, near) - n0
    assert dn < df < 0 and math.isclose(dn / df, 2.5, rel_tol=1e-6)    # a near layer moves more than a far one: depth 0.5 against 0.2
    assert tx(d, boat) == b0                                           # the boat is at depth 0
    assert d.pg.locator('.rk-sky .warm, .rk-layer.art-sky .warm').first.evaluate('e => getComputedStyle(e).opacity') != '0'

def test_caption_changes_at_a_time_mark(draw):
    d = draw(DEMO)
    cap = lambda: d.pg.locator('.rk-caption p').inner_text()
    assert cap().startswith('Dawn')
    d.pg.locator('.rk-timeline input').focus()
    d.pg.keyboard.press('e'); assert d.st('t') == 30 and cap().startswith('Morning')
    d.pg.keyboard.press('e'); assert d.st('t') == 60 and cap().startswith('Afternoon')
    d.pg.keyboard.press('e'); d.pg.keyboard.press('e'); assert d.st('t') == 100 and cap().startswith('Dusk')
    d.pg.keyboard.press('q'); assert d.st('t') == 85
    d.pg.get_by_role('button', name='Time of day Morning').click(); assert d.st('t') == 30

def test_timeline_keys_and_play(draw):
    d = draw({**DEMO, 'blocks': [DEMO['blocks'][0], {**DEMO['blocks'][1], 'speed': 400}, DEMO['blocks'][2]]})
    d.pg.locator('.rk-timeline input').focus()
    d.pg.keyboard.press('d'); assert d.st('t') == 21
    d.pg.keyboard.press('a'); d.pg.keyboard.press('a'); assert d.st('t') == 19
    d.pg.keyboard.press('w')
    d.pg.wait_for_function("document.querySelector('[data-rupaka]').rupaka.st.t >= 100")
    assert d.st('t') == 100 and d.pg.locator('.rk-tl-play').inner_text() == 'Play'     # it stops at the end
    d.pg.keyboard.press('w'); assert d.pg.locator('.rk-tl-play').inner_text() == 'Pause'
    d.pg.keyboard.press('w'); t = d.st('t'); d.pg.wait_for_timeout(120); assert d.st('t') == t   # pause holds

def test_handle_drag_writes_the_key_and_shows_a_ghost(draw):
    d = draw(DEMO)
    ghosts = lambda: d.pg.locator('.rk-layer.art-boat .ghost:visible').count()
    h = d.pg.locator('.handle').first.bounding_box()      # the sun handle comes first
    boat = d.pg.locator('.handle[aria-label="Boat position"]'); bb = boat.bounding_box()
    cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
    d.pg.mouse.move(cx, cy); d.pg.mouse.down()
    d.pg.mouse.move(cx + 120, cy, steps=6)
    assert d.st('boat') > 50 and ghosts() == 1                  # the picture keeps a faint boat where it was
    d.pg.mouse.up()
    assert ghosts() == 0
    sun0 = d.st('sun'); sb = d.pg.locator('.handle[aria-label="Sun height"]').bounding_box()
    d.pg.mouse.move(sb['x'] + sb['width'] / 2, sb['y'] + sb['height'] / 2); d.pg.mouse.down()
    d.pg.mouse.move(sb['x'] + sb['width'] / 2, sb['y'] - 30, steps=5); d.pg.mouse.up()
    assert d.st('sun') > sun0 and 10 <= d.st('sun') <= 75       # up is higher, inside its range
    assert d.errors == []

def test_handle_keys_and_range(draw):
    d = draw(DEMO)
    b = d.pg.locator('.handle[aria-label="Boat position"]'); b.focus()
    d.pg.keyboard.press('d'); assert d.st('boat') == 50.5
    d.pg.keyboard.press('Shift+a'); assert d.st('boat') == 45.5
    for _ in range(30): d.pg.keyboard.press('Shift+d')
    assert d.st('boat') == 146                                  # stays in xr
    s = d.pg.locator('.handle[aria-label="Sun height"]'); s.focus()
    d.pg.keyboard.press('w'); assert d.st('sun') == 58.5       # W lifts the sun
    d.pg.keyboard.press('s'); d.pg.keyboard.press('s'); assert d.st('sun') == 57.5

def test_scrub_shows_ghosts_then_clears(draw):
    d = draw(DEMO)
    d.pg.locator('.rk-timeline input').focus(); d.pg.keyboard.press('Shift+d')
    assert d.pg.locator('.rk-layer .ghost:visible').count() >= 1
    d.pg.wait_for_function("document.querySelectorAll('.rk-layer .ghost:not([style*=none])').length === 0", timeout=3000)

def test_named_values_are_the_state_keys(draw):
    d = draw(DEMO)
    assert {'t', 'boat', 'sun'} <= set(d.st()) and 'gate' in d.st()
    assert d.pg.evaluate("Rupaka.state(document.querySelector('[data-rupaka]'))") == dict(t=20, boat=50, sun=58)
    d.pg.evaluate("Rupaka.set(document.querySelector('[data-rupaka]'), {boat: 90, t: 60})")
    assert d.st('boat') == 90 and d.pg.locator('.rk-caption p').inner_text().startswith('Afternoon')

def test_export_works_from_file(br):
    with tempfile.TemporaryDirectory() as td:
        p = save(DEMO, Path(td).resolve()/'scene.html', fonts='none')
        pg = br.new_page(viewport=dict(width=800, height=900)); errs = []
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text)); pg.on('pageerror', lambda e: errs.append(str(e)))
        try:
            pg.goto(p.as_uri()); pg.wait_for_selector('[data-rk-ready="1"]', state='attached')
            assert pg.locator('.rk-layer').count() == 8 and errs == []
            pg.locator('.rk-timeline input').focus(); pg.keyboard.press('e')
            assert pg.locator('.rk-caption p').inner_text().startswith('Morning')
        finally: pg.close()
