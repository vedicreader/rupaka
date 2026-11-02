"The board of the screen guide (static/board.js): the vendored pen libraries, the rules that keep model text out of the page code, and its marks and side panel in headless Chromium."
import hashlib, re, pytest
from rupaka.board import assets, bundle, LIBS
from rupaka.render import font_css, STATIC

PINNED = {'rough.js': '6853af8619532f3939b156cd16824d2e14f31e71d3df306ad5558eeafacab194',              # roughjs 4.6.6, bundled/rough.js
          'perfect-freehand.mjs': '0ddf0e44c727ab39d7211af95685bf12234236f0e2eca376091e5791a71626e4'}  # perfect-freehand 1.2.2, dist/esm/index.mjs

def test_vendored_pens_are_pinned():
    assert set(PINNED) == set(LIBS)
    for name, h in PINNED.items(): assert hashlib.sha256((assets().libs/name).read_bytes()).hexdigest() == h, name

def test_licences_are_kept():
    t = (assets().libs/'LICENSES.md').read_text()
    for s in ('Rough.js 4.6.6', 'Preet Shihn', 'perfect-freehand 1.2.2', 'Stephen Ruiz', 'MIT License'): assert s in t, s

def test_model_text_goes_in_as_text():
    "board.js never writes HTML: each say, label, quote and title goes in with textContent, and a link is http(s) or a local path."
    js = (STATIC/'board.js').read_text()
    assert 'innerHTML' not in js and 'insertAdjacentHTML' not in js and 'outerHTML' not in js and 'eval(' not in js
    assert 'textContent' in js and "noopener" in js and r"/^(https?:\/\/|\/(?!\/))/" in js

def test_the_panel_is_on_the_paper_of_the_demos():
    "The side panel takes the paper tokens that the paper theme of a demo takes: one look."
    css, paper = (STATIC/'board.css').read_text(), (STATIC/'rupaka.css').read_text()
    for k in ('paper', 'paper-ink', 'paper-mute', 'paper-line', 'paper-in', 'paper-out', 'hand'): assert f'var(--rk-{k})' in css and f'var(--rk-{k})' in paper, k
    assert not re.search(r'--paper[\w-]*:\s*#', css)   # no colour of its own

# --- in the browser ---------------------------------------------------------------------------------------------------------
HOST = 'http://rk.test'
PAGE = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{font_css(base='/fonts/')}</style>
<style>body {{ margin: 0; font: 17px/1.5 Georgia, serif; }} body > nav {{ position: sticky; top: 0; height: 56px; background: #eee; z-index: 50; }}
main {{ max-width: 720px; margin: 24px auto; padding: 0 24px; box-sizing: border-box; }}</style>
<link rel="stylesheet" href="/board.css"></head><body><nav>Top bar</nav><main><h1>A page</h1><p>Some words of the page.</p></main>
<script src="/board.js"></script></body></html>"""
FILES = {'/': (PAGE, 'text/html'), '/board.js': (bundle('js'), 'text/javascript'), '/board.css': (bundle('css'), 'text/css'),
         **{f'/vendor/{n}': ((assets().libs/n).read_text(), 'text/javascript') for n in LIBS},
         **{f'/fonts/{p.name}': (p.read_bytes(), 'font/woff2') for p in (STATIC/'fonts').glob('*.woff2')}}

def _serve(route):
    "The files of the test page; any other request fails, so the board needs no network."
    url = route.request.url
    path = url[len(HOST):].split('?')[0] if url.startswith(HOST) else None
    if path not in FILES: return route.abort()
    body, mime = FILES[path]
    route.fulfill(status=200, content_type=mime, body=body)

CARD = """() => document.body.insertAdjacentHTML('beforeend', `
  <pre data-guide-id="out" style="position:absolute;left:40px;top:300px;width:420px;margin:0">when input is tensor([18]) the target: 47
when input is tensor([18, 47]) the target: 56</pre>
  <div data-guide-id="card" style="position:absolute;left:40px;top:420px;width:420px;height:160px"><p style="margin:0">Open in Leela</p></div>`)"""

@pytest.fixture
def page(br):
    "One headless page with the board, the output of a cell (`out`) and a card with one line of text at its top (`card`)."
    pg = br.new_page(viewport=dict(width=1200, height=800), reduced_motion='reduce')
    try:
        pg.route('**/*', _serve)
        pg.goto(HOST + '/'); pg.wait_for_function('window.rupakaBoard')
        pg.evaluate(CARD)
        yield pg
    finally: pg.close()

def play(pg, steps, streaming=False, **kw):
    pg.evaluate("([ss, streaming, kw]) => rupakaBoard.play({steps: ss, tier: 'tutor', sources: [], streaming}, {quiet: true, auto: false, ...kw})", [steps, streaming, kw])
    pg.wait_for_function('rupakaBoard.state && rupakaBoard.state.done', timeout=5000)

STEP = lambda say, at: dict(say=say, strokes=[dict(op='box', at=at)])

def test_the_old_names_are_the_same_objects(page):
    assert page.evaluate('window.abhyasaBoard === window.rupakaBoard && window.abhyasaTex === window.rupakaTex && !!rupakaTex.texParts')

def test_a_streaming_board_takes_steps_as_they_come(page):
    "A board that starts with step 1 waits at it, goes on when add() gives step 2, and shows its end line only after finish()."
    pg = page
    pg.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<p data-guide-id="a">Alpha</p><p data-guide-id="b">Beta</p>')""")
    s1, s2 = STEP('One word.', 'a'), STEP('Two words.', 'b')
    assert pg.evaluate('s => rupakaBoard.add(s)', s2) is False   # no board shows
    pg.evaluate("s => rupakaBoard.play({steps: [s], tier: 'tutor', sources: [], streaming: true}, {quiet: true})", s1)
    pg.wait_for_function('rupakaBoard.state && rupakaBoard.state.done')
    pg.wait_for_timeout(1500)   # step 1 is said, and with no step 2 the board waits at it
    assert pg.evaluate('rupakaBoard.state') | {'first': 0} == dict(i=0, steps=1, tier='tutor', first=0, streaming=True, done=True)
    assert pg.evaluate("document.querySelector('#guide-strip .board-n').textContent") == 'Step 1'
    assert pg.evaluate("!document.querySelector('#guide-strip .board-end')")
    assert pg.evaluate('s => rupakaBoard.add(s)', s2) is True
    pg.wait_for_function('rupakaBoard.state.i === 1')   # it goes on at once
    assert pg.evaluate("rupakaBoard.finish({steps: [{say: 'Not the same.', strokes: []}], tier: 'tutor', sources: []})") is False
    assert pg.evaluate("ss => rupakaBoard.finish({steps: ss, tier: 'vault', sources: [], end: 'The end line.'})", [s1, s2]) is True
    st = pg.evaluate('rupakaBoard.state')
    assert (st['steps'], st['streaming'], st['tier']) == (2, False, 'vault')
    assert pg.evaluate("document.querySelector('#guide-strip .board-end').textContent") == 'The end line.'
    assert pg.evaluate("document.querySelector('#guide-strip .board-n').textContent") == 'Step 2 of 2'
    pg.evaluate("() => rupakaBoard.play({steps: [{say: 'Whole.', strokes: []}], tier: 'tutor', sources: []}, {quiet: true})")
    assert pg.evaluate('s => rupakaBoard.add(s)', s2) is False   # a whole board takes no steps

def test_reduced_motion_draws_a_point_with_no_pulse(page):
    "With reduced motion, a point mark shows its dot at once: no pulse and no running animation on the board."
    page.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<div data-guide-id="t" style="position:absolute;left:420px;top:260px;width:90px;height:28px"></div>')""")
    page.evaluate("() => rupakaBoard.play({steps: [{say: 'Look here now.', strokes: [{op: 'point', at: 't'}]}], tier: 'tutor', sources: []}, {quiet: true, auto: false, point: 'dot'})")
    page.wait_for_function("document.querySelector('#board-layer circle.board-dot')", timeout=5000)
    for _ in range(4):   # look a few times while the step plays
        assert page.evaluate("document.querySelectorAll('.board-pulse').length") == 0
        assert page.evaluate("document.getAnimations().filter(a => a.playState === 'running' && a.effect?.target?.closest?.('#board-layer')).length") == 0
        page.wait_for_timeout(100)

def test_a_mark_with_no_thing_under_it_is_not_drawn(page):
    "A box on a bare point, or on the empty lower part of the card, draws nothing. A box on the words of the card draws its glow."
    glows = "[...document.querySelectorAll('.board-glow')].filter(g => g.style.display !== 'none').length"
    play(page, [dict(say='Look here.', strokes=[dict(op='box', at=dict(a='card', pt=[-200, 900]))])])
    assert page.evaluate(glows) == 0
    play(page, [dict(say='Look here.', strokes=[dict(op='box', at=dict(a='card', box=[0, 500, 1000, 1000])), dict(op='circle', at=dict(a='card', box=[0, 500, 1000, 1000]))])])
    assert page.evaluate(glows) == 0 and page.evaluate("[...document.querySelectorAll('#board-layer g[data-op=circle]')].every(g => g.style.display === 'none')")
    play(page, [dict(say='Look here.', strokes=[dict(op='box', at=dict(a='card', box=[0, 0, 1000, 200]))])])
    assert page.evaluate(glows) == 1

def row(cells, to, text=None, **kw): return dict(op='row', cells=cells, to=to, **({'at': dict(a='out', text=text)} if text else {}), **kw)

def panel(pg):
    "The side panel as text: its title, heading, column names, and the cells of each row that shows."
    return pg.evaluate("""() => { const p = document.getElementById('board-panel'); if (!p) return null;
        const t = s => (p.querySelector(s) || {}).textContent || '';
        return {title: t('.board-panel-title'), head: t('.board-panel-head'), cols: [...p.querySelectorAll('.board-panel-cols span')].map(s => s.textContent),
                rows: [...p.querySelectorAll('.board-row, .board-panel-note')].filter(r => r.style.display !== 'none').map(r => r.textContent)}; }""")

def test_the_side_panel_builds_one_row_in_each_step(page):
    """The panel is at the top right. Each step that comes adds its row, and the rows before stay. A row with `at` has a curve from the
    words on the page to its first cell. A new panel line starts a new beat with its own rows; back to an older step shows its beat again."""
    s1 = dict(say='Each line makes one question.', strokes=[dict(op='panel', title='tensors and targets', head='Make a question and its answer', cols=['Input', 'Target']),
                                                           dict(op='circle', at=dict(a='out', text='tensor([18])')), row(['[18]'], '47', 'tensor([18])')])
    s2 = dict(say='The next one adds a token.', strokes=[row(['[18, 47]'], '56', 'tensor([18, 47])')])
    s3 = dict(say='The model guesses, compares and adjusts.', strokes=[row(['Guess', 'Compare', 'Adjust'], None, chain=True), dict(op='note', text='This code prepares the examples.')])
    s4 = dict(say='Then think big.', strokes=[dict(op='panel', title='from this to chatgpt', head='One small task, enormous practice', numbered=True), row(['The', 'sky', 'is'], 'blue')])
    s3['strokes'][0].pop('to')
    play(page, [s1], streaming=True)
    p = panel(page)
    assert (p['title'], p['head'], p['cols'], p['rows']) == ('tensors and targets', 'Make a question and its answer', ['Input', 'Target'], ['[18]⟶47'])
    r = page.evaluate("(() => { const b = document.getElementById('board-panel').getBoundingClientRect(); return [b.right, b.top]; })()")
    assert r[0] > 1150 and r[1] < 100   # the top right of the window
    assert page.evaluate("document.querySelectorAll('#board-layer g[data-op=link] path').length") >= 2   # the curve and its head
    for s, want in ((s2, ['[18]⟶47', '[18, 47]⟶56']), (s3, ['[18]⟶47', '[18, 47]⟶56', 'Guess→Compare→Adjust', 'This code prepares the examples.'])):
        page.evaluate('s => rupakaBoard.add(s)', s); page.evaluate('rupakaBoard.next()')
        page.wait_for_function('rupakaBoard.state.done')
        assert panel(page)['rows'] == want
    page.evaluate('s => rupakaBoard.add(s)', s4); page.evaluate('rupakaBoard.next()'); page.wait_for_function('rupakaBoard.state.done')
    p = panel(page)
    assert (p['title'], p['rows']) == ('from this to chatgpt', ['1Theskyis⟶blue'])
    page.evaluate('rupakaBoard.back()'); page.wait_for_function('rupakaBoard.state.done')
    assert panel(page)['title'] == 'tensors and targets' and len(panel(page)['rows']) == 4
    page.evaluate('rupakaBoard.stop()')
    assert panel(page) is None

def test_a_row_with_at_draws_its_own_circle_in_a_fixed_order(page):
    """A row with `at` and no circle line: the board draws one circle and one curve for it. The circle starts at once, the curve 120 ms
    later, the row when the curve lands, then each cell 80 ms after the one before."""
    play(page, [dict(say='The first question.', strokes=[dict(op='panel', head='Make a question'), row(['[18]'], '47', 'tensor([18])')])])
    assert page.evaluate("[...document.querySelectorAll('#board-layer g[data-op=circle][data-step=\"0\"]')].length") == 1
    assert page.evaluate("[...document.querySelectorAll('#board-layer g[data-op=link][data-step=\"0\"]')].length") == 1
    t = [x for x in page.evaluate('rupakaBoard.timeline()') if x[0] == 'row']
    pen, dash, cells = t[0], [x for x in t if x[1] == 'dash'][0], [x[2] for x in t if x[1] == 'node']
    assert (pen[1], pen[2], dash[2]) == ('pen', 0, 120)
    land = max(x[2] for x in t if x[1] in ('dash', 'head'))
    assert cells[0] >= land - 60 and all(b - a == 80 for a, b in zip(cells, cells[1:])) and len(cells) == 3   # the cell, the arrow, the answer

def test_d_next_keeps_the_panel(page):
    "D next keeps the same panel node and its rows, and adds the row of the new step."
    s1 = dict(say='One.', strokes=[dict(op='panel', head='Make a question'), row(['[18]'], '47', 'tensor([18])')])
    s2 = dict(say='Two.', strokes=[row(['[18, 47]'], '56', 'tensor([18, 47])')])
    play(page, [s1, s2])
    page.evaluate("document.getElementById('board-panel').dataset.tag = 'kept'; document.querySelector('.board-row').dataset.tag = 'kept'")
    page.evaluate('rupakaBoard.next()'); page.wait_for_function('rupakaBoard.state.i === 1 && rupakaBoard.state.done')
    assert page.evaluate("document.getElementById('board-panel').dataset.tag") == 'kept' and page.evaluate("document.querySelector('.board-row').dataset.tag") == 'kept'
    assert len(panel(page)['rows']) == 2

def test_the_board_scrolls_its_first_mark_into_view(page):
    "A step whose mark is far down the page scrolls it into view first: the mark is under the top bar and above the strip."
    page.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<p data-guide-id="far" style="position:absolute;left:40px;top:2400px;margin:0">Far down the page</p><div style="height:3200px"></div>')""")
    play(page, [dict(say='Look here.', strokes=[dict(op='box', at='far')])])
    page.wait_for_timeout(200)
    r = page.evaluate("(() => { const g = document.querySelector('.board-glow').getBoundingClientRect(), s = document.getElementById('guide-strip'); return [g.top, g.bottom, innerHeight - (s && !s.hidden ? s.offsetHeight : 0)]; })()")
    assert 64 <= r[0] and r[1] <= r[2], r

def test_a_box_on_words_stays_inside_its_line(page):
    "A box on words has at most a quarter line of pad above them, so it does not cover the line above."
    play(page, [dict(say='Look here.', strokes=[dict(op='box', at=dict(a='out', text='tensor([18, 47])'))])])
    g, b = page.evaluate("[parseFloat(document.querySelector('.board-glow').style.top), rupakaBoard.boxOf({a: 'out', text: 'tensor([18, 47])'})]")
    assert g >= b['y'] - .25 * b['h'] - .5, (g, b)

LONG = """() => { const m = document.querySelector('main'); const p = document.createElement('pre'); p.dataset.guideId = 'm'; p.style.whiteSpace = 'pre-wrap';
  p.textContent = 'x = tensor([18, 47, 56]) and more text to the right edge of the column ' + 'y'.repeat(60); m.prepend(p); }"""
PANEL_STEP = dict(say='The values.', strokes=[dict(op='panel', title='tensors and targets', head='Make a question'), dict(op='row', cells=['[18]'], to='47', at=dict(a='m', text='tensor([18, 47, 56])'))])

def test_the_panel_covers_no_text_and_no_mark_at_1400(page):
    "At 1400 by 900 the page column moves left while the panel shows: the panel covers no text of main and no mark. The panel is on paper, in the hand font."
    page.set_viewport_size(dict(width=1400, height=900))
    page.evaluate(LONG)
    play(page, [PANEL_STEP])
    page.wait_for_timeout(400)   # the column moves
    p, m = [page.evaluate(f"(() => {{ const b = document.querySelector('{q}').getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; }})()") for q in ('#board-panel', 'main')]
    assert m[2] <= p[0], (m, p)
    marks = page.evaluate("[...document.querySelectorAll('#board-layer g[data-op=circle]')].map(g => { const b = g.getBoundingClientRect(); return [b.left, b.right]; })")
    assert marks and all(r <= p[0] for _, r in marks)
    assert page.evaluate("getComputedStyle(document.querySelector('.board-panel-head')).fontFamily").startswith('"Patrick Hand"')
    assert page.evaluate("document.fonts.ready.then(() => [...document.fonts].some(f => f.family.includes('Patrick Hand') && f.status === 'loaded'))")   # rupaka's file
    paper = page.evaluate("[getComputedStyle(document.getElementById('board-panel')).backgroundColor, (() => { const e = document.createElement('i'); e.style.color = 'var(--rk-paper)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; })()]")
    assert paper[0] == paper[1], paper   # the paper of the demos

def test_a_panel_is_whole_after_its_pop_in(page):
    "With motion on, a panel that a panel line opens ends at full opacity, with no transform: it never stays faint."
    page.emulate_media(reduced_motion='no-preference')
    page.evaluate(LONG)
    play(page, [PANEL_STEP])
    page.wait_for_timeout(1200)
    assert page.evaluate("getComputedStyle(document.getElementById('board-panel')).opacity") == '1'
    assert page.evaluate("document.getElementById('board-panel').style.transform") == ''

@pytest.mark.parametrize('w', [1280, 1400, 1728])
def test_the_column_moves_and_keeps_its_width(page, w):
    "While the panel shows, the page column moves left into the free gutter with its width kept, the panel covers it not, and the page does not jump."
    page.set_viewport_size(dict(width=w, height=900))
    page.evaluate(LONG)
    box = "(() => { const b = document.querySelector('main').getBoundingClientRect(); return [b.left, b.right, b.width]; })()"
    before = page.evaluate(box)
    play(page, [PANEL_STEP])
    page.wait_for_timeout(300)
    after, y0 = page.evaluate(box), page.evaluate('scrollY')
    pl = page.evaluate("document.getElementById('board-panel').getBoundingClientRect().left")
    assert after[2] == before[2] or w < 1400, (w, before, after)   # at 1280 the gutter can be too small: then it narrows only as much as it must
    assert after[1] <= pl - 23 and page.evaluate("document.body.classList.contains('has-panel')")
    page.wait_for_timeout(800)
    assert page.evaluate('scrollY') == y0
    ring = page.evaluate("(() => { const b = document.querySelector('#board-layer g[data-op=circle]').getBoundingClientRect(); return [b.top, b.bottom]; })()")
    assert 0 <= ring[0] and ring[1] <= 900
    page.evaluate('rupakaBoard.stop()')
    assert page.evaluate(box) == before   # the column takes its place back

def test_each_step_scrolls_its_marks_into_view(page):
    "Step 3 marks a line above the window: when step 3 starts, the page scrolls it into view."
    page.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<p data-guide-id="low" style="position:absolute;left:40px;top:2600px;margin:0">Low on the page</p><div style="height:3200px"></div>')""")
    steps = [dict(say='One.', strokes=[dict(op='box', at='low')]), dict(say='Two.', strokes=[dict(op='box', at='low')]), dict(say='Three.', strokes=[dict(op='box', at='card')])]
    play(page, steps)
    page.evaluate('rupakaBoard.next()'); page.wait_for_function('rupakaBoard.state.i === 1 && rupakaBoard.state.done')
    assert page.evaluate('scrollY') > 1500
    page.evaluate('rupakaBoard.next()'); page.wait_for_function('rupakaBoard.state.i === 2 && rupakaBoard.state.done')
    page.wait_for_timeout(200)
    r = page.evaluate("(() => { const g = [...document.querySelectorAll('.board-glow')].find(e => e.dataset.step === '2').getBoundingClientRect(); return [g.top, g.bottom, innerHeight]; })()")
    assert 50 <= r[0] and r[1] <= r[2], r

def test_an_inline_panel_draws_no_curve_back_up(page):
    "Below 1100 px the panel stands in the page under the marked line. A curve goes down from the ring, never back up across the text, and none when the row is right under the ring."
    page.set_viewport_size(dict(width=1024, height=900))
    page.evaluate(LONG)
    play(page, [PANEL_STEP])
    assert page.evaluate("document.getElementById('board-panel').classList.contains('inline')")
    ring = page.evaluate("document.querySelector('#board-layer g[data-op=circle]').getBoundingClientRect().bottom")
    links = page.evaluate("[...document.querySelectorAll('#board-layer g[data-op=link]')].filter(g => g.style.display !== 'none' && g.childElementCount).map(g => g.getBoundingClientRect().top)")
    assert all(t >= ring - 2 for t in links), (ring, links)

def test_at_1280_the_ring_is_above_the_strip(page):
    "At 1280 px, with motion on, the column makes room before the board scrolls: the ring of step 1 ends fully above the strip, and the page does not move after."
    page.set_viewport_size(dict(width=1280, height=900))
    page.emulate_media(reduced_motion='no-preference')
    page.evaluate("""() => document.querySelector('main').insertAdjacentHTML('beforeend', '<div style="height:1400px"></div><pre data-guide-id="m" style="white-space:pre-wrap">x = tensor([18, 47, 56]) and more words that wrap when the column gets narrow ' + 'y'.repeat(120) + '</pre><div style="height:1400px"></div>')""")
    play(page, [PANEL_STEP])
    page.wait_for_timeout(1500)
    y0 = page.evaluate('scrollY')
    r = page.evaluate("(() => { const g = document.querySelector('#board-layer g[data-op=circle]').getBoundingClientRect(), s = document.getElementById('guide-strip'); return [g.top, g.bottom, s.getBoundingClientRect().top]; })()")
    assert 0 <= r[0] and r[1] <= r[2], r
    page.wait_for_timeout(800)
    assert page.evaluate('scrollY') == y0

def test_a_step_that_comes_again_grows_in_place(page):
    "The server sends step 1 with its first mark, then again with its rows. The board keeps step 1 and adds only the new rows; then step 2 comes as a new step."
    s1 = dict(n=1, say='Each test is a question.', strokes=[dict(op='panel', head='Make a question')])
    play(page, [s1], streaming=True)
    assert panel(page)['rows'] == []
    page.evaluate('s => rupakaBoard.add(s)', {**s1, 'strokes': [*s1['strokes'], row(['[18]'], '47', 'tensor([18])')]})
    page.wait_for_function("document.querySelectorAll('.board-row').length === 1")
    page.evaluate('s => rupakaBoard.add(s)', {**s1, 'strokes': [*s1['strokes'], row(['[18]'], '47', 'tensor([18])'), row(['[18, 47]'], '56', 'tensor([18, 47])')]})
    page.wait_for_function("document.querySelectorAll('.board-row').length === 2")
    assert page.evaluate('rupakaBoard.state.steps') == 1
    page.evaluate('s => rupakaBoard.add(s)', dict(n=2, say='Then it adds up.', strokes=[]))
    assert page.evaluate('rupakaBoard.state.steps') == 2

def test_a_late_stroke_out_of_view_scrolls_in(page):
    "A row of step 1 that comes late, on a thing far down the page, scrolls that thing into view before its ring draws."
    page.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<pre data-guide-id="far" style="position:absolute;left:40px;top:2600px;margin:0">assert f(1.0) == 1.414</pre><div style="height:3200px"></div>')""")
    s1 = dict(n=1, say='Each test is a question.', strokes=[dict(op='box', at='card')])
    play(page, [s1], streaming=True)
    y0 = page.evaluate('scrollY')
    page.evaluate('s => rupakaBoard.add(s)', {**s1, 'strokes': [*s1['strokes'], dict(op='row', cells=['1.0'], to='1.414', at=dict(a='far', text='1.414'))]})
    page.wait_for_function("document.querySelector('#board-layer g[data-op=circle]')")
    page.wait_for_timeout(300)
    r = page.evaluate("(() => { const g = document.querySelector('#board-layer g[data-op=circle]').getBoundingClientRect(), s = document.getElementById('guide-strip'); return [g.top, g.bottom, s.getBoundingClientRect().top]; })()")
    assert page.evaluate('scrollY') > y0 and 0 <= r[0] and r[1] <= r[2], r

def test_column_heads_stand_over_their_cells(page):
    "With 2 and with 3 column names, the middle of each head is within 3 px of the middle of the cells of its column, in each row. A numbered panel too."
    centres = """() => { const mid = e => { const r = e.getBoundingClientRect(); return r.left + r.width / 2; };
        const p = document.getElementById('board-panel');
        return {heads: [...p.querySelectorAll('.board-panel-cols span')].map(mid),
                rows: [...p.querySelectorAll('.board-row')].filter(r => r.style.display !== 'none').map(r => [...r.querySelectorAll('.board-cell')].map(mid))}; }"""
    for cols, rows, numbered in ((['Input', 'Target'], [(['[18]'], '47'), (['[18, 47, 56]'], '57')], False),
                                 (['p', 't', '(p − t)²'], [(['0.9', '1'], '0.01'), (['0.25', '0.5'], '0.0625')], False),
                                 (['p', 't', '(p − t)²'], [(['0.9', '1'], '0.01'), (['0.25', '0.5'], '0.0625')], True),
                                 (['a', 'b', 'c'], [(['1', '2', '3'], None)], False)):
        play(page, [dict(say='Look.', strokes=[dict(op='panel', title='t', head='h', cols=cols, numbered=numbered), *[row(c, t) for c, t in rows]])])
        got = page.evaluate(centres)
        assert len(got['heads']) == len(cols) and got['rows']
        for cells in got['rows']:
            assert len(cells) == len(cols), cells
            for h, c in zip(got['heads'], cells): assert abs(h - c) <= 3, (cols, got)

def test_a_formula_part_gets_its_id(page):
    "texparts.js wraps each part of a formula with a letter in an id, and gives the parts as [tex, id]."
    marked, parts = page.evaluate(r"rupakaTex.texParts('\\bar\\alpha_t x', 1)")
    assert r'\htmlId{g-1-' in marked and [p[0] for p in parts] == [r'\bar\alpha_t', 'x'] and page.evaluate("rupakaTex.trust({command: '\\\\htmlId', id: 'g-1-0'})")

# --- the panel and its marks keep off the passage --------------------------------------------------------------------------
PASSAGE = """() => { const m = document.querySelector('main'); const p = document.createElement('p'); p.dataset.guideId = 'pass';
  p.textContent = 'A neuron takes numbers x1 to xn, multiplies each by a weight wi, adds a bias b, and outputs z = w1x1 + w2x2 + b. '
    + 'In Python this is a loop that sums the products, then adds one number. The output of one neuron is the input of the next one. '
    + 'Learning means a small change to each weight and to the bias.'; m.append(p); }"""
LINES = """root => { const out = [], r = document.createRange(), tw = document.createTreeWalker(document.querySelector(root), NodeFilter.SHOW_TEXT);
  for (let n; (n = tw.nextNode());) { if (!n.data.trim() || n.parentElement.closest('#board-panel, #board-host, #guide-strip')) continue; r.selectNodeContents(n);
    for (const q of r.getClientRects()) out.push([q.left + scrollX, q.top + scrollY, q.right + scrollX, q.bottom + scrollY]); }
  return out; }"""

def lines_of(pg, root='main'): return pg.evaluate(LINES, root)
def inside(p, q, m=1): return q[0] + m < p[0] < q[2] - m and q[1] + m < p[1] < q[3] - m
def overlap(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

def test_a_cell_with_maths_draws_maths(page):
    "A cell, a head and a note with `$…$` or a bare maths token draw their maths: no raw `_` shows. With no KaTeX, a script is a <sub>."
    play(page, [dict(say='Multiply each input by its weight.', strokes=[dict(op='panel', head='Inside $z$', cols=['Step', 'Result']),
        row(['Multiply each x_i by w_i'], '$w_1x_1, …, w_nx_n$'), dict(op='note', text='Sum with \\sum_i w_ix_i.')])])
    got = page.evaluate("""() => [...document.querySelectorAll('#board-panel .board-cell, #board-panel .board-panel-note, #board-panel .board-panel-head')]
        .map(e => ({text: e.textContent, tex: e.querySelectorAll('.board-tex').length, sub: e.querySelectorAll('sub').length}))""")
    assert len(got) == 4 and all(g['tex'] and '_' not in g['text'] and '$' not in g['text'] for g in got[1:]), got
    assert got[0]['tex'] == 1 and got[2]['sub'] >= 4 and '∑' in got[3]['text'], got   # the head, the answer cell and the note

def test_a_code_name_stays_text(page):
    "alpha_bar and x_train are code names, not maths: they stay as they are."
    play(page, [dict(say='Look.', strokes=[dict(op='panel', head='h'), row(['alpha_bar'], 'x_train')])])
    assert page.evaluate("[...document.querySelectorAll('#board-panel .board-cell')].map(e => [e.textContent, e.querySelectorAll('.board-tex').length])") == [['alpha_bar', 0], ['x_train', 0]]

def test_the_curve_to_the_panel_goes_around_the_text(page):
    "At 1440 px, the curve from a mark on line 2 of the passage to its row crosses no line of text after its start: it leaves through the gap above its line and goes along the edge of the column."
    page.set_viewport_size(dict(width=1440, height=900))
    page.evaluate(PASSAGE)
    play(page, [dict(say='It multiplies each input by its weight.', strokes=[dict(op='panel', head='Inside one neuron'), dict(op='row', cells=['Multiply x by w'], to='w1x1', at=dict(a='pass', text='w1x1'))])])
    page.wait_for_timeout(300)
    pts = page.evaluate("""() => { const p = document.querySelector('#board-layer g[data-op=link] path'), L = p.getTotalLength(), out = [];
        for (let s = 0; s <= L; s += 3) { const q = p.getPointAtLength(s); out.push([q.x, q.y, s]); } return out; }""")
    mark, text = page.evaluate("rupakaBoard.boxOf({a: 'pass', text: 'w1x1'})"), lines_of(page)
    assert len(pts) > 20
    bad = [p for p in pts if p[2] > 14 and any(inside(p, q) for q in text)]
    assert not bad, bad[:5]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    assert min(ys) < mark['y'] and max(xs) > max(q[2] for q in text)   # it goes up and out to the gutter, then to the panel

def test_a_label_covers_no_line_of_what_it_marks(page):
    "A label on words in the middle of the passage sits where it covers neither those words nor a line of the passage, with a leader to them."
    page.set_viewport_size(dict(width=1440, height=900))
    page.evaluate(PASSAGE)
    at = dict(a='pass', text='In Python this is a loop')
    play(page, [dict(say='In Python this is a loop.', strokes=[dict(op='label', at=at, text='a loop that sums', side='below')])])
    page.wait_for_timeout(300)
    rows = sorted({round(q[1]) for q in lines_of(page, '[data-guide-id=pass]')})
    assert len(rows) >= 4 and rows[0] < page.evaluate('a => rupakaBoard.boxOf(a).y', at) < rows[-2]   # the words are in a middle line: text is above and below them
    chip = page.evaluate("(() => { const b = document.querySelector('.board-label').getBoundingClientRect(); return [b.left + scrollX, b.top + scrollY, b.right + scrollX, b.bottom + scrollY]; })()")
    b = page.evaluate('a => rupakaBoard.boxOf(a)', at)
    assert not overlap(chip, [b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']])
    assert not any(overlap(chip, q) for q in lines_of(page, '[data-guide-id=pass]')), chip
    lead = page.evaluate("document.querySelector('#board-layer .board-lead path').getAttribute('d')")
    assert lead and lead.startswith('M')
