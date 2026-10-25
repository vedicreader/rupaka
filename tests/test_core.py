"The core runtime: mount, boot one time, the error state, the theme vars, and no network."
import pytest
from rupaka.render import page, bundle

ONE = dict(rupaka=1, id='one', state=dict(a=7), blocks=[dict(type='readout', text='a is {a}')])

def test_blank_page_has_no_errors(br):
    pg = br.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(e)); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    pg.set_content('<p>blank</p>')
    assert errs == []

def test_fetch_is_seen_as_network(draw):
    d = draw(ONE, html=page(ONE, fonts='none').replace('</body>', '<script>fetch("https://example.com").catch(() => 0)</script></body>'))
    d.pg.wait_for_timeout(300)
    assert any('network https://example.com' in e for e in d.errors)

def test_readout_mounts_and_boots_once(draw):
    d = draw(ONE)
    assert d.pg.locator('.rk-readout .big').inner_text() == 'a is 7'
    assert d.pg.locator('[data-rupaka]').get_attribute('data-rk-ready') == '1'
    d.pg.evaluate('Rupaka.boot(); Rupaka.boot()')
    assert d.pg.locator('.rk').count() == 1 and d.errors == []

def test_bad_spec_shows_a_line(draw):
    d = draw(None, html=page({**ONE, 'blocks': [dict(type='dial')]}, fonts='none'))
    assert 'unknown block "dial"' in d.pg.locator('.rk-err').inner_text()
    assert d.pg.locator('[data-rupaka]').get_attribute('data-rk-ready') == 'error'

def test_newer_schema_is_refused(draw):
    d = draw(None, html=page({**ONE, 'rupaka': 3}, fonts='none'))
    assert 'schema 3 is not supported' in d.pg.locator('.rk-err').inner_text()

def test_script_in_spec_text_still_mounts(draw):
    d = draw({**ONE, 'ask': 'Text with </script><script>window.BAD=1</script> in it.'})
    assert d.pg.evaluate('window.BAD') is None and '</script>' in d.pg.locator('.rk-ask').inner_text()

@pytest.mark.parametrize('var,val', [('--fg', 'rgb(10, 120, 30)'), ('--mh-ink', 'rgb(200, 20, 20)'), ('--lee-fg', 'rgb(20, 20, 200)')])
def test_theme_var_chain(br, var, val):
    "A host that sets only abhyasa's, vedicreader's or leela's var gives the demo that colour."
    html = (f'<html><head><style>:root {{ {var}: {val}; }}</style><style>{bundle("css")}</style></head><body>'
            f'<div data-rupaka><script type="application/json">{{"id":"t","state":{{}},"blocks":[{{"type":"readout","text":"x"}}]}}</script></div>'
            f'<script>{bundle()}</script></body></html>')
    pg = br.new_page(); pg.set_content(html); pg.wait_for_selector('[data-rk-ready]')
    assert pg.evaluate("getComputedStyle(document.querySelector('.rk-readout .big')).color") == val
    pg.close()

def test_shadow_root_mount(br):
    "A host in a shadow root mounts with Rupaka.boot(root), and the predict event crosses the shadow boundary."
    pg = br.new_page()
    pg.set_content(f'<div id="h"></div><script>{bundle()}</script>')
    pg.evaluate("""() => { const r = document.getElementById('h').attachShadow({mode: 'open'}); window.__ev = [];
      document.addEventListener('rk-predict', e => __ev.push(e.detail));
      r.innerHTML = '<div data-rupaka><script type="application/json">' + JSON.stringify({id: 's', state: {a: 1}, derive: [{fn: 'expr', expr: 'a + 1', out: 'b'}],
        blocks: [{type: 'gate', id: 'g', prompt: 'a + 1?', options: [1, 2], answer: 'b'}]}) + '</' + 'script></div>'; Rupaka.boot(r);
      r.querySelector('.opts button:nth-child(2)').click(); r.querySelector('button.go').click(); }""")
    assert pg.evaluate('__ev[0].ok') is True
    pg.close()
