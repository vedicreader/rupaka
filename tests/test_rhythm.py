"The rhythm block: its spec checks, its schedule on the shared audio clock, Stop, and a real recording through ctx.asset."
import io, json, threading, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from copy import deepcopy
from pathlib import Path
import pytest
import rupaka.spec as S
from rupaka.render import show

REAL = S.PKG/'demos'/'media'
WEB = 'http://rk.test/m/'

def synth(**kw):
    "The mridangam-profile demo (synthesised voices) with one rhythm block after its gate."
    s = deepcopy(S.gallery()['mridangam-profile']); s['state'] = dict(beats=[])
    s['blocks'].append(dict(type='rhythm', after='support', profile='mridangam', pattern=['nam', 'tha', 'rest', 'tha'], beats='beats', **kw))
    return s

def errs(s): return list(S.validate(s))
def at(es, path): return [e for e in es if e.startswith(f'{path}:')]

# spec

def test_a_good_rhythm_passes():
    assert errs(synth()) == []
    assert errs(synth(tempo=120, count_in=0, turns=False, cycles=16, label='Round')) == []

@pytest.mark.parametrize('prop', ['profile', 'pattern'])
def test_profile_and_pattern_are_needed(prop):
    s = synth(); del s['blocks'][-1][prop]
    assert any(f'needs "{prop}"' in e for e in at(errs(s), 'blocks[3]')), errs(s)

def test_an_unknown_technique_or_profile_is_refused():
    s = synth(); s['blocks'][-1]['pattern'][1] = 'dhin'
    assert at(errs(s), 'blocks[3].pattern[1]'), errs(s)
    s = synth(); s['blocks'][-1]['profile'] = 'violin'
    assert at(errs(s), 'blocks[3].profile'), errs(s)
    s = synth(); s['blocks'][-1]['pattern'] = ['rest', 'rest']
    assert at(errs(s), 'blocks[3].pattern'), errs(s)

@pytest.mark.parametrize('prop,value', [('tempo', 10), ('tempo', 241), ('count_in', 9), ('cycles', 0), ('cycles', 17)])
def test_numbers_out_of_range_are_refused(prop, value):
    s = synth(**{prop: value})
    assert any('must be from' in e for e in at(errs(s), f'blocks[3].{prop}')), errs(s)

def test_beats_is_a_state_key():
    s = synth(); s['blocks'][-1]['beats'] = 'nope'
    assert at(errs(s), 'blocks[3].beats'), errs(s)

def test_a_hidden_technique_makes_the_round_wait():
    s = synth(); del s['blocks'][-1]['after']
    assert any(e.startswith('blocks[3]:') and 'gate "support"' in e for e in errs(s)), errs(s)

def test_manifest_catalog_skill_example_and_gallery():
    from rupaka.agent import catalog
    from rupaka.skill import skill_md
    assert '- rhythm:' in catalog() and '`rhythm`' in skill_md()
    ex = S.examples()['rhythm']
    assert errs(ex) == [] and ex == S.gallery()['mridangam-rhythm']
    voices = [t['voice']['kind'] for t in ex['profiles']['mridangam']['data']['techniques'].values()]
    assert set(voices) == {'strike'} and 'media' not in ex['profiles']['mridangam']['data']

# the shared clock

def test_the_shared_clock_line_is_byte_identical():
    js = (S.PKG/'static'/'rupaka.js').read_text()
    line = '    ctx.build = b => build(b, ctx);\n    ctx.audio = () => (window.__rkAudio ||= new (window.AudioContext || window.webkitAudioContext)());\n'
    assert line in js

def test_the_block_makes_no_network_request():
    js = (S.PKG/'blocks'/'rhythm'/'rhythm.js').read_text()
    assert not any(x in js for x in ('fetch(', 'XMLHttpRequest', 'innerHTML', 'eval(', 'setInterval('))

# scheduling, with a spy for the shared context. The clock runs 4 times faster than real time, so a round takes about 1.5 s.

SPY = r"""
window.spy = {starts: [], stops: [], decoded: 0, resumes: 0};
const T0 = performance.now();
class P { setValueAtTime() {} linearRampToValueAtTime() {} exponentialRampToValueAtTime() {} }
class N {
  constructor(kind) { this.kind = kind; this.frequency = new P(); this.detune = new P(); this.gain = new P(); this.buffer = null; this.id = spy.starts.length + ':' + Math.random(); }
  connect(n) { return n; } disconnect() {}
  start(t, off, dur) { spy.starts.push({id: this.id, kind: this.kind, t, sample: this.buffer?.sample ?? null}); }
  stop(t) { spy.stops.push({id: this.id, t: t === undefined ? null : t}); }
}
window.__rkAudio = {
  get currentTime() { return 5 + 4 * (performance.now() - T0) / 1000; }, sampleRate: 48000, state: 'suspended', destination: {},
  resume() { spy.resumes++; this.state = 'running'; return Promise.resolve(); },
  createOscillator() { return new N('osc'); }, createGain() { return new N('gain'); }, createBufferSource() { return new N('buf'); },
  createBuffer(c, n) { return {getChannelData: () => new Float32Array(n)}; },
  decodeAudioData(ab) { spy.decoded++; return Promise.resolve({duration: 0.4, sample: ab.byteLength}); },
};
"""

def real(**kw):
    "The mridangam-real demo, whose voices are recordings, with one rhythm block."
    s = deepcopy(S.gallery()['mridangam-real']); s['state'] = dict(beats=[])
    s['blocks'].append(dict(type='rhythm', after='nam', profile='mridangam', beats='beats', **kw))
    return s

def _page(br, h, spy=True):
    pg = br.new_page(viewport=dict(width=720, height=1400)); log = dict(errors=[], web=[])
    pg.on('console', lambda m: m.type == 'error' and log['errors'].append(m.text))
    pg.on('pageerror', lambda e: log['errors'].append(str(e)))
    pg.on('request', lambda r: r.url.split(':')[0] not in ('file', 'data', 'about') and log['web'].append(r.url))
    pg.set_content(('<script>' + SPY + '</script>' if spy else '') + h); pg.wait_for_selector('[data-rk-ready]', state='attached')
    return pg, log

HOST = "document.querySelector('[data-rupaka]')"

def _sizes():
    d = S.gallery()['mridangam-real']['profiles']['mridangam']['data']['media']
    return {k: (REAL/m['src'].removeprefix('asset:')).stat().st_size for k, m in d.items()}

def test_the_round_is_on_the_audio_clock(br):
    s = real(pattern=['tha', 'nam', 'tha', 'tha'], tempo=120, count_in=4, cycles=1)
    assert errs(s) == []
    pg, log = _page(br, show(s, assets=REAL)._repr_html_())
    try:
        r = pg.locator('.rk-rhythm'); go = r.locator('button', has_text='Start')
        assert go.is_disabled() and pg.evaluate('spy.starts.length') == 0
        pg.evaluate(f"Rupaka.settle({HOST}, 'nam', 'ringing')")
        assert go.is_enabled() and pg.evaluate('spy.starts.length') == 0       # nothing plays before Start
        go.click()
        pg.wait_for_function("document.querySelector('[data-rupaka]').rupaka.st.beats.length === 4", timeout=5000)
        pg.wait_for_function("[...document.querySelectorAll('.rk-rhythm button')].some(b => b.textContent.startsWith('Start'))", timeout=5000)
        sp, beats = pg.evaluate('spy'), pg.evaluate(f'{HOST}.rupaka.st.beats')
        clicks = sorted(x['t'] for x in sp['starts'] if x['kind'] == 'osc')
        t0 = clicks[0]; assert clicks == pytest.approx([t0 + i * .5 for i in range(4)], abs=.002)   # the count-in, and no click on my turn
        samples = [x for x in sp['starts'] if x['sample'] is not None]
        sz = _sizes()
        assert [x['sample'] for x in samples] == [sz['tha-1'], sz['nam-1'], sz['tha-1'], sz['tha-1']]
        for k, x in enumerate(samples): assert abs(x['t'] - (t0 + (4 + k) * .5)) <= .002, (k, x['t'], t0)
        assert [x for x in sp['starts'] if x['t'] >= t0 + 4 - .001] == []         # the silent cycle schedules no source
        assert beats == pytest.approx([t0 + (8 + k) * .5 for k in range(4)], abs=.002)
        assert sp['decoded'] == 2 and sp['resumes'] == 1
        assert log['errors'] == [] and log['web'] == []
    finally: pg.close()

def test_the_indicator_says_listen_then_your_turn(br):
    s = real(pattern=['tha', 'tha'], tempo=60, count_in=0, cycles=1)
    pg, log = _page(br, show(s, assets=REAL)._repr_html_())
    try:
        pg.evaluate(f"Rupaka.settle({HOST}, 'nam', 'ringing')")
        r = pg.locator('.rk-rhythm'); r.locator('button', has_text='Start').click()
        cue = r.locator('.rk-rhythm-cue')
        pg.wait_for_function("() => document.querySelector('.rk-rhythm-cue').textContent.startsWith('Listen')", timeout=3000)
        assert r.locator('.rk-rhythm-beat[aria-current="true"]').count() == 1
        pg.wait_for_function("() => document.querySelector('.rk-rhythm-cue').textContent.startsWith('Your turn')", timeout=3000)
        assert r.locator('.rk-rhythm-beat[aria-current="true"]').count() == 1
        assert log['errors'] == []
    finally: pg.close()

def test_stop_cancels_every_scheduled_source(br):
    s = real(pattern=['tha', 'nam', 'tha', 'nam'], tempo=60, count_in=2, cycles=4)
    pg, log = _page(br, show(s, assets=REAL)._repr_html_())
    try:
        pg.evaluate(f"Rupaka.settle({HOST}, 'nam', 'ringing')")
        r = pg.locator('.rk-rhythm'); r.locator('button', has_text='Start').click()
        pg.wait_for_function('spy.starts.some(x => x.sample !== null)', timeout=5000)
        r.locator('button', has_text='Stop').click()
        sp = pg.evaluate('spy'); started = {x['id'] for x in sp['starts']}
        cancelled = {x['id'] for x in sp['stops'] if x['t'] is None}
        assert started and started <= cancelled
        n = len(sp['starts']); pg.wait_for_timeout(300)
        assert len(pg.evaluate('spy.starts')) == n and r.locator('button', has_text='Start').count() == 1
        pg.evaluate(f"Rupaka.open({HOST}, 'nam')")
        assert r.locator('button', has_text='Start').is_disabled()
        assert log['errors'] == []
    finally: pg.close()

# a real recording through ctx.asset, on a real AudioContext

REC = """
window.rec = [];
const st = AudioBufferSourceNode.prototype.start;
AudioBufferSourceNode.prototype.start = function (...a) { rec.push({when: a[0], n: this.buffer ? this.buffer.length : 0, rate: this.buffer ? this.buffer.sampleRate : 0}); return st.apply(this, a); };
"""

def _frames(name):
    with wave.open(str(REAL/name)) as w: return w.getnframes(), w.getframerate()

def _play_tha(br, h, wait):
    "Draw `h` with a spy on AudioBufferSourceNode.start, click Start, and wait for `wait`. Give the starts, the requests to `WEB` and the status."
    pg = br.new_page(viewport=dict(width=720, height=1400)); asked = []
    pg.route(f'{WEB}**', lambda r: (asked.append(r.request.url), r.fulfill(body=(REAL/r.request.url.removeprefix(WEB)).read_bytes(), content_type='audio/wav')))
    try:
        pg.set_content('<script>' + REC + '</script>' + h); pg.wait_for_selector('[data-rk-ready]', state='attached')
        r = pg.locator('.rk-rhythm'); r.locator('button', has_text='Start').click()
        pg.wait_for_function(wait, timeout=5000)
        shots = Path(__file__).parent/'screens'; shots.mkdir(exist_ok=True); pg.screenshot(path=str(shots/'mridangam-rhythm-real.png'), full_page=True)
        return pg.evaluate('rec'), asked, r.inner_text()
    finally: pg.close()

def test_a_real_recording_plays_through_ctx_asset(br):
    s = real(pattern=['tha'], count_in=0, cycles=1, turns=False); del s['blocks'][-1]['after']
    assert errs(s) == []
    n, rate = _frames(s['profiles']['mridangam']['data']['media']['tha-1']['src'].removeprefix('asset:'))
    rec, asked, text = _play_tha(br, show(s, media=WEB, assets=REAL)._repr_html_(), 'rec.length > 0')     # assets inline, as data URIs
    assert len(rec) == 1 and asked == [] and rec[0]['when'] > 0
    assert rec[0]['n'] / rec[0]['rate'] == pytest.approx(n / rate, abs=.01)
    assert 'CC BY-NC 4.0' in text and 'Mridangam Stroke Dataset 1.5' in text

def test_a_media_base_on_another_origin_stays_silent_with_no_request(br):
    "A page from set_content has an opaque origin, so the media base at rk.test is another origin: ctx.buffer asks nothing."
    s = real(pattern=['tha'], count_in=0, cycles=1, turns=False); del s['blocks'][-1]['after']
    rec, asked, text = _play_tha(br, show(s, media=WEB)._repr_html_(), "document.querySelector('.rk-rhythm').innerText.includes('silent')")
    assert rec == [] and asked == [] and 'did not load' in text

# a served page: the media base on the same origin, and on another origin (a second local port)

def _server(pages):
    "A server on 127.0.0.1 that gives `pages` by path and the real WAV files under /m/. `seen` holds each path it was asked for."
    seen = []
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?')[0]; seen.append(path)
            f = REAL/path.removeprefix('/m/') if path.startswith('/m/') else None
            if f is not None and f.is_file(): body, mime = f.read_bytes(), 'audio/wav'
            elif path in pages: body, mime = pages[path].encode(), 'text/html; charset=utf-8'
            else: return self.send_error(404)
            self.send_response(200); self.send_header('Content-Type', mime); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}', seen, pages

@pytest.fixture
def two():
    "Two servers: `a` serves the page, `b` is another origin that also holds the media."
    a, b = _server({}), _server({})
    try: yield a, b
    finally:
        for srv, *_ in (a, b): srv.shutdown(); srv.server_close()

def _doc(s, media): return '<!doctype html><html><body>' + show(s, media=media)._repr_html_() + '</body></html>'   # no assets in the page

def _served_round(br, url, wait):
    pg = br.new_page(viewport=dict(width=720, height=1400)); web, errors = [], []
    pg.on('request', lambda r: web.append(r.url)); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(REC)
    try:
        pg.goto(url); pg.wait_for_selector('[data-rk-ready]', state='attached')
        r = pg.locator('.rk-rhythm'); r.locator('button', has_text='Start').click()
        pg.wait_for_function(wait, timeout=8000)
        return pg.evaluate('rec'), web, r.inner_text(), errors
    finally: pg.close()

def test_a_recording_from_the_same_origin_media_base_plays_once_fetched(br, two):
    (_, base, seen, pages), _ = two
    s = real(pattern=['tha', 'tha', 'rest', 'tha'], tempo=240, count_in=0, cycles=1, turns=False); del s['blocks'][-1]['after']
    assert errs(s) == []
    tha = s['profiles']['mridangam']['data']['media']['tha-1']['src'].removeprefix('asset:')
    n, rate = _frames(tha)
    pages['/'] = _doc(s, '/m/')
    rec, web, text, errors = _served_round(br, base + '/', 'rec.length >= 3')
    assert errors == [] and len(rec) == 3 and all(x['when'] > 0 for x in rec)
    assert all(x['n'] / x['rate'] == pytest.approx(n / rate, abs=.01) for x in rec)
    assert seen.count(f'/m/{tha}') == 1 and [u for u in web if u.endswith(tha)] == [f'{base}/m/{tha}']
    assert 'did not load' not in text

def test_a_media_base_on_another_port_is_another_origin_and_gets_no_request(br, two):
    (_, base, _, pages), (_, other, seen_b, _) = two
    s = real(pattern=['tha'], count_in=0, cycles=1, turns=False); del s['blocks'][-1]['after']
    pages['/'] = _doc(s, other + '/m/')
    rec, web, text, errors = _served_round(br, base + '/', "document.querySelector('.rk-rhythm').innerText.includes('silent')")
    assert errors == [] and rec == [] and seen_b == [] and not any(u.startswith(other) for u in web)
    assert 'did not load' in text
