/* caption: the explain text. Only **bold** and {path} are special; all text goes in with textContent, so no HTML runs. */
Rupaka.block('caption', (b, ctx) => {
  const {el, fmt} = Rupaka, p = el('p');
  ctx.s.on(() => p.replaceChildren(...String(b.text ?? '').split('**').map((t, i) => i % 2 ? el('b', {text: fmt(t, ctx.s.st)}) : fmt(t, ctx.s.st))));
  return el('div', {}, Rupaka.label(b), p);
});
