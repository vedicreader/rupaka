"The film scene: it parses with no manimgl, and it draws each figure kind that a plan of a gallery demo gives."
import ast
from rupaka.spec import gallery
from rupaka.film import plan, SCENE

def kinds() -> set:
    "The keys of `KINDS` in the scene."
    t = ast.parse(SCENE.read_text())
    d = next(n.value for n in t.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'KINDS')
    return {k.arg for k in d.keywords}

def used(fs):
    for f in fs:
        yield f['k']
        yield from used(f.get('items', []) if f['k'] in ('row', 'stack') else [])

def test_scene_parses(): assert {'axis', 'bars', 'wheel', 'flow', 'pair'} <= kinds()

def test_scene_draws_each_kind():
    need = {k for s in gallery().values() for b in plan(s)['beats'] for fs in b['frames'] for k in used(fs)}
    assert need <= kinds(), need - kinds()

def test_scene_reads_only_data():
    src = SCENE.read_text()
    assert not any(w in src for w in ('eval(', 'exec(', 'import subprocess', '__import__')), 'the scene must not run code from the plan'
