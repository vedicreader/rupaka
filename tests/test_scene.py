"The scene blocks in a headless browser: the view draws, the steps build, the chips never overlap, three.js loads only for a scene, and an explainer draws with no gate."
import json
import pytest
from rupaka.spec import examples, validate
from rupaka.check import check
from rupaka.render import page, bundle, three_js, THREE

EX = examples()
F35 = EX['scene']
HOST = 'http://rk.test/rupaka/'

def stage(d): return d.pg.locator('.rk-scene .stage')

def settled(pg):
    "Wait for two frames, then for the scene to rest (no move and no growth)."
    pg.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    pg.wait_for_function("[...document.querySelectorAll('.rk-scene .stage')].every(s => s.dataset.rkGl === 'ready' && s.dataset.rkStill === '1')", timeout=10000)

def drawn(pg) -> dict:
    "Read the canvas in the page: the share of pixels that differ from the page colour, and the count of distinct colours."
    return pg.evaluate("""() => { const c = document.querySelector('.rk-scene canvas.gl'), w = c.width, h = c.height;
      const x = Object.assign(document.createElement('canvas'), {width: w, height: h}).getContext('2d');
      x.drawImage(c, 0, 0); const px = x.getImageData(0, 0, w, h).data, bg = Rupaka.rgb(c, '--rk-bg'), seen = new Set(); let n = 0;
      for (let i = 0; i < px.length; i += 16) { const d = Math.abs(px[i] - bg[0]) + Math.abs(px[i + 1] - bg[1]) + Math.abs(px[i + 2] - bg[2]);
        if (d > 30) n++; seen.add(px[i] >> 4 << 8 | px[i + 1] >> 4 << 4 | px[i + 2] >> 4); }
      return {share: n / (px.length / 16), colours: seen.size}; }""")

def chips(pg) -> list:
    "The boxes of the chips that show, and the box of the view."
    return pg.evaluate("""() => { const s = document.querySelector('.rk-scene .stage').getBoundingClientRect();
      return [...document.querySelectorAll('.rk-scene .rk-chip:not(.off)')].filter(c => !c.hidden).map(c => { const r = c.getBoundingClientRect();
        return {text: c.textContent, x: r.x, y: r.y, w: r.width, h: r.height, inside: r.x >= s.x && r.y >= s.y && r.right <= s.right && r.bottom <= s.bottom}; }); }""")

def overlaps(cs):
    return [(a['text'], b['text']) for i, a in enumerate(cs) for b in cs[i + 1:]
            if a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']]

def step(d, n):
    d.pg.evaluate(f"Rupaka.set(document.querySelector('[data-rupaka]'), {{step: {n}}})"); settled(d.pg)

# drawing

@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_scene_draws(draw, mode):
    d = draw(F35, mode=mode); settled(d.pg)
    r = drawn(d.pg)
    assert r['share'] > .05 and r['colours'] > 12, r
    assert d.pg.evaluate('RupakaTHREE.REVISION') == THREE.version.split('.')[1] and d.errors == []

def test_steps_build_and_chips_never_overlap(draw):
    d = draw(F35); settled(d.pg)
    host = "document.querySelector('[data-rupaka]')"
    assert d.pg.evaluate(f"Rupaka.settle({host}, 'hover', 3900)")
    seen = []
    for n in range(1, 7):
        step(d, n)
        cs = chips(d.pg)
        assert overlaps(cs) == [] and all(c['inside'] for c in cs), (n, cs)
        assert d.pg.locator('.rk-scene .say').inner_text() == F35['blocks'][0]['steps'][n - 1]
        seen.append((stage(d).get_attribute('data-rk-shot'), len(cs)))
    assert [s for s, _ in seen] == ['wide', 'close:fan', 'side', 'side', 'front', 'wide']
    assert [k for _, k in seen] == [1, 2, 3, 4, 5, 6] and d.errors == []   # each step adds one chip, and each chip finds a free place

def test_think_rule_hides_the_posts_until_the_gate(draw):
    d = draw(F35); settled(d.pg); step(d, 6)
    texts = [c['text'] for c in chips(d.pg)]
    assert not any('roll posts' in t or 'lbf up' in t for t in texts), texts
    d.lock(2); settled(d.pg)
    assert any(t == 'roll posts, 3900 lbf in all' for t in (c['text'] for c in chips(d.pg)))

def test_keys_step_and_turn(draw):
    d = draw(F35); settled(d.pg)
    stage(d).focus()
    d.pg.keyboard.press('d'); settled(d.pg)
    assert d.st('step') == 2 and stage(d).get_attribute('data-rk-shot') == 'close:fan'
    d.pg.keyboard.press('a'); d.pg.keyboard.press('4'); settled(d.pg)
    assert d.st('step') == 4
    before = d.pg.evaluate("document.querySelector('.rk-scene canvas.gl').toDataURL().length")
    d.pg.keyboard.press('e'); settled(d.pg)
    assert d.pg.evaluate("document.querySelector('.rk-scene canvas.gl').toDataURL().length") != before
    assert d.pg.locator('.rk-scene .bar .count').inner_text() == 'Step 4 of 6' and d.errors == []

def test_reduced_motion_cuts(br):
    pg = br.new_page(viewport=dict(width=720, height=900), reduced_motion='reduce')
    try:
        pg.set_content(page(F35, fonts='none')); settled(pg)
        pg.evaluate("Rupaka.set(document.querySelector('[data-rupaka]'), {step: 2})")
        pg.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        s = pg.locator('.rk-scene .stage')
        assert s.get_attribute('data-rk-still') == '1' and s.get_attribute('data-rk-shot') == 'close:fan'
    finally: pg.close()

# an explainer: the F-35 scene with no gate

def explainer(spec):
    "A copy of `spec` with mode learn, no gate, and no block that waits for a gate."
    def strip(bs): return [{**{k: v for k, v in b.items() if k != 'after'}, **({'blocks': strip(b['blocks'])} if 'blocks' in b else {})}
                           for b in bs if b['type'] != 'gate']
    return {**spec, 'mode': 'learn', 'ask': 'Step through the scene with D.', 'blocks': strip(spec['blocks'])}

LEARN = explainer(F35)

def test_explainer_needs_the_mode():
    assert validate(LEARN) == []
    assert validate({k: v for k, v in LEARN.items() if k != 'mode'}) == ['blocks: needs at least one gate: the learner predicts first']
    assert validate({**LEARN, 'mode': 'learning'}) == ['mode: "learning" is not a mode; use predict or learn']

def test_explainer_passes_check(br):
    r = check(LEARN, b=br)
    assert r.errors == [] and r.info['light'] == [] and r.shots == []

def test_explainer_shows_its_label_and_every_part(draw):
    d = draw(LEARN); settled(d.pg)
    assert d.pg.evaluate("[document.querySelector('.rk-mode').textContent, document.querySelector('.rk').dataset.rkMode]") == ['Explainer', 'learn']
    assert d.pg.locator('.rk-gate').count() == 0
    step(d, 6)
    assert 'roll posts, 3900 lbf in all' in [c['text'] for c in chips(d.pg)] and d.errors == []
    d = draw(F35)
    assert d.pg.locator('.rk-mode').count() == 0 and d.pg.evaluate("document.querySelector('.rk').dataset.rkMode") is None

# the host API: the board's cam operation

def test_cam_sets_the_bound_shot(draw):
    d = draw(F35); settled(d.pg)
    host = "document.querySelector('[data-rupaka]')"
    assert d.pg.evaluate(f"Rupaka.cam({host}, 'top')") is True; settled(d.pg)
    assert d.st('cam') == 'top' and stage(d).get_attribute('data-rk-shot') == 'top'
    assert d.pg.evaluate(f"Rupaka.cam({host}, 'close:nose')") is True; settled(d.pg)
    assert stage(d).get_attribute('data-rk-shot') == 'close:nose'
    assert d.pg.evaluate(f"[Rupaka.cam({host}, 'zoom'), Rupaka.cam({host}, 'close:wingtip')]") == [False, False]
    assert d.st('cam') == 'close:nose' and d.errors == []

def test_cam_on_a_scene_with_no_bound_shot_gives_false(draw):
    d = draw(EX['force']); settled(d.pg)
    assert d.pg.evaluate("Rupaka.cam(document.querySelector('[data-rupaka]'), 'top')") is False

# bad specs

def test_bad_body_kind_is_refused_at_runtime(draw):
    bad = json.loads(json.dumps(EX['body'])); bad['blocks'][1]['blocks'][1]['kind'] = 'pyramid'
    d = draw(None, html=page(bad, fonts='none'))
    assert '"pyramid" is not a body kind' in d.pg.locator('.rk-err').inner_text()

def test_part_outside_a_scene_is_refused_at_runtime(draw):
    d = draw(None, html=page(dict(rupaka=1, id='x', state={}, blocks=[dict(type='force', dir=[0, 1, 0], mag=1)]), fonts='none'))
    assert 'a force must be inside a scene' in d.pg.locator('.rk-err').inner_text()

# the lazy load

def served(br, spec):
    "A page on a host that serves rupaka.js and three.js beside it. It gives the page and the list of requests."
    pg, reqs = br.new_page(), []
    pg.on('request', lambda r: reqs.append(r.url))
    html = (f'<html><head><style>{bundle("css")}</style></head><body><div data-rupaka><script type="application/json">{json.dumps(spec)}</script></div>'
            f'<script src="{HOST}rupaka.js?v=1"></script></body></html>')
    pg.route(f'{HOST}rupaka.js?v=1', lambda r: r.fulfill(body=bundle(), content_type='text/javascript'))
    pg.route(f'{HOST}three.js?v=1', lambda r: r.fulfill(body=three_js(), content_type='text/javascript'))
    pg.route('http://rk.test/', lambda r: r.fulfill(body=html, content_type='text/html'))
    pg.goto('http://rk.test/'); pg.wait_for_selector('[data-rk-ready]', state='attached')
    return pg, reqs

def test_host_loads_three_only_for_a_scene(br):
    pg, reqs = served(br, EX['gate'])
    try:
        pg.wait_for_timeout(300)
        assert pg.evaluate('[typeof RupakaTHREE, Rupaka.base]') == ['undefined', HOST]
        assert [u for u in reqs if 'three' in u] == [] and pg.locator('script[src*="three"]').count() == 0
    finally: pg.close()
    pg, reqs = served(br, F35)
    try:
        settled(pg)
        assert [u for u in reqs if 'three' in u] == [f'{HOST}three.js?v=1']
        assert drawn(pg)['share'] > .05
    finally: pg.close()

def test_page_holds_three_only_for_a_scene(draw):
    d = draw(EX['gate'])
    assert d.pg.evaluate('typeof RupakaTHREE') == 'undefined' and 'window.RupakaTHREE=' not in page(EX['gate'])
    d = draw(F35); settled(d.pg)
    assert d.pg.evaluate('typeof RupakaTHREE.WebGLRenderer') == 'function' and d.errors == []

def test_a_removed_scene_lets_go_of_its_view(draw):
    d = draw(F35); settled(d.pg)
    d.pg.evaluate("document.querySelector('[data-rupaka]').remove(); document.documentElement.classList.add('rk-theme-test')")
    d.pg.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    assert d.errors == []
