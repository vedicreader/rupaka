"Each gallery demo passes validate and the whole headless check; screenshots go to tests/screens/ for a person to look at."
from pathlib import Path
import pytest
from rupaka.spec import gallery, validate
from rupaka.check import check

G = gallery()
SCREENS = Path(__file__).parent/'screens'

@pytest.mark.parametrize('name', sorted(G))
def test_gallery_demo(br, name):
    assert validate(G[name]) == []
    r = check(G[name], shots=SCREENS, b=br)
    assert r.errors == []
    assert all(i and i['verdict'] for i in r.info['light'])
