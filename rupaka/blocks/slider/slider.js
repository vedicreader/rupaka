/* slider: a number in a range. ←/→ (native) or A/D move one step; ⇧A/⇧D move ten. */
Rupaka.block('slider', (b, ctx) => {
  const {el, fmt, show} = Rupaka, s = ctx.s, step = b.step ?? 1, lo = b.min ?? 0, hi = b.max ?? 100;
  const inp = el('input', {type: 'range', min: lo, max: hi, step, 'aria-label': b.label || b.bind});
  const out = el('output');
  const set = v => { if (!ctx.put(b, b.bind, +Math.min(hi, Math.max(lo, v)).toFixed(6))) inp.value = s.get(b.bind); };
  inp.addEventListener('input', () => set(+inp.value));
  inp.addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if (k !== 'a' && k !== 'd') return;
    e.preventDefault(); set(+s.get(b.bind) + (k === 'd' ? 1 : -1) * step * (e.shiftKey ? 10 : 1));
  });
  ctx.s.on(() => {
    const v = s.get(b.bind), t = show(v, b.digits);
    inp.value = v; out.textContent = t; inp.disabled = !ctx.live(b.lock);
    inp.setAttribute('aria-valuetext', b.valuetext ? fmt(b.valuetext, s.st) : `${b.label || b.bind} ${t}`);
  });
  return el('div', {}, el('span', {class: 'rk-lbl'}, b.label || b.bind, out), inp, b.note ? el('div', {class: 'rk-note', text: b.note}) : null);
});
