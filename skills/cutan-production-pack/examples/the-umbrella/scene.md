# The Umbrella

A stranger at a dusk bus stop, a missed last bus, and one umbrella between two people.

```yaml meta
title: The Umbrella
fps: 24
resolution: {width: 1280, height: 720}
default_renderer: cutout
style_pack: dusk
closing_transition: {kind: fade, duration: 1.0, color: "#000000"}
```

## Shot title (cutout)

The title fades in word by word on a dark card.

```yaml shot
duration: 3.0
camera: {move: hold}
```

```yaml entities
- {kind: environment, id: card, store: environments, ref: title_card}
- {kind: prop, id: title, store: props, ref: title}
```

```yaml actions
- {kind: set, target: title/word_0, property: alpha, value: 0.0, at: 0.0}
- {kind: set, target: title/word_1, property: alpha, value: 0.0, at: 0.0}
- {kind: tween, target: title/word_0, property: alpha, from: 0.0, to: 1.0, duration: 0.6, start: 0.4}
- {kind: tween, target: title/word_1, property: alpha, from: 0.0, to: 1.0, duration: 0.6, start: 0.9}
```

## Shot arrival (cutout)

Wide. Mara waits by the shelter. Teo walks in from the left in profile, turns to face us, and greets her. She turns three-quarters toward him, unimpressed.

```yaml shot
duration: 9.0
camera: {move: hold}
transition: {kind: fade, duration: 0.6, color: "#000000"}
```

```yaml entities
- {kind: environment, id: set, store: environments, ref: bus_stop}
- {kind: character, id: mara, store: characters, ref: mara, stage: {at: [180, 200], scale: 1.0}}
- {kind: character, id: teo, store: characters, ref: teo, stage: {at: [-760, 200], scale: 1.1}}
```

```yaml actions
- {kind: set, target: teo, property: view, value: side, at: 0.0}
- {kind: play, target: mara, animation: idle_breath}
- {kind: play, target: teo, animation: walk, args: {distance: 560}, start: 0.3}
- {kind: play, target: teo, animation: turn, args: {to: front}, start: 3.0}
- {kind: play, target: teo, animation: hop, args: {height: 25}, start: 3.5}
- {kind: play, target: mara, animation: turn, args: {to: three_quarter, direction: left}, start: 5.6}
- {kind: expression, target: mara, preset: skeptical, intensity: 0.7, start: 5.8, duration: 3.2}
```

```dialogue
teo [happy] (at 3.6): Evening! Is this the stop for the number nine?
mara [skeptical] (pause 0.5): It was. Until about an hour ago.
```

## Shot regret (cutout)

Close on Mara. The camera pushes in slowly as it sinks in.

```yaml shot
duration: 4.0
camera: {move: push_in}
```

```yaml entities
- {kind: environment, id: set, store: environments, ref: bus_stop}
- {kind: character, id: mara, store: characters, ref: mara, stage: {at: [60, 680], scale: 2.8}}
```

```yaml actions
- {kind: set, target: mara, property: x, value: 60, at: 0.0}
- {kind: set, target: mara, property: y, value: 680, at: 0.0}
- {kind: set, target: mara, property: scale_y, value: 2.8, at: 0.0}
- {kind: set, target: mara, property: scale_x, value: -2.8, at: 0.0}
- {kind: set, target: mara, property: view, value: three_quarter, at: 0.0}
- {kind: expression, target: mara, preset: sad, intensity: 0.6, axes: {gaze_x: 0.5, gaze_y: 0.4}}
- {kind: play, target: mara, animation: nod, args: {count: 1, angle: 0.12}, start: 2.2}
```

```dialogue
mara [sad 0.6] (at 0.4): The last bus left without me.
```

## Shot offer (cutout)

Wide again. Teo produces an umbrella with a flourish and holds it out. Mara gives a startled little hop, then smiles despite herself.

```yaml shot
duration: 7.0
camera: {move: hold}
```

```yaml entities
- {kind: environment, id: set, store: environments, ref: bus_stop}
- {kind: character, id: mara, store: characters, ref: mara, stage: {at: [180, 200], scale: 1.0}}
- {kind: character, id: teo, store: characters, ref: teo, stage: {at: [-200, 200], scale: 1.1}}
- {kind: prop, id: umbrella, store: props, ref: umbrella, stage: {at: [-112, 118], scale: 0.6, after: teo}}
```

```yaml actions
- {kind: set, target: mara, property: x, value: 180, at: 0.0}
- {kind: set, target: mara, property: y, value: 200, at: 0.0}
- {kind: set, target: mara, property: scale_y, value: 1.0, at: 0.0}
- {kind: set, target: mara, property: scale_x, value: -1.0, at: 0.0}
- {kind: set, target: mara, property: view, value: three_quarter, at: 0.0}
- {kind: set, target: teo, property: x, value: -200, at: 0.0}
- {kind: set, target: teo, property: y, value: 200, at: 0.0}
- {kind: set, target: umbrella, property: scale_x, value: 0.0, at: 0.0}
- {kind: set, target: umbrella, property: scale_y, value: 0.0, at: 0.0}
- {kind: play, target: umbrella, animation: pop_in, start: 1.2}
- {kind: tween, target: teo/arm_r, property: rotation, to: -1.3, duration: 0.3, start: 1.0}
- {kind: play, target: mara, animation: hop, args: {height: 20}, start: 3.9}
- {kind: expression, target: mara, preset: happy, intensity: 0.6, start: 5.4}
```

```dialogue
teo [happy] (at 0.3): Then we walk! I brought an umbrella.
mara [amused] (pause 0.4): You brought... one umbrella.
```
