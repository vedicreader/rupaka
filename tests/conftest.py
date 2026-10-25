"A headless browser for the whole session, and `draw(spec)`: a page that holds one demo and collects errors."
import pytest
from rupaka.check import browser, can_check
from rupaka.render import page

def pytest_collection_modifyitems(config, items):
    if not can_check():
        skip = pytest.mark.skip(reason='no browser for playwright')
        for it in items:
            if 'br' in getattr(it, 'fixturenames', ()): it.add_marker(skip)

@pytest.fixture(scope='session')
def br():
    with browser() as b: yield b

class Drawn:
    "A page with one demo: `st()` reads its state, `errors` holds console errors, page errors and network requests."
    def __init__(self, pg, errors): self.pg, self.errors = pg, errors
    def st(self, k=None):
        s = self.pg.evaluate("JSON.parse(JSON.stringify(document.querySelector('[data-rupaka]').rupaka.st))")
        return s if k is None else s[k]
    def lock(self, n=1, gate=0):
        "Pick option `n` of a gate with its key, and lock in with ⌘↩."
        g = self.pg.locator('.rk-gate').nth(gate)
        g.locator('.opts button').first.focus(); self.pg.keyboard.press(str(n)); self.pg.keyboard.press('Meta+Enter')

@pytest.fixture
def draw(br):
    pages = []
    def f(spec, html=None, mode='light'):
        pg = br.new_page(viewport=dict(width=720, height=900), color_scheme=mode)
        errs = []
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('request', lambda r: r.url.split(':')[0] not in ('file', 'data', 'about') and errs.append(f'network {r.url}'))
        pg.set_content(html or page(spec, fonts='none'))
        pg.wait_for_selector('[data-rk-ready]', state='attached')
        pages.append(pg)
        return Drawn(pg, errs)
    yield f
    for p in pages: p.close()
