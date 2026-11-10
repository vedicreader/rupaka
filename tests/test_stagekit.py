"The stage that rupaka took over from abhyasa: `rupaka.stagekit` (room_spec, is_local) and `rupaka/static/stage.js`."
import json, shutil, subprocess, sys
from importlib.resources import files
import pytest

def test_room_spec_takes_out_each_gate_answer():
    "room_spec takes `answer` out of a gate at any depth, and keeps the rest; a state-path gate keeps its state, where the value stays."
    from rupaka.stagekit import room_spec
    gate = dict(type='gate', id='g', prompt='Which?', options=['a', 'b'], answer={'is': 'b'})
    spec = dict(id='d', state=dict(best='b'), blocks=[dict(type='row', blocks=[dict(type='stack', blocks=[gate])]),
                                                       dict(type='gate', id='h', prompt='Best?', options={'from': 'opts'}, answer='best'),
                                                       dict(type='caption', answer='not a gate', text='x')])
    out = room_spec(spec)
    assert 'answer' not in out['blocks'][0]['blocks'][0]['blocks'][0] and out['blocks'][0]['blocks'][0]['blocks'][0]['options'] == ['a', 'b']
    assert 'answer' not in out['blocks'][1] and out['state'] == dict(best='b')
    assert out['blocks'][2]['answer'] == 'not a gate' and spec['blocks'][1]['answer'] == 'best' and gate['answer'] == {'is': 'b'}   # a copy

def test_room_spec_contract():
    "The contract that Leela tests: only a gate loses its answer, and the spec that went in does not change."
    from rupaka.stagekit import room_spec
    s = {'state': {'x': 2}, 'blocks': [{'type': 'row', 'blocks': [{'type': 'gate', 'id': 'g', 'answer': {'is': 'two'}, 'why': 'w'}]}, {'type': 'readout', 'answer': 1}]}
    assert room_spec(s) == {'state': {'x': 2}, 'blocks': [{'type': 'row', 'blocks': [{'type': 'gate', 'id': 'g', 'why': 'w'}]}, {'type': 'readout', 'answer': 1}]}
    assert s['blocks'][0]['blocks'][0]['answer'] == {'is': 'two'}

HOSTILE = ('https://evil.example/x', '//evil.example', '/\\evil.example', '\\\\evil.example', 'javascript:alert(1)', 'data:text/html,hi', 'w/g', '', None, 3,
           '/\t/evil.example', '/\n/evil.example', ' /w/g', '/w/g\x00', '/w\\..\\x')

def test_is_local_takes_only_a_path_in_the_app():
    from rupaka.stagekit import is_local
    assert is_local('/w/g-1a2b/0') and is_local('/w/g?x=1#check')
    for bad in HOSTILE: assert not is_local(bad), bad

def test_stagekit_imports_only_the_standard_library():
    "Leela imports room_spec and is_local with no web code and no browser driver."
    code = "import rupaka.stagekit, sys; assert not {'playwright', 'fastcore', 'rupaka.render'} & set(sys.modules), sorted(sys.modules)"
    subprocess.run([sys.executable, '-I', '-c', code], check=True)

def test_stage_js_is_found_by_importlib_resources():
    "A consumer reads the file from the installed package, so it must be package data."
    f = files('rupaka') / 'static' / 'stage.js'
    assert f.is_file()
    src = f.read_text()
    assert 'abhyasaStage' in src and 'rupakaStage' in src and 'room' in src

def test_stage_js_ships_in_the_wheel():
    "The hatchling wheel takes the whole `rupaka` package, so `static/stage.js` and `stagekit.py` are in it."
    import tomllib
    from pathlib import Path
    cfg = tomllib.loads((Path(__file__).parents[1] / 'pyproject.toml').read_text())
    assert cfg['tool']['hatch']['build']['targets']['wheel']['packages'] == ['rupaka']

@pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')
def test_stage_js_checks_messages_in_node():
    "The file loads in node, and `valid` takes a good message and drops a bad one."
    js = str(files('rupaka') / 'static' / 'stage.js')
    code = ("const s = require(process.argv[1]); process.stdout.write(JSON.stringify([s.V, s.valid({v: 1, t: 'go', slide: 's1', beat: 2}), "
            "s.valid({v: 1, t: 'go', slide: 's1', beat: 2.5}), s.isLocal('/w/x'), s.isLocal('//evil.example')]))")
    out = subprocess.run(['node', '-e', code, js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [1, True, False, True, False]
