"The listen block: its manifest, the matcher, the onset worklet, and the microphone path in Chromium with a fake input device."
import json, math, random, re, subprocess, sys, threading, wave
from array import array
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import pytest
from fastcore.xml import to_xml
from rupaka.render import Assets, Demo, bundle
from rupaka.spec import examples, validate

HERE = Path(__file__).parent
WAV = HERE/'listen_strikes.wav'
SR, PERIOD, LOOP, FIRST = 48000, 0.5, 2.0, 0.25   # a strike each half second; the fake device plays the file again and again

# --- the manifest ------------------------------------------------------------------------------------------------------------

GATE = {'type': 'gate', 'id': 'g', 'prompt': 'Do you play early, on the beat or late?', 'options': ['early', 'on the beat', 'late'],
        'answer': {'is': 'on the beat'}}

# The checker wants a rhythm block that writes the beats key of each listen. Nothing plays and nothing is written before Start,
# so the round does not change the tests that set the beats in state themselves.
PROFILES = examples()['rhythm']['profiles']
ROUND = {'type': 'rhythm', 'profile': 'mridangam', 'pattern': ['nam', 'tha', 'tha', 'nam'], 'beats': 'beats'}

def spec(**kw):
    b = {'type': 'listen', 'after': 'g', 'beats': ['beats'], 'out': ['verdicts'], **kw}
    return {'rupaka': 1, 'id': 'l', 'title': 'Listen', 'state': {'beats': [], 'verdicts': []}, 'profiles': PROFILES,
            'blocks': [GATE, {k: v for k, v in b.items() if v is not None}, {**ROUND, 'after': 'g'}]}

def test_a_listen_spec_passes_validate():
    assert validate(spec(tolerance=30, window=150, calibrate=True)) == []

def test_listen_needs_beats():
    errs = validate(spec(beats=None))
    assert any('needs "beats"' in e for e in errs), errs

def test_listen_keep_is_a_bool():
    assert validate(spec(keep=False)) == [] and validate(spec(keep=True)) == []
    assert any('keep' in e for e in validate(spec(keep='no'))), validate(spec(keep='no'))

def test_listen_tolerance_has_a_range():
    errs = validate(spec(tolerance=5))
    assert any('tolerance' in e and 'must be from 10 to 80' in e for e in errs), errs

NO_ROUND = 'blocks[1].beats: no rhythm block writes "beats"; add a rhythm block with "beats": "beats"'

def test_a_listen_with_no_rhythm_is_refused():
    s = spec(); s['blocks'] = [b for b in s['blocks'] if b['type'] != 'rhythm']; del s['profiles']
    assert validate(s) == [NO_ROUND]

def test_a_listen_with_a_rhythm_that_writes_its_key_passes():
    assert validate(spec()) == []

def test_a_listen_that_reads_another_key_than_the_rhythm_writes_is_refused():
    s = spec(); s['state']['other'] = []
    s['blocks'] = [{**b, 'beats': 'other'} if b['type'] == 'rhythm' else b for b in s['blocks']]
    assert validate(s) == [NO_ROUND]

# --- a local host: the bundle, three.js and listen-worklet.js at /rupaka/, as a FastHTML server serves them ---------------------

KINDS = {'rupaka.js': 'js', 'rupaka.css': 'css', 'three.js': 'three', 'listen-worklet.js': 'listen-worklet'}

class _Host(BaseHTTPRequestHandler):
    pages, seen = {}, []
    def do_GET(self):
        path = self.path.split('?')[0]; self.seen.append(self.path)
        try:
            if path.startswith('/rupaka/') and path[8:] in KINDS:
                k = KINDS[path[8:]]; body, mime = bundle(k), 'text/css' if k == 'css' else 'text/javascript'
            else: body, mime = self.pages.get(path), 'text/html'
        except Exception as e: return self.send_error(500, str(e)[:200])
        if body is None: return self.send_error(404)
        b = body.encode()
        self.send_response(200); self.send_header('Content-Type', f'{mime}; charset=utf-8'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

def html(s):
    css, js = Assets('/rupaka', v='1')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8">{to_xml(css)}</head><body>{to_xml(Demo(s))}{to_xml(js)}</body></html>'

LEARN = {'rupaka': 1, 'id': 'mic', 'mode': 'learn', 'title': 'Listen', 'state': {'beats': [], 'verdicts': []}, 'profiles': PROFILES,
         'blocks': [{'type': 'listen', 'beats': ['beats'], 'out': ['verdicts']}, ROUND]}

@pytest.fixture(scope='module')
def served():
    "A server on 127.0.0.1, a secure context, so the page has `audioWorklet` and `getUserMedia`."
    nokeep = {**LEARN, 'blocks': [{**LEARN['blocks'][0], 'keep': False}, ROUND]}
    _Host.pages.update({'/': html(LEARN), '/gate': html(spec()), '/nokeep': html(nokeep)})
    srv = ThreadingHTTPServer(('127.0.0.1', 0), _Host)
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    try: yield f'http://127.0.0.1:{srv.server_address[1]}'
    finally: srv.shutdown(); srv.server_close()

@pytest.fixture
def pg(br, served):
    p = br.new_page()
    try:
        p.goto(served + '/'); p.wait_for_selector('[data-rk-ready]', state='attached')
        yield p
    finally: p.close()

# --- the matcher -------------------------------------------------------------------------------------------------------------

def m(pg, beats, onsets, **opts):
    return [(x['verdict'], x['ms']) for x in pg.evaluate('([b, o, p]) => Rupaka.blocks.listen.match(b, o, p)', [beats, onsets, opts])]

def test_match_on_is_inclusive_at_the_tolerance(pg):
    assert m(pg, [1.0], [1.030]) == [('on', 30)]
    assert m(pg, [1.0], [0.970]) == [('on', -30)]
    assert m(pg, [1.0], [1.031]) == [('late', 31)]
    assert m(pg, [1.0], [0.969]) == [('early', -31)]
    assert m(pg, [1.0], [1.020], tolerance=10) == [('late', 20)]

def test_match_window_edge(pg):
    assert m(pg, [1.0], [1.150]) == [('late', 150)]
    assert m(pg, [1.0], [1.151]) == [('missed', None)]
    assert m(pg, [1.0], [0.849]) == [('missed', None)]
    assert m(pg, [1.0], [1.090], window=80) == [('missed', None)]
    assert m(pg, [1.0], []) == [('missed', None)]

def test_match_reach_is_half_the_beat_gap(pg):
    "Beats 200 ms apart reach 100 ms each way, though the window is 150 ms."
    assert m(pg, [1.0, 1.2], [1.101]) == [('missed', None), ('early', -99)]

def test_match_takes_the_nearest_of_two_onsets_in_one_window(pg):
    assert m(pg, [1.0], [1.04, 1.10]) == [('late', 40)]
    assert m(pg, [1.0, 1.2], [1.09, 1.11]) == [('late', 90), ('early', -90)]

def test_match_uses_one_onset_for_one_beat_only(pg):
    assert m(pg, [1.0, 1.2], [1.1]) == [('late', 100), ('missed', None)]
    assert m(pg, [1.0, 1.05], [1.02]) == [('on', 20), ('missed', None)]

def test_match_gives_the_beat_times(pg):
    r = pg.evaluate('Rupaka.blocks.listen.match([2, 2.5], [2.51])')
    assert [x['beat'] for x in r] == [2, 2.5] and [x['verdict'] for x in r] == ['missed', 'on']

# --- calibration -------------------------------------------------------------------------------------------------------------

def cal(pg, clicks, onsets):
    return pg.evaluate('([c, o]) => Rupaka.blocks.listen.calib(c, o)', [clicks, onsets])

def test_calib_median_and_bleed(pg):
    clicks = [1 + .6 * k for k in range(8)]
    r = cal(pg, clicks, [c + .010 for c in clicks] + [c + .060 for c in clicks])   # the speaker at +10 ms, the taps at +60 ms
    assert r['ms'] == 60 and r['n'] == 8 and r['spread'] < 1 and r['wide'] is False

def test_calib_warns_on_a_wide_spread(pg):
    clicks = [1 + .6 * k for k in range(8)]
    r = cal(pg, clicks, [c + (-.020 if k % 2 else .100) for k, c in enumerate(clicks)])   # 60 ms either side of +40 ms
    assert r['ms'] == 40 and r['spread'] == 60 and r['wide'] is True

def test_calib_needs_four_taps(pg):
    clicks = [1 + .6 * k for k in range(8)]
    assert cal(pg, clicks, [c + .060 for c in clicks[:3]]) is None

# --- the worklet -------------------------------------------------------------------------------------------------------------

OFFLINE = r"""async ([noise, times]) => {
  const sr = 48000, n = sr * 3, ac = new OfflineAudioContext(1, n, sr), buf = ac.createBuffer(1, n, sr), x = buf.getChannelData(0);
  let seed = 7; const rnd = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return (seed >>> 0) / 2147483648 - 1; };
  if (noise) for (let i = 0; i < n; i++) x[i] = 0.01 * Math.sqrt(3) * rnd();   // white noise at -40 dB RMS
  for (const t of times) { const s = Math.round(t * sr);
    for (let i = 0; i < 0.08 * sr && s + i < n; i++) x[s + i] += Math.exp(-i / (0.015 * sr)) * (0.5 * Math.sin(2 * Math.PI * 180 * i / sr) + 0.3 * rnd()); }
  await ac.audioWorklet.addModule(Rupaka.base + 'listen-worklet.js');
  const node = new AudioWorkletNode(ac, 'rupaka-listen'), got = [];
  node.port.onmessage = e => { if ('t' in e.data) got.push(e.data.t); };   // the level messages are not onsets
  const src = ac.createBufferSource(); src.buffer = buf; src.connect(node); node.connect(ac.destination); src.start(0);
  await ac.startRendering(); await new Promise(r => setTimeout(r, 300));
  return got;
}"""
TRAIN = [0.4, 0.75, 1.2, 1.5, 1.82, 2.3, 2.62]   # not evenly spaced, so a fixed lag cannot hide

def near(got, want, ms=5):
    return len(got) == len(want) and all(abs(g - w) * 1000 <= ms for g, w in zip(sorted(got), want))

def test_worklet_finds_a_strike_train_in_silence(pg):
    got = pg.evaluate(OFFLINE, [False, TRAIN])
    assert near(got, TRAIN), [round((g - w) * 1000, 2) for g, w in zip(got, TRAIN)] or got

def test_worklet_finds_a_strike_train_in_noise(pg):
    got = pg.evaluate(OFFLINE, [True, TRAIN])
    assert near(got, TRAIN), [round((g - w) * 1000, 2) for g, w in zip(got, TRAIN)] or got

@pytest.mark.parametrize('noise', [False, True])
def test_worklet_finds_nothing_in_silence_or_noise(pg, noise):
    assert pg.evaluate(OFFLINE, [noise, []]) == []

# --- the block in a page -----------------------------------------------------------------------------------------------------

def test_an_inlined_page_says_the_mic_is_not_there(draw):
    "`page()` puts the script in the page, so `R.base` is '' and the worklet has no URL."
    d = draw(spec()); d.lock(2)
    box = d.pg.locator('.rk-listen')
    assert box.locator('.rk-listen-why').inner_text() == 'The microphone is not available here.'
    assert box.locator('button:visible').count() == 0 and d.errors == []

def test_no_get_user_media_says_the_mic_is_not_there(br, served):
    p = br.new_page()
    try:
        p.add_init_script('Object.defineProperty(navigator, "mediaDevices", {value: undefined})')
        p.goto(served + '/'); p.wait_for_selector('[data-rk-ready]', state='attached')
        assert p.locator('.rk-listen-why').inner_text() == 'The microphone is not available here.'
    finally: p.close()

def test_a_refused_mic_says_the_mic_is_not_there(br, served):
    p, errs = br.new_page(), []
    try:
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.add_init_script('navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException("no", "NotAllowedError"))')
        p.goto(served + '/'); p.wait_for_selector('[data-rk-ready]', state='attached')
        p.locator('button', has_text='Listen on this device').click()
        p.wait_for_function("document.querySelector('.rk-listen-why')?.textContent === 'The microphone is not available here.'")
        assert errs == [] and p.locator('button', has_text='Stop listening').is_hidden()
    finally: p.close()

# --- a fake microphone -------------------------------------------------------------------------------------------------------

def strikes_wav(path, sr=SR):
    "A loop of `LOOP` seconds with a strike each `PERIOD` seconds from `FIRST`, as 16-bit mono PCM, made with the stdlib `wave`."
    rnd, n = random.Random(1), int(sr * LOOP)
    x = [0.0] * n
    for k in range(int((LOOP - FIRST) / PERIOD) + 1):
        s = round((FIRST + k * PERIOD) * sr)
        for i in range(int(.08 * sr)):
            if s + i < n: x[s + i] += math.exp(-i / (.015 * sr)) * (.5 * math.sin(2 * math.pi * 180 * i / sr) + .3 * (rnd.random() * 2 - 1))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(array('h', (round(max(-1, min(1, v)) * 32767) for v in x)).tobytes())
    return path

def test_the_wav_in_tests_is_the_one_this_file_makes(tmp_path):
    assert WAV.read_bytes() == strikes_wav(tmp_path/'w.wav').read_bytes()

MIC = r"""
import sys, json, math
from playwright.sync_api import sync_playwright
base, wav, period = sys.argv[1], sys.argv[2], float(sys.argv[3])
SPY = '''(() => { window.__gum = []; window.__streams = [];
  const md = navigator.mediaDevices; if (!md) return; const orig = md.getUserMedia.bind(md);
  md.getUserMedia = c => { window.__gum.push(JSON.stringify(c)); return orig(c).then(s => { window.__streams.push(s); return s; }); };
  const W = window.AudioWorkletNode; window.__nodes = [];
  window.AudioWorkletNode = class extends W { constructor(...a) { super(...a); window.__nodes.push(this); } }; })()'''
# The calibration fixture: the raw onsets of the block's own worklet node, with the same latency terms. A second MediaStreamSource on
# the same stream can have another buffer delay (25 ms apart in some runs), so the fixture listens on the block's own path.
PROBE = '''async () => {
  const ac = window.__rkAudio, s = window.__streams[0], tr = s.getAudioTracks()[0], node = window.__nodes[0], got = [];
  const hear = e => { if ('t' in e.data) got.push(e.data.t); };
  node.port.addEventListener('message', hear);
  await new Promise(r => setTimeout(r, 3000));
  node.port.removeEventListener('message', hear);
  return {raw: got, lat: (tr.getSettings().latency || 0) + (ac.outputLatency || 0), input: tr.getSettings().latency || 0, output: ac.outputLatency || 0, now: ac.currentTime};
}'''
HOST = "document.querySelector('[data-rupaka]')"
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--mute-audio', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                                               f'--use-file-for-fake-audio-capture={wav}'])
    try:
        pg, reqs, errs = b.new_page(), [], []
        pg.on('request', lambda r: reqs.append(r.url)); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.add_init_script(SPY)
        pg.goto(base + '/'); pg.wait_for_selector('[data-rk-ready]', state='attached'); pg.wait_for_timeout(800)
        out['before'] = pg.evaluate('window.__gum.length')
        pg.locator('button', has_text='Listen on this device').click()
        pg.wait_for_function("document.querySelector('.rk-listen-status')?.textContent.startsWith('Listening')", timeout=10000)
        out['gum'] = pg.evaluate('window.__gum')
        probe = pg.evaluate(PROBE)
        on = [t - probe['lat'] for t in probe['raw']]
        out['probe_gaps_ms'] = [round((b2 - a) * 1000, 2) for a, b2 in zip(on, on[1:])]
        last = on[-1]
        k0 = math.ceil((probe['now'] + .8 - last) / period)
        beats = [last + (k0 + k) * period - .040 for k in range(6)]   # each strike of the fake device comes 40 ms after its beat
        pg.evaluate(f'b => Rupaka.set({HOST}, {{beats: b}})', beats)
        pg.wait_for_function(f'{HOST}.rupaka.st.verdicts.length === 6', timeout=15000)
        out['verdicts'] = pg.evaluate(f'{HOST}.rupaka.st.verdicts')
        out['shown'] = pg.locator('.rk-listen-out li').all_inner_texts()
        out['latency'] = dict(probe_input=probe['input'], probe_output=probe['output'], judge_output=pg.evaluate('window.__rkAudio.outputLatency || 0'))
        pg.locator('button', has_text='Stop listening').click()
        out['tracks'] = pg.evaluate('window.__streams.flatMap(s => s.getTracks()).map(t => t.readyState)')
        out['offsite'] = [u for u in reqs if not u.startswith(base + '/')]
        out['errs'] = errs
    finally: b.close()
print(json.dumps(out))
"""

def test_a_fake_mic_reads_late_by_40_ms(served):
    "Its own Chromium, in its own process, with a fake input device that plays `listen_strikes.wav` again and again."
    r = subprocess.run([sys.executable, '-c', MIC, served, str(WAV), str(PERIOD)], capture_output=True, text=True, timeout=120)
    if 'Executable doesn' in r.stderr: pytest.skip("Playwright's Chromium is not installed")
    assert r.returncode == 0, r.stderr[-3000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    print('fake mic:', json.dumps(out))
    assert out['before'] == 0, out
    assert out['gum'] == ['{"audio":{"echoCancellation":false,"noiseSuppression":false,"autoGainControl":false}}'], out
    ms = [v['ms'] for v in out['verdicts']]
    assert [v['verdict'] for v in out['verdicts']] == ['late'] * 6 and all(abs(x - 40) <= 10 for x in ms), out
    assert all(t.startswith('late ') for t in (s.split(': ', 1)[1] for s in out['shown'])) and len(out['shown']) == 6, out
    assert out['tracks'] and set(out['tracks']) == {'ended'}, out
    assert out['offsite'] == [] and out['errs'] == [], out

# --- live feedback, and the kept round: replay, timeline and save ---------------------------------------------------------------

# One Chromium with the fake device, one page for each case. The spy counts the worklet's messages by kind (a message that holds an
# ArrayBuffer or a typed array is a sample buffer), the buffer sources and oscillators that start, and the object URLs.
REPLAY = r"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright
base, wav, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
SPY = '''(() => { window.__msgs = {pcm: 0, level: 0, onset: 0, other: 0}; window.__starts = []; window.__osc = 0; window.__urls = {made: [], revoked: []};
  const bin = d => !!d && typeof d === 'object' && Object.values(d).some(v => v instanceof ArrayBuffer || ArrayBuffer.isView(v));
  const W = window.AudioWorkletNode;
  window.AudioWorkletNode = class extends W { constructor(...a) { super(...a); this.port.addEventListener('message', e => { const d = e.data, m = window.__msgs;
    if (bin(d)) m.pcm++; else if (d && 'level' in d) m.level++; else if (d && 't' in d) m.onset++; else m.other++; }); } };
  const st = AudioBufferSourceNode.prototype.start;
  AudioBufferSourceNode.prototype.start = function (...a) { window.__starts.push({main: this.context === window.__rkAudio, dur: this.buffer ? this.buffer.duration : null}); return st.apply(this, a); };
  const os = OscillatorNode.prototype.start;
  OscillatorNode.prototype.start = function (...a) { window.__osc++; return os.apply(this, a); };
  const mk = URL.createObjectURL, rv = URL.revokeObjectURL;
  URL.createObjectURL = o => { const u = mk.call(URL, o); window.__urls.made.push(u); return u; };
  URL.revokeObjectURL = u => { window.__urls.revoked.push(u); return rv.call(URL, u); }; })()'''
HOST = "document.querySelector('[data-rupaka]')"
LINE = '.rk-listen-line'
def ev(pg, js): return pg.evaluate(js)
def listen(pg):
    pg.locator('button', has_text='Listen on this device').click()
    pg.wait_for_function("document.querySelector('.rk-listen-status')?.textContent.startsWith('Listening')", timeout=10000)
def round_(pg):
    ev(pg, f"Rupaka.set({HOST}, {{verdicts: []}})")
    b = ev(pg, f"(() => {{ const t = window.__rkAudio.currentTime + .8, b = Array.from({{length: 6}}, (_, k) => t + k * .5); Rupaka.set({HOST}, {{beats: b}}); return b; }})()")
    pg.wait_for_function(f'{HOST}.rupaka.st.verdicts.length === 6', timeout=15000)
    return b
def shown(pg, text): return pg.locator('button', has_text=text).is_visible()
def play_shown(pg, timeout=4000):
    try: pg.locator('button', has_text='Play what I played').wait_for(state='visible', timeout=timeout); return True
    except Exception: return False
def privacy(pg): return ev(pg, "document.querySelector('.rk-listen-privacy')?.textContent ?? null")
def box(pg, label): return pg.get_by_label(label)

def a(pg, r):
    listen(pg)
    r['meter_visible'] = pg.locator('.rk-listen-level').is_visible(); r['count_visible'] = pg.locator('.rk-listen-count').is_visible()
    t0, l0 = ev(pg, 'performance.now()'), ev(pg, 'window.__msgs.level')
    r['levels'], r['counts'] = [], []
    for _ in range(12):
        pg.wait_for_timeout(150)
        r['levels'].append(ev(pg, "document.querySelector('.rk-listen-level')?.value ?? null"))
        r['counts'].append(ev(pg, "document.querySelector('.rk-listen-count')?.textContent ?? null"))
    t1, l1 = ev(pg, 'performance.now()'), ev(pg, 'window.__msgs.level')
    r['level_rate'] = (l1 - l0) / ((t1 - t0) / 1000)
    r['verdicts'] = ev(pg, f'{HOST}.rupaka.st.verdicts.length'); r['msgs'] = ev(pg, 'window.__msgs')

def b(pg, r):
    r['keep_box'] = box(pg, 'Keep my playing').count()
    r['keep_checked'] = box(pg, 'Keep my playing').is_checked() if r['keep_box'] == 1 else None
    listen(pg); round_(pg); pg.wait_for_timeout(600)
    r['verdicts'] = len(ev(pg, f'{HOST}.rupaka.st.verdicts'))
    r['play'], r['save'], r['line'] = shown(pg, 'Play what I played'), shown(pg, 'Save my playing'), pg.locator(LINE).count()
    r['msgs'], r['privacy'] = ev(pg, 'window.__msgs'), privacy(pg)

def c(pg, r):
    box(pg, 'Keep my playing').check(timeout=3000)
    r['privacy'] = privacy(pg)
    listen(pg); r['beats'] = round_(pg)
    r['play'] = play_shown(pg); r['save'] = shown(pg, 'Save my playing')
    line = pg.locator(LINE)
    r['seconds'], r['frames'] = float(line.get_attribute('data-seconds')), int(line.get_attribute('data-frames'))
    r['beat_ticks'], r['stroke_ticks'] = line.locator('.rk-listen-beat').count(), line.locator('.rk-listen-stroke').count()
    r['rate'] = ev(pg, 'window.__rkAudio.sampleRate')
    pg.locator('button', has_text='Play what I played').click(); pg.wait_for_timeout(300)
    r['starts'] = ev(pg, 'window.__starts')
    o0 = ev(pg, 'window.__osc'); box(pg, 'Click on each beat').check(timeout=3000)
    pg.locator('button', has_text='Play what I played').click(); pg.wait_for_timeout(300)
    r['clicks'] = ev(pg, 'window.__osc') - o0
    with pg.expect_download(timeout=5000) as dl: pg.locator('button', has_text='Save my playing').click()
    d = dl.value; r['name'] = d.suggested_filename; p = outdir/d.suggested_filename; d.save_as(p); r['file'] = str(p)
    pg.wait_for_timeout(1500)
    r['urls'], r['msgs'] = ev(pg, 'window.__urls'), ev(pg, 'window.__msgs')

def e(pg, r):
    keep = box(pg, 'Keep my playing'); keep.check(timeout=3000)
    listen(pg); round_(pg); r['play_first'] = play_shown(pg)
    keep.uncheck(); pg.wait_for_timeout(200)
    r['play_after_untick'], r['line_after_untick'] = shown(pg, 'Play what I played'), pg.locator(LINE).count()
    keep.check(); pg.wait_for_timeout(200); r['play_after_recheck'] = shown(pg, 'Play what I played')
    round_(pg); r['play_again'] = play_shown(pg)
    pg.locator('button', has_text='Stop listening').click(); pg.wait_for_timeout(200)
    r['play_after_stop'], r['save_after_stop'] = shown(pg, 'Play what I played'), shown(pg, 'Save my playing')
    r['line_after_stop'] = pg.locator(LINE).count()

def f(pg, r):
    pg.goto(base + '/nokeep'); pg.wait_for_selector('[data-rk-ready]', state='attached')
    r['keep_box'] = box(pg, 'Keep my playing').count()
    listen(pg); r['privacy'] = privacy(pg); r['msgs'] = ev(pg, 'window.__msgs')

out = {}
with sync_playwright() as p:
    br = p.chromium.launch(headless=True, args=['--mute-audio', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                                                f'--use-file-for-fake-audio-capture={wav}'])
    try:
        for name, case in dict(a=a, b=b, c=c, e=e, f=f).items():
            r, errs = {}, []
            pg = br.new_page(accept_downloads=True)
            pg.on('pageerror', lambda x: errs.append(str(x))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
            try:
                pg.add_init_script(SPY); pg.goto(base + '/'); pg.wait_for_selector('[data-rk-ready]', state='attached')
                case(pg, r)
            except Exception as x: r['error'] = str(x)[:400]
            finally: pg.close()
            out[name] = {**r, 'errs': errs}
    finally: br.close()
print(json.dumps(out))
"""

@pytest.fixture(scope='module')
def replay(served, tmp_path_factory):
    d = tmp_path_factory.mktemp('replay')
    r = subprocess.run([sys.executable, '-c', REPLAY, served, str(WAV), str(d)], capture_output=True, text=True, timeout=240)
    if 'Executable doesn' in r.stderr: pytest.skip("Playwright's Chromium is not installed")
    assert r.returncode == 0, r.stderr[-3000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    print('replay:', json.dumps(out))
    return out

OFF_TEXT = 'The sound stays on this device. Nothing is recorded or sent.'
KEEP_TEXT = ('While this box is ticked, this page holds the last second of sound and your last round. '
             'Both go when you untick it, press Stop listening or leave the page. '
             'Save my playing writes a WAV file on this device. Nothing is sent.')
SPAN = 5 * PERIOD + 2 * .150   # six beats half a second apart, and the default window of 150 ms on each side

def heard(s):
    m = re.fullmatch(r'Heard (\d+) strokes?', s or '')
    return int(m[1]) if m else None

def test_the_meter_and_the_stroke_count_move_before_any_round(replay):
    a = replay['a']
    assert a.get('meter_visible') is True and a.get('count_visible') is True, a
    lv = a['levels']
    assert None not in lv and max(lv) > .05 and len(set(lv)) >= 3, a
    assert 15 <= a['level_rate'] <= 40, a
    ns = [heard(s) for s in a['counts']]
    assert None not in ns and ns[-1] > ns[0] and ns[-1] >= 2, a
    assert a['verdicts'] == 0 and a['msgs']['pcm'] == 0 and a['errs'] == [], a

def test_keep_off_keeps_nothing_and_posts_no_samples(replay):
    b = replay['b']
    assert b.get('keep_box') == 1 and b.get('keep_checked') is False, b
    assert b['verdicts'] == 6 and b['play'] is False and b['save'] is False and b['line'] == 0, b
    assert b['msgs']['level'] > 0 and b['msgs']['onset'] > 0 and b['msgs']['pcm'] == 0, b
    assert b['privacy'] == OFF_TEXT and b['errs'] == [], b

def test_keep_on_replays_the_last_round_with_a_timeline(replay):
    c = replay['c']
    assert c.get('play') is True and c.get('save') is True and c.get('privacy') == KEEP_TEXT, c
    assert abs(c['seconds'] - SPAN) <= .050 and abs(c['frames'] / c['rate'] - SPAN) <= .050, c
    assert c['beat_ticks'] == 6 and c['stroke_ticks'] >= 1 and c['msgs']['pcm'] > 0, c
    assert any(s['main'] and abs(s['dur'] - c['frames'] / c['rate']) < .001 for s in c['starts']), c
    assert c['clicks'] == 6 and c['errs'] == [], c

def test_save_writes_the_round_as_a_16_bit_wav(replay):
    c = replay['c']
    assert re.fullmatch(r'rupaka-mic-\d{8}-\d{6}\.wav', c.get('name') or ''), c
    raw = Path(c['file']).read_bytes()
    assert raw[:4] == b'RIFF' and raw[8:12] == b'WAVE' and raw[12:16] == b'fmt ' and int.from_bytes(raw[4:8], 'little') == len(raw) - 8
    assert int.from_bytes(raw[20:22], 'little') == 1   # PCM
    with wave.open(c['file']) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, c['rate'], c['frames'])
        x = array('h', w.readframes(w.getnframes()))
    assert abs(len(x) / c['rate'] - SPAN) <= .050 and max(map(abs, x)) > 3000   # the strikes are in it
    assert c['urls']['made'] and set(c['urls']['made']) <= set(c['urls']['revoked']), c

def test_untick_and_stop_drop_the_kept_round(replay):
    e = replay['e']
    assert e.get('play_first') is True and e.get('play_after_untick') is False and e.get('line_after_untick') == 0, e
    assert e.get('play_after_recheck') is False and e.get('play_again') is True, e
    assert e.get('play_after_stop') is False and e.get('save_after_stop') is False and e.get('line_after_stop') == 0 and e['errs'] == [], e

def test_keep_false_hides_the_box(replay):
    f = replay['f']
    assert f.get('keep_box') == 0 and f.get('privacy') == OFF_TEXT and f['msgs']['pcm'] == 0 and f['errs'] == [], f

def test_the_listen_files_make_no_request():
    for f in (Path(__file__).parents[1]/'rupaka'/'blocks'/'listen'/'listen.js', Path(__file__).parents[1]/'rupaka'/'static'/'listen-worklet.js'):
        js = f.read_text()
        assert not any(x in js for x in ('fetch(', 'XMLHttpRequest', 'innerHTML', 'eval(', 'sendBeacon', 'WebSocket')), f
