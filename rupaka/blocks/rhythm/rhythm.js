/* rhythm: a practice round on the shared audio clock, ctx.audio(). Nothing plays before Start.
   A lookahead scheduler wakes about every 25 ms and gives each sound that starts in the next 100 ms its exact start time on the audio clock.
   The strike synthesis repeats the few lines of sound.js, so that the sound block stays as it is. */
Rupaka.block('rhythm', (b, ctx) => {
  const {el} = Rupaka, AHEAD = .1, WAKE = 25, LEAD = .1, LO = 30, HI = 240;
  const clamp = (v, lo, hi, d) => { const x = v == null ? NaN : +v; return Number.isFinite(x) ? Math.min(hi, Math.max(lo, x)) : d; };
  const web = u => typeof u === 'string' && /^https?:\/\//i.test(u);
  const data = ctx.spec.profiles?.[b.profile]?.data || {}, techs = data.techniques || {}, recs = data.media || {};
  const pattern = Array.isArray(b.pattern) ? b.pattern : [], n = pattern.length;
  const countIn = Math.round(clamp(b.count_in, 0, 8, 4)), cycles = Math.round(clamp(b.cycles, 1, 16, 2)), turns = b.turns !== false;
  let tempo = clamp(b.tempo, LO, HI, 60);
  // The same asset rule as sound: only a hash-named asset through ctx.asset, never another URL.
  const asset = src => { const m = /^asset:([0-9a-f]{64}\.[a-z0-9]+)$/.exec(src || ''); return m ? ctx.asset(m[1]) : null; };
  const voice = id => {
    const v = techs[id]?.voice, r = v?.kind === 'sample' ? recs[v.media] : null, url = r?.kind === 'audio' ? asset(r.src) : null;
    return v?.kind === 'strike' ? v : url ? {kind: 'sample', url, start: +r.start || 0, end: r.end == null ? null : +r.end} : null;
  };
  const voices = pattern.map(x => x === 'rest' ? null : voice(x)), playable = voices.some(Boolean);
  const used = [...new Set(pattern.map(x => techs[x]?.voice).filter(v => v?.kind === 'sample' && recs[v.media]?.kind === 'audio').map(v => v.media))];

  const go = el('button', {type: 'button', class: 'rk-rhythm-go'}, 'Start', el('kbd', {text: 'W'}));
  const tick = el('button', {type: 'button', 'aria-pressed': 'false'}, 'Click on my turn', el('kbd', {text: 'Q'}));
  const inp = el('input', {type: 'range', min: LO, max: HI, step: 1, 'aria-label': 'Tempo in beats per minute'}), bpm = el('output');
  const cue = el('span', {class: 'rk-rhythm-cue', 'aria-live': 'polite', text: 'Press Start.'});
  const cells = pattern.map(x => el('span', {class: 'rk-rhythm-beat', text: x === 'rest' ? '–' : techs[x]?.label || String(x)}));
  const note = el('span', {class: 'rk-note', text: !playable ? 'This pattern has no sound.' : used.length ? 'Recorded samples.' : 'Synthesised strokes; a real instrument sounds different.'});
  const status = el('span', {class: 'rk-note', 'aria-live': 'polite'}), credits = el('div', {class: 'rk-rhythm-credits'});
  const root = el('div', {}, el('span', {class: 'rk-lbl', text: b.label || 'Rhythm'}),
    el('div', {class: 'rk-rhythm-acts'}, go, tick),
    el('div', {class: 'rk-rhythm-tempo'}, inp, bpm),
    el('div', {class: 'rk-rhythm-show'}, cue, el('div', {class: 'rk-rhythm-beats'}, ...cells)),
    note, credits, status);

  let audio = null, timer = 0, epoch = 0, on = false, run = null, active = [], clickOn = false, shown = false;
  const hiss = new Map(), buffers = new Map();   // noise buffers by length; url -> a promise of a decoded recording or null
  const allowed = () => ctx.live(b.after) && ctx.live(b.lock);
  const setTempo = v => { tempo = clamp(v, LO, HI, tempo); inp.value = tempo; bpm.textContent = `${+tempo.toFixed(1)} beats per minute`; };
  setTempo(tempo);

  const stop = (text = '') => {
    epoch++; clearTimeout(timer); timer = 0; on = false; run = null;
    active.splice(0).forEach(({source, gain}) => {
      try { source.stop(); } catch (_) { /* A source can already have ended. */ }
      source.disconnect(); gain.disconnect();
    });
    go.firstChild.textContent = 'Start'; cue.textContent = text;
    cells.forEach(c => c.removeAttribute('aria-current')); root.classList.remove('rk-rhythm-turn');
  };
  // Connect a source through a gain to the output; with decay, the gain falls over `dur` seconds.
  const out = (source, level, at, dur, decay = true) => {
    const gain = audio.createGain();
    gain.gain.setValueAtTime(Math.max(.00001, level), at);
    if (decay) gain.gain.exponentialRampToValueAtTime(.00001, at + dur);
    source.connect(gain); gain.connect(audio.destination);
    const part = {source, gain}; active.push(part);
    source.onended = () => { source.disconnect(); gain.disconnect(); active = active.filter(x => x !== part); };
  };
  const click = (at, level, hz) => {
    const o = audio.createOscillator(); o.frequency.setValueAtTime(hz, at);
    out(o, level, at, .03); o.start(at); o.stop(at + .03);
  };
  const noise = d => {
    const k = `${audio.sampleRate}:${d}`;
    if (!hiss.has(k)) {
      const buf = audio.createBuffer(1, Math.ceil(audio.sampleRate * d), audio.sampleRate), x = buf.getChannelData(0);
      for (let i = 0; i < x.length; i++) x[i] = Math.random() * 2 - 1;
      hiss.set(k, buf);
    }
    return hiss.get(k);
  };
  // The strike of sound.js, at time `at`: one oscillator per partial, and a short noise burst.
  const strike = (v, at) => {
    const scale = v.gain / Math.max(1, v.partials.reduce((s, p) => s + p.gain, 0) + (v.noise || 0));
    v.partials.forEach(p => {
      const o = audio.createOscillator();
      o.frequency.setValueAtTime(v.frequency * p.ratio, at);
      o.detune.setValueAtTime(v.bend || 0, at);
      o.detune.linearRampToValueAtTime(0, at + Math.min(.08, v.decay));
      out(o, scale * p.gain, at, v.decay); o.start(at); o.stop(at + v.decay);
    });
    if (v.noise) {
      const d = Math.min(.04, v.decay), src = audio.createBufferSource(); src.buffer = noise(d);
      out(src, scale * v.noise, at, d); src.start(at); src.stop(at + d);
    }
  };
  // A recording plays its [start, end] window from a decoded buffer, so it too starts on the audio clock.
  const sample = (v, buf, at) => {
    const off = Math.min(v.start, buf.duration), len = (v.end == null ? buf.duration : Math.min(v.end, buf.duration)) - off;
    if (len <= 0) return;
    const src = audio.createBufferSource(); src.buffer = buf;
    out(src, 1, at, len, false); src.start(at, off, len);
  };
  // The demo makes no network request, so it decodes only a recording that the page holds as a data URI (show(spec, assets=...)).
  // A recording from the media base plays in the sound block, but here its strokes are silent.
  const bytes = url => {
    const m = /^data:[^,]*;base64,([A-Za-z0-9+/=]+)$/.exec(url);
    if (!m) return null;
    const s = atob(m[1]), a = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
    return a.buffer;
  };
  const load = url => {
    if (!buffers.has(url)) {
      const x = bytes(url);
      buffers.set(url, x ? audio.decodeAudioData(x).catch(() => { buffers.delete(url); return null; }) : Promise.resolve(null));
    }
    return buffers.get(url);
  };

  // The round: a count-in, then each played cycle, and with turns a silent cycle after each one.
  const plan = () => [...(countIn ? [{kind: 'count', len: countIn}] : []),
    ...Array.from({length: cycles}, () => [{kind: 'play', len: n}, ...(turns ? [{kind: 'turn', len: n}] : [])]).flat()];
  const showCue = c => {
    const turn = c.kind === 'turn';
    cue.textContent = c.kind === 'count' ? `Count in: ${c.beat + 1}` : turn ? 'Your turn' : 'Listen';
    root.classList.toggle('rk-rhythm-turn', turn);
    cells.forEach((x, i) => c.kind !== 'count' && i === c.beat ? x.setAttribute('aria-current', 'true') : x.removeAttribute('aria-current'));
  };
  const wake = ticket => {
    if (ticket !== epoch || !run) return;
    if (!root.isConnected) return stop();
    const now = audio.currentTime;
    while (run.seg < run.segs.length && run.next < now + AHEAD) {
      const seg = run.segs[run.seg];
      if (run.beat === 0) {   // a cycle keeps the tempo that it starts with
        run.spb = 60 / tempo; run.start = run.next;
        if (seg.kind === 'turn' && b.beats) ctx.put(b, b.beats, Array.from({length: seg.len}, (_, k) => run.start + k * run.spb));
      }
      const at = run.start + run.beat * run.spb, v = voices[run.beat];
      if (seg.kind === 'count') click(at, .3, 1500);
      else if (seg.kind === 'play') { if (v?.kind === 'strike') strike(v, at); else if (v?.kind === 'sample' && run.bufs[run.beat]) sample(v, run.bufs[run.beat], at); }
      else if (clickOn) click(at, .05, 1000);
      run.cues.push({at, kind: seg.kind, beat: run.beat});
      run.beat++; run.next = run.start + run.beat * run.spb;
      if (run.beat >= seg.len) { run.seg++; run.beat = 0; }
    }
    while (run.cues.length && run.cues[0].at <= now) showCue(run.cues.shift());
    if (run.seg >= run.segs.length && now >= run.next) return stop('Done. Press Start to play again.');
    timer = setTimeout(() => wake(ticket), WAKE);
  };
  const start = async () => {
    if (!allowed() || !root.isConnected || !playable) return;
    on = true; const ticket = ++epoch;
    go.firstChild.textContent = 'Stop'; status.textContent = ''; cue.textContent = 'Get ready.';
    try {
      audio = ctx.audio();
      if (audio.state === 'suspended') await audio.resume();
      const bufs = await Promise.all(voices.map(v => v?.kind === 'sample' ? load(v.url) : null));
      if (ticket !== epoch || !allowed() || !root.isConnected) return;
      if (voices.some((v, i) => v?.kind === 'sample' && !bufs[i])) status.textContent = 'This page does not hold a recording, so its strokes are silent.';
      run = {segs: plan(), seg: 0, beat: 0, next: audio.currentTime + LEAD, start: 0, spb: 60 / tempo, cues: [], bufs};
      wake(ticket);
    } catch (_) { stop(); status.textContent = 'Sound could not start. Try Start again.'; }
  };

  go.addEventListener('click', () => on ? stop('Stopped.') : start());
  tick.addEventListener('click', () => { clickOn = !clickOn; tick.setAttribute('aria-pressed', String(clickOn)); });
  inp.addEventListener('input', () => setTempo(+inp.value));
  inp.addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if ((k !== 'a' && k !== 'd') || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault(); setTempo(tempo + (k === 'd' ? 1 : -1) * (e.shiftKey ? 10 : 1));
  });
  const key = (btn, k) => btn.addEventListener('keydown', e => {
    if (e.key.toLowerCase() !== k || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault(); btn.click();
  });
  key(go, 'w'); key(tick, 'q');

  const credit = r => el('p', {class: 'rk-note rk-rhythm-credit'}, `${r.credit?.who}, ${r.credit?.license}. `,
    web(r.credit?.url) ? el('a', {href: r.credit.url, target: '_blank', rel: 'noopener noreferrer', text: 'Source'}) : null);
  const sync = () => {
    const ok = allowed();
    go.disabled = !ok || !playable; inp.disabled = tick.disabled = !ok;
    if (!ok && on) stop();
    if (ok !== shown) { shown = ok; credits.replaceChildren(...(ok ? used.map(id => credit(recs[id])) : [])); }
  };
  ctx.s.on(sync); sync();
  return root;
});
