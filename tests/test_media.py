"Profile media: the record checks, the school rule, the gated runtime, the media base, `save` with assets, and `rupaka.media`."
import json, re, shutil
from copy import deepcopy
from pathlib import Path
import pytest
from fastcore.xml import to_xml
from fastcore.xtras import run
import rupaka.spec as S
from rupaka.render import host, page, Demo, save, media_files
from rupaka.media import import_asset, clip, still, find_span

FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason='no ffmpeg')
CREDIT = dict(who='A. Player', license='CC BY 4.0', url='https://example.org/rec')
YT = 'youtube:dQw4w9WgXcQ'

def fake(c, ext): return f'asset:{c * 64}.{ext}'
FAKE = dict(photo=fake('a', 'png'), clip=fake('b', 'mp4'), hit=fake('c', 'wav'), palani=fake('d', 'png'), tanjore=fake('e', 'png'))

def with_media(srcs=FAKE):
    "The mridangam-profile demo with a media table, nam media entries per school, and a sample voice for nam."
    s = deepcopy(S.gallery()['mridangam-profile']); d = s['profiles']['mridangam']['data']
    img = lambda k, alt: dict(kind='image', src=srcs[k], alt=alt, credit=CREDIT)
    d['media'] = deepcopy({'nam-photo': img('photo', 'A hand plays nam on the right side.'),
                  'nam-clip': dict(kind='video', src=srcs['clip'], start=1, end=2, credit=CREDIT),
                  'nam-yt': dict(kind='video', src=YT, start=10, end=20, credit=CREDIT),
                  'nam-hit': dict(kind='audio', src=srcs['hit'], start=0.5, end=2.5, credit=CREDIT, sources=['nam']),
                  'palani-photo': img('palani', 'The middle finger supports nam.'),
                  'tanjore-photo': img('tanjore', 'The ring finger supports nam.')})
    t = d['techniques']['nam']
    t['voice'] = dict(kind='sample', media='nam-hit')
    t['media'] = [dict(media='nam-photo'), dict(media='nam-clip'), dict(media='nam-yt'),
                  dict(media='palani-photo', school='palani'), dict(media='tanjore-photo', school='tanjore')]
    s['profiles']['mridangam']['revision'] = S.profile_hash(d)
    return s

def data(): return with_media()['profiles']['mridangam']['data']

def _set(d, path, v):
    *ks, last = path.split('.')
    for k in ks: d = d[int(k)] if isinstance(d, list) else d[k]
    if v is ...: del d[last]
    else: d[last] = v

def test_media_profile_is_good():
    assert S.profile_errors(data()) == []
    assert S.validate(with_media()) == []

@pytest.mark.parametrize('path,value,where', [
    ('media.nam-hit.src', 'https://bad.test/a.wav', 'media.nam-hit.src'),
    ('media.nam-hit.src', 'asset:abc.wav', 'media.nam-hit.src'),
    ('media.nam-hit.src', fake('c', 'jpg'), 'media.nam-hit.src'),
    ('media.nam-hit.src', fake('C', 'wav'), 'media.nam-hit.src'),
    ('media.nam-photo.src', YT, 'media.nam-photo.src'),
    ('media.nam-photo.kind', 'gif', 'media.nam-photo.kind'),
    ('media.nam-photo.alt', ..., 'media.nam-photo.alt'),
    ('media.nam-photo.start', 1, 'media.nam-photo.start'),
    ('media.nam-photo.credit', ..., 'media.nam-photo.credit'),
    ('media.nam-photo.credit.url', 'javascript:alert(1)', 'media.nam-photo.credit.url'),
    ('media.nam-photo.credit.license', ..., 'media.nam-photo.credit.license'),
    ('media.nam-photo.credit.who', ' ', 'media.nam-photo.credit.who'),
    ('media.nam-photo.extra', 1, 'media.nam-photo.extra'),
    ('media.nam-photo.sources', ['nope'], 'media.nam-photo.sources'),
    ('media.nam-yt.end', ..., 'media.nam-yt.end'),
    ('media.nam-yt.end', 131, 'media.nam-yt.end'),
    ('media.nam-yt.end', 5, 'media.nam-yt.end'),
    ('media.nam-yt.start', -1, 'media.nam-yt.start'),
    ('media.nam-yt.start', '10', 'media.nam-yt.start'),
    ('media.nam-yt.src', 'youtube:short', 'media.nam-yt.src'),
    ('media.nam-hit.end', 0.2, 'media.nam-hit.end'),
    ('techniques.nam.media', [dict(media='nope')], 'techniques.nam.media[0].media'),
    ('techniques.nam.media', [dict(media='nam-photo', school='mysore')], 'techniques.nam.media[0].school'),
    ('techniques.nam.media', [dict(media='nam-photo', at=1)], 'techniques.nam.media[0].at'),
    ('techniques.nam.media', [dict(media='nam-photo')] * 2, 'techniques.nam.media[1]'),
    ('techniques.nam.voice', dict(kind='sample', media='nam-photo'), 'techniques.nam.voice.media'),
    ('techniques.nam.voice', dict(kind='sample', media='nope'), 'techniques.nam.voice.media'),
    ('techniques.nam.voice', dict(kind='sample', media='nam-hit', url='x'), 'techniques.nam.voice.url')])
def test_media_refusals(path, value, where):
    d = data(); _set(d, path, value)
    assert any(e.startswith(f'{where}:') for e in S.profile_errors(d)), S.profile_errors(d)

@pytest.mark.parametrize('path,value,where', [
    ('media', [], 'media'), ('media.nam-photo.kind', [], 'media.nam-photo.kind'),
    ('techniques.nam.media', [dict(media=[])], 'techniques.nam.media[0].media'),
    ('techniques.nam.media', [dict(media='nam-photo', school=[])], 'techniques.nam.media[0].school'),
    ('techniques.nam.voice', dict(kind='sample', media=[]), 'techniques.nam.voice.media')])
def test_malformed_media_gives_errors_not_exceptions(path, value, where):
    d = data(); _set(d, path, value)
    assert any(e.startswith(f'{where}:') for e in S.profile_errors(d))

def test_a_block_voice_stays_strike_only():
    s = with_media(); s['blocks'][1] = dict(type='sound', voice=dict(kind='sample', media='nam-hit'))
    assert any(e.startswith('blocks[1].voice.') for e in S.validate(s))

def test_media_of_a_hidden_technique_needs_the_wait():
    s = with_media(); del s['blocks'][2]['after']
    assert any(e.startswith('blocks[2]:') and 'gate "support"' in e for e in S.validate(s))

def test_host_page_and_demo_take_a_media_base():
    s = with_media()
    assert 'data-rk-media="/m/"' in host(s, media='/m/')
    assert 'data-rk-media="/m/"' in page(s, fonts='none', media='/m/')
    assert 'data-rk-media="/m/"' in to_xml(Demo(s, media='/m/'))
    assert 'data-rk-media' not in host(s) and 'data-rk-media' not in to_xml(Demo(s))

def test_save_copies_the_referenced_assets(tmp_path):
    s, store = with_media(), tmp_path/'store'; store.mkdir()
    names = media_files(s)
    assert names == sorted(x.removeprefix('asset:') for x in FAKE.values())
    assert media_files([s, S.gallery()['mridangam-profile']]) == names
    for n in names: (store/n).write_bytes(n.encode())
    (store/'other.wav').write_bytes(b'x')
    p = save(s, tmp_path/'site'/'p.html', fonts='none', media=store)
    assert sorted(x.name for x in (p.parent/'media').iterdir()) == names
    (store/names[0]).unlink()
    with pytest.raises(FileNotFoundError, match=re.escape(names[0])): save(s, tmp_path/'site2'/'p.html', fonts='none', media=store)
    assert not (tmp_path/'site2').exists()

def test_import_asset_names_a_file_by_its_content(tmp_path):
    a = tmp_path/'Tha-1.WAV'; a.write_bytes(b'RIFF tha')
    src = import_asset(a, tmp_path/'store')
    assert re.fullmatch(r'asset:[0-9a-f]{64}\.wav', src)
    assert (tmp_path/'store'/src.removeprefix('asset:')).read_bytes() == b'RIFF tha'
    b = tmp_path/'copy.wav'; b.write_bytes(b'RIFF tha')
    assert import_asset(b, tmp_path/'store') == src and len(list((tmp_path/'store').iterdir())) == 1
    gif = tmp_path/'a.gif'; gif.write_bytes(b'GIF')
    with pytest.raises(ValueError): import_asset(gif, tmp_path/'store')

VTT = '''WEBVTT

00:00:01.000 --> 00:00:03.000
The next stroke is <c>nam</c>.

00:00:03.000 --> 00:00:05.000
Listen: it rings, and then it fades!

00:01:00.000 --> 00:01:02.000
It rings again.
'''
JSON3 = {'events': [{'tStartMs': 1000, 'dDurationMs': 2000, 'segs': [{'utf8': 'The'}, {'utf8': ' next', 'tOffsetMs': 400}, {'utf8': ' stroke', 'tOffsetMs': 800},
                                                                {'utf8': ' is', 'tOffsetMs': 1200}, {'utf8': ' Nam.', 'tOffsetMs': 1600}]},
                    {'tStartMs': 3000, 'segs': [{'utf8': '\n'}]},
                    {'tStartMs': 3000, 'dDurationMs': 2000, 'segs': [{'utf8': 'it rings'}, {'utf8': ' and fades', 'tOffsetMs': 1000}]}]}
WHISPER = {'text': '...', 'segments': [
    {'start': 1.0, 'end': 3.0, 'text': ' The next stroke is nam.',
     'words': [{'word': ' The', 'start': 1.0, 'end': 1.3}, {'word': ' next', 'start': 1.4, 'end': 1.7}, {'word': ' stroke', 'start': 1.8, 'end': 2.2},
               {'word': ' is', 'start': 2.3, 'end': 2.4}, {'word': ' nam.', 'start': 2.5, 'end': 2.9}]},
    {'start': 3.0, 'end': 5.0, 'text': ' It rings and fades.'}]}

def test_find_span():
    assert find_span(WHISPER, 'STROKE, is nam', pad=0) == (1.8, 2.9)
    assert find_span(WHISPER, 'stroke is nam', pad=1) == (0.8, 3.9)
    assert find_span(WHISPER, 'the next', pad=2) == (0, 3.7)
    assert find_span(WHISPER, 'rings and fades', pad=0) == (3.5, 5.0)
    assert find_span(JSON3, 'stroke is nam', pad=0) == (1.8, 3.0)
    assert find_span(JSON3, 'it rings and fades', pad=0) == (3.0, 5.0)
    assert find_span(VTT, 'stroke is nam', pad=0) == pytest.approx((1.8, 3.0))
    assert find_span(VTT, 'it rings', pad=0) == pytest.approx((3 + 2/7, 3 + 6/7), abs=1e-3)
    assert find_span(VTT, 'rings, it', pad=0) == pytest.approx((3 + 4/7, 3 + 12/7), abs=1e-3)
    assert find_span(VTT, 'next fades') is None
    for t in (VTT, JSON3, WHISPER): assert find_span(t, 'dhin') is None and find_span(t, 'nam stroke') is None

def _probe(p, *entries):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_entries', ','.join(entries), '-of', 'json', str(p)]))

@pytest.fixture(scope='module')
def fx(tmp_path_factory):
    "Tiny generated sources: a 3 s tone, a 3 s 320x240 test video with sound, and a still."
    d = tmp_path_factory.mktemp('fx'); ff = lambda *a: run(['ffmpeg', '-v', 'error', '-y', *a])
    ff('-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', str(d/'tone.wav'))
    ff('-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=25:duration=3', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=3',
       '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(d/'src.mp4'))
    ff('-f', 'lavfi', '-i', 'color=c=orange:size=64x48', '-frames:v', '1', str(d/'photo.png'))
    return d

@needs_ffmpeg
def test_clip_and_still(fx, tmp_path):
    out = tmp_path/'store'
    a = clip(fx/'tone.wav', 1, 2, out)
    assert re.fullmatch(r'asset:[0-9a-f]{64}\.m4a', a)
    assert float(_probe(out/a[6:], 'format=duration')['format']['duration']) == pytest.approx(1, abs=.1)
    w = clip(fx/'tone.wav', .5, 1, out, ext='wav')
    assert w.endswith('.wav') and float(_probe(out/w[6:], 'format=duration')['format']['duration']) == pytest.approx(.5, abs=.05)
    v = clip(fx/'src.mp4', 0.5, 2, out, kind='video')
    assert re.fullmatch(r'asset:[0-9a-f]{64}\.mp4', v)
    st = _probe(out/v[6:], 'stream=codec_name,width,height')['streams']
    assert {'codec_name': 'h264', 'width': 320, 'height': 240} in st
    b = (out/v[6:]).read_bytes(); assert b.index(b'moov') < b.index(b'mdat')
    j = still(fx/'src.mp4', 1, out)
    assert re.fullmatch(r'asset:[0-9a-f]{64}\.jpg', j) and (out/j[6:]).read_bytes()[:2] == b'\xff\xd8'
    with pytest.raises(ValueError): clip(fx/'tone.wav', 2, 1, out)
    with pytest.raises(ValueError): clip(fx/'tone.wav', 0, 1, out, kind='image')

@pytest.fixture
def site(fx, tmp_path):
    "The media demo saved with real assets, as a file:// page."
    store = tmp_path/'store'
    srcs = dict(photo=import_asset(fx/'photo.png', store), clip=clip(fx/'src.mp4', 0, 3, store, kind='video'), hit=import_asset(fx/'tone.wav', store),
                palani=still(fx/'src.mp4', 0.2, store), tanjore=still(fx/'src.mp4', 2.5, store))
    return save(with_media(srcs), tmp_path/'site'/'p.html', fonts='none', media=store)

def _open(br, p):
    pg = br.new_page(viewport=dict(width=720, height=1400)); log = dict(errors=[], web=[])
    pg.on('console', lambda m: m.type == 'error' and log['errors'].append(m.text))
    pg.on('pageerror', lambda e: log['errors'].append(str(e)))
    pg.on('request', lambda r: r.url.split(':')[0] not in ('file', 'data', 'about') and log['web'].append(r.url))
    pg.route('https://www.youtube-nocookie.com/**', lambda r: r.fulfill(body='<p>stub</p>', content_type='text/html'))
    pg.goto(p.as_uri()); pg.wait_for_selector('[data-rk-ready]', state='attached')
    return pg, log

@needs_ffmpeg
def test_media_shows_after_the_gate_with_credits(br, site):
    pg, log = _open(br, site)
    try:
        nam = pg.locator('.rk-sound').nth(1); play = nam.locator('button', has_text='Play')
        assert nam.locator('img, video, iframe, audio').count() == 0 and play.is_disabled()
        assert pg.evaluate("performance.getEntriesByType('resource').filter(e => e.name.includes('/media/')).length") == 0
        g = pg.locator('.rk-gate'); g.locator('.opts button').nth(1).click(); g.locator('.go').click()
        assert nam.is_visible() and play.is_enabled()
        alts = nam.locator('img').evaluate_all('es => es.map(e => e.alt)')
        assert alts == ['A hand plays nam on the right side.', 'The ring finger supports nam.']
        assert all(x.endswith('.png') or x.endswith('.jpg') for x in nam.locator('img').evaluate_all('es => es.map(e => e.getAttribute("src"))'))
        assert nam.locator('img').first.get_attribute('src').startswith('media/')
        credits = nam.locator('.rk-sound-credit')
        assert credits.count() == 5
        assert all('A. Player' in t and 'CC BY 4.0' in t for t in credits.all_inner_texts())
        assert set(credits.locator('a').evaluate_all('es => es.map(e => e.href)')) == {CREDIT['url']}
        v = nam.locator('video')
        assert v.count() == 1 and v.get_attribute('controls') is not None
        pg.wait_for_function("v => v.readyState >= 1 && Math.abs(v.currentTime - 1) < 0.05", arg=v.element_handle())
        loop = nam.locator('button', has_text='Loop')
        assert loop.get_attribute('aria-pressed') == 'false'; loop.click(); assert loop.get_attribute('aria-pressed') == 'true'
        v.evaluate('v => { v.currentTime = 1.95; return v.play(); }')
        pg.wait_for_function('v => !v.paused && v.currentTime < 1.5', arg=v.element_handle(), timeout=3000)
        loop.click(); v.evaluate('v => { v.currentTime = 1.9; return v.play(); }')
        pg.wait_for_function('v => v.paused', arg=v.element_handle(), timeout=3000)
        assert 2 <= v.evaluate('v => v.currentTime') <= 2.4
        assert nam.locator('iframe').count() == 0 and log['web'] == []
        nam.locator('button', has_text='Load video').click()
        f = nam.locator('iframe')
        assert f.get_attribute('src') == 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?start=10&end=20&rel=0'
        assert log['web'] and all(u.startswith('https://www.youtube-nocookie.com/') for u in log['web'])
        assert nam.locator('audio').count() == 0
        play.click()
        a = nam.locator('audio')
        assert a.count() == 1 and a.get_attribute('src').startswith('media/') and a.get_attribute('src').endswith('.wav')
        pg.wait_for_function("a => !a.paused && a.currentTime >= 0.5", arg=a.element_handle())
        assert 'Recorded sample' in nam.inner_text()
        pg.locator('.rk-gate .acts button').filter(has_text='Try another').click()
        assert play.is_disabled() and nam.locator('img, video, iframe').count() == 0
        assert nam.locator('audio').count() == 0
        assert log['errors'] == []
    finally: pg.close()

REAL = S.PKG/'demos'/'media'

def test_real_demo_and_its_assets():
    s = S.gallery()['mridangam-real']
    assert S.validate(s) == []
    names = media_files(s)
    assert len(names) == 2 and all((REAL/n).exists() for n in names)
    for m in s['profiles']['mridangam']['data']['media'].values():
        assert m['credit'] == dict(who='Akshay Anantapadmanabhan, Ashwin Bellur, Hema A. Murthy (IIT Madras), Mridangam Stroke Dataset 1.5',
                                   license='CC BY-NC 4.0', url='https://doi.org/10.5281/zenodo.4068196')

def test_real_demo_plays_in_chromium(br, tmp_path):
    p = save(S.gallery()['mridangam-real'], tmp_path/'real'/'index.html', fonts='none', media=REAL)
    pg, log = _open(br, p); shots = Path(__file__).parent/'screens'; shots.mkdir(exist_ok=True)
    try:
        pg.screenshot(path=str(shots/'mridangam-real-before.png'), full_page=True)
        assert pg.locator('.rk-sound audio, .rk-sound iframe').count() == 0
        tha = pg.locator('.rk-sound').nth(0)
        tha.locator('button', has_text='Play').click()
        pg.wait_for_function("a => a && a.currentTime > 0", arg=tha.locator('audio').element_handle())
        g = pg.locator('.rk-gate'); g.locator('.opts button').first.click(); g.locator('.go').click()
        nam = pg.locator('.rk-sound').nth(1); nam.locator('button', has_text='Play').click()
        pg.wait_for_function("a => a && a.currentTime > 0", arg=nam.locator('audio').element_handle())
        assert 'CC BY-NC 4.0' in nam.inner_text() and 'Mridangam Stroke Dataset 1.5' in nam.inner_text()
        pg.screenshot(path=str(shots/'mridangam-real-after.png'), full_page=True)
        assert log['errors'] == [] and log['web'] == []
    finally: pg.close()
