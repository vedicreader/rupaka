"The fns in the browser give the same values as their Python twins; expr refuses unsafe text."
import math
import pytest
from rupaka.spec import run, parse_expr, gallery

def js_run(draw, spec):
    d = draw({**spec, 'id': 'f', 'blocks': [dict(type='readout', text='x')]})
    return d.st()

def close(a, b): return all(math.isclose(x['value'], y['value'], rel_tol=1e-9) and x['id'] == y['id'] for x, y in zip(a, b)) and len(a) == len(b)

@pytest.mark.parametrize('k', [60, 1])
def test_rrf_matches_python(draw, k):
    spec = dict(state=dict(bm25=list('ACEB'), vec=list('DFGB'), k=k), derive=[dict(fn='rrf', k='k', out='fused', **{'in': ['bm25', 'vec']})])
    assert close(js_run(draw, spec)['fused'], run(spec)['fused'])

@pytest.mark.parametrize('t', [0.5, 1, 2])
def test_softmax_matches_python(draw, t):
    spec = dict(state=dict(z=[2, 1, 0.5, -1], t=t), derive=[dict(fn='softmax', t='t', labels=list('abcd'), sort=True, out='p', **{'in': 'z'})])
    js, py = js_run(draw, spec)['p'], run(spec)['p']
    assert close(js, py) and math.isclose(sum(x['value'] for x in js), 1)

def test_rules_alts_match_python(draw):
    s = gallery()['vowel-sandhi']
    for a, b in [('a', 'i'), ('e', 'a'), ('u', 'ā'), ('ai', 'o')]:
        spec = {**s, 'state': dict(a=a, b=b)}
        js, py = js_run(draw, spec)['join'], run(spec)['join']
        assert (js['out'], js['alts']) == (py['out'], py['alts'])

def test_expr_both_sides(draw):
    d = draw(dict(id='e', state=dict(x=3), blocks=[dict(type='readout', text='x')]))
    assert d.pg.evaluate("Rupaka.expr('2*x^2 - 1')({x: 3})") == 17 == parse_expr('2*x^2 - 1')[0](dict(x=3))
    for bad in ('constructor', '__proto__', 'alert(1)', 'x;y', 'toString()'):
        assert d.pg.evaluate(f"() => {{ try {{ Rupaka.expr({bad!r})({{x: 1, y: 2}}); return 'ran'; }} catch (e) {{ return e.message; }} }}").startswith('expr:'), bad

def test_path_reads_own_keys_only(draw):
    d = draw(dict(id='g', state=dict(o=dict(a=1)), blocks=[dict(type='readout', text='{o.constructor}|{o.__proto__}|{o.a}')]))
    assert d.pg.locator('.rk-readout .big').inner_text() == '||1'
