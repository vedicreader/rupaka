---
title: Easy-to-read 3D scenes
---

A 3D scene teaches well only when depth is part of the idea. This page gives the test for choosing a scene, the rules that make a scene easy to read, and the checks that `check` runs. The rules are also in the block manifests and in `demo_sp`, so the model reads each rule beside the block it uses.

## Choose 2D or 3D

Use a `scene` when the learner must see depth: a tilt, a turn about an axis, a globe, an orbit seen from Earth, a shape in space, or a flow round a circuit or a network. Use an `axis` with `point` and `plot` blocks when the idea happens in one plane.

| Idea | Use | Reason |
|---|---|---|
| Seasons from axial tilt | scene | The tilt of the axis against the orbit is the idea |
| Time zones | scene, `coords` globe | Sunlight falls on a turning ball |
| Phases of the Moon | scene, look sky | The phase depends on the view from Earth |
| Projectile range | axis and plot | The flight is in one vertical plane |
| Torque on a lever | axis, or a 2D diagram | The beam turns in one plane about one pivot |
| Vector addition | 2D | The vectors lie in one plane |

A 3D scene of a planar idea adds a camera that turns, parts that hide each other and empty space. It adds nothing that the learner needs.

The `throw-angle` gallery demo shows the 2D form. The flight is a `plot` on an `axis`. `ghost` keeps the last throw faint, so 30 degrees and 60 degrees show together.

## Make a scene easy to read

1. Give each step one new thing. Each line of `steps` says what is new in its step.
2. Show compared cases together. A scene about two angles shows both arcs in one step.
3. Make every part that the learner must see at least one twentieth of the scene across.
4. Draw each trajectory, orbit, route or wire as a `path`. A row of small bodies reads as dots.
5. Give each `force` an `on`: the body that the force acts on. The arrow then starts on that body.
6. Put the chip of a bright or large body beside the body with `at`. A chip over a sun is hard to read.
7. Choose the `shot` that faces the plane of the picture. A flat picture seen edge-on is a line.

The `sun-over-earth` and `panchangam-sky` gallery demos follow these rules.

## What `check` measures

`check` draws the demo in a headless browser in the light and the dark mode. It reports each text whose contrast is under the WCAG need. A chip over a scene is measured against the canvas pixels under it, not against the page colour. A repair prompt names the text, so the model fixes the part in place.

In the sky look a chip has a dark panel, so its text reads over a bright body. A body with `drag` has a grip that covers its disc on screen. An orbit grip writes an angle from 0 to under 360.
