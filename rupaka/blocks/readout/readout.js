/* readout: one large line from a template, for example "{a} + {b} → {join.out}". */
Rupaka.block('readout', (b, ctx) => {
  const {el, fmt} = Rupaka, d = el('div', {class: 'big', 'aria-live': 'polite'});
  ctx.s.on(() => { d.textContent = fmt(b.text, ctx.s.st); });
  return el('div', {}, Rupaka.label(b), d);
});
