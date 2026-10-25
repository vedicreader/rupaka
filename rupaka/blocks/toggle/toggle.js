/* toggle: on or off. Space or ↩ (native button keys) flip it. */
Rupaka.block('toggle', (b, ctx) => {
  const {el} = Rupaka, s = ctx.s;
  const btn = el('button', {type: 'button', role: 'switch', class: 'sw', 'aria-label': b.label || b.bind}, el('i'), el('span'));
  btn.onclick = () => ctx.put(b, b.bind, !s.get(b.bind));
  s.on(() => {
    const v = !!s.get(b.bind);
    btn.setAttribute('aria-checked', String(v)); btn.lastChild.textContent = v ? (b.on || 'On') : (b.off || 'Off'); btn.disabled = !ctx.live(b.lock);
  });
  return el('div', {}, Rupaka.label(b), btn);
});
