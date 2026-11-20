/* listen: opt-in microphone timing on this device. Only a click on Listen on this device asks for the microphone. The sound goes to an
   onset worklet (rupaka/static/listen-worklet.js, served beside rupaka.js), which posts onset times and a level for the meter.
   With Keep my playing off, no audio is kept. With it on, the worklet also posts samples, and the block keeps the last round only
   (its beats with the match window on each side, at most 60 s), in page memory, for Play what I played and Save my playing.
   No network: Save is a Blob on an object URL. The beats are times in seconds on the shared page clock, ctx.audio(). */
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

  // A 16-bit mono PCM WAV: the 44-byte RIFF header, then each sample clipped to ±1.
  const wav = (x, sr) => {
    const n = x.length, buf = new ArrayBuffer(44 + 2 * n), v = new DataView(buf);
    const tag = (o, s) => { for (let i = 0; i < 4; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    tag(0, 'RIFF'); v.setUint32(4, 36 + 2 * n, true); tag(8, 'WAVE'); tag(12, 'fmt '); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true); v.setUint32(28, 2 * sr, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true); tag(36, 'data'); v.setUint32(40, 2 * n, true);
    for (let i = 0; i < n; i++) v.setInt16(44 + 2 * i, Math.round(Math.max(-1, Math.min(1, x[i])) * 32767), true);
    return buf;
  };
  const two = n => String(n).padStart(2, '0');
  const stamp = d => `${d.getFullYear()}${two(d.getMonth() + 1)}${two(d.getDate())}-${two(d.getHours())}${two(d.getMinutes())}${two(d.getSeconds())}`;
  const slug = s => String(s ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  const KEEP_MAX = 60;   // the longest kept round, in seconds
  const OFF = 'The sound stays on this device. Nothing is recorded or sent.';
  const ON = 'While this box is ticked, this page holds the last second of sound and your last round. ' +
             'Both go when you untick it, press Stop listening or leave the page. ' +
             'Save my playing writes a WAV file on this device. Nothing is sent.';

  const loaded = new WeakMap();   // context -> the promise of its worklet module
  const say = r => r.verdict === 'missed' || r.verdict === 'on' ? r.verdict : `${r.verdict} ${Math.abs(Math.round(r.ms))} ms`;

  Rupaka.block('listen', Object.assign((b, ctx) => {
    const {el} = Rupaka, key = b.beats?.[0], outKey = b.out?.[0], tolerance = b.tolerance ?? 30, window_ = b.window ?? 150;
    // A key fires a control only when that control has focus. W, S, E: the microphone. Q: keep. A, D, 1: the kept round.
    const keyed = (e, k) => {
      e.addEventListener('keydown', ev => {
        if (ev.key.toLowerCase() !== k || ev.repeat || ev.metaKey || ev.ctrlKey || ev.altKey) return;
        ev.preventDefault(); e.click();
      });
      return e;
    };
    const kbd = k => el('kbd', {text: k.toUpperCase()});
    const button = (text, k) => keyed(el('button', {type: 'button'}, text, kbd(k)), k);
    const tick = (text, k) => { const i = keyed(el('input', {type: 'checkbox'}), k); return [i, el('label', {class: 'rk-listen-tick'}, i, ` ${text} `, kbd(k))]; };
    const start = button('Listen on this device', 'w'), stop = button('Stop listening', 's'), cal = button('Calibrate', 'e');
    const play = button('Play what I played', 'a'), save = button('Save my playing', 'd');
    const [keepBox, keepRow] = tick('Keep my playing', 'q'), [beatBox, beatRow] = tick('Click on each beat', '1');
    const level = el('meter', {class: 'rk-listen-level', min: 0, max: 1, value: 0, 'aria-label': 'Sound level'});
    const count = el('span', {class: 'rk-listen-count'});
    const live = el('div', {class: 'rk-listen-live', hidden: true}, level, count);
    const status = el('p', {class: 'rk-note rk-listen-status', 'aria-live': 'polite'});
    const why = el('p', {class: 'rk-note rk-listen-why', hidden: true});
    const list = el('ul', {class: 'rk-listen-out', 'aria-live': 'polite'});
    const lines = el('div', {class: 'rk-listen-lines'});
    const replay = el('div', {class: 'rk-listen-replay', hidden: true}, el('div', {class: 'rk-listen-acts'}, play, beatRow, save), lines);
    const privacy = el('p', {class: 'rk-note rk-listen-privacy', text: OFF});
    const root = el('div', {}, el('span', {class: 'rk-lbl', text: 'Microphone timing'}), el('div', {class: 'rk-listen-acts'}, start, stop, cal),
      b.keep === false ? null : keepRow, live, status, why, list, replay, privacy);   // keep: false leaves the box out
    let mic = null, epoch = 0, heard = [], shift = 0, busy = false, seen = null, timer = 0, clock = 0;
    // keep: the box is ticked. hist: the last second or so of samples, so that a round can start before its beats were written.
    // pend: the round that is being caught. kept: the last judged round. playing: the nodes of a replay.
    let keep = false, hist = [], pend = null, kept = null, playing = [], strokes = 0, peak = 0;

    const can = () => !!(Rupaka.base && navigator.mediaDevices?.getUserMedia && window.AudioWorkletNode && (window.AudioContext || window.webkitAudioContext));
    const show = () => {
      start.hidden = !!mic; stop.hidden = !mic; cal.hidden = !mic || b.calibrate === false;
      live.hidden = !mic; replay.hidden = !kept;
    };
    const none = () => {
      why.textContent = 'The microphone is not available here.'; why.hidden = false; status.textContent = '';
      [start, stop, cal, keepRow, live, replay].forEach(x => { x.hidden = true; });
    };
    const hush = () => { playing.forEach(ns => ns.forEach(n => { try { n.stop?.(); } catch (_) { /* not started */ } n.disconnect(); })); playing = []; };
    const drop = () => { hush(); hist = []; pend = null; kept = null; lines.replaceChildren(); replay.hidden = true; };
    const counted = () => { count.textContent = `Heard ${strokes} stroke${strokes === 1 ? '' : 's'}`; };
    const end = () => {
      epoch++; busy = false; clearTimeout(timer); clearTimeout(clock); drop();
      if (!mic) return;
      const m = mic; mic = null; clearInterval(m.alive);
      m.stream.getTracks().forEach(t => t.stop());
      m.node.port.onmessage = null;
      [m.src, m.node, m.mute].forEach(n => n.disconnect());
    };
    const late = ac => mic.lat + (ac.outputLatency || 0);   // the input and output latency, in seconds

    // Copy the part of a chunk that falls in the round. `cs` is the capture time of the round's first sample.
    const fill = (p, x, t0) => {
      const s = Math.round((t0 - p.cs) * p.sr), a = Math.max(0, -s), z = Math.min(x.length, p.buf.length - s);
      if (z > a) p.buf.set(x.subarray(a, z), s + a);
    };
    const take = (x, t0) => {
      const sr = ctx.audio().sampleRate;
      hist.push({x, t0});
      while (hist.length && hist[0].t0 + hist[0].x.length / sr < t0 - window_ / 1000 - 0.6) hist.shift();
      if (pend) fill(pend, x, t0);
    };
    // The timeline: a long line for each beat, coloured by its verdict, and a short line for each stroke heard.
    const draw = () => {
      const k = kept, W = 600, H = 56, dur = k.buf.length / k.sr, x = t => (Math.max(0, Math.min(dur, t - k.from)) / dur * W).toFixed(1);
      const svg = Rupaka.sv('svg', {class: 'rk-listen-line', viewBox: `0 0 ${W} ${H}`, role: 'img', 'data-seconds': dur.toFixed(4), 'data-frames': k.buf.length,
          'aria-label': `Your last round: ${k.beats.length} beats and ${k.strokes.length} strokes heard`},
        Rupaka.sv('line', {class: 'rk-listen-axis', x1: 0, x2: W, y1: H / 2, y2: H / 2}),
        k.beats.map((t, i) => Rupaka.sv('line', {class: `rk-listen-beat rk-listen-${k.res[i]?.verdict || 'missed'}`, x1: x(t), x2: x(t), y1: 4, y2: H - 4})),
        k.strokes.map(t => Rupaka.sv('line', {class: 'rk-listen-stroke', x1: x(t), x2: x(t), y1: H / 2 - 10, y2: H / 2 + 10})));
      lines.replaceChildren(svg, el('p', {class: 'rk-note', text: 'Long lines are the beats. Short lines are the strokes that the microphone heard.'}));
      replay.hidden = false;
    };

    const judge = beats => {
      const ac = ctx.audio(), res = match(beats, heard.map(t => t - late(ac) - shift), {tolerance, window: window_});
      list.replaceChildren(...res.map((r, i) => el('li', {text: `Beat ${i + 1}: ${say(r)}`})));
      if (pend && pend.beats === beats) {   // this round replaces the kept one
        const p = pend, endAt = p.from + p.buf.length / p.sr;
        hush(); pend = null;
        kept = {...p, res, strokes: heard.map(t => t - p.off).filter(t => t >= p.from && t <= endAt)};
        draw();
      }
      if (outKey) ctx.s.set(outKey, res);
    };
    // When the beats change, wait until their last beat (and its window) has passed on the page clock, then judge them.
    const watch = () => {
      const beats = key ? ctx.s.get(key) : null, sig = JSON.stringify(beats ?? null);
      if (sig === seen) return;
      seen = sig; clearTimeout(timer); pend = null;
      if (!mic || !Array.isArray(beats) || !beats.length || !beats.every(Number.isFinite)) return;
      const last = Math.max(...beats), ticket = epoch;
      if (last < mic.from) return;   // a round from before the microphone was on
      if (keep) {   // catch this round: from its first beat minus the window to its last beat plus the window, at most KEEP_MAX s
        const ac = ctx.audio(), sr = ac.sampleRate, w = window_ / 1000, from = Math.min(...beats) - w, off = late(ac) + shift;
        pend = {beats, from, off, sr, cs: from + off, buf: new Float32Array(Math.round(Math.min(last + w - from, KEEP_MAX) * sr))};
        hist.forEach(h => fill(pend, h.x, h.t0));
      }
      const wait = () => {
        if (ticket !== epoch || !mic) return;
        const left = last + window_ / 1000 + 0.1 + (pend ? pend.off + 0.1 : 0) - ctx.audio().currentTime;   // the last samples come in chunks
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
        heard = []; strokes = 0; peak = 0; hist = []; pend = null; counted();
        node.port.onmessage = e => {
          const d = e.data;
          if ('t' in d) { heard.push(d.t); if (heard.length > 4000) heard.splice(0, 2000); strokes++; counted(); }
          else if ('level' in d) { peak = Math.max(Math.sqrt(d.level), peak * 0.85); level.value = Math.min(1, peak); }   // falls back slowly
          else if (d.pcm && keep) take(d.pcm, d.at / ac.sampleRate);
        };
        node.port.postMessage({keep});
        busy = false; why.hidden = true;
        status.textContent = 'Listening. Play along with the beats.';
        show(); seen = null; watch();
      } catch (_) {
        stream?.getTracks().forEach(t => t.stop());
        if (ticket === epoch) { busy = false; none(); }
      }
    });
    stop.addEventListener('click', () => { end(); status.textContent = 'The microphone is off.'; show(); });

    keepBox.addEventListener('change', () => {
      keep = keepBox.checked && b.keep !== false;
      privacy.textContent = keep ? ON : OFF;
      if (!keep) drop();
      mic?.node.port.postMessage({keep});
    });
    play.addEventListener('click', async () => {
      const k = kept, ac = ctx.audio();
      if (!k) return;
      if (ac.state === 'suspended') await ac.resume();
      if (k !== kept) return;
      hush();
      const buf = ac.createBuffer(1, k.buf.length, k.sr); buf.getChannelData(0).set(k.buf);
      const src = ac.createBufferSource(), t0 = ac.currentTime + 0.05, part = [src];
      src.buffer = buf; src.connect(ac.destination); src.start(t0); playing.push(part);
      src.onended = () => { src.disconnect(); playing = playing.filter(x => x !== part); };
      if (beatBox.checked) k.beats.forEach(t => {   // a soft click on each beat, as the rhythm block's Your turn click
        const at = t0 + t - k.from, o = ac.createOscillator(), g = ac.createGain(), clk = [o, g];
        o.frequency.value = 1000; g.gain.setValueAtTime(0.05, at); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.03);
        o.connect(g); g.connect(ac.destination); o.start(at); o.stop(at + 0.04); playing.push(clk);
        o.onended = () => { o.disconnect(); g.disconnect(); playing = playing.filter(x => x !== clk); };
      });
    });
    save.addEventListener('click', () => {
      if (!kept) return;
      const url = URL.createObjectURL(new Blob([wav(kept.buf, kept.sr)], {type: 'audio/wav'}));
      const name = `rupaka-${slug(ctx.spec?.id) || slug(ctx.spec?.title) || 'listen'}-${stamp(new Date())}.wav`;
      const a = el('a', {href: url, download: name, hidden: true});
      root.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);   // the download has the file by then
    });

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
  }, {match, calib, wav}));
})();
