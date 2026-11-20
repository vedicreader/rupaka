/* listen: opt-in microphone timing on this device. Only a click on Listen on this device asks for the microphone. The sound goes to an
   onset worklet (rupaka/static/listen-worklet.js, served beside rupaka.js) and is not kept: no recorder, no stored audio, no network.
   The beats are times in seconds on the shared page clock, ctx.audio(). */
(() => {
  const SRC = document.currentScript?.src || '', query = SRC.match(/\?[^#]*/)?.[0] || '';   // the bundle and this block are one script
  const us = d => Math.round(d * 1e6) / 1e3;   // seconds to ms, rounded to a microsecond, so that 1.03 - 1 gives 30 ms
  const median = a => { const s = [...a].sort((x, y) => x - y), n = s.length; return n ? (n % 2 ? s[n >> 1] : (s[n / 2 - 1] + s[n / 2]) / 2) : null; };

  // Each beat takes the nearest onset within ±min(half the gap to its next beat, window) ms. The closest pairs go first, and one onset
  // goes to one beat at most. Within ±tolerance ms it is 'on'; else 'early' or 'late' with signed ms; with no onset, 'missed'.
  const match = (beats, onsets, {tolerance = 30, window = 150} = {}) => {
    const bs = (beats || []).map(Number), os = (onsets || []).map(Number), pairs = [];
    bs.forEach((t, i) => {
      const gap = Math.min(i > 0 ? Math.abs(us(t - bs[i - 1])) : Infinity, i < bs.length - 1 ? Math.abs(us(bs[i + 1] - t)) : Infinity);
      const reach = Math.min(window, gap / 2);
      os.forEach((o, j) => { const d = us(o - t); if (Math.abs(d) <= reach) pairs.push([Math.abs(d), i, j, d]); });
    });
    pairs.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const got = new Map(), used = new Set();
    for (const [, i, j, d] of pairs) if (!got.has(i) && !used.has(j)) { got.set(i, d); used.add(j); }
    return bs.map((beat, i) => {
      if (!got.has(i)) return {beat, verdict: 'missed', ms: null};
      const d = got.get(i);
      return {beat, verdict: Math.abs(d) <= tolerance ? 'on' : d < 0 ? 'early' : 'late', ms: Math.round(d * 10) / 10 || 0};
    });
  };

  // Tap-to-calibrate: the median ms of the taps after their clicks. An onset in the 40 ms after a click is the speaker that the
  // microphone hears, so it does not count. With fewer than four taps, null. `wide` when the taps spread (SD) more than 30 ms.
  const calib = (clicks, onsets, {window = 150, bleed = 40} = {}) => {
    const cs = (clicks || []).map(Number);
    const kept = (onsets || []).map(Number).filter(o => !cs.some(c => { const d = us(o - c); return d >= 0 && d <= bleed; }));
    const ds = match(cs, kept, {window, tolerance: 0}).filter(r => r.ms != null).map(r => r.ms);
    if (ds.length < 4) return null;
    const mean = ds.reduce((a, d) => a + d, 0) / ds.length, sd = Math.sqrt(ds.reduce((a, d) => a + (d - mean) ** 2, 0) / ds.length);
    return {ms: median(ds), spread: Math.round(sd * 10) / 10, n: ds.length, wide: sd > 30};
  };

  const loaded = new WeakMap();   // context -> the promise of its worklet module
  const say = r => r.verdict === 'missed' || r.verdict === 'on' ? r.verdict : `${r.verdict} ${Math.abs(Math.round(r.ms))} ms`;

  Rupaka.block('listen', Object.assign((b, ctx) => {
    const {el} = Rupaka, key = b.beats?.[0], outKey = b.out?.[0], tolerance = b.tolerance ?? 30, window_ = b.window ?? 150;
    const button = (text, k) => {
      const e = el('button', {type: 'button'}, text, el('kbd', {text: k.toUpperCase()}));
      e.addEventListener('keydown', ev => {
        if (ev.key.toLowerCase() !== k || ev.repeat || ev.metaKey || ev.ctrlKey || ev.altKey) return;
        ev.preventDefault(); e.click();
      });
      return e;
    };
    const start = button('Listen on this device', 'w'), stop = button('Stop listening', 's'), cal = button('Calibrate', 'e');
    const status = el('p', {class: 'rk-note rk-listen-status', 'aria-live': 'polite'});
    const why = el('p', {class: 'rk-note rk-listen-why', hidden: true});
    const list = el('ul', {class: 'rk-listen-out', 'aria-live': 'polite'});
    const root = el('div', {}, el('span', {class: 'rk-lbl', text: 'Microphone timing'}), el('div', {class: 'rk-listen-acts'}, start, stop, cal),
      status, why, list, el('p', {class: 'rk-note', text: 'The sound stays on this device. Nothing is recorded or sent.'}));
    let mic = null, epoch = 0, heard = [], shift = 0, busy = false, seen = null, timer = 0, clock = 0;

    const can = () => !!(Rupaka.base && navigator.mediaDevices?.getUserMedia && window.AudioWorkletNode && (window.AudioContext || window.webkitAudioContext));
    const show = () => { start.hidden = !!mic; stop.hidden = !mic; cal.hidden = !mic || b.calibrate === false; };
    const none = () => {
      why.textContent = 'The microphone is not available here.'; why.hidden = false; status.textContent = '';
      [start, stop, cal].forEach(x => { x.hidden = true; });
    };
    const end = () => {
      epoch++; busy = false; clearTimeout(timer); clearTimeout(clock);
      if (!mic) return;
      const m = mic; mic = null; clearInterval(m.alive);
      m.stream.getTracks().forEach(t => t.stop());
      m.node.port.onmessage = null;
      [m.src, m.node, m.mute].forEach(n => n.disconnect());
    };
    const late = ac => mic.lat + (ac.outputLatency || 0);   // the input and output latency, in seconds

    const judge = beats => {
      const ac = ctx.audio(), res = match(beats, heard.map(t => t - late(ac) - shift), {tolerance, window: window_});
      list.replaceChildren(...res.map((r, i) => el('li', {text: `Beat ${i + 1}: ${say(r)}`})));
      if (outKey) ctx.s.set(outKey, res);
    };
    // When the beats change, wait until their last beat (and its window) has passed on the page clock, then judge them.
    const watch = () => {
      const beats = key ? ctx.s.get(key) : null, sig = JSON.stringify(beats ?? null);
      if (sig === seen) return;
      seen = sig; clearTimeout(timer);
      if (!mic || !Array.isArray(beats) || !beats.length || !beats.every(Number.isFinite)) return;
      const last = Math.max(...beats), ticket = epoch;
      if (last < mic.from) return;   // a round from before the microphone was on
      const wait = () => {
        if (ticket !== epoch || !mic) return;
        const left = last + window_ / 1000 + 0.1 - ctx.audio().currentTime;
        if (left > 0) timer = setTimeout(wait, Math.min(1000, left * 1000 + 20));
        else judge(beats);
      };
      wait();
    };

    start.addEventListener('click', async () => {
      if (mic || busy || !ctx.live(b.after)) return;
      if (!can()) return none();
      busy = true;
      const ticket = ++epoch;
      let stream = null;
      try {
        const ac = ctx.audio();
        if (ac.state === 'suspended') await ac.resume();
        stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: false}});
        if (!loaded.has(ac)) loaded.set(ac, ac.audioWorklet.addModule(Rupaka.base + 'listen-worklet.js' + query).catch(e => { loaded.delete(ac); throw e; }));
        await loaded.get(ac);
        if (ticket !== epoch || !root.isConnected) { stream.getTracks().forEach(t => t.stop()); return; }
        const src = ac.createMediaStreamSource(stream), node = new AudioWorkletNode(ac, 'rupaka-listen'), mute = ac.createGain();
        mute.gain.value = 0; src.connect(node); node.connect(mute); mute.connect(ac.destination);   // a silent pull keeps the node running
        const tr = stream.getAudioTracks()[0];
        mic = {stream, src, node, mute, lat: tr?.getSettings?.().latency || 0, from: ac.currentTime,
               alive: setInterval(() => { if (!root.isConnected) end(); }, 1000)};   // a demo taken off the page lets go of the microphone
        heard = [];
        node.port.onmessage = e => { heard.push(e.data.t); if (heard.length > 4000) heard.splice(0, 2000); };
        busy = false; why.hidden = true;
        status.textContent = 'Listening. Play along with the beats.';
        show(); seen = null; watch();
      } catch (_) {
        stream?.getTracks().forEach(t => t.stop());
        if (ticket === epoch) { busy = false; none(); }
      }
    });
    stop.addEventListener('click', () => { end(); status.textContent = 'The microphone is off.'; show(); });

    cal.addEventListener('click', () => {
      if (!mic || busy) return;
      busy = true;
      const ac = ctx.audio(), ticket = epoch, t0 = ac.currentTime + 0.6, clicks = Array.from({length: 8}, (_, k) => t0 + k * 0.6);
      clicks.forEach(at => {
        const o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = 1000; g.gain.setValueAtTime(0.3, at); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.03);
        o.connect(g); g.connect(ac.destination); o.onended = () => { o.disconnect(); g.disconnect(); };
        o.start(at); o.stop(at + 0.04);
      });
      status.textContent = 'Tap the drum with each of the 8 clicks. Headphones help: then the microphone does not hear the clicks.';
      const done = () => {
        if (ticket !== epoch || !mic) return;
        if (ac.currentTime < clicks[7] + 0.4) { clock = setTimeout(done, 100); return; }
        busy = false;
        const r = calib(clicks, heard.map(t => t - late(ac)), {window: window_});
        if (!r) { status.textContent = 'Too few taps were heard. Click Calibrate to try again.'; return; }
        shift = r.ms / 1000;
        status.textContent = `Calibrated: ${Math.round(r.ms)} ms.` +
          (r.wide ? ` Your taps spread by ${Math.round(r.spread)} ms, which is more than 30 ms. Try again for a better value.` : '');
      };
      done();
    });

    ctx.s.on(k => {
      if (mic && !ctx.live(b.after)) { end(); show(); status.textContent = ''; }
      if (k === '*' || k === key) watch();
    });
    if (can()) show(); else none();
    return root;
  }, {match, calib}));
})();
