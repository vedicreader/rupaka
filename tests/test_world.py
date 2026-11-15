"The world parts of a scene in a headless browser: a grip moves with keys and the pointer, a lock holds it, and a bad state value does not stop the view."
import json
from rupaka.spec import gallery, demo, gate, expr, scene, body, links, path, points, shot, validate
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

def world(*parts, state=None, derive=(), **kw):
    "A demo with one sky scene of `parts`, and a gate that reads no part."
    return demo('w', 'W', state=dict(a=0, **(state or {})), derive=[expr('a + 1', 'b'), *derive],
                blocks=[gate('g', 'What is a + 1?', [1, 2], 'b'), scene(*parts, **{'look': 'sky', **kw})])

def tones(pg) -> dict:
    "The canvas of the scene: the mean red, green and blue of the pixels that are not the ground, and the count of their distinct colours."
    return pg.evaluate("""() => { const c = document.querySelector('.rk-scene canvas.gl'), w = c.width, h = c.height;
      const x = Object.assign(document.createElement('canvas'), {width: w, height: h}).getContext('2d');
      x.drawImage(c, 0, 0); const px = x.getImageData(0, 0, w, h).data, bg = [px[0], px[1], px[2]], sum = [0, 0, 0], seen = new Set(); let n = 0;
      for (let i = 0; i < px.length; i += 4) { if (Math.abs(px[i] - bg[0]) + Math.abs(px[i + 1] - bg[1]) + Math.abs(px[i + 2] - bg[2]) < 24) continue;
        n++; sum[0] += px[i]; sum[1] += px[i + 1]; sum[2] += px[i + 2]; seen.add(px[i] >> 3 << 10 | px[i + 1] >> 3 << 5 | px[i + 2] >> 3); }
      return {rgb: sum.map(v => v / Math.max(1, n)), colours: seen.size}; }""")

def test_plot_rows_draw_a_path(draw):
    "A path takes the {x, y} rows of expr with over, so a curve of a plot is a line in a scene, and a body rides it."
    s = world(path(of='curve', id='c'), body('m', 'sphere', [.3], along='c', t=0.5), derive=[expr('x * x', 'curve', over=dict(x=[0, 2, 9]))])
    assert validate(s) == []
    d = draw(s); settled(d.pg)
    assert not d.errors and tones(d.pg)['colours'] > 1

def test_sky_body_has_shade_with_no_lamp(draw):
    "A sky scene with no lamp body has a key light, so the faces of a box differ."
    d = draw(world(body('p', 'box', [2, 2, 2], round=0))); settled(d.pg)
    assert tones(d.pg)['colours'] >= 10 and not d.errors   # one flat grey gives about 4

def test_halo_has_the_colour_of_its_body(draw):
    "The halo of a green lamp is green, not the orange of a sun."
    d = draw(world(body('p', 'sphere', [1], color='ok', glow=1))); settled(d.pg)
    r, g, _ = tones(d.pg)['rgb']
    assert g > r * 1.15 and not d.errors

def test_chip_behind_the_globe_hides(draw):
    "On a globe, the name of a place on the far side does not show. With no at, the globe is at the centre of the world."
    s = world(body('e', 'globe'), points(pts=[[0, 0, .2], [180, 0, .2]], names=['Near', 'Far']), shot('wide', turn=60), coords='globe')
    d = draw(s); settled(d.pg)
    off = lambda t: 'off' in d.pg.locator('.rk-chip', has_text=t).get_attribute('class')
    assert not off('Near') and off('Far') and not d.errors   # the names show with no change of the state
