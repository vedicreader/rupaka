/* sound: voices are data. Only the local Play click creates or resumes audio. Technique media exists in the page only while the block may show. */
Rupaka.block('sound', (b, ctx) => {
  const {el} = Rupaka, web = u => typeof u === 'string' && /^https?:\/\//i.test(u);
  const prof = b.play ? ctx.spec.profiles?.[b.play.profile] : null, data = prof?.data || {}, tech = data.techniques?.[b.play?.technique];
  const v = b.voice || tech?.voice, recs = data.media || {};
  // Only a hash-named asset on the host origin or inline in the page, or a YouTube id; never another URL.
  const asset = src => { const m = /^asset:([0-9a-f]{64}\.[a-z0-9]+)$/.exec(src || ''); return m ? ctx.asset(m[1]) : null; };
  const sample = v?.kind === 'sample' && recs[v.media]?.kind === 'audio' ? recs[v.media] : null, tapeUrl = asset(sample?.src);
  const sounds = v?.kind === 'strike' || !!tapeUrl;
  const play = el('button', {type: 'button'}, 'Play', el('kbd', {text: 'W'}));
  const note = el('span', {class: 'rk-note', text: !sounds ? 'This technique has no sound.' : tapeUrl ? 'Recorded sample.' : 'Synthesised approximation; a real instrument sounds different.'});
  const status = el('span', {class: 'rk-note', 'aria-live': 'polite'});
  let audio, tape, active = [], epoch = 0, shown = false;
  const allowed = () => ctx.live(b.after) && ctx.live(b.lock);
  const stop = () => {
    epoch++;
    tape?.pause();
    active.splice(0).forEach(({source, gain}) => {
      gain.disconnect();
      try { source.stop(); } catch (_) { /* A source can already have ended. */ }
      source.disconnect();
    });
  };
  const envelope = (source, level, duration, at) => {
    const gain = audio.createGain();
    gain.gain.setValueAtTime(Math.max(.00001, level), at);
    gain.gain.exponentialRampToValueAtTime(.00001, at + duration);
    source.connect(gain); gain.connect(audio.destination);
    const part = {source, gain}; active.push(part);
    source.onended = () => { source.disconnect(); gain.disconnect(); active = active.filter(x => x !== part); };
    source.start(at); source.stop(at + duration);
  };
  // Keep a local audio or video inside [start, end]. With loop() true, go back to start at the end.
  const windowed = (m, r, loop = () => false) => {
    const s = +r.start || 0, e = r.end == null ? null : +r.end;
    m.addEventListener('loadedmetadata', () => { m.currentTime = s; });
    m.addEventListener('timeupdate', () => { if (e != null && m.currentTime >= e) { if (loop()) m.currentTime = s; else m.pause(); } });
    m.addEventListener('ended', () => { if (loop()) { m.currentTime = s; m.play().catch(() => {}); } });
    return m;
  };
  const sampled = () => {
    if (!tape) { tape = windowed(el('audio', {src: tapeUrl, preload: 'auto', hidden: true}), sample); root.append(tape); }
    tape.currentTime = +sample.start || 0;
    tape.play().then(() => { status.textContent = ''; }, () => { status.textContent = 'Sound could not start. Try Play again.'; });
  };
  play.addEventListener('click', async () => {
    if (!allowed() || !root.isConnected || !root.getClientRects().length || !sounds) return;
    stop(); const ticket = epoch;
    if (tapeUrl) return sampled();
    try {
      audio ||= new (window.AudioContext || window.webkitAudioContext)();
      if (audio.state === 'suspended') await audio.resume();
      if (ticket !== epoch || !allowed() || !root.isConnected) return;
      const at = audio.currentTime, scale = v.gain / Math.max(1, v.partials.reduce((n, p) => n + p.gain, 0) + (v.noise || 0));
      v.partials.forEach(p => {
        const source = audio.createOscillator();
        source.frequency.setValueAtTime(v.frequency * p.ratio, at);
        source.detune.setValueAtTime(v.bend || 0, at);
        source.detune.linearRampToValueAtTime(0, at + Math.min(.08, v.decay));
        envelope(source, scale * p.gain, v.decay, at);
      });
      if (v.noise) {
        const duration = Math.min(.04, v.decay), buffer = audio.createBuffer(1, Math.ceil(audio.sampleRate * duration), audio.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
        const source = audio.createBufferSource(); source.buffer = buffer;
        envelope(source, scale * v.noise, duration, at);
      }
      status.textContent = '';
    } catch (_) { stop(); status.textContent = 'Sound could not start. Try Play again.'; }
  });
  const key = (btn, k) => btn.addEventListener('keydown', e => {
    if (e.key.toLowerCase() !== k || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault(); btn.click();
  });
  key(play, 'w');
  const ref = b.ref && web(b.ref.url) ? el('a', {href: b.ref.url, title: b.ref.title, target: '_blank', rel: 'noopener noreferrer', text: 'Hear it played'}) : null;
  // A fact or a media entry with no school holds for all schools. A per-school one shows only for the embed school, never for another school.
  const schools = data.schools || {}, school = prof?.school, facts = tech?.facts || [], used = new Set(tech?.sources || []);
  const ours = x => x.school == null || (school != null && x.school === school);
  const lines = [...new Set(facts.map(f => f.key))].map(k => {
    const fs = facts.filter(f => f.key === k), all = fs.find(f => f.school == null);
    const f = all || (school != null ? fs.find(x => x.school === school) : null);
    (f?.sources || []).forEach(s => used.add(s));
    const who = all ? '' : ` (${schools[school]?.label || 'no school chosen'})`;
    return el('li', {text: `${k}${who}: ${f ? String(f.value) : 'unknown'}`});
  });
  const parts = (tech?.parts || []).map(p => data.parts?.[p]?.label).filter(Boolean);
  const chips = [...used].map(s => data.sources?.[s]).filter(s => s && web(s.url))
    .map(s => el('a', {class: 'rk-sound-src', href: s.url, title: s.passage, target: '_blank', rel: 'noopener noreferrer', text: s.title}));
  const about = tech ? el('div', {class: 'rk-sound-about'},
    parts.length ? el('span', {class: 'rk-note', text: `Played on: ${parts.join(', ')}`}) : null,
    lines.length ? el('ul', {class: 'rk-sound-facts'}, ...lines) : null,
    chips.length ? el('div', {class: 'rk-sound-srcs'}, el('span', {class: 'rk-note', text: 'Sources:'}), ...chips) : null) : null;
  const credit = r => el('p', {class: 'rk-note rk-sound-credit'}, `${r.credit?.who}, ${r.credit?.license}. `,
    web(r.credit?.url) ? el('a', {href: r.credit.url, target: '_blank', rel: 'noopener noreferrer', text: 'Source'}) : null);
  const youtube = (r, id) => {
    const box = el('div', {class: 'rk-sound-yt'}), load = el('button', {type: 'button'}, 'Load video', el('kbd', {text: 'E'}));
    const src = `https://www.youtube-nocookie.com/embed/${id}?start=${Math.floor(+r.start)}&end=${Math.ceil(+r.end)}&rel=0`;
    load.addEventListener('click', () => box.replaceChildren(el('iframe', {src, title: r.alt || 'Video clip', allow: 'encrypted-media; picture-in-picture',
      referrerpolicy: 'strict-origin-when-cross-origin', sandbox: 'allow-scripts allow-same-origin allow-presentation'})));
    key(load, 'e');
    box.append(load, el('span', {class: 'rk-note', text: 'The video loads from YouTube only when you click Load video.'}));
    return box;
  };
  const looped = (r, u) => {
    let on = false;
    const lp = el('button', {type: 'button', 'aria-pressed': 'false'}, 'Loop', el('kbd', {text: 'Q'}));
    lp.addEventListener('click', () => { on = !on; lp.setAttribute('aria-pressed', String(on)); });
    key(lp, 'q');
    return el('div', {class: 'rk-sound-clip'}, windowed(el('video', {src: u, controls: true, preload: 'metadata', 'aria-label': r.alt || null}), r, () => on), lp);
  };
  const item = r => {
    const yt = r.kind === 'video' && /^youtube:([A-Za-z0-9_-]{11})$/.exec(r.src || ''), u = asset(r.src);
    if (yt) return youtube(r, yt[1]);
    if (!u) return null;
    if (r.kind === 'image') return el('img', {src: u, alt: r.alt || ''});
    if (r.kind === 'video') return looped(r, u);
    if (r.kind === 'audio') return windowed(el('audio', {src: u, controls: true, preload: 'metadata', 'aria-label': r.alt || null}), r);
    return null;
  };
  const build = () => [sample && tapeUrl ? credit(sample) : null,
    ...(tech?.media || []).filter(x => x && ours(x)).map(x => recs[x.media]).filter(Boolean)
      .map(r => { const n = item(r); return n && el('figure', {class: 'rk-sound-item'}, n, credit(r)); })].filter(Boolean);
  const shelf = el('div', {class: 'rk-sound-media'});
  const root = el('div', {}, el('span', {class: 'rk-lbl', text: b.label || tech?.label || 'Sound'}), el('div', {class: 'rk-sound-acts'}, play, ref), about, shelf, note, status);
  const sync = () => {
    const ok = allowed();
    play.disabled = !sounds || !ok; if (play.disabled) stop();
    if (!ok && tape) { tape.remove(); tape = null; }
    if (ok !== shown) { shown = ok; shelf.replaceChildren(...(ok ? build() : [])); }
  };
  ctx.s.on(sync); sync();
  return root;
});
