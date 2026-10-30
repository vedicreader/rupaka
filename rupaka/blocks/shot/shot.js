/* shot: the camera of a scene. `name` is a fixed shot, or `bind` is the state key that holds the shot name. The scene uses the
   last shot that shows, and it moves the camera to it with easing. The scene finds the framing from the bounds of what shows. */
Rupaka.block('shot', (b, ctx) => {
  const S = ctx.scene;
  if (!S) throw new Error('a shot must be inside a scene');
  const name = () => b.name ?? ctx.s.get(b.bind), node = Rupaka.el('li');
  ctx.s.on(() => { node.textContent = `The camera: ${name()}`; });
  return S.part(b, {name}, node);
});
