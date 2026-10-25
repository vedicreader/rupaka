/* rupaka boot: the last part of the bundle. Mount each [data-rupaka] on load and after each htmx swap, one time each. */
(() => {
  const R = window.Rupaka, go = () => R.boot();
  if (R.booted) return;
  R.booted = true;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
  document.addEventListener('htmx:afterSwap', go);
  document.addEventListener('htmx:afterSettle', go);
})();
