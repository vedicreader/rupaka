"Sample-free strikes only start at the learner's Play button."
import json
from copy import deepcopy
from pathlib import Path
import pytest
from rupaka.spec import validate, examples, gallery
from rupaka.agent import catalog, demo_sp
from rupaka.render import page
from rupaka.skill import skill_md

REF = dict(url='https://www.mrithang.com/mridangam-tour/', title='Mridangam tour')
VOICE = dict(kind='strike', frequency=138.59, decay=1.2, gain=.6,
             partials=[dict(ratio=1, gain=1), dict(ratio=2, gain=.4), dict(ratio=3, gain=.2)], noise=.08, bend=20)

def spec():
    return dict(rupaka=1, id='sound-test', state=dict(x=0), blocks=[
        dict(type='gate', id='g', prompt='Is nam a vibrating (ringing) stroke or a non-vibrating (damped) one?',
             options=['vibrating', 'non-vibrating'], answer={'is': 'vibrating'}, again=True),
        dict(type='sound', label='Nam', voice=deepcopy(VOICE), ref=REF, after='g')])

@pytest.mark.parametrize('field,value,path', [
    ('sample', 'https://bad.test/a.wav', 'sample'), ('frequency', 19, 'frequency'),
    ('frequency', 8001, 'frequency'), ('frequency', float('nan'), 'frequency'),
    ('frequency', True, 'frequency'), ('decay', 0, 'decay'), ('decay', 6, 'decay'),
    ('gain', 1.1, 'gain'), ('noise', -.1, 'noise'), ('bend', 1201, 'bend'),
    ('partials', [dict(ratio=1, gain=1)] * 9, 'partials'),
    ('partials', [dict(ratio='https://bad.test/a', gain=1)], 'partials[0].ratio'),
    ('partials', [dict(ratio=1, gain=1, code='alert(1)')], 'partials[0].code'),
    ('frequency', 'https://bad.test/a', 'frequency'), ('kind', 'tone', 'kind')])
def test_voice_refusals(field, value, path):
    s = spec(); s['blocks'][1]['voice'][field] = value
    assert any(e.startswith(f'blocks[1].voice.{path}:') for e in validate(s))

def test_catalog_skill_and_demo():
    assert '- sound:' in catalog()
    assert 'strike' in catalog() and 'partials' in catalog()
    assert 'sound' in demo_sp() and 'approximation' in demo_sp()
    assert '`sound`' in skill_md() and 'strike' in skill_md()
    assert validate(spec()) == []
    s = examples()['sound']; assert validate(s) == []
    assert s == gallery()['mridangam-strokes']
    sounds = [b for b in s['blocks'] if b['type'] == 'sound']
    assert [b['label'] for b in sounds] == ['Nam', 'Tha']
    assert all(b['ref'] == REF and b['after'] == 'nam' for b in sounds)

RECORDER = r"""
window.audio = {contexts:0, resumes:0, nodes:[], starts:[], stops:[], params:[]};
class Param {
  constructor(kind) { this.kind=kind; }
  setValueAtTime(v,t) { audio.params.push({kind:this.kind,v,t}); }
  linearRampToValueAtTime(v,t) { audio.params.push({kind:this.kind,v,t}); }
  exponentialRampToValueAtTime(v,t) { audio.params.push({kind:this.kind,v,t}); }
}
class Node {
  constructor(kind) { this.kind=kind; this.frequency=new Param('frequency'); this.detune=new Param('detune'); this.gain=new Param('gain'); audio.nodes.push(kind); }
  connect(n) { return n; }
  disconnect() {}
  start(t) { audio.starts.push({kind:this.kind,t}); }
  stop(t) { audio.stops.push({kind:this.kind,t}); }
}
window.AudioContext = class {
  constructor() { audio.contexts++; this.currentTime=10; this.sampleRate=48000; this.state='suspended'; this.destination={}; }
  resume() { audio.resumes++; this.state='running'; return Promise.resolve(); }
  createOscillator() { return new Node('oscillator'); }
  createGain() { return new Node('gain'); }
  createBufferSource() { return new Node('noise'); }
  createBuffer(c,n,r) { return {getChannelData:()=>new Float32Array(n)}; }
};
"""

@pytest.fixture
def sound_page(br):
    pg = br.new_page(viewport=dict(width=720, height=900))
    errors=[]; pg.on('pageerror', lambda e: errors.append(str(e)))
    def mount(s):
        pg.set_content('<script>'+RECORDER+'</script>'+page(s, fonts='none'))
        pg.wait_for_selector('[data-rk-ready]', state='attached')
        assert pg.locator('.rk-sound').count() > 0
        return pg
    yield mount, errors
    pg.close()

def silent(pg):
    assert pg.evaluate('audio.contexts') == 0
    assert pg.evaluate('audio.nodes') == []

def pick(pg): pg.locator('.rk-gate .opts button').first.click()
def lock(pg): pg.locator('.rk-gate .go').click()

def test_explicit_play_and_reopen(sound_page):
    mount, errors = sound_page; pg=mount(spec())
    play=pg.locator('.rk-sound button')
    assert play.is_disabled() and not play.is_visible(); silent(pg)
    pg.evaluate("Rupaka.set(document.querySelector('[data-rupaka]'), {x:1})"); silent(pg)
    pick(pg); silent(pg)
    pg.evaluate("document.addEventListener('rk-predict', e=>{e.preventDefault(); window.savePrediction=e.detail.settle;})")
    lock(pg); silent(pg)
    assert pg.locator('.rk-gate .note').inner_text() == 'Saving your prediction.'
    pg.evaluate("savePrediction(false, 'Save failed')"); silent(pg)
    assert play.is_disabled()
    lock(pg); silent(pg)
    pg.evaluate('savePrediction(true)'); silent(pg)
    assert play.is_visible() and play.is_enabled()
    assert 'Synthesised' in pg.locator('.rk-sound').inner_text()
    link=pg.locator('.rk-sound a'); assert link.inner_text() == 'Hear it played'
    assert link.get_attribute('href') == REF['url']
    assert link.evaluate("e => {const p=document.createElement('span'); p.style.color='var(--rk-mute)'; e.parentNode.append(p); const c=getComputedStyle(p).color; p.remove(); return getComputedStyle(e).color===c;}")
    play.click()
    a=pg.evaluate('audio')
    assert a['contexts'] == 1 and a['resumes'] == 1
    assert [x['kind'] for x in a['starts']] == ['oscillator']*3+['noise']
    assert [x['v'] for x in a['params'] if x['kind']=='frequency'] == pytest.approx([138.59,277.18,415.77])
    assert any(x['kind']=='gain' and x['v']>0 for x in a['params'])
    assert len({x['t'] for x in a['starts']}) == 1
    pg.locator('.rk-gate .acts button').filter(has_text='Try another').click()
    assert play.is_disabled() and not play.is_visible()
    assert len(pg.evaluate('audio.stops')) > len(a['stops'])
    assert not errors

def test_host_restore_and_keyboard(sound_page):
    mount, errors=sound_page; pg=mount(spec())
    pg.evaluate("Rupaka.settle(document.querySelector('[data-rupaka]'), 'g', 'vibrating')")
    silent(pg)
    play=pg.locator('.rk-sound button'); play.focus(); pg.keyboard.press('w')
    assert len(pg.evaluate('audio.starts')) == 4
    pg.evaluate("Rupaka.open(document.querySelector('[data-rupaka]'), 'g')")
    assert play.is_disabled()
    assert not errors

def test_demo_screenshots(sound_page):
    mount, errors=sound_page
    assert 'sound' in examples()
    pg=mount(examples()['sound'])
    dest=Path('/Users/71293/code/personal/orgs/tmp_try/sketchd/music/slice1'); dest.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(dest/'mridangam-before.png'), full_page=True)
    silent(pg); pick(pg); lock(pg); silent(pg)
    assert pg.locator('.rk-sound:visible').count() == 2
    pg.screenshot(path=str(dest/'mridangam-after.png'), full_page=True)
    assert not errors
