/* timeline: the time t of a scene. Drag the bar, press Play (rAF), or jump to a marker. A/D step (⇧ ten), Q/E the marker before and after, W play and pause.
   A drag or a key sends rk-hold, so layers can show a ghost at the earlier time. */
Rupaka.block('timeline', (b, ctx) => {
  const {el, show} = Rupaka, s = ctx.s, lo = b.min ?? 0, hi = b.max ?? 100, step = b.step ?? 1, speed = b.speed ?? (hi - lo) / 10;
  const marks = [...(b.markers || [])].sort((a, c) => a.t - c.t), name = b.label || 'Time';
  const inp = el('input', {type: 'range', min: lo, max: hi, step, 'aria-label': name}), out = el('output');
  const btn = el('button', {type: 'button', class: 'rk-tl-play', text: 'Play', 'aria-pressed': 'false'});
  const chips = marks.map(m => {
    const c = el('button', {type: 'button', class: 'rk-tl-mark', text: m.label, 'aria-label': `${name} ${m.label}`});
    c.style.setProperty('--p', (m.t - lo) / (hi - lo));
    c.addEventListener('click', () => nudge(() => go(m.t)));
    return c;
  });
  const wrap = el('div', {}, el('span', {class: 'rk-lbl'}, name, out), el('div', {class: 'rk-tl'}, btn, el('div', {class: 'rk-tl-bar'}, inp, el('div', {class: 'rk-tl-marks'}, chips))));
  const hold = on => ctx.root.dispatchEvent(new CustomEvent('rk-hold', {detail: {on}}));
  let timer = 0, playing = false, raf = 0, last = null;
  const nudge = f => { if (!timer) hold(true); clearTimeout(timer); timer = setTimeout(() => { timer = 0; hold(false); }, 800); f(); };
  const put = v => ctx.put(b, b.bind, +Math.min(hi, Math.max(lo, v)).toFixed(6));
  const go = v => { stop(); put(Math.round(v / step) * step); };
  const tick = now => {
    if (!playing) return;
    if (!wrap.isConnected) { playing = false; return; }
    const dt = last == null ? 0 : Math.min(.1, (now - last) / 1000); last = now;
    const v = +s.get(b.bind) + speed * dt;
    if (v >= hi && !b.loop) { put(hi); stop(); return; }
    put(v >= hi ? lo : v);
    raf = requestAnimationFrame(tick);
  };
  const stop = () => { playing = false; cancelAnimationFrame(raf); last = null; btn.textContent = 'Play'; btn.setAttribute('aria-pressed', 'false'); };
  const play = () => {
    if (!ctx.live(b.lock)) return;
    if (+s.get(b.bind) >= hi) put(lo);
    playing = true; btn.textContent = 'Pause'; btn.setAttribute('aria-pressed', 'true'); raf = requestAnimationFrame(tick);
  };
  btn.addEventListener('click', () => playing ? stop() : play());
  inp.addEventListener('pointerdown', () => { stop(); hold(true); });
  ['pointerup', 'pointercancel'].forEach(ev => inp.addEventListener(ev, () => hold(false)));
  inp.addEventListener('input', () => { if (!put(+inp.value)) inp.value = s.get(b.bind); });
  wrap.addEventListener('keydown', e => {
    const k = e.key.toLowerCase(), t = +s.get(b.bind);
    if (k === 'w') { e.preventDefault(); playing ? stop() : play(); }
    else if (k === 'a' || k === 'd') { e.preventDefault(); nudge(() => go(t + (k === 'd' ? 1 : -1) * step * (e.shiftKey ? 10 : 1))); }
    else if (k === 'q' || k === 'e') {
      e.preventDefault();
      const to = k === 'q' ? marks.filter(m => m.t < t - 1e-6).pop()?.t ?? lo : marks.find(m => m.t > t + 1e-6)?.t ?? hi;
      nudge(() => go(to));
    }
  });
  s.on(() => {
    const t = +s.get(b.bind), cur = marks.filter(m => m.t <= t + 1e-6).length - 1;
    inp.value = t; out.textContent = show(t, 1); inp.disabled = !ctx.live(b.lock);
    inp.setAttribute('aria-valuetext', `${name} ${show(t, 1)}${cur >= 0 ? `, ${marks[cur].label}` : ''}`);
    chips.forEach((c, i) => { c.classList.toggle('on', i === cur); i === cur ? c.setAttribute('aria-current', 'true') : c.removeAttribute('aria-current'); });
  });
  return wrap;
});
