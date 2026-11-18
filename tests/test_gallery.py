"Each gallery demo passes validate and the whole headless check; screenshots go to tests/screens/ for a person to look at."
from pathlib import Path
import pytest
from rupaka.spec import gallery, validate, run
from rupaka.check import check

G = gallery()
SCREENS = Path(__file__).parent/'screens'

@pytest.mark.parametrize('name', sorted(G))
def test_gallery_demo(br, name):
    assert validate(G[name]) == []
    r = check(G[name], shots=SCREENS, b=br)
    assert r.errors == []
    assert all(i and i['verdict'] for i in r.info['light'])

def test_bubble_trace_views_show_one_run(draw):
    "The gate answer is the swap count of the sorted run, and a new input starts its own run at step 0, so no view shows an old run."
    s = G['bubble-trace']
    assert s['blocks'][0]['answer'] == {'is': run(s, {**s['state'], 'pick': 'sorted [1, 2, 3, 4]', 'tick': 6})['at']['swaps']}
    d = draw(s); d.lock(1)
    big = lambda: d.pg.locator('.rk-readout .big').inner_text()
    tl = d.pg.locator('.rk-timeline input')
    tl.focus(); d.pg.keyboard.press('Shift+d')
    assert d.st('tick') == 6 and big() == 'sorted: 6 of 6 compares, 0 swaps'
    d.pg.locator('.rk-choice button').nth(0).click()                # reversed
    assert d.st('tick') == 0 and big() == 'reversed: 0 of 6 compares, 0 swaps'
    tl.focus(); d.pg.keyboard.press('Shift+d')
    assert big() == 'reversed: 6 of 6 compares, 6 swaps' and d.errors == []
