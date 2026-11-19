"Embedded instrument profiles: sourced data, a stable hash, sound.play, and gate hides on profile techniques."
import json, re
from copy import deepcopy
from pathlib import Path
import pytest
import rupaka.spec as S
from rupaka.agent import catalog, demo_sp
from rupaka.skill import skill_md

VIOLIN = json.loads((Path(__file__).parent/'violin_profile.json').read_text())
NAM = 'profiles.mridangam.techniques.nam'

def demo(): return deepcopy(S.gallery()['mridangam-profile'])
def data(): return demo()['profiles']['mridangam']['data']
def embed(d, school=None): return dict(id='p', revision=S.profile_hash(d), data=d, **({'school': school} if school else {}))
def errs(spec): return list(S.validate(spec))

def with_data(d, school='tanjore'):
    s = demo(); s['profiles']['mridangam'] = embed(d, school); return s

def test_hash_is_canonical_sha256_of_data():
    d = data(); h = S.profile_hash(d)
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', h)
    assert S.profile_hash(json.loads(json.dumps(d, sort_keys=True))) == h
    assert S.profile_hash(dict(reversed(list(d.items())))) == h
    assert S.profile_hash({**d, 'label': 'Other'}) != h
    with pytest.raises(ValueError): S.profile_hash({'x': float('nan')})

def test_fixtures_are_good():
    assert S.profile_errors(data()) == []
    assert S.profile_errors(VIOLIN) == []
    assert errs(demo()) == []
    assert all(p['kind'] == 'string' for p in VIOLIN['parts'].values())
    assert not any('voice' in t for t in VIOLIN['techniques'].values())

def test_slice1_demo_is_unchanged():
    assert S.examples()['sound'] == S.gallery()['mridangam-strokes']
    assert 'profiles' not in S.gallery()['mridangam-strokes']

def _set(d, path, v):
    *ks, last = path.split('.')
    for k in ks: d = d[int(k)] if isinstance(d, list) else d[k]
    if v is ...: del d[last]
    elif isinstance(d, list): d[int(last)] = v
    else: d[last] = v
    return d

@pytest.mark.parametrize('path,value,where', [
    ('sources.nam-palani.url', 'ftp://x.test/a', 'sources.nam-palani.url'),
    ('sources.nam-palani.passage', ..., 'sources.nam-palani.passage'),
    ('sources.nam-palani.passage', '  ', 'sources.nam-palani.passage'),
    ('sources.nam-palani.date', '2024-01-01', 'sources.nam-palani.date'),
    ('parts.right-outer.kind', 'pedal', 'parts.right-outer.kind'),
    ('parts.right-outer.sources', ['nope'], 'parts.right-outer.sources'),
    ('parts.right-outer.sources', [], 'parts.right-outer.sources'),
    ('techniques.nam.parts', ['nope'], 'techniques.nam.parts'),
    ('techniques.nam.facts.0.school', 'mysore', 'techniques.nam.facts[0].school'),
    ('techniques.nam.facts.0.value', float('nan'), 'techniques.nam.facts[0].value'),
    ('techniques.nam.voice.frequency', 9000, 'techniques.nam.voice.frequency'),
    ('techniques.nam.voice.sample', 'https://bad.test/a.wav', 'techniques.nam.voice.sample'),
    ('schools.palani.sources', ['nope'], 'schools.palani.sources'),
    ('label', ..., 'label'),
    ('extra', 1, 'extra')])
def test_profile_refusals(path, value, where):
    d = data(); _set(d, path, value)
    assert any(e.startswith(f'{where}:') for e in S.profile_errors(d)), S.profile_errors(d)

def test_fact_keys_are_general_or_per_school():
    d = data(); fs = d['techniques']['nam']['facts']
    fs.append(deepcopy(next(f for f in fs if f.get('school') == 'palani')))
    assert any('twice' in e for e in S.profile_errors(d))
    d = data(); fs = d['techniques']['nam']['facts']
    fs.append({**next(f for f in fs if f.get('school')), 'school': None}); fs[-1].pop('school')
    assert any('both' in e for e in S.profile_errors(d))

def test_bounds():
    d = data(); src = d['sources']['tha']
    d['sources'] = {f's{i}': src for i in range(17)}
    assert any(e.startswith('sources:') for e in S.profile_errors(d))
    d = data(); d['techniques']['tha']['facts'] *= 13
    assert any(e.startswith('techniques.tha.facts:') for e in S.profile_errors(d))
    d = data(); d['label'] = 'x' * 40000
    assert any('32' in e for e in S.profile_errors(d))

def test_embed_checks():
    s = demo(); s['profiles']['mridangam']['revision'] = 'sha256:' + '0' * 64
    assert any(e.startswith('profiles.mridangam.revision:') for e in errs(s))
    s = demo(); s['profiles']['mridangam']['school'] = 'mysore'
    assert any(e.startswith('profiles.mridangam.school:') for e in errs(s))
    s = demo(); s['profiles']['mridangam']['data']['sources']['tha']['url'] = 'javascript:alert(1)'
    assert any(e.startswith('profiles.mridangam.data.sources.tha.url:') for e in errs(s))
    s = demo(); s['profiles']['mridangam']['extra'] = 1
    assert any(e.startswith('profiles.mridangam.extra:') for e in errs(s))

def _sound(s): return next(i for i, b in enumerate(s['blocks']) if b['type'] == 'sound' and b.get('play', {}).get('technique') == 'nam')

def test_play_references():
    s = demo(); i = _sound(s); s['blocks'][i]['play']['technique'] = 'dhi'
    assert any(e.startswith(f'blocks[{i}].play:') for e in errs(s))
    s = demo(); s['blocks'][i]['play']['profile'] = 'veena'
    assert any(e.startswith(f'blocks[{i}].play:') for e in errs(s))
    s = demo(); s['blocks'][i]['voice'] = deepcopy(s['profiles']['mridangam']['data']['techniques']['nam']['voice'])
    assert f'blocks[{i}]: needs exactly one of voice, play' in errs(s)
    s = demo(); del s['blocks'][i]['play']
    assert f'blocks[{i}]: needs exactly one of voice, play' in errs(s)

def test_play_accepts_technique_with_no_voice():
    s = demo(); s['profiles']['violin'] = embed(VIOLIN)
    i = _sound(s); s['blocks'][i]['play'] = dict(profile='violin', technique='open-pa')
    assert errs(s) == []

def test_declared_technique_must_wait_for_its_gate():
    s = demo(); i = _sound(s); g = s['blocks'][0]
    assert NAM in g['hides'] and s['blocks'][i]['after'] == g['id']
    del s['blocks'][i]['after']
    assert any(e.startswith(f'blocks[{i}]:') and f'gate "{g["id"]}"' in e for e in errs(s))

def test_only_the_declaring_gate_needs_a_wait():
    s = demo()
    s['blocks'].insert(0, dict(type='gate', id='other', prompt='Which side is the right side?', options=['left', 'right'], answer={'is': 'right'}))
    assert errs(s) == []

def test_undeclared_listening_first_is_allowed():
    s = demo(); tha = [b for b in s['blocks'] if b['type'] == 'sound' and b['play']['technique'] == 'tha']
    assert tha and all('after' not in b for b in tha)
    assert errs(s) == []

def test_hides_refs_are_checked_not_treated_as_state():
    s = demo(); s['blocks'][0]['hides'] = ['profiles.mridangam.techniques.dhi']
    e = errs(s)
    assert any(x.startswith('blocks[0].hides:') and 'dhi' in x for x in e)
    assert not any('"profiles" is not in state' in x for x in e)
    s = demo(); s['blocks'][0]['hides'] = ['profiles.mridangam']
    assert any(x.startswith('blocks[0].hides:') for x in errs(s))

def test_malformed_input_gives_errors_not_exceptions():
    for hides in ([[1]], 5):
        s = demo(); s['blocks'][0]['hides'] = hides
        assert any(e.startswith('blocks[0].hides:') for e in errs(s))
    s = demo(); s['profiles'][1] = s['profiles']['mridangam']
    assert any(e.startswith('profiles.1:') for e in errs(s))

def test_technique_sources_name_no_school():
    d = data(); schooled = {s for t in d['techniques'].values() for f in t['facts'] if f.get('school') for s in f['sources']}
    general = {s for t in d['techniques'].values() for s in t['sources'] + [x for f in t['facts'] if not f.get('school') for x in f['sources']]}
    assert not schooled & general

def test_state_answer_gate_still_enforces_declared_technique():
    s = demo(); i = _sound(s); g = s['blocks'][0]
    s['state']['best'] = g['answer']['is']; g['answer'] = 'best'; del s['blocks'][i]['after']
    assert any(e.startswith(f'blocks[{i}]:') for e in errs(s))

def test_reveal_shows_school_facts_and_sources(draw):
    from rupaka.render import page
    from test_sound import RECORDER
    s = demo(); d = draw(s, html='<script>'+RECORDER+'</script>'+page(s, fonts='none'))
    tha, nam = d.pg.locator('.rk-sound').nth(0), d.pg.locator('.rk-sound').nth(1)
    assert tha.is_visible() and not nam.is_visible()
    assert 'tone: non-vibrating' in tha.inner_text() and 'Synthesised approximation' in tha.inner_text()
    d.lock(2)
    t = nam.inner_text()
    assert nam.is_visible() and 'support (Tanjore style): ring finger' in t and 'middle finger' not in t
    hrefs = nam.locator('a.rk-sound-src').evaluate_all('es => es.map(e => e.href)')
    assert hrefs and all(h.startswith('https://') for h in hrefs)
    assert not any('Middle finger' in x for x in nam.locator('a.rk-sound-src').evaluate_all('es => es.map(e => e.title)'))
    assert d.pg.evaluate('audio.contexts') == 0
    nam.locator('button').click()
    assert len(d.pg.evaluate('audio.starts')) == 4
    s = demo(); del s['profiles']['mridangam']['school']
    d2 = draw(s); d2.lock(2)
    assert 'support (no school chosen): unknown' in d2.pg.locator('.rk-sound').nth(1).inner_text()
    assert d.errors == [] and d2.errors == []

def test_public_shape_is_taught():
    assert 'play' in catalog() and 'profiles' in demo_sp()
    assert 'profiles' in skill_md() and 'play' in skill_md()
