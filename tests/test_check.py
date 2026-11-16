"The headless check reads a 3D scene as a person sees it: a chip over the scene is measured against the pixels under it."
from rupaka.spec import demo, gate, expr, scene, body, label3d
from rupaka.check import check, contrast
from test_scene import settled

def sun_demo():
    return demo('m', 'Moon', state=dict(a=0), derive=[expr('a + 1', 'b')],
                blocks=[gate('g', 'What is a + 1?', [1, 2], 'b'),
                        scene(body('sun', 'sphere', [3], texture='sun', glow=1), label3d('Sun: the light source', on='sun'), look='sky')])

def test_chip_over_a_bright_sun(br, draw):
    "A sky chip over a big glowing Sun reads in both modes. A chip with no fill there would not, and the measure reads the pixels under it."
    assert not [e for e in check(sun_demo(), b=br).errors if 'contrast' in e]
    d = draw(sun_demo()); settled(d.pg)
    d.pg.add_style_tag(content='.rk-scene .stage[data-look="sky"] .rk-chip { background: none !important; color: #fff !important; text-shadow: none !important; }')
    d.pg.wait_for_timeout(300)
    assert any(t == 'Sun: the light source' for t, *_ in contrast(d.pg))
