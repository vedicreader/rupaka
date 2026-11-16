"The world parts of a scene in a headless browser: a grip moves with keys and the pointer, a lock holds it, and a bad state value does not stop the view."
import json, math
from pathlib import Path
from rupaka.spec import gallery, demo, gate, expr, scene, body, links, path, points, shot, slider, validate
from test_scene import settled

SKY = json.loads((Path(__file__).parent/'sky_grips.json').read_text())   # the panchangam sky with a grip on the Sun and the Moon

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

def test_a_lamp_body_makes_the_look_sky(draw):
    "With no look, a scene with a lamp body is in the sky look, so the lamp alone makes the day and night halves. A plain scene stays toon."
    sun = body('s', 'sphere', [1], at=[8, 0, 0], texture='sun', light=True)
    for parts, look in (((body('m', 'sphere', [1], texture='moon'), sun), 'sky'), ((body('p', 'box', [1, 1, 1]),), 'toon')):
        s = world(*parts, look=None); assert validate(s) == []
        d = draw(s); settled(d.pg)
        assert d.pg.locator('.rk-scene .stage').get_attribute('data-look') == look and not d.errors

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

def put(d, **kw): d.pg.evaluate(f"Rupaka.set(document.querySelector('[data-rupaka]'), {json.dumps(kw)})"); settled(d.pg)

def test_arc_builds_again_only_when_its_angles_change(draw):
    "A ring with an arc makes a new shape when a key of the arc changes, and not for another key."
    d = draw(world(body('r', 'ring', [1, 2], arc=[0, 'n']), state=dict(n=90, z=0))); settled(d.pg)
    d.pg.evaluate("(() => { const P = RupakaTHREE.BufferGeometry.prototype, f = P.dispose; window.__gone = 0; P.dispose = function () { __gone++; return f.call(this); }; })()")
    for z in (1, 2, 3): put(d, z=z)
    assert d.pg.evaluate('__gone') == 0
    put(d, n=180)
    assert d.pg.evaluate('__gone') == 1 and not d.errors

def test_spin_stands_still_with_reduced_motion(draw):
    "With reduced motion, a spinning body does not jump to a new angle when the view draws again."
    d = draw(world(body('p', 'box', [2, 1, 1], round=0, spin=90), state=dict(z=0))); settled(d.pg)
    d.pg.emulate_media(reduced_motion='reduce'); put(d, z=1)
    snap = lambda: d.pg.evaluate("document.querySelector('.rk-scene canvas.gl').toDataURL()")
    a = snap(); d.pg.wait_for_timeout(400); put(d, z=2)
    assert snap() == a and not d.errors

def test_gate_prompt_follows_the_state_when_the_host_refuses(draw):
    "When the host cannot save a prediction, the gate opens again and its prompt shows the state as it is now."
    d = draw(demo('p', 'P', state=dict(k=1), derive=[expr('k + 1', 'b')],
                  blocks=[gate('g', 'What is {k} + 1?', [2, 3], 'b', context='For {k}:'), slider('k', 'k', 0, 9, 1, lock='g')]))
    d.pg.evaluate("document.addEventListener('rk-predict', e => { e.preventDefault(); window.__settle = e.detail.settle; })")
    d.lock(); q = d.pg.locator('.rk-gate .q')
    d.pg.evaluate("Rupaka.set(document.querySelector('[data-rupaka]'), {k: 5})")
    assert q.inner_text() == 'What is 1 + 1?'                          # pending: the prompt as it was at lock-in
    d.pg.evaluate("__settle(false, 'The save did not work.')")
    assert q.inner_text() == 'What is 5 + 1?' and not d.errors

def test_vector_sum_can_stand_straight_up(draw):
    "A 2D demo: the sum arrow shows after the gate. The caption asks where it stands straight up, at b = (-3, 2), and the point reaches it."
    d = draw(gallery()['vector-sum']); settled(d.pg)
    s = d.pg.locator('.rk-arrow').filter(has_text='a + b')
    assert not s.is_visible()
    d.lock(); settled(d.pg)
    d.pg.locator('.rk-point').focus()
    for _ in range(4): d.pg.keyboard.press('ArrowLeft')
    tip = s.evaluate("g => +g.querySelector('path.hd').getAttribute('d').match(/^M\\s*(-?[\\d.]+)/)[1]")
    x0 = s.evaluate("g => +g.querySelector('line.ln').getAttribute('x1')")
    assert d.st('bx') == -3 and d.st('sx') == 0 and abs(tip - x0) < 0.05 and not d.errors

def test_throw_ball_is_in_the_air_half_way(draw):
    "Half way through the flight the ball is half way to where it lands, and above the ground, at any angle."
    d = draw(gallery()['throw-angle']); settled(d.pg)
    for a in (30, 80):
        put(d, a=a, t=0.5)
        assert abs(d.st('bx') - d.st('range') / 2) < 1e-9 and d.st('by') > 0
    assert not d.errors

def test_throw_flight_ends_where_the_ball_lands(draw):
    "After the landing the flight leaves the plot under the ground: no point of it runs along the ground to the edge."
    d = draw(gallery()['throw-angle']); settled(d.pg)
    put(d, a=45)
    after = [p['y'] for p in d.st('arc') if p['x'] > d.st('range') + 0.5]
    assert after and all(y < 0 for y in after) and not d.errors

def test_flight_plane_is_at_dubai_when_the_label_says_5500_km(draw):
    "The label counts km and the plane rides the drawn route, so both must reach Dubai at the same share."
    d = draw(gallery()['flight-route']); settled(d.pg)
    leg = lambda a, b: ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** .5
    pts = [(0, 51.5), (55.3, 25.3), (103.8, 1.4), (151.2, -33.9)]
    ls = [leg(*pts[i:i + 2]) for i in range(3)]
    put(d, t=5500 / 17600)
    assert d.st('km') == 5500 and abs(d.st('pt') - ls[0] / sum(ls)) < 1e-3
    put(d, t=11300 / 17600)
    assert abs(d.st('pt') - (ls[0] + ls[1]) / sum(ls)) < 1e-3 and not d.errors

def test_sun_west_of_london_comes_round_later(draw):
    "The Sun moves west only, so noon at 90 degrees west reaches London in 18 hours, not in -6."
    d = draw(gallery()['sun-over-earth']); settled(d.pg)
    for lon, h in ((90, 6), (-90, 18), (0, 0), (180, 12)):
        put(d, lon=lon); assert d.st('hours') == h, (lon, d.st('hours'))
    assert not d.errors

def test_orbit_drag_with_no_range_wraps(draw):
    "An orbit grip with no range writes an angle in [0, 360), with the keys and the pointer, so a slider on the same key does not jam."
    d = draw(SKY); settled(d.pg); d.lock(); settled(d.pg)
    g = grip(d); g.focus()
    for _ in range(10): d.pg.keyboard.press('Shift+d')
    assert 0 <= d.st('moon') < 360, d.st('moon')   # 272 + 100 is 12
    for _ in range(4): d.pg.keyboard.press('Shift+a')
    assert 0 <= d.st('moon') < 360, d.st('moon')   # 12 - 40 is 332
    settled(d.pg); b = grip(d).bounding_box(); x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    sb = d.pg.locator('.rk-scene .stage').bounding_box(); cx, cy = sb['x'] + sb['width'] / 2, sb['y'] + sb['height'] / 2
    r = ((x - cx) ** 2 + (y - cy) ** 2) ** .5
    a0 = math.atan2(y - cy, x - cx)
    d.pg.mouse.move(x, y); d.pg.mouse.down()
    seen = []
    for i in range(1, 41):
        a = a0 + i / 40 * 2.2 * math.pi; d.pg.mouse.move(cx + r * math.cos(a), cy + r * math.sin(a)); seen.append(d.st('moon'))
    d.pg.mouse.up()
    assert all(0 <= v < 360 for v in seen) and len(set(seen)) > 10 and not d.errors, seen

def test_grip_covers_the_disc_of_its_body(draw):
    "A press inside the disc of a large body, off its centre, takes the grip and moves the body."
    d = draw(world(body('p', 'sphere', [1], orbit=3, angle='a', drag='orbit', to='a'))); settled(d.pg)
    b = d.pg.locator('.rk-grip').bounding_box(); x, y = b['x'] + b['width'] / 2 + 25, b['y'] + b['height'] / 2
    d.pg.mouse.move(x, y); d.pg.mouse.down(); d.pg.mouse.move(x, y - 60, steps=6); d.pg.mouse.up()
    assert d.st('a') != 0 and not d.errors

def test_drag_snaps_to_the_nudge(draw):
    "A drag stops on a whole number of nudges, so the value the learner reads matches the step of the keys."
    for b, key in ((body('p', 'sphere', [1], orbit=3, angle='a', drag='orbit', to='a', nudge=15), 'a'),
                   (body('p', 'sphere', [1], at=['a', 0, 0], drag='x', to='a', range=[-4, 4], nudge=0.5), 'a')):
        d = draw(world(b)); settled(d.pg)
        g = d.pg.locator('.rk-grip').bounding_box(); x, y = g['x'] + g['width'] / 2, g['y'] + g['height'] / 2
        d.pg.mouse.move(x, y); d.pg.mouse.down(); d.pg.mouse.move(x + 37, y - 23, steps=5); d.pg.mouse.up()
        v, n = d.st(key), b['nudge']
        assert v != 0 and abs(v / n - round(v / n)) < 1e-9 and not d.errors, v

def test_locked_grip_says_why(draw):
    "A press or a key on a locked grip shows a short note by the grip, and the state stays."
    d = draw(SKY); settled(d.pg)
    note = d.pg.locator('.rk-scene .rk-gripnote').nth(1)   # the note of the Moon
    b = grip(d).bounding_box(); x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    d.pg.mouse.move(x, y); d.pg.mouse.down(); d.pg.mouse.move(x + 40, y, steps=4); d.pg.mouse.up()
    assert note.is_visible() and note.inner_text() == 'Lock in your prediction first.' and d.st('moon') == 272
    d.pg.wait_for_timeout(2600); assert not note.is_visible()
    grip(d).focus(); d.pg.keyboard.press('d')
    assert note.is_visible() and d.st('moon') == 272 and not d.errors

def test_panchangam_days_move_the_sun_and_the_moon(draw):
    "One day moves the Moon about 13 degrees and the Sun about 1 degree, so the Moon gains about 12 degrees: one tithi."
    d = draw(gallery()['panchangam-sky']); settled(d.pg); d.lock(); settled(d.pg)
    t0, s0, m0 = d.st('tithi'), d.st('sunAt'), d.st('moonAt')
    put(d, days=1)
    assert abs(d.st('sunAt') - s0 - 0.9856) < 1e-6 and abs(d.st('moonAt') - m0 - 13.176) < 1e-6
    assert d.st('tithi') == t0 + 1 and not d.errors

def test_panchangam_names_the_new_moon_and_counts_from_one(draw):
    "Tithi 30 is Amavasya, and the nakshatra number counts from 1, as the names do."
    d = draw(gallery()['panchangam-sky']); settled(d.pg)
    put(d, sun=0, moon=355)
    assert d.st('tithi') == 30 and d.st('tn')['name'] == 'Amavasya' and d.st('nakNo') == 27
    put(d, sun=0, moon=174)
    assert d.st('tithi') == 15 and d.st('tn')['name'] == 'Purnima' and d.st('pa')['name'].startswith('Shukla') and not d.errors
