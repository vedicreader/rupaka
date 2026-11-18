/* choice: a row of options with one picked. ←/→ or A/D move, 1-9 pick.
   A new pick sets the keys of `resets` back in the same change, so there is one derive and one draw: no view shows the new pick with an old value. */
Rupaka.block('choice', (b, ctx) => {
  const {el, show} = Rupaka, s = ctx.s, os = b.options || [];
  const pick = o => {
    if (!ctx.live(b.lock)) return false;
    if (o !== s.get(b.bind)) for (const [k, v] of Object.entries(b.resets || {})) s.st[k] = structuredClone(v);
    return ctx.put(b, b.bind, o);
  };
  const box = el('div', {class: 'opts', role: 'radiogroup', 'aria-label': b.label || b.bind});
  const btns = os.map((o, i) => el('button', {type: 'button', role: 'radio', onclick: () => pick(o)}, show(o), i < 9 ? el('kbd', {text: i + 1}) : null));
  box.append(...btns);
  box.addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toLowerCase(), i = os.indexOf(s.get(b.bind));
    const j = ['arrowright', 'd'].includes(k) ? i + 1 : ['arrowleft', 'a'].includes(k) ? i - 1 : /^[1-9]$/.test(k) ? +k - 1 : null;
    if (j == null || j < 0 || j >= os.length) return;
    e.preventDefault();
    if (pick(os[j])) btns[j].focus();
  });
  s.on(() => {
    const v = s.get(b.bind), at = Math.max(0, os.indexOf(v));
    btns.forEach((x, i) => { x.setAttribute('aria-checked', String(os[i] === v)); x.tabIndex = i === at ? 0 : -1; x.disabled = !ctx.live(b.lock); });
  });
  return el('div', {}, Rupaka.label(b), box);
});
