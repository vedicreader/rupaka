"The world parts of a scene in a headless browser: a grip moves with keys and the pointer, a lock holds it, and a bad state value does not stop the view."
import json
from rupaka.spec import gallery, demo, gate, expr, scene, body, links, path
from test_scene import settled

SKY = gallery()['panchangam-sky']

def grip(d, n=1): return d.pg.locator('.rk-grip').nth(n)   # 0 is the Sun, 1 is the Moon

def test_grip_is_locked_before_the_gate(draw):
    d = draw(SKY); settled(d.pg)
    g = grip(d); assert g.get_attribute('data-locked') is not None
    g.focus(); d.pg.keyboard.press('d')
    assert d.st('moon') == 272 and not d.errors

def test_grip_keys_move_the_moon(draw):
    d = draw(SKY); settled(d.pg); d.lock()
    g = grip(d); g.focus(); d.pg.keyboard.press('d'); d.pg.keyboard.press('Shift+ArrowRight')
    assert d.st('moon') == 283 and d.st('tithi') == 6 and not d.errors     # 272 + 1 + 10; the gap is 71 degrees, still the 6th tithi
    d.pg.keyboard.press('a'); assert d.st('moon') == 282

def test_grip_drag_moves_the_moon_round(draw):
    d = draw(SKY); settled(d.pg); d.lock(); settled(d.pg)
    b = grip(d).bounding_box(); x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    d.pg.mouse.move(x, y); d.pg.mouse.down(); d.pg.mouse.move(x + 60, y - 20, steps=6); d.pg.mouse.up()
    assert d.st('moon') != 272 and not d.errors

def test_bad_state_does_not_stop_the_view(draw):
    s = demo('w', 'W', state=dict(w=[0.2, 0.8], pts=[[0, 0, 0], [1, 1, 0]], a=0), derive=[expr('a + 1', 'b')],
             blocks=[gate('g', 'What is a + 1?', [1, 2], 'b'), scene(body('p', 'box', [1, 1, 1]), body('q', 'box', [1, 1, 1], at=[3, 0, 0]),
                     links(['p', 'q'], 'w', row=0), path(of='pts'), body('m', 'sphere', [.3], orbit=2, angle='a'), look='sky')])
    d = draw(s); settled(d.pg)
    d.pg.evaluate("Rupaka.set(document.querySelector('[data-rupaka]'), {w: 'oops', pts: [null, 3, {x: 1}], a: 'x'})")
    settled(d.pg)
    assert not d.errors and d.pg.locator('.rk-scene .stage').get_attribute('data-rk-gl') == 'ready'
