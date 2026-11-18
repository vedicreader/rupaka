/* sound: voices are data. Only the local Play click creates or resumes audio. */
Rupaka.block('sound', (b, ctx) => {
  const {el} = Rupaka, v = b.voice;
  const play = el('button', {type: 'button'}, 'Play', el('kbd', {text: 'W'}));
  const note = el('span', {class: 'rk-note', text: 'Synthesised approximation; a real drum sounds different.'});
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
  const ref = b.ref && /^https?:\/\//i.test(b.ref.url) ? el('a', {href: b.ref.url, title: b.ref.title, target: '_blank', rel: 'noopener noreferrer', text: 'Hear it played'}) : null;
  const root = el('div', {}, el('span', {class: 'rk-lbl', text: b.label || 'Sound'}), el('div', {class: 'rk-sound-acts'}, play, ref), note, status);
  const sync = () => { play.disabled = !allowed(); if (play.disabled) stop(); };
  ctx.s.on(sync); sync();
  return root;
});
