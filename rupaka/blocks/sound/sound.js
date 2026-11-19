/* sound: voices are data. Only the local Play click creates or resumes audio. */
Rupaka.block('sound', (b, ctx) => {
  const {el} = Rupaka, web = u => typeof u === 'string' && /^https?:\/\//i.test(u);
  const prof = b.play ? ctx.spec.profiles?.[b.play.profile] : null, data = prof?.data || {}, tech = data.techniques?.[b.play?.technique];
  const v = b.voice || tech?.voice;
  const play = el('button', {type: 'button'}, 'Play', el('kbd', {text: 'W'}));
  const note = el('span', {class: 'rk-note', text: v ? 'Synthesised approximation; a real instrument sounds different.' : 'This technique has no sound.'});
  const status = el('span', {class: 'rk-note', 'aria-live': 'polite'});
  let audio, active = [], epoch = 0;
  const allowed = () => ctx.live(b.after) && ctx.live(b.lock);
  const stop = () => {
    epoch++;
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
  play.addEventListener('click', async () => {
    if (!allowed() || !root.isConnected || !root.getClientRects().length || v?.kind !== 'strike') return;
    stop(); const ticket = epoch;
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
  play.addEventListener('keydown', e => {
    if (e.key.toLowerCase() !== 'w' || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault(); play.click();
  });
  const ref = b.ref && web(b.ref.url) ? el('a', {href: b.ref.url, title: b.ref.title, target: '_blank', rel: 'noopener noreferrer', text: 'Hear it played'}) : null;
  // A fact with no school holds for all schools. A per-school key shows only the embed school, never another school, else unknown.
  const schools = data.schools || {}, school = prof?.school, facts = tech?.facts || [], used = new Set(tech?.sources || []);
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
  const root = el('div', {}, el('span', {class: 'rk-lbl', text: b.label || tech?.label || 'Sound'}), el('div', {class: 'rk-sound-acts'}, play, ref), about, note, status);
  const sync = () => { play.disabled = !v || !allowed(); if (play.disabled) stop(); };
  ctx.s.on(sync); sync();
  return root;
});
