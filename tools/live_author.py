"Author demos with a real Claude model (the claude CLI), check each one in a headless browser, and save the spec, the page and the shots."
import json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from rupaka.agent import author
from rupaka.check import check
from rupaka.render import save

CASES = {
 'panchangam': dict(name='Panchangam sky: tithi and nakshatra from the Sun and the Moon', subject='astronomy',
    statement='Earth is at the centre. The Sun and the Moon move round the ecliptic ring, which has 27 equal nakshatra sectors of 13.33 degrees. '
              'The nakshatra is the sector that holds the Moon. The tithi counts each 12 degrees of the angle from the Sun to the Moon, so 30 tithis make one lunar month. '
              'The learner drags the Sun or the Moon round the ring and sees the tithi and the nakshatra change.',
    misconceptions=['the tithi is a solar day', 'the nakshatra is set by the Sun', 'a tithi always lasts 24 hours']),
 'attention': dict(name='Attention in a transformer', subject='machine learning',
    statement='Each word makes a query. It scores every word key by a dot product, divides by a temperature, and uses softmax to get weights. '
              'A low temperature puts almost all the weight on one word. The word then takes a mix of the values of the others by those weights. Show it as a 3D scene: words as boxes in a row, with arcs as thick as the weights.',
    misconceptions=['attention picks exactly one word', 'the weights of a word do not add up to 1']),
 'circuit': dict(name='Current in a series circuit', subject='physics',
    statement='A battery of V volts drives a current I = V / R through a loop with a resistor of R ohms. The power in the resistor is P = V * I. '
              'Charge moves faster in a loop when the current is larger. Two resistors in series add up: R = R1 + R2.',
    misconceptions=['a resistor uses up the current', 'the current is larger before the resistor than after it']),
 'ww2': dict(name='The Pacific War 1941 to 1945: the island-hopping advance', subject='history',
    statement='After Pearl Harbor on 7 December 1941, Japan took a wide arc of islands by mid 1942. From 1942 the Allies took back the islands one by one, '
              'and skipped the strongest bases. Guadalcanal fell in February 1943, Tarawa in November 1943, Saipan in July 1944, Iwo Jima in March 1945 and Okinawa in June 1945. '
              'Each step brought the Allied bombers closer to Japan. Show it as a 3D scene: a globe or map with the routes, and a slider for the date.',
    misconceptions=['the Allies took every island on the way', 'the war in the Pacific ended with Midway']),
 'tides': dict(name='Spring and neap tides', subject='physics',
    statement='The tide has two bulges on Earth: one toward the Moon and one away from it. At new moon and full moon the Sun, Earth and Moon are in a line, '
              'and the pulls add up to a spring tide. At the quarter moons the pulls are at a right angle, and the tide is a neap tide.',
    misconceptions=['there is one bulge, under the Moon', 'the Sun has no effect on the tides']),
}

def claude_ask(model='sonnet', effort=None):
    "An `ask(prompt, sp)` for `author` that calls the claude CLI with no tools."
    def ask(prompt, sp):
        cmd = ['claude', '-p', prompt, '--system-prompt', sp, '--model', model, '--tools', '', '--no-session-persistence', '--disable-slash-commands']
        if effort: cmd += ['--effort', effort]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode: raise RuntimeError(r.stderr[-400:] or f'exit {r.returncode}')
        return r.stdout
    return ask

def run(key, out, model='sonnet', level='', effort=None):
    "Author case `key`, check it, and save `<key>.json`, `<key>.html`, the shots and a log under `out`."
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    log, t0 = [], time.time()
    spec = author(CASES[key], claude_ask(model, effort), repairs=2, log=log, level=level)
    res = dict(key=key, secs=round(time.time() - t0), tries=len(log) + 1, log=log, ok=False)
    if spec:
        (out/f'{key}.json').write_text(json.dumps(spec, indent=1, ensure_ascii=False))
        save(spec, out/f'{key}.html', fonts='none')
        c = check(spec, shots=out/'shots', modes=('light',))
        res.update(ok=c.ok, errors=c.errors, shots=[str(s) for s in c.shots])
    (out/f'{key}.log.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res

if __name__ == '__main__':
    out, keys = sys.argv[1], sys.argv[2:] or list(CASES)
    with ThreadPoolExecutor(len(keys)) as ex:
        for r in ex.map(lambda k: run(k, out), keys): print(r['key'], 'ok' if r['ok'] else 'FAIL', f"{r['secs']}s", 'tries', r['tries'], r.get('errors', r['log'])[:3])
