"The Python text of a value is the browser text: `js_str` is `String(v)`, `show_value` is `Rupaka.show`, and `of_gate` gives the text of the drawn gate."
import math
import pytest
from rupaka.spec import js_str, show_value
from rupaka.poll import of_gate

VALS = [0, 7, -3, 2.0, 0.1, 1.5, -1.5, -0.0, 1/3, 0.1 + 0.2, 1.03125, -1.03125, 1e21, -1e21, 1.5e300, 123456789012345680000.0, 2**53 + 2, 1e16,
        1e-7, 1.5e-5, 0.000001, 5e-324, math.inf, -math.inf, True, False, None, 'hi', 'a-b', [1, None, 2.5], dict(a=1)]

def blank(draw): return draw(dict(id='s', state=dict(x=1), blocks=[dict(type='readout', text='x')]))

def test_js_str_is_String(draw):
    js = blank(draw).pg.evaluate('vs => vs.map(v => String(v))', VALS)
    assert [(repr(v), s) for v, s in zip(VALS, js)] == [(repr(v), js_str(v)) for v in VALS]

@pytest.mark.parametrize('n', [None, 0, 2, 6, 9])
def test_show_value_is_show(draw, n):
    js = blank(draw).pg.evaluate('([vs, n]) => vs.map(v => Rupaka.show(v, n))', [VALS, n])
    assert [(repr(v), s) for v, s in zip(VALS, js)] == [(repr(v), show_value(v, n)) for v in VALS]

def test_of_gate_is_the_drawn_gate(draw):
    spec = dict(id='q', state=dict(b=2.0, t=0.1, x=-1.5, z=-0.0, n=None, ok=True, big=1e21, tiny=1e-7, p=1/3),
                blocks=[dict(type='gate', id='g', prompt='{b} {t} {x} {z} {n} {ok} {big} {tiny} {p} {p:2}',
                             options=[2.0, 0.1, -1.5, 1.03125, True], answer={'is': 2.0})])
    d, q = draw(spec), of_gate(spec, 'g')
    assert d.pg.evaluate("document.querySelector('.rk-gate .q').textContent") == q['q']
    assert d.pg.evaluate("[...document.querySelectorAll('.rk-gate .opts button')].map(b => b.firstChild.textContent)") == q['options']
    assert not d.errors
