"The listen block: its manifest, the matcher, the onset worklet, and the microphone path in Chromium with a fake input device."
import json, math, random, subprocess, sys, threading, wave
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
    _Host.pages.update({'/': html(LEARN), '/gate': html(spec())})
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
  node.port.onmessage = e => got.push(e.data.t);
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
  const hear = e => got.push(e.data.t);
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
